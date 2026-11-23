"""Weekly Globalping traceroutes for Solomon Islands (SB) corridors. Report only.

Per the project owner (2026-11-23): RIPE Atlas had no connected SB probe,
but Globalping's SATSOL (AS132468) probe in Honiara was verified that day
(private hops, then SISCC AS139609 at 0.5 ms, then IX Australia NSW at
38 ms). "Use all Globalping probes" was settled as every Globalping probe in
the in-scope economies, found fresh each run, so:

- every SB probe traces to every in-scope target ASN (domestic SB -> SB and
  outbound SB -> other economies), and
- every other in-scope probe also traces to each SB target ASN (inbound).

One measurement per target ASN covers all its sources. Target addresses come
from `atlas.targets.list_target_ips`, so pins and `EXCLUDED_TARGET_PREFIXES`
(SATSOL's Sydney-hosted 103.188.182.0/23 among them) apply as they do for
Atlas. Traces are ICMP, the Atlas default.

Nothing here files findings or escalations: Globalping results are not Atlas
results (no MPLS label data, no stable probe IDs, probe locations come from IP
geolocation). The report flags any trace faster than fibre allows, because
that means the probe or the target is not where it is labelled. Runs
Wednesdays from `scripts/nightly_corridor_testing.sh`.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

from pacific_peering.analysis.corridor_backlog import EXTERNAL_NON_CANDIDATE_ASNS
from pacific_peering.analysis.feasibility import great_circle_km, min_feasible_rtt_ms
from pacific_peering.analysis.fishbowl import DEFAULT_SUMMARY_PATH
from pacific_peering.analysis.traceroute_topology import extract_as_sequence, resolve_traceroute_hops
from pacific_peering.atlas.targets import list_target_ips
from pacific_peering.discovery.economy_coordinates import ECONOMY_LATLON, ECONOMY_SPREAD_KM
from pacific_peering.discovery.quarantined_asns import QUARANTINED_ASN_SET
from pacific_peering.globalping import client
from pacific_peering.globalping.sb_report import diff_snapshots, load_last_snapshot, render_report

logger = logging.getLogger(__name__)

SB = "SB"
REPORT_PATH = Path("outputs/reports/globalping_sb.txt")
HISTORY_PATH = Path("outputs/reports/globalping_sb_history.jsonl")
RAW_DIR = Path("data/globalping/raw")
# Under the 250-tests-an-hour unauthenticated limit, leaving room for a manual check.
DEFAULT_TEST_BUDGET = 240
MAX_PROBES_PER_MEASUREMENT = 50


@dataclass(frozen=True)
class ProbeGroup:
    """The Globalping probes on one network in one economy (no stable probe IDs exist)."""

    cc: str
    asn: int
    network: str
    cities: tuple[str, ...]
    count: int

    def location(self) -> dict:
        return {"country": self.cc, "asn": self.asn, "limit": self.count}

    @property
    def label(self) -> str:
        return f"{self.cc} AS{self.asn} {self.network} ({', '.join(self.cities)}) x{self.count}"


@dataclass(frozen=True)
class Target:
    asn: int
    cc: str
    ip: str


@dataclass(frozen=True)
class Planned:
    """One measurement: every source group tracing to one target."""

    target: Target
    sources: tuple[ProbeGroup, ...]

    @property
    def tests(self) -> int:
        return sum(g.count for g in self.sources)


def _skip_reason(asn: int, asn_to_cc: dict[int, str]) -> str | None:
    """Why a probe's network can't be an in-economy source, matching `corridor_backlog`'s source filter."""
    if asn in EXTERNAL_NON_CANDIDATE_ASNS:
        return "does not egress locally"
    if asn in QUARANTINED_ASN_SET:
        return "quarantined ASN"
    if asn not in asn_to_cc:
        return "ASN not in the in-scope registry"
    return None


def pacific_probe_groups(probes: list[dict], asn_to_cc: dict[int, str]) -> tuple[list[ProbeGroup], list[str]]:
    """Group probes in in-scope economies by (economy, ASN). Returns (groups, skipped notes).

    A probe whose ASN is external (Starlink, Zscaler, Renater), quarantined,
    or outside the registry is skipped and named in the report: Globalping's
    IP geolocation alone doesn't make it a local vantage point.
    """
    in_scope_ccs = set(asn_to_cc.values())
    by_key: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for probe in probes:
        loc = probe.get("location") or {}
        if loc.get("country") in in_scope_ccs and loc.get("asn") is not None:
            by_key[(loc["country"], int(loc["asn"]))].append(loc)
    groups: list[ProbeGroup] = []
    skipped: list[str] = []
    for (cc, asn), locs in sorted(by_key.items()):
        cities = tuple(sorted({loc.get("city") or "?" for loc in locs}))
        group = ProbeGroup(cc, asn, locs[0].get("network") or "?", cities, len(locs))
        reason = _skip_reason(asn, asn_to_cc)
        if reason is None:
            groups.append(group)
        else:
            skipped.append(f"{group.label}: {reason}")
    return groups, skipped


