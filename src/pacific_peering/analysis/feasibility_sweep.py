"""Report-only Validation Rule 2 sweep over every existing confirmed detour.

Per the project owner (2026-09-29): before wiring the feasibility check into
nightly classification, run it once over the corpus and read the results.
Changes nothing in the findings store; writes
`outputs/reports/feasibility_sweep.txt` and the per-probe detail to
`data/analysis/feasibility/sweep.json`.

For each `confirmed_detour` finding and each corroborating measurement, every
probe's trace is checked with `feasibility.check_detour_trace`. The vantage
point is the probe's live economy from the probe listing (a finding's stored
vantage label has been wrong before -- see `auto_classify._original_vantage`),
falling back to the corroboration's label for probes no longer listed.
Coordinates are capital-city level, so every distance is shrunk by each
economy's spread (`economy_coordinates.ECONOMY_SPREAD_KM`) to keep floors
conservative; the target floor applies only where a trace reached its target.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

from pacific_peering.analysis import store as _store
from pacific_peering.analysis.auto_classify import NON_LOCAL_FIRST_HOP_ASNS
from pacific_peering.analysis.feasibility import (
    DEFAULT_ATLAS_PARSED_DIR,
    DEFAULT_OUTPUT_DIR,
    VERDICT_IMPOSSIBLE,
    VERDICT_MIXED,
    VERDICT_NO_HOP,
    check_detour_trace,
    claim_probes,
    claim_verdict,
)
from pacific_peering.analysis.ixp_lan_registry import DEFAULT_REGISTRY_PATH, load_ixp_lan_registry
from pacific_peering.analysis.traceroute_topology import extract_as_sequence, resolve_traceroute_hops
from pacific_peering.atlas.probes import load_probe_listing
from pacific_peering.discovery.economy_coordinates import ECONOMY_LATLON, ECONOMY_SPREAD_KM, EXTERNAL_HUB_LATLON

logger = logging.getLogger(__name__)

REPORT_PATH = Path("outputs/reports/feasibility_sweep.txt")
DETAIL_PATH = DEFAULT_OUTPUT_DIR / "sweep.json"
_CHECKS = ("hub", "target_via_hub")


def finding_verdict(probe_results: list[dict]) -> str:
    """Across all measurements' claim probes: ok / impossible / mixed, or unchecked."""
    verdict = claim_verdict(probe_results)
    return "unchecked" if verdict == VERDICT_NO_HOP else verdict


def sweep(parsed_dir: Path = DEFAULT_ATLAS_PARSED_DIR) -> list[dict]:
    listing = load_probe_listing()
    probe_cc = {p["id"]: cc for cc, probes in listing.items() for p in probes}
    ix_city = {ix_id: e.city for ix_id, e in load_ixp_lan_registry(DEFAULT_REGISTRY_PATH).items()}
    conn = _store.connect()
    results = []
    try:
        for finding in _store.all_findings(conn):
            if finding.kind != _store.KIND_CONFIRMED_DETOUR:
                continue
            row = {"finding": finding.id, "source_cc": finding.source_cc, "target_cc": finding.target_cc,
                   "target_asn": finding.target_asn, "hub": finding.detour_hub, "probes": [], "skipped": None}
            results.append(row)
            if finding.detour_hub not in EXTERNAL_HUB_LATLON or finding.target_cc not in ECONOMY_LATLON:
                row["skipped"] = f"no coordinates for hub {finding.detour_hub!r} / target {finding.target_cc}"
                continue
            seen: set[int] = set()  # one corroboration row per probe, so measurements repeat
            for corrob in _store.get_corroborations(conn, finding.id):
                if corrob.measurement_id in seen:
                    continue
                seen.add(corrob.measurement_id)
                path = parsed_dir / f"{corrob.measurement_id}.json"
                if not path.exists():
                    continue
                checks = []
                for trace in json.loads(path.read_text()):
                    cc = probe_cc.get(trace["probe_id"], corrob.vantage_point_cc)
                    resolved = resolve_traceroute_hops(trace["hops"], persist=False)
                    sequence = extract_as_sequence(resolved)
                    if cc not in ECONOMY_LATLON or (sequence and sequence[0].asn in NON_LOCAL_FIRST_HOP_ASNS):
                        continue  # same guard as classification: Starlink/proxy egress isn't the economy's path
                    check = check_detour_trace(
                        trace, resolved, ECONOMY_LATLON[cc],
                        EXTERNAL_HUB_LATLON[finding.detour_hub], finding.detour_hub,
                        ECONOMY_LATLON[finding.target_cc], ix_city,
                        ECONOMY_SPREAD_KM.get(cc, 0.0), ECONOMY_SPREAD_KM.get(finding.target_cc, 0.0),
                    )
                    checks.append({"measurement": corrob.measurement_id, "vantage_cc": cc, **check})
                row["probes"] += claim_probes(checks)
            if not row["probes"]:
                row["skipped"] = "no parsed measurement data on disk"
    finally:
        conn.close()
    for row in results:
        row["verdict"] = "skipped" if row["skipped"] else finding_verdict(row["probes"])
    return results


