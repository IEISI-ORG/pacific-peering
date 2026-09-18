"""Text report, one sole purpose: where does this project need new RIPE Atlas probes.

Per the project owner, this stays deliberately separate from the
findings-oriented ASCII/HTML/presentation reports (which draw from
`ReportData` and answer "what have we found"). This one answers a
single operational question instead — "where should a human go request
a new probe next" — meant to run on its own weekly cadence, not
bundled into the same output as the substantive analysis.

Coverage and the full probe listing are both re-fetched live every run
(40 cheap, unauthenticated Atlas API calls, no credits spent) rather
than reading the possibly-stale `data/atlas/probe_coverage.json` — a
report whose entire point is current operational status defeats its
own purpose if it reports last month's numbers.

Per the project owner: this report should distinguish "listed" (every
probe Atlas has ever registered for an economy, any status) from
"actually useful" (currently Connected) — a listed-but-inactive probe
is either a stale registration (fix the data) or a real host that
could be reconnected (get it back online), and naming the specific
probe IDs and their status gives the wider Atlas/Pacific-networking
community something concrete to act on, not just an aggregate count.
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
from pacific_peering.atlas.asn_probes import load_asn_probe_registry
from pacific_peering.atlas.probes import (
    asn_listed_registry,
    build_probe_coverage,
    build_probe_listing,
)
from pacific_peering.discovery.economies import ECONOMIES_BY_CC
from pacific_peering.discovery.registry import DEFAULT_OUTPUT_PATH as _ASN_REGISTRY_PATH
from pacific_peering.reports.data import FISHBOWL_EXPLANATION, PathwayCoverageSummary
from pacific_peering.reports.data import _compute_pathway_coverage

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("outputs/reports/probe_gaps.txt")

# Hand-curated, same restraint as this project's other small real-data
# structures (confirmed_detours.py etc.) — only add an entry once a
# specific probe's unsuitability has actually been confirmed directly,
# never speculatively.
KNOWN_ISSUES: dict[str, str] = {
    "FJ": (
        "Fiji's only connected probe (id 60575, hosted on AS53813 -- "
        "Zscaler corporate VPN) sits behind Zscaler's own routing, not "
        "real Fiji ISP behavior. Confirmed unusable for path analysis "
        "as-is; not a request for a new probe -- this one becomes usable "
        "automatically, with no code/data action needed, if its hosting "
        "ASN ever changes off Zscaler (the next `asn_probes`/"
        "`probe_coverage` refresh would pick that up on its own)."
    ),
}

# Same restraint as KNOWN_ISSUES above, for the opposite situation: a real,
# verifiable organization already has a physical presence in an economy
# with zero (or fragile) Atlas coverage, making it a concrete lead for
# requesting a new probe -- not a confirmed commitment, just somewhere
# worth actually asking. Only add an entry once the organization's
# presence is confirmed from its own material or an independent report,
# never speculatively.
HOST_LEADS: dict[str, str] = {
    "SB": (
        "No Atlas probe has ever been registered here (confirmed live, "
        "any status). The Pacific Community (SPC) has operated a real "
        "national coordination office in Honiara since 2009 (Anthony Saru "
        "building, under a formal Host Country Agreement -- Solomon "
        "Islands was the first member country to host one) -- the same "
        "kind of organization that already hosts a real Atlas probe for "
        "this project in Fiji, New Caledonia, and FSM. Not yet contacted "
        "about hosting one here; a lead, not a commitment."
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


def render_probe_gap_report(
    coverage: dict[str, int],
    asn_registry: dict,
    pathway_coverage: tuple[PathwayCoverageSummary, ...],
    listing: dict[str, list[dict]],
) -> str:
    """Render the probe-gap report as plain text.

    Args:
        coverage: economy cc -> connected Atlas probe count, from
            `atlas.probes.build_probe_coverage` (a live, geographic
            "is any probe physically in this country" count).
        asn_registry: The Phase 0b ASN registry (cc -> {"asns": [...], ...}),
            used to name the actual in-scope ASNs a new probe should be
            requested against for each zero/fragile economy below --
            "where to request a probe" is more actionable as a specific
            ASN than a bare country code.
        pathway_coverage: Per-economy test-coverage summaries from
            `reports.data._compute_pathway_coverage` -- ASN-tracked
            listed-vs-active-probe counts (deliberately a different
            question from `coverage` above -- see `PathwayCoverageSummary`'s
            own docstring) plus how many of the other in-scope economies
            still have zero finding connecting to this one.
        listing: economy cc -> every probe Atlas has ever registered
            there, any status (see `atlas.probes.build_probe_listing`) --
            used to name the specific probe IDs that are actually useful
            (Connected) versus listed-but-not (a data-quality fix or a
            reconnection opportunity, either way a concrete target).

    Returns:
        The full report as a single string.
    """
    finding_ccs = _economies_used_in_findings()

    def _flag(cc: str) -> str:
        marker = " [used in a confirmed/candidate finding]" if cc in finding_ccs else ""
        issue = f"\n      KNOWN ISSUE: {KNOWN_ISSUES[cc]}" if cc in KNOWN_ISSUES else ""
        lead = f"\n      HOST LEAD: {HOST_LEADS[cc]}" if cc in HOST_LEADS else ""
        return marker + issue + lead

    def _asns(cc: str) -> str:
        asns = sorted(asn_registry.get(cc, {}).get("asns", []))
        return f"\n      ASNs: {', '.join(str(a) for a in asns)}" if asns else ""

    def _probes(cc: str) -> str:
        probes = sorted(listing.get(cc, []), key=lambda p: p["id"])
        if not probes:
            return ""
        useful = [p for p in probes if p["status"] == "Connected"]
        not_useful = [p for p in probes if p["status"] != "Connected"]
        out = [f"\n      Probes: {len(probes)} listed, {len(useful)} actually useful"]
        if useful:
            out.append("\n        Useful (Connected): " + ", ".join(str(p["id"]) for p in useful))
        if not_useful:
            out.append(
                "\n        Not useful yet -- fix the data or get it back online: "
                + ", ".join(f"{p['id']} ({p['status']})" for p in not_useful)
            )
        return "".join(out)

    zero = sorted(cc for cc, n in coverage.items() if n == 0)
    fragile = sorted(cc for cc, n in coverage.items() if n == 1)
    adequate = sorted(cc for cc, n in coverage.items() if n >= 2)

    lines: list[str] = []
    lines.append("PACIFIC PEERING -- RIPE ATLAS PROBE COVERAGE GAPS")
    lines.append("Sole purpose: where to request a new probe next. Not a findings report.")
    lines.append(
        "\"Probes\" breakdowns below distinguish every probe Atlas has ever listed for "
        "an economy (any status) from the subset that's actually useful right now "
        "(status: Connected) -- a listed-but-not-Connected probe is either a stale "
        "registration worth cleaning up or a real host that could be brought back "
        "online, and naming the specific probe IDs gives the Atlas/Pacific-networking "
        "community a concrete target either way."
    )
    lines.append("=" * 78)
    lines.append("")

    lines.append(
        f"ZERO CONNECTED PROBES ({len(zero)}/{len(coverage)}) -- cannot source or "
        "target a traceroute here at all. ASNs listed are this economy's own "
        "in-scope ASNs -- candidates to approach for hosting a new probe:"
    )
    if not zero:
        lines.append("  (none -- every in-scope economy has at least one connected probe)")
    for cc in zero:
        lines.append(f"  {cc}  {ECONOMIES_BY_CC[cc].name}{_flag(cc)}{_asns(cc)}{_probes(cc)}")
    lines.append("")

    lines.append(
        f"FRAGILE -- exactly 1 connected probe ({len(fragile)}/{len(coverage)}) -- a "
        "single point of failure, and there's no second probe to cross-check it "
        "against. ASNs listed are candidates for a second, independent probe:"
    )
    if not fragile:
        lines.append("  (none)")
    for cc in fragile:
        lines.append(f"  {cc}  {ECONOMIES_BY_CC[cc].name}{_flag(cc)}{_asns(cc)}{_probes(cc)}")
    lines.append("")

    lines.append(f"ADEQUATE -- 2+ connected probes ({len(adequate)}/{len(coverage)}):")
    if not adequate:
        lines.append("  (none)")
    for cc in adequate:
        lines.append(
            f"  {cc}  {ECONOMIES_BY_CC[cc].name} ({coverage[cc]} connected){_probes(cc)}"
        )
    lines.append("")
    lines.append("=" * 78)
    lines.append("")

    lines.append(
        f"PATHWAY COVERAGE ({len(pathway_coverage)} economies) -- same table as the "
        "main report's Pathway Coverage section, kept here too since it's the "
        "other half of \"where does a new probe actually help\": ASN count, listed "
        "vs. active probes on this project's own tracked ASNs (not the same count "
        "as above -- see note below), and how many of the other in-scope "
        "economies still have zero finding connecting to this one. Sorted by "
        "untested pathways, most first:"
    )
    for p in pathway_coverage:
        lines.append(
            f"  {p.cc}  {p.name} ({p.subregion}) -- {p.asn_count} ASN(s), "
            f"{p.listed_probes} listed / {p.active_probes} active probe(s) on a "
            f"tracked ASN, {p.untested_pathways} untested pathway(s)"
        )
    lines.append("")
    lines.append(
        "  Note: this section's \"listed\"/\"active\" counts only probes hosted on "
        "one of this project's own tracked in-scope ASNs -- a different, "
        "stricter question than the ZERO/FRAGILE/ADEQUATE breakdown above, "
        "which counts any physically-connected probe in the country. A country "
        "can show >=1 active above and 0 here (e.g. a probe hosted on a Starlink "
        "ASN, or on an ASN registered to a different country) -- that's expected, "
        "not a data-quality problem."
    )
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
        refresh: Re-check live Atlas probe counts and the full probe
            listing (default). Pass False only to render from whatever
            `data/atlas/probe_coverage.json`/`probe_listing.json` already
            hold, e.g. for a quick offline re-render.

    Returns:
        The path the report was written to.
    """
    coverage = (
        build_probe_coverage()
        if refresh
        else json.loads(Path("data/atlas/probe_coverage.json").read_text())
    )
    listing = (
        build_probe_listing()
        if refresh
        else json.loads(Path("data/atlas/probe_listing.json").read_text())
    )
    asn_registry = json.loads(_ASN_REGISTRY_PATH.read_text())
    pathway_coverage = _compute_pathway_coverage(
        asn_registry, load_asn_probe_registry(), asn_listed_registry(listing)
    )
    text = render_probe_gap_report(coverage, asn_registry, pathway_coverage, listing)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text + "\n")
    logger.info("Wrote probe-gap report to %s", output_path)
    return output_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    write_probe_gap_report()


if __name__ == "__main__":
    main()
