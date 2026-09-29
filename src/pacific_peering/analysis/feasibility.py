"""Latency/hop-count feasibility checks (Validation Rule 2).

A two-source (RIS + Atlas) agreement on an adjacency still isn't enough
to report per task_plan.md's Validation Rules — the observed RTT has to
be physically plausible for the claimed path. This module computes the
speed-of-light-in-fiber floor for a great-circle distance, and compares
observed RTT against both a direct path and a named detour path, so a
finding like "Guam -> PNG detours via Sydney" can be checked against real
numbers instead of asserted from IXP membership alone.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_ATLAS_PARSED_DIR = Path("data/atlas/parsed")
DEFAULT_OUTPUT_DIR = Path("data/analysis/feasibility")

# Refractive index of typical single-mode fiber puts signal propagation at
# roughly 2/3 c. This is a floor, not an estimate: real paths are never
# faster than this, only slower (routing, queueing, processing all add
# delay, never subtract it).
_SPEED_OF_LIGHT_KM_S = 299_792.458
_FIBER_SPEED_KM_S = _SPEED_OF_LIGHT_KM_S * 2 / 3

# Approximate reference points for named locations used in this project's
# feasibility checks (city-level, not exact endpoint geolocation, since we
# usually only know the destination's economy/city, not its precise site).
REFERENCE_POINTS_LATLON: dict[str, tuple[float, float]] = {
    "Guam": (13.4443, 144.7937),
    "Port Moresby": (-9.4438, 147.1803),
    "Sydney": (-33.8688, 151.2093),
}


def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine great-circle distance between two lat/lon points, in km."""
    earth_radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * earth_radius_km * math.asin(math.sqrt(a))


def min_feasible_rtt_ms(distance_km: float) -> float:
    """Minimum physically possible round-trip time for a given one-way distance.

    This is a floor: an observed RTT below this value would mean the
    measurement is wrong (impossible), not that the path is unusually
    fast. It says nothing about the upper bound — real paths are almost
    always well above this floor due to routing, queueing, and processing.
    """
    one_way_seconds = distance_km / _FIBER_SPEED_KM_S
    return one_way_seconds * 2 * 1000


def check_path_feasibility(
    observed_rtt_ms: float,
    source_lat: float,
    source_lon: float,
    target_lat: float,
    target_lon: float,
) -> dict:
    """Compare an observed RTT against the direct-path physical floor.

    Returns:
        A dict with the great-circle distance, the physical RTT floor,
        the observed RTT, whether the observation is physically possible
        (`feasible`), and how many multiples of the floor the observed
        RTT represents (`excess_ratio`) — a high ratio doesn't prove a
        detour by itself, but is consistent with one and worth explaining.
    """
    distance_km = great_circle_km(source_lat, source_lon, target_lat, target_lon)
    floor_ms = min_feasible_rtt_ms(distance_km)
    return {
        "distance_km": round(distance_km, 1),
        "min_feasible_rtt_ms": round(floor_ms, 2),
        "observed_rtt_ms": observed_rtt_ms,
        "feasible": observed_rtt_ms >= floor_ms,
        "excess_ratio": round(observed_rtt_ms / floor_ms, 2) if floor_ms > 0 else None,
    }


def compare_direct_vs_relay(
    observed_rtt_ms: float,
    source_latlon: tuple[float, float],
    target_latlon: tuple[float, float],
    relay_latlon: tuple[float, float],
) -> dict:
    """Check observed RTT against a direct path and a named single-relay detour.

    Useful for a concrete question like "does this RTT look more like a
    direct path, or a path via a specific relay point (e.g. Sydney)?" —
    the relay distance is computed as source->relay->target, a rough but
    physically grounded proxy for "goes via that city" rather than a
    literal claim about the fiber route.
    """
    direct = check_path_feasibility(observed_rtt_ms, *source_latlon, *target_latlon)
    relay_distance_km = great_circle_km(*source_latlon, *relay_latlon) + great_circle_km(
        *relay_latlon, *target_latlon
    )
    relay_floor_ms = min_feasible_rtt_ms(relay_distance_km)
    return {
        "direct": direct,
        "via_relay": {
            "relay_distance_km": round(relay_distance_km, 1),
            "min_feasible_rtt_ms": round(relay_floor_ms, 2),
            "observed_rtt_ms": observed_rtt_ms,
            "feasible": observed_rtt_ms >= relay_floor_ms,
            "excess_ratio": round(observed_rtt_ms / relay_floor_ms, 2) if relay_floor_ms > 0 else None,
        },
    }