def load_targets(fishbowl_path: Path = DEFAULT_SUMMARY_PATH) -> tuple[list[Target], list[str]]:
    """In-scope target ASNs, filtered as `corridor_backlog` does. Returns (targets, unusable notes)."""
    fishbowl = json.loads(fishbowl_path.read_text())
    targets: list[Target] = []
    unusable: list[str] = []
    for key, entry in sorted(fishbowl.items(), key=lambda kv: (kv[1]["economy"]["cc"], int(kv[0]))):
        asn = int(key)
        if asn in EXTERNAL_NON_CANDIDATE_ASNS or asn in QUARANTINED_ASN_SET:
            continue
        if entry.get("num_distinct_prefixes", 0) <= 0:
            continue
        try:
            ip = list_target_ips(asn)[0]
        except (FileNotFoundError, ValueError) as exc:
            unusable.append(f"AS{asn}: no target address ({exc})")
            continue
        targets.append(Target(asn, entry["economy"]["cc"], ip))
    return targets, unusable


def plan_measurements(groups: list[ProbeGroup], targets: list[Target]) -> list[Planned]:
    """SB targets first (domestic + inbound in one measurement each), then SB outbound to the rest."""
    sb_groups = [g for g in groups if g.cc == SB]
    other_groups = [g for g in groups if g.cc != SB]
    plan: list[Planned] = []
    for target in sorted(targets, key=lambda t: (t.cc != SB, t.cc, t.asn)):
        sources = [g for g in sb_groups if g.asn != target.asn]
        if target.cc == SB:
            sources += other_groups
        if not sources:
            continue
        if sum(g.count for g in sources) > MAX_PROBES_PER_MEASUREMENT:
            logger.warning("AS%d: more than %d source probes; trimming", target.asn, MAX_PROBES_PER_MEASUREMENT)
            while sum(g.count for g in sources) > MAX_PROBES_PER_MEASUREMENT:
                sources.pop()
        if not sources:
            # Never POST empty locations: Globalping would pick a random probe anywhere.
            continue
        plan.append(Planned(target, tuple(sources)))
    return plan


def fire(plan: list[Planned], budget: int) -> tuple[list[tuple[Planned, str]], list[str]]:
    """Create the planned measurements in order within the test budget and the rate limit.

    A measurement too big for what's left is skipped and smaller ones after
    it still run. A 429, a connection failure or a timeout stops the run: the
    rest would fail the same way, and a timed-out POST may still have spent
    tests. Returns ([(planned, measurement_id)], [notes on targets not measured]).
    """
    fired: list[tuple[Planned, str]] = []
    unmeasured: list[str] = []
    spent = 0
    remaining: int | None = None
    for index, planned in enumerate(plan):
        t = planned.target
        if planned.tests > budget - spent:
            unmeasured.append(f"AS{t.asn} ({t.cc}): test budget used up")
            continue
        if remaining is not None and planned.tests > remaining:
            unmeasured.append(f"AS{t.asn} ({t.cc}): Globalping rate limit")
            continue
        try:
            created = client.create_measurement(t.ip, [g.location() for g in planned.sources])
        except client.RateLimited:
            unmeasured += [f"AS{p.target.asn} ({p.target.cc}): Globalping rate limit" for p in plan[index:]]
            break
        except (requests.ConnectionError, requests.Timeout) as exc:
            unmeasured += [f"AS{p.target.asn} ({p.target.cc}): network error ({type(exc).__name__})"
                           for p in plan[index:]]
            break
        except requests.RequestException as exc:
            unmeasured.append(f"AS{t.asn} ({t.cc}): not created ({exc})")
            continue
        spent += planned.tests
        remaining = created.rate_limit_remaining
        fired.append((planned, created.measurement_id))
    return fired, unmeasured


def to_parsed_hops(gp_hops: list[dict]) -> list[dict]:
    """Globalping hops in the parsed-Atlas shape `resolve_traceroute_hops` reads."""
    parsed = []
    for number, hop in enumerate(gp_hops, start=1):
        address = hop.get("resolvedAddress")
        rtts = [t["rtt"] for t in hop.get("timings") or [] if t.get("rtt") is not None]
        parsed.append({"hop": number, "addresses": [address] if address else [],
                       "min_rtt_ms": min(rtts) if rtts else None})
    return parsed


def fibre_floor_ms(probe_loc: dict, target_cc: str) -> float:
    """RTT floor from the probe's claimed position to the nearest edge of the target economy."""
    if target_cc == probe_loc["country"] or target_cc not in ECONOMY_LATLON:
        return 0.0
    km = great_circle_km(probe_loc["latitude"], probe_loc["longitude"], *ECONOMY_LATLON[target_cc])
    return min_feasible_rtt_ms(max(0.0, km - ECONOMY_SPREAD_KM.get(target_cc, 0.0)))


