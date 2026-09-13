"""Cross-check Atlas traceroutes against RIS-observed neighbors (Validation Rule 1).

Resolves each traceroute hop to an ASN, collapses the result into an
AS-level path, and checks whether the AS immediately upstream of the
target ASN in that path also shows up as a RIS-observed neighbor (Phase
1a's `fishbowl.json`). Per task_plan.md's Validation Rules, an
ASN-to-ASN adjacency only counts as established once RIS and an Atlas
traceroute agree on it — this module is that agreement check, not a
full topology map yet (that needs many more measurements than the one
Phase 1b has produced so far).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from pacific_peering.analysis.fishbowl import DEFAULT_SUMMARY_PATH
from pacific_peering.analysis.ip_resolution_cache import DEFAULT_CACHE_PATH, IpResolutionCache
from pacific_peering.discovery.peeringdb import resolve_ip_via_netixlan
from pacific_peering.ris.ripestat import resolve_ip_to_asns

logger = logging.getLogger(__name__)

DEFAULT_ATLAS_PARSED_DIR = Path("data/atlas/parsed")
DEFAULT_TRIANGULATION_DIR = Path("data/analysis/triangulation")


@dataclass(frozen=True)
class HopResolution:
    """One traceroute hop resolved to whichever ASN(s) its address(es) belong to.

    An empty `asns` means neither resolver could identify an owner —
    genuinely unresolved (e.g. a private/CGNAT address), not necessarily
    an IXP fabric address, now that `resolve_ip_via_netixlan` already
    catches most of those (see `resolution_source`).
    """

    hop: int
    addresses: tuple[str, ...]
    asns: tuple[int, ...]
    resolution_source: str | None  # "bgp", "peeringdb_netixlan", or None


def _resolve_address(address: str, cache: IpResolutionCache) -> tuple[int | None, str | None]:
    """Resolve one address to (asn, source), trying BGP first, then PeeringDB netixlan.

    BGP-based resolution (`resolve_ip_to_asns`) is tried first since it
    covers the general internet; PeeringDB's netixlan lookup is the
    fallback specifically for IXP peering-LAN addresses, which are
    frequently *not* announced in global BGP at all and so resolve to
    nothing via the BGP path alone (discovered directly in loop tranche
    4: `103.26.68.83` resolved to no ASN via BGP, but PeeringDB's
    netixlan table correctly attributes it to AS45349).

    Results (including negative ones) are cached by IP across calls —
    the same backbone/IXP-fabric addresses recur across many
    measurements, and re-querying them every time is exactly what got
    this project rate-limited by PeeringDB in loop tranche 4.
    """
    cached = cache.get(address)
    if cached is not None:
        return cached

    bgp_asns = resolve_ip_to_asns(address)
    if len(bgp_asns) == 1:
        result = (bgp_asns[0], "bgp")
    elif not bgp_asns:
        netixlan_asn = resolve_ip_via_netixlan(address)
        result = (netixlan_asn, "peeringdb_netixlan") if netixlan_asn is not None else (None, None)
    else:
        result = (None, None)  # ambiguous (multiple BGP-announcing ASNs); don't guess

    cache.set(address, *result)
    return result


def resolve_traceroute_hops(
    hops: list[dict], cache_path: Path = DEFAULT_CACHE_PATH
) -> list[HopResolution]:
    """Resolve every hop's responding address(es) to an ASN.

    Args:
        hops: the `hops` list from one parsed Atlas traceroute record
            (each a dict with "hop" and "addresses").
        cache_path: Where to load/persist the IP-resolution cache.
    """
    cache = IpResolutionCache.load(cache_path)
    resolved: list[HopResolution] = []
    for hop in hops:
        addresses = tuple(hop.get("addresses", []))
        resolutions = [_resolve_address(address, cache) for address in addresses]
        asns = sorted({asn for asn, _source in resolutions if asn is not None})
        source = next((s for _asn, s in resolutions if s is not None), None)
        resolved.append(
            HopResolution(
                hop=hop["hop"], addresses=addresses, asns=tuple(asns), resolution_source=source
            )
        )
    cache.save()
    return resolved


@dataclass(frozen=True)
class AsHop:
    """One ASN in a resolved AS-level path, with its resolution provenance."""

    asn: int
    resolution_source: str
    contiguous_with_previous: bool  # False if 1+ unresolved hops sit between this and the prior entry


def extract_as_sequence(resolved_hops: list[HopResolution]) -> list[AsHop]:
    """Collapse resolved hops into an ordered AS-level path, tracking gaps.

    Unresolved or ambiguous (multi-ASN) hops don't appear in the output,
    but they do mark the *next* resolved entry as non-contiguous with the
    previous one — this distinction matters because a "last resolved ASN
    before target" is only a real adjacency claim when there was no gap;
    across a gap (e.g. an unresolvable IXP fabric hop, or one PeeringDB
    also can't attribute), the true intermediate AS is simply unknown,
    and treating the two sides as directly adjacent would overclaim.
    """
    sequence: list[AsHop] = []
    gap_pending = False
    for hop in resolved_hops:
        if len(hop.asns) != 1:
            gap_pending = True
            continue
        asn = hop.asns[0]
        if sequence and sequence[-1].asn == asn:
            continue  # same-AS repeat hop; not a new entry, doesn't clear/set gap state
        sequence.append(
            AsHop(
                asn=asn,
                resolution_source=hop.resolution_source or "unknown",
                contiguous_with_previous=not gap_pending,
            )
        )
        gap_pending = False
    return sequence


def check_neighbor_agreement(
    as_sequence: list[AsHop], target_asn: int, fishbowl_path: Path = DEFAULT_SUMMARY_PATH
) -> dict:
    """Check whether the traceroute-observed upstream of `target_asn` is a RIS neighbor too.

    Args:
        as_sequence: Resolved AS-level path from `extract_as_sequence`.
        target_asn: The ASN the traceroute was aimed at.
        fishbowl_path: Path to Phase 1a's `fishbowl.json` (RIS-observed neighbors).

    Returns:
        A dict recording the traceroute-observed upstream ASN (if any),
        whether it was a *contiguous* hop (no unresolved gap in between —
        see `extract_as_sequence`) or just the nearest resolved ASN across
        a gap, and whether RIS independently observed it as a neighbor.
    """
    fishbowl = json.loads(fishbowl_path.read_text())
    ris_neighbors = fishbowl.get(str(target_asn), {}).get("neighbors", {})
    asns = [entry.asn for entry in as_sequence]

    if target_asn not in asns:
        # Common in practice: the traceroute goes dark before a hop
        # actually resolves to target_asn (ICMP filtering near the
        # destination is normal). The last ASN we *did* resolve is still
        # meaningful — if RIS independently lists it as a neighbor of
        # target_asn, that's real corroboration of "traffic got to the
        # right neighborhood," just weaker than a direct hit.
        if not as_sequence:
            return {
                "traceroute_upstream_asn": None,
                "ris_agrees": False,
                "note": "no traceroute hops resolved to any ASN",
            }
        last = as_sequence[-1]
        ris_count = ris_neighbors.get(str(last.asn))
        return {
            "traceroute_upstream_asn": last.asn,
            "contiguous": last.contiguous_with_previous,
            "resolution_source": last.resolution_source,
            "ris_agrees": ris_count is not None,
            "ris_observation_count": ris_count,
            "note": (
                "target ASN never resolved (likely ICMP filtering near destination); "
                "comparing RIS against the last ASN the traceroute did reach"
            ),
        }

    target_index = asns.index(target_asn)
    if target_index == 0:
        return {
            "traceroute_upstream_asn": None,
            "ris_agrees": False,
            "note": "target ASN was the first resolved hop; no upstream to compare",
        }

    target_entry = as_sequence[target_index]
    upstream = as_sequence[target_index - 1]
    ris_count = ris_neighbors.get(str(upstream.asn))
    result = {
        "traceroute_upstream_asn": upstream.asn,
        "contiguous": target_entry.contiguous_with_previous,
        "resolution_source": upstream.resolution_source,
        "ris_agrees": ris_count is not None,
        "ris_observation_count": ris_count,
    }
    if not target_entry.contiguous_with_previous:
        result["note"] = (
            "one or more unresolved hops sit between this ASN and the target; "
            "true adjacency is not confirmed by the traceroute alone"
        )
    return result


def analyze_measurement(
    measurement_id: int,
    target_asn: int,
    atlas_parsed_dir: Path = DEFAULT_ATLAS_PARSED_DIR,
    fishbowl_path: Path = DEFAULT_SUMMARY_PATH,
    output_dir: Path = DEFAULT_TRIANGULATION_DIR,
) -> dict:
    """Run the RIS/Atlas agreement check for every probe in one measurement and persist it."""
    parsed_path = atlas_parsed_dir / f"{measurement_id}.json"
    traceroutes = json.loads(parsed_path.read_text())

    per_probe = []
    for traceroute in traceroutes:
        resolved_hops = resolve_traceroute_hops(traceroute["hops"])
        as_sequence = extract_as_sequence(resolved_hops)
        agreement = check_neighbor_agreement(as_sequence, target_asn, fishbowl_path)
        as_sequence_json = [
            {
                "asn": entry.asn,
                "resolution_source": entry.resolution_source,
                "contiguous_with_previous": entry.contiguous_with_previous,
            }
            for entry in as_sequence
        ]
        per_probe.append(
            {"probe_id": traceroute["probe_id"], "as_sequence": as_sequence_json, **agreement}
        )

    result = {"measurement_id": measurement_id, "target_asn": target_asn, "probes": per_probe}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{measurement_id}.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Defaults to Phase 1b's first live measurement (Guam -> PNG DataCo).
    result = analyze_measurement(measurement_id=210901499, target_asn=17828)
    for probe in result["probes"]:
        logger.info(
            "Probe %s: AS-sequence=%s upstream-of-target=%s RIS-agrees=%s",
            probe["probe_id"],
            probe["as_sequence"],
            probe.get("traceroute_upstream_asn"),
            probe.get("ris_agrees"),
        )


if __name__ == "__main__":
    main()