def _fmt(check: dict) -> str:
    if check["verdict"] == "no_hop":
        return "no hop"
    return f"hop {check['hop']} {check['rtt_ms']}ms vs floor {check['floor_ms']}ms (x{check['ratio']})"


def render(results: list[dict]) -> str:
    counts = Counter(r["verdict"] for r in results)
    per_check = {c: Counter(p[c]["verdict"] for r in results for p in r["probes"]) for c in _CHECKS}
    lines = [
        "Validation Rule 2 feasibility sweep -- report only, no findings changed",
        "(analysis/feasibility_sweep.py). Floors: fibre at 2/3 c, capital-city coordinates.",
        "",
        f"Confirmed detours: {len(results)} -- " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())),
        "Per probe trace: " + "; ".join(
            f"{c}: " + ", ".join(f"{k} {v}" for k, v in sorted(per_check[c].items())) for c in _CHECKS
        ),
        "",
        "IMPOSSIBLE (every checkable claim probe breaks a floor) / MIXED (some do, some don't).",
        "Claim probes: those that crossed the hub IXP, or all probes if none did; Starlink/proxy",
        "first hops excluded. Only the offending probes are listed:",
    ]
    for r in results:
        if r["verdict"] not in (VERDICT_IMPOSSIBLE, VERDICT_MIXED):
            continue
        lines.append(
            f"  #{r['finding']} {r['source_cc']} -> {r['target_cc']} AS{r['target_asn']} via {r['hub']} [{r['verdict']}]"
        )
        for p in r["probes"]:
            bad = [c for c in _CHECKS if p[c]["verdict"] == VERDICT_IMPOSSIBLE]
            if bad:
                lines.append(
                    f"    msm {p['measurement']} probe {p['probe_id']} ({p['vantage_cc']}): "
                    + "; ".join(f"{c} {_fmt(p[c])}" for c in bad)
                    + f"; direct floor {p['target_direct']['floor_ms']}ms"
                )
    lines += ["", "Unchecked (no hub-IXP hop with an RTT, and no trace reached its target) / skipped:"]
    for r in results:
        if r["verdict"] in ("unchecked", "skipped"):
            why = r["skipped"] or "no checkable hop"
            lines.append(f"  #{r['finding']} {r['source_cc']} -> {r['target_cc']} via {r['hub']}: {why}")
    return "\n".join(lines) + "\n"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    results = sweep()
    DETAIL_PATH.parent.mkdir(parents=True, exist_ok=True)
    DETAIL_PATH.write_text(json.dumps(results, indent=1) + "\n")
    REPORT_PATH.write_text(render(results))
    logger.info("Wrote %s and %s", REPORT_PATH, DETAIL_PATH)


if __name__ == "__main__":
    main()