def analyse_result(target: Target, result: dict) -> dict:
    """One probe's trace, summarised for the report and history."""
    loc = result["probe"]
    hops = to_parsed_hops(result["result"].get("hops") or [])
    resolved = resolve_traceroute_hops(hops)
    answered = [h for h in hops if h["addresses"]]
    reached = next((h for h in answered if target.ip in h["addresses"]), None)
    last = answered[-1] if answered else None
    floor = fibre_floor_ms(loc, target.cc)
    rtt = reached["min_rtt_ms"] if reached else None
    return {
        "src_cc": loc["country"], "src_asn": int(loc["asn"]), "src_city": loc.get("city") or "?",
        "target_cc": target.cc, "target_asn": target.asn, "target_ip": target.ip,
        "status": result["result"].get("status"),
        "reached": reached is not None, "rtt_ms": rtt,
        "last_address": last["addresses"][0] if last and not reached else None,
        "last_rtt_ms": last["min_rtt_ms"] if last and not reached else None,
        "hops": len(hops),
        "as_path": [entry.asn for entry in extract_as_sequence(resolved)],
        "ixps": [{"hop": h.hop, "name": h.ixp_context.get("name"), "in_fishbowl": h.ixp_context.get("in_fishbowl"),
                  "rtt_ms": hops[h.hop - 1]["min_rtt_ms"]} for h in resolved if h.ixp_context],
        "floor_ms": round(floor, 1),
        "below_floor": rtt is not None and floor > 0 and rtt < floor,
    }


def collect(fired: list[tuple[Planned, str]], raw_dir: Path = RAW_DIR) -> tuple[list[dict], list[str]]:
    """Wait for every measurement, save the raw JSON, and summarise each probe's trace.

    Returns (traces, notes). A measurement never fetched, or a result that
    can't be parsed, becomes a note instead of stopping the run: by now the
    tests are spent, and the rest of the week's results must still be recorded.
    """
    measurements = client.wait_for_all([mid for _planned, mid in fired])
    raw_dir.mkdir(parents=True, exist_ok=True)
    traces: list[dict] = []
    notes: list[str] = []
    for planned, measurement_id in fired:
        t = planned.target
        measurement = measurements.get(measurement_id)
        if measurement is None:
            notes.append(f"AS{t.asn} ({t.cc}): results not collected ({measurement_id})")
            continue
        (raw_dir / f"{measurement_id}.json").write_text(json.dumps(measurement, indent=1) + "\n")
        for result in measurement.get("results") or []:
            try:
                trace = analyse_result(t, result)
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Globalping %s: unparseable result skipped: %r", measurement_id, exc)
                notes.append(f"AS{t.asn} ({t.cc}): one result unparseable ({measurement_id}: {exc!r})")
                continue
            trace["measurement_id"] = measurement_id
            traces.append(trace)
    return traces, notes


def run(fire_measurements: bool, budget: int = DEFAULT_TEST_BUDGET, now: datetime | None = None,
        asn_registry_path: Path = Path("data/asn_registry.json")) -> dict:
    """Plan (and with `fire_measurements`, run and record) this week's SB corridor traces."""
    now = now or datetime.now(timezone.utc)
    registry = json.loads(asn_registry_path.read_text())
    asn_to_cc = {asn: cc for cc, entry in registry.items() for asn in entry["asns"]}
    groups, skipped = pacific_probe_groups(client.fetch_probes(), asn_to_cc)
    targets, unusable = load_targets()
    plan = plan_measurements(groups, targets)
    logger.info("Globalping SB: %d probe groups (%d SB), %d targets, %d measurements, %d tests planned",
                len(groups), sum(g.cc == SB for g in groups), len(targets), len(plan),
                sum(p.tests for p in plan))
    if not any(g.cc == SB for g in groups):
        logger.warning("No Globalping probe in SB today; only inbound traces are possible")
    if not fire_measurements:
        for g in groups:
            logger.info("  %s", g.label)
        logger.info("Dry run -- pass --fire to run the traceroutes (Globalping tests, no Atlas credits)")
        return {"plan": plan}
    fired, unmeasured = fire(plan, budget)
    traces, collect_notes = collect(fired)
    snapshot = {
        "date": now.date().isoformat(),
        "probe_groups": [g.label for g in groups],
        "skipped_probes": skipped,
        "measurement_ids": [mid for _planned, mid in fired],
        "tests": sum(planned.tests for planned, _mid in fired),
        "unmeasured": unusable + unmeasured + collect_notes,
        "traces": traces,
    }
    report = render_report(snapshot, diff_snapshots(load_last_snapshot(HISTORY_PATH), snapshot), asn_to_cc)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report)
    if not traces:
        # An empty week must not become the baseline the next diff compares against.
        logger.warning("Globalping SB: no traces this run; report written, history not appended")
        return snapshot
    with HISTORY_PATH.open("a") as f:
        f.write(json.dumps(snapshot) + "\n")
    logger.info("Globalping SB: %d traces from %d measurements -> %s", len(traces), len(fired), REPORT_PATH)
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fire", action="store_true", help="run the traceroutes (Globalping tests) and record")
    parser.add_argument("--budget", type=int, default=DEFAULT_TEST_BUDGET,
                        help=f"most Globalping tests to spend (default {DEFAULT_TEST_BUDGET}; limit 250/hour)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(fire_measurements=args.fire, budget=args.budget)


if __name__ == "__main__":
    main()
