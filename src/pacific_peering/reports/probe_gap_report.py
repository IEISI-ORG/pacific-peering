"""Text report, one sole purpose: where does this project need new RIPE Atlas probes.

Per the project owner, this stays deliberately separate from the
findings-oriented ASCII/HTML/presentation reports (which draw from
`ReportData` and answer "what have we found"). This one answers a
single operational question instead — "where should a human go request
a new probe next" — meant to run on its own weekly cadence, not
bundled into the same output as the substantive analysis.

Coverage is re-fetched live every run (20 cheap, unauthenticated Atlas
API calls, no credits spent) rather than reading the possibly-stale
`data/atlas/probe_coverage.json` — a report whose entire point is
current operational status defeats its own purpose if it reports last
month's numbers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pacific_peering.analysis import store as _store

# Loaded from the SQLite store, not the legacy dataclass modules directly --
# see reports/data.py's module docstring for why.
_conn = _store.connect()
CONFIRMED_DETOURS = _store.load_confirmed_detours(_conn)
CONFIRMED_LOCAL_TRANSIT = _store.load_confirmed_local_transit(_conn)
CANDIDATE_PEERING = _store.load_candidate_peering(_conn)
_conn.close()
from pacific_peering.atlas.probes import build_probe_coverage
from pacific_peering.discovery.economies import ECONOMIES_BY_CC
from pacific_peering.reports.data import FISHBOWL_EXPLANATION

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("outputs/reports/probe_gaps.txt")

# Hand-curated, same restraint as this project's other small real-data
# structures (confirmed_detours.py etc.) — only add an entry once a
# specific probe's unsuitability has actually been confirmed directly,
# never speculatively.
KNOWN_ISSUES: dict[str, str] = {
    "FJ": (
        "Fiji's only connected probe sits behind AS53813 (Zscaler corporate "
        "VPN) -- a traceroute sourced from it shows Zscaler's own routing, "
        "not real Fiji ISP behavior. Confirmed unusable for path analysis; "
        "a new, non-proxied probe is needed to actually study Fiji's routing."
    ),
}


def _economies_used_in_findings() -> set[str]:
    """Every economy referenced (as source/target/vantage) by a confirmed or candidate finding.

    Used only to flag "this thin economy is already load-bearing for a
    real finding" — a reason to prioritize it over an equally-thin
    economy no finding has touched yet.
    """
    ccs: set[str] = set()
    for d in CONFIRMED_DETOURS:
        ccs.update({d.source_cc, d.target_cc})
    for t in CONFIRMED_LOCAL_TRANSIT:
        ccs.update({t.provider_cc, t.customer_cc, t.vantage_point_cc})
    for c in CANDIDATE_PEERING:
        ccs.update({c.upstream_cc, c.target_cc, c.vantage_point_cc})
    return ccs


def render_probe_gap_report(coverage: dict[str, int]) -> str:
    """Render the probe-gap report as plain text.

    Args:
        coverage: economy cc -> connected Atlas probe count, from
            `atlas.probes.build_probe_coverage`.

    Returns:
        The full report as a single string.
    """
    finding_ccs = _economies_used_in_findings()

    def _flag(cc: str) -> str:
        marker = " [used in a confirmed/candidate finding]" if cc in finding_ccs else ""
        issue = f"\n      KNOWN ISSUE: {KNOWN_ISSUES[cc]}" if cc in KNOWN_ISSUES else ""
        return marker + issue

    zero = sorted(cc for cc, n in coverage.items() if n == 0)
    fragile = sorted(cc for cc, n in coverage.items() if n == 1)
    adequate = sorted(cc for cc, n in coverage.items() if n >= 2)

    lines: list[str] = []
    lines.append("PACIFIC PEERING -- RIPE ATLAS PROBE COVERAGE GAPS")
    lines.append("Sole purpose: where to request a new probe next. Not a findings report.")
    lines.append("=" * 78)
    lines.append("")

    lines.append(
        f"ZERO CONNECTED PROBES ({len(zero)}/{len(coverage)}) -- cannot source or "
        "target a traceroute here at all:"
    )
    if not zero:
        lines.append("  (none -- every in-scope economy has at least one connected probe)")
    for cc in zero:
        lines.append(f"  {cc}  {ECONOMIES_BY_CC[cc].name}{_flag(cc)}")
    lines.append("")

    lines.append(
        f"FRAGILE -- exactly 1 connected probe ({len(fragile)}/{len(coverage)}) -- a "
        "single point of failure, and there's no second probe to cross-check it against:"
    )
    if not fragile:
        lines.append("  (none)")
    for cc in fragile:
        lines.append(f"  {cc}  {ECONOMIES_BY_CC[cc].name}{_flag(cc)}")
    lines.append("")

    lines.append(f"ADEQUATE -- 2+ connected probes ({len(adequate)}/{len(coverage)}):")
    if not adequate:
        lines.append("  (none)")
    for cc in adequate:
        lines.append(f"  {cc}  {ECONOMIES_BY_CC[cc].name} ({coverage[cc]} connected)")
    lines.append("")
    lines.append("=" * 78)
    lines.append("")
    lines.append(FISHBOWL_EXPLANATION)
    return "\n".join(lines)


def write_probe_gap_report(
    output_path: Path = DEFAULT_OUTPUT_PATH, refresh: bool = True
) -> Path:
    """Build (optionally re-fetching live) coverage, render the report, and write it.

    Args:
        output_path: Where to write the plain-text report.
        refresh: Re-check live Atlas probe counts (default). Pass False
            only to render from whatever `data/atlas/probe_coverage.json`
            already holds, e.g. for a quick offline re-render.

    Returns:
        The path the report was written to.
    """
    coverage = (
        build_probe_coverage()
        if refresh
        else json.loads(Path("data/atlas/probe_coverage.json").read_text())
    )
    text = render_probe_gap_report(coverage)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text + "\n")
    logger.info("Wrote probe-gap report to %s", output_path)
    return output_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    write_probe_gap_report()


if __name__ == "__main__":
    main()