VERDICT_OK = "ok"
VERDICT_IMPOSSIBLE = "impossible"  # observed RTT below the physical floor
VERDICT_NO_HOP = "no_hop"  # the path never showed the hop this check needs


def _rtt_check(rtt_ms: float | None, hop: int | None, distance_km: float) -> dict:
    floor = min_feasible_rtt_ms(distance_km)
    if rtt_ms is None:
        return {"verdict": VERDICT_NO_HOP, "hop": hop, "floor_ms": round(floor, 2)}
    return {
        "verdict": VERDICT_OK if rtt_ms >= floor else VERDICT_IMPOSSIBLE,
        "hop": hop,
        "rtt_ms": rtt_ms,
        "floor_ms": round(floor, 2),
        "ratio": round(rtt_ms / floor, 2) if floor > 0 else None,
    }


def check_detour_trace(
    traceroute: dict,
    resolved_hops: list,
    source_latlon: tuple[float, float],
    hub_latlon: tuple[float, float],
    hub_city: str,
    target_latlon: tuple[float, float],
    ix_city: dict[int, str],
    source_spread_km: float = 0.0,
    target_spread_km: float = 0.0,
) -> dict:
    """Validation Rule 2 for one probe's trace of a claimed detour via `hub_city`.

    Two floors, both hard physical lower bounds (fibre at ~2/3 c):

    - hub: the first hop on an IXP LAN whose city is `hub_city` must show at
      least the source->hub floor. Below it, that router can't be in the hub
      city (wrong registry city, or a remote-peering/fabric extension), so
      the detour claim rests on a mislocated hop.
    - target: the hop where the trace *reached its target address* must show
      at least the source->hub->target floor. Below it, the path can't have
      gone via the hub. Only the destination itself counts: any other
      target-ASN router may be that network's own PoP near the source or
      the hub (e.g. a Fiji carrier's Sydney router), and hop 255 can come
      from one (code review, 2026-09-29). A trace that didn't reach the
      target, or has no recorded target, isn't checked. The direct
      source->target floor is reported alongside.

    Distances shrink by each end's `*_spread_km` (capital to farthest
    inhabited island, `economy_coordinates.ECONOMY_SPREAD_KM`), since the
    coordinates are capital-city level and the floor must stay a lower bound
    wherever the probe or target really is. Hops with more than one address
    (ECMP) never supply an RTT: `min_rtt_ms` is the minimum across all of
    them, so it may not belong to the router being checked.

    Cumulative RTTs only ever overstate a segment, so neither check can
    false-flag a slow path; a high RTT is never evidence against the claim.
    `resolved_hops` are `traceroute_topology.resolve_traceroute_hops` output
    for this trace; `ix_city` maps IXP id to its registry city.
    """
    single = {h["hop"]: h.get("min_rtt_ms") for h in traceroute["hops"] if len(h.get("addresses", [])) == 1}
    hub_hop = next(
        (h.hop for h in resolved_hops
         if h.ixp_context is not None and ix_city.get(h.ixp_context.get("ix_id")) == hub_city),
        None,
    )
    target = traceroute.get("target")
    target_hop = next(
        (h["hop"] for h in traceroute["hops"] if target is not None and target in h.get("addresses", [])), None
    )
    src_hub_km = max(0.0, great_circle_km(*source_latlon, *hub_latlon) - source_spread_km)
    hub_tgt_km = max(0.0, great_circle_km(*hub_latlon, *target_latlon) - target_spread_km)
    direct_km = max(0.0, great_circle_km(*source_latlon, *target_latlon) - source_spread_km - target_spread_km)
    return {
        "probe_id": traceroute["probe_id"],
        "hub": _rtt_check(single.get(hub_hop), hub_hop, src_hub_km),
        "target_via_hub": _rtt_check(single.get(target_hop), target_hop, src_hub_km + hub_tgt_km),
        "target_direct": _rtt_check(single.get(target_hop), target_hop, direct_km),
    }


