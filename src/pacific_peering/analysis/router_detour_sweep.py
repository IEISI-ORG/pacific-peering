"""Report-only sweep: which existing findings would the router-location detour rule have read differently?

Per the project owner's precedent for Validation Rule 2 (2026-09-29, see
`feasibility_sweep.py`): run a new classification rule over the corpus once and
read the results before wiring it into nightly classification. Changes nothing
in the findings store; writes `outputs/reports/router_detour_sweep.txt`.

For every corroboration with a measurement, each parsed trace that does not
already cross an off-region IXP is checked with `router_location.find_router_hub`,
using the corroboration's `vantage_point_cc` as the source economy (a label --
`auto_classify._original_vantage` exists because labels have been wrong). PTR
lookups are live and cached for the run.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import sqlite3
from collections import Counter
from pathlib import Path

from pacific_peering.analysis import store as _store
from pacific_peering.analysis.feasibility import DEFAULT_ATLAS_PARSED_DIR
from pacific_peering.analysis.ixp_lan_registry import load_ixp_lan_registry
from pacific_peering.analysis.router_location import PtrResolver, find_router_hub, reverse_dns

logger = logging.getLogger(__name__)

REPORT_PATH = Path("outputs/reports/router_detour_sweep.txt")


def off_region_ixp_networks(registry: dict) -> list:
    """LAN prefixes of every exchange classified out-of-fishbowl (in_fishbowl is False, never "TBA")."""
    return [ipaddress.ip_network(p) for e in registry.values() if e.in_fishbowl is False for p in e.prefixes]


def _crosses(trace: dict, networks: list) -> bool:
    for h in trace.get("hops", []):
        for a in h.get("addresses", []):
            try:
                ip = ipaddress.ip_address(a)
            except ValueError:
                continue
            if any(ip.version == n.version and ip in n for n in networks):
                return True
    return False


def sweep(conn: sqlite3.Connection, parsed_dir: Path, networks: list, resolver: PtrResolver) -> list[dict]:
    rows = conn.execute(
        "SELECT f.id, f.kind, c.measurement_id, c.vantage_point_cc FROM corroborations c "
        "JOIN findings f ON f.id = c.finding_id WHERE c.measurement_id IS NOT NULL ORDER BY f.id, c.measurement_id"
    ).fetchall()
    out: list[dict] = []
    seen: set[tuple[int, int, int]] = set()
    for finding_id, kind, measurement_id, source_cc in rows:
        path = parsed_dir / f"{measurement_id}.json"
        if not path.exists():
            continue
        for trace in json.loads(path.read_text()):
            key = (finding_id, measurement_id, trace["probe_id"])
            if key in seen or _crosses(trace, networks):
                continue
            seen.add(key)
            hub = find_router_hub(trace, source_cc, resolver)
            if hub is None:
                continue
            out.append({
                "finding_id": finding_id, "kind": kind, "measurement_id": measurement_id,
                "probe_id": trace["probe_id"], "source_cc": source_cc, "city": hub.city,
                "verdict": hub.verdict, "note": hub.note(),
            })
    return out


def render(rows: list[dict]) -> str:
    by_kind = Counter(r["kind"] for r in {r["finding_id"]: r for r in rows}.values())
    lines = [
        "Router-location detour sweep (report-only; nothing in findings.db changed)",
        "",
        "Findings with at least one trace through a hostname-located off-region router and no off-region IXP:",
        *(f"  {kind}: {n}" for kind, n in sorted(by_kind.items())),
        "",
    ]
    for r in rows:
        if r["kind"] == _store.KIND_CONFIRMED_DETOUR:
            continue
        lines.append(f"#{r['finding_id']} {r['kind']} msm {r['measurement_id']} probe {r['probe_id']} "
                     f"(from {r['source_cc']}): {r['note']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    conn = _store.connect()
    try:
        rows = sweep(conn, DEFAULT_ATLAS_PARSED_DIR, off_region_ixp_networks(load_ixp_lan_registry()), reverse_dns)
    finally:
        conn.close()
    REPORT_PATH.write_text(render(rows))
    logger.info("Wrote %s (%d trace rows)", REPORT_PATH, len(rows))


if __name__ == "__main__":
    main()