VERDICT_MIXED = "mixed"  # some probes consistent with the claim, others not
_CLAIM_CHECKS = ("hub", "target_via_hub")


def probe_verdict(check: dict) -> str:
    """One probe: impossible if it breaks either floor, ok if it passed one, else no_hop."""
    verdicts = {check[c]["verdict"] for c in _CLAIM_CHECKS}
    if VERDICT_IMPOSSIBLE in verdicts:
        return VERDICT_IMPOSSIBLE
    return VERDICT_OK if VERDICT_OK in verdicts else VERDICT_NO_HOP


def claim_probes(checks: list[dict]) -> list[dict]:
    """The probes a detour claim rests on, from one measurement's checks.

    If any probe actually crossed the hub IXP, only those: country-sourced
    measurements mix source ASNs, and a probe that went direct (e.g. GU
    AS152735 via Guam IX while AS3605 detours via Tokyo) doesn't contradict
    the probes that detoured. If none did (a hub inferred from carrier
    chains, as on hand-filed findings), the claim covers every probe.
    """
    # By hop, not verdict: a hub hop with no usable RTT still shows the probe
    # crossed it, and must not let direct-routing probes in (code review).
    crossed = [c for c in checks if c["hub"]["hop"] is not None]
    return crossed or checks


def claim_verdict(checks: list[dict]) -> str:
    """ok / impossible / mixed across claim probes; no_hop if none was checkable."""
    verdicts = {probe_verdict(c) for c in checks} - {VERDICT_NO_HOP}
    if not verdicts:
        return VERDICT_NO_HOP
    return verdicts.pop() if len(verdicts) == 1 else VERDICT_MIXED


def analyze_measurement_feasibility(
    measurement_id: int,
    source_point: str,
    target_point: str,
    relay_point: str,
    atlas_parsed_dir: Path = DEFAULT_ATLAS_PARSED_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict:
    """Run the direct-vs-relay feasibility check for every probe in a measurement.

    Uses each traceroute's last hop that actually returned an address as
    the observed RTT — the closest real sample to true end-to-end delay
    we have without a guaranteed reply from the exact destination.

    Args:
        measurement_id: An Atlas measurement with parsed results already
            on disk (see `atlas.smoketest` / `atlas.client`).
        source_point, target_point, relay_point: Keys into
            `REFERENCE_POINTS_LATLON`.
    """
    parsed_path = atlas_parsed_dir / f"{measurement_id}.json"
    traceroutes = json.loads(parsed_path.read_text())
    source_latlon = REFERENCE_POINTS_LATLON[source_point]
    target_latlon = REFERENCE_POINTS_LATLON[target_point]
    relay_latlon = REFERENCE_POINTS_LATLON[relay_point]

    per_probe = []
    for traceroute in traceroutes:
        responsive_hops = [h for h in traceroute["hops"] if h["addresses"]]
        if not responsive_hops:
            continue
        last_hop = responsive_hops[-1]
        comparison = compare_direct_vs_relay(
            last_hop["min_rtt_ms"], source_latlon, target_latlon, relay_latlon
        )
        per_probe.append(
            {
                "probe_id": traceroute["probe_id"],
                "last_responsive_hop": last_hop["hop"],
                "last_responsive_addresses": last_hop["addresses"],
                **comparison,
            }
        )

    result = {
        "measurement_id": measurement_id,
        "source_point": source_point,
        "target_point": target_point,
        "relay_point": relay_point,
        "probes": per_probe,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{measurement_id}.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Defaults to Phase 1b's first live measurement (Guam -> PNG DataCo),
    # checked against the Sydney-relay hypothesis from Phase 1a/1d.
    result = analyze_measurement_feasibility(
        measurement_id=210901499,
        source_point="Guam",
        target_point="Port Moresby",
        relay_point="Sydney",
    )
    for probe in result["probes"]:
        logger.info(
            "Probe %s: observed=%.1fms direct_excess=%sx via_%s_excess=%sx",
            probe["probe_id"],
            probe["direct"]["observed_rtt_ms"],
            probe["direct"]["excess_ratio"],
            result["relay_point"],
            probe["via_relay"]["excess_ratio"],
        )


if __name__ == "__main__":
    main()
