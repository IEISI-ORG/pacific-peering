"""Plain-text (ASCII) report renderer (Phase 1f).

Renders the shared `ReportData` structure — same data the HTML report
uses — as a fixed-width plain-text report suitable for a terminal, an
email body, or a NOG mailing list post.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pacific_peering.reports.data import FISHBOWL_EXPLANATION, ReportData, build_report_data

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("outputs/reports/report.txt")

_WIDTH = 78


def _rule(char: str = "-") -> str:
    return char * _WIDTH


def _section(title: str) -> str:
    return f"\n{title}\n{_rule('=')}"


def render_ascii_report(data: ReportData) -> str:
    """Render `data` as a plain-text report.

    Returns:
        The full report as a single string.
    """
    lines: list[str] = []
    lines.append(_rule("="))
    lines.append("PACIFIC PEERING — REGIONAL ROUTING REPORT".center(_WIDTH))
    lines.append(f"Generated: {data.generated_at}".center(_WIDTH))
    lines.append(_rule("="))

    lines.append(_section("SUMMARY"))
    lines.append(
        f"HEADLINE: {data.ixp_registry_out_of_fishbowl_share:.0%} of the real peering points "
        "this region's own networks use sit OUTSIDE the fish bowl"
        f" ({data.ixp_registry_out_of_fishbowl} of "
        f"{data.ixp_registry_in_fishbowl + data.ixp_registry_out_of_fishbowl})"
    )
    lines.append("")
    lines.append("PATHWAYS (every corridor with a filed finding, of any kind):")
    lines.append(f"  Total pathways found:                    {data.pathways_total}")
    lines.append(f"  Internal (never leave the fish bowl):    {data.pathways_internal}")
    lines.append(f"  External / Leaves the region:            {data.pathways_external}")
    lines.append(
        "  (full corridor-by-corridor detail -- every confirmed detour, confirmed "
        "local transit, and candidate peering entry -- is in the appendix at the "
        "end of this report, not repeated here)"
    )
    lines.append("")
    lines.append(f"Economies in scope:            {data.total_economies}")
    lines.append(f"ASNs in scope:                  {data.total_asns}")
    lines.append(f"ASNs with >=1 RIS neighbor:     {data.asns_with_neighbors}")
    lines.append(f"ASNs with >=1 IXP membership:   {data.asns_with_ixp}")
    lines.append(f"ASNs with >=1 facility presence:{data.asns_with_facility}")
    lines.append(
        f"IXP LAN registry: {data.ixp_registry_in_fishbowl} in-fishbowl, "
        f"{data.ixp_registry_out_of_fishbowl} out-of-fishbowl, "
        f"{data.ixp_registry_tba} unconfirmed"
    )

    lines.append(_section("ECONOMIES"))
    header = f"{'CC':<4} {'Name':<32} {'Subregion':<12} {'ASNs':>5} {'Nbr':>5} {'IXP':>5} {'Fac':>5}"
    lines.append(header)
    lines.append(_rule())
    for economy in data.economies:
        lines.append(
            f"{economy.cc:<4} {economy.name:<32} {economy.subregion:<12} "
            f"{economy.asn_count:>5} {economy.asns_with_neighbors:>5} "
            f"{economy.asns_with_ixp:>5} {economy.asns_with_facility:>5}"
        )

    lines.append(
        _section(
            "FINDINGS: TRANSIT SUPPLIER CONCENTRATION "
            "(RIS + Atlas confirmed immediate upstream)"
        )
    )
    lines.append(
        "Ranked by \"dependent\" economies -- those whose own reachability "
        "this carrier was confirmed as the immediate upstream for -- not "
        "by every economy a measurement happened to be fired from. "
        "\"Vantage-only\" economies merely tested a path through this "
        "carrier to reach a dependent economy elsewhere; they have no "
        "confirmed reliance on it themselves (this split exists because a "
        "single-island submarine-cable operator like SISCC was otherwise "
        "misreading as a broad regional concentration risk, when almost "
        "every economy in its count was just a vantage point testing a "
        "path to Solomon Islands). This counts confirmed, measured "
        "corridors only, not total internet exposure: most economies are "
        "likely multi-homed via paths this project hasn't measured. "
        "\"Regional\" marks a carrier itself based in an in-scope Pacific "
        "economy, rather than an external Tier-1."
    )
    lines.append("")
    if not data.transit_suppliers:
        lines.append("(none recorded yet)")
    else:
        header = (
            f"{'ASN':<9} {'Carrier':<32} {'Dependent':>9} {'Vantage':>8} "
            f"{'Corrob.':>7} {'Regional':>8}"
        )
        lines.append(header)
        lines.append(_rule())
        for supplier in data.transit_suppliers[:8]:
            dep_count = len(supplier["dependent_economies"])
            van_count = len(supplier["vantage_only_economies"])
            asn_str = f"AS{supplier['asn']}"
            lines.append(
                f"{asn_str:<9} {supplier['name']:<32.32} {dep_count:>9} "
                f"{van_count:>8} {supplier['corroboration_count']:>7} "
                f"{'yes' if supplier['is_regional'] else 'no':>8}"
            )
            lines.append(f"    Dependent: {', '.join(supplier['dependent_economies']) or '(none)'}")
            lines.append(
                f"    Vantage-only: {', '.join(supplier['vantage_only_economies']) or '(none)'}"
            )
    lines.append("")
    lines.append(
        "AS9241 (FINTEL, Fiji) doesn't crack the table above by dependent-"
        "economy count (just Tuvalu), but is the starkest single-point-of-"
        "failure finding this project has confirmed: it's Tuvalu's *only* "
        "RIS-observed neighbor of consequence, reconfirmed by 8 independent "
        "vantage points across the region. Every measured path into Tuvalu "
        "-- from every direction this project has tested -- passes through "
        "one single carrier."
    )

    lines.append(_section("FINDINGS: REGIONAL HUB CONCENTRATION"))
    lines.append(
        "Which in-scope Pacific economies serve as a real transit "
        "waypoint for *other* in-scope economies, entirely inside the "
        "fishbowl -- the mirror image of transit supplier concentration "
        "above, but for carriers based in the region rather than "
        "external Tier-1s. Built from `ConfirmedLocalTransit` entries "
        "where the provider and customer are different economies. "
        "\"Corrob.\" sums each underlying relationship's own "
        "corroboration depth, so an economy serving two economies each "
        "reconfirmed many times outranks one serving two economies "
        "confirmed only once each."
    )
    lines.append("")
    if not data.regional_hubs:
        lines.append("(none recorded yet)")
    else:
        subregion_of = {e.cc: e.subregion for e in data.economies}
        header = f"{'Economy':<32} {'Serves':>7} {'Corrob.':>7} {'Subregions served':<28}"
        lines.append(header)
        lines.append(_rule())
        for hub in data.regional_hubs:
            name = f"{hub['economy_name']} ({hub['economy_cc']})"
            subregions = sorted(
                {subregion_of.get(cc) for cc in hub["dependent_economies"]} - {None}
            )
            lines.append(
                f"{name:<32.32} {len(hub['dependent_economies']):>7} "
                f"{hub['corroboration_count']:>7} {', '.join(subregions):<28}"
            )
            lines.append(f"    Serves: {', '.join(hub['dependent_economies'])}")
            lines.append(f"    Carriers: {', '.join(hub['carriers'])}")

    lines.append(_section("FINDINGS: EXTERNAL HUB CONCENTRATION"))
    lines.append(
        "The mirror image of the regional hubs above: the real external "
        "cities where confirmed detours physically leave the fishbowl. "
        "Every `ConfirmedDetour` names one (`detour_hub`, set from "
        "actual hop evidence or a real IXP-LAN address match, never a "
        "carrier-level guess). Ranked by how many confirmed detours "
        "cross there. \"Carriers\" is how many distinct confirmed-"
        "upstream ASNs have been observed crossing at that city -- a "
        "high count means a genuine shared crossroads, not one "
        "carrier's path repeated."
    )
    lines.append("")
    if not data.external_hubs:
        lines.append("(none recorded yet)")
    else:
        total_detours = len(data.confirmed_detours)
        subregion_of = {e.cc: e.subregion for e in data.economies}
        header = f"{'City':<14} {'Entries':>7} {'Share':>6} {'Carriers':>8} {'Subregions reached':<30}"
        lines.append(header)
        lines.append(_rule())
        for hub in data.external_hubs:
            share = hub["entry_count"] / total_detours if total_detours else 0.0
            subregions = sorted({subregion_of.get(cc) for cc in hub["dependent_economies"]} - {None})
            lines.append(
                f"{hub['name']:<14} {hub['entry_count']:>7} {share:>6.0%} "
                f"{hub['carrier_count']:>8} {', '.join(subregions)}"
            )
            lines.append(f"    Dependent economies: {', '.join(hub['dependent_economies'])}")
        top3_share = sum(h["entry_count"] for h in data.external_hubs[:3]) / total_detours
        lines.append("")
        lines.append(
            f"Just the top 3 cities above account for {top3_share:.0%} of every "
            "confirmed detour this project has recorded -- almost the entire "
            "region's out-of-fishbowl traffic funnels through three physical "
            "places."
        )

    lines.append(_section("FINDINGS: SATELLITE OPERATOR PATHWAYS"))
    lines.append(
        "Which in-scope economies have a known relationship to a satellite "
        "operator, and how strong the evidence is. \"RIS economies\" is a "
        "real, BGP-observed neighbor relationship (this project's own "
        "fishbowl cache) that no traceroute has necessarily confirmed "
        "carries traffic; \"traceroute-confirmed\" means an Atlas "
        "traceroute has actually been observed transiting that operator's "
        "network."
    )
    lines.append("")
    if not data.satellite_pathways:
        lines.append("(none recorded yet)")
    else:
        subregion_of = {e.cc: e.subregion for e in data.economies}
        header = f"{'ASN':<10} {'Operator':<30} {'Subregions reached':<28}"
        lines.append(header)
        lines.append(_rule())
        for sat in data.satellite_pathways:
            all_economies = set(sat["ris_economies"]) | set(sat["traceroute_confirmed_economies"])
            subregions = sorted({subregion_of.get(cc) for cc in all_economies} - {None})
            lines.append(
                f"AS{sat['asn']:<8} {sat['name']:<30.30} {', '.join(subregions):<28}"
            )
            lines.append(
                f"    RIS economies: {', '.join(sat['ris_economies']) or '(none)'}"
            )
            lines.append(
                f"    Traceroute-confirmed (served): "
                f"{', '.join(sat['traceroute_confirmed_economies']) or '(none)'}"
            )
            lines.append(
                f"    Tested from (vantage points): "
                f"{', '.join(sat['traceroute_vantage_economies']) or '(none)'}"
            )
    lines.append("")
    lines.append(
        "Per-operator evidence summary, computed fresh from the current "
        "finding dataclasses every regeneration -- \"served\" means the "
        "economy's own reachability was confirmed to depend on this "
        "operator; \"vantage points\" just means a traceroute was fired "
        "from there, which is a measure of testing breadth, not reach:"
    )
    for narrative in data.satellite_narrative:
        lines.append(f"- {narrative}")

    lines.append(_section("PEERINGDB DATA QUALITY"))
    lines.append(
        f"{data.peeringdb_asns_on_pdb} of {data.total_asns} in-scope ASNs have a PeeringDB "
        "net record at all. 'Zero facilities'/'zero IXP memberships' elsewhere in this report "
        "can mean either of two very different things: this ASN was never on PeeringDB to "
        "begin with, or it IS registered and simply declared nothing. The two columns below "
        "are counted against ASNs that ARE on PeeringDB, not against every in-scope ASN, so "
        "they show the real gap, not a re-blend of the two. Known concrete cases: AS12684 "
        "(SES Astra) and AS3549 (the former Global Crossing backbone ASN) are both real, "
        "traceroute-confirmed carriers with zero PeeringDB facilities -- this is PeeringDB's "
        "own coverage gap, not a measurement gap in this project's findings."
    )
    lines.append(
        f"{'CC':<4} {'Name':<24} {'ASNs':>5} {'On PDB':>7} "
        f"{'w/ Facility':>12} {'w/ IXP':>7}"
    )
    lines.append(_rule())
    for e in data.peeringdb_economies:
        if e.on_peeringdb == 0:
            continue
        lines.append(
            f"{e.cc:<4} {e.name:<24.24} {e.asn_count:>5} {e.on_peeringdb:>7} "
            f"{e.with_facility:>12} {e.with_ixp:>7}"
        )
    if not any(e.on_peeringdb for e in data.peeringdb_economies):
        lines.append("(no in-scope ASN is on PeeringDB)")
    # TODO: PeeringDB net-record `updated` staleness (a registered-but-
    # abandoned org is weaker evidence than a maintained one) -- deferred,
    # not in this pass.

    lines.append(_section("ASPA PROGRESS (RFC 9582 upstream-authorization adoption)"))
    lines.append(
        f"{data.aspa_asns_with_record} of {data.total_asns} in-scope ASNs now publish an "
        f"ASPA record ({data.aspa_global_total_records} total across the whole internet, "
        "per Cloudflare Radar). Adoption is still early -- absence means "
        "'not published yet', not 'no real upstream'. Per-economy: how many of its own "
        "ASNs publish a record, and the distinct upstream ASNs those records declare, "
        "split by whether the declared provider is itself an in-scope Pacific ASN or an "
        "external carrier."
    )
    lines.append(
        f"{'CC':<4} {'Name':<24} {'ASNs':>5} {'w/ ASPA':>8} "
        f"{'Upstr in-FB':>12} {'Upstr ext':>10}"
    )
    lines.append(_rule())
    for e in data.aspa_economies:
        if e.asns_with_aspa == 0:
            continue
        lines.append(
            f"{e.cc:<4} {e.name:<24.24} {e.asn_count:>5} {e.asns_with_aspa:>8} "
            f"{e.unique_upstream_in_fishbowl:>12} {e.unique_upstream_out_of_fishbowl:>10}"
        )
    if not any(e.asns_with_aspa for e in data.aspa_economies):
        lines.append("(no in-scope ASN publishes an ASPA record yet)")
    # TODO: once enough ASPA-confirmed findings exist, add a "certified
    # supply" marker to the Confirmed Local Transit / Candidate Peering
    # sections above so an ASPA-backed confirmation is visually
    # distinguishable from a RIS-agreement-only one (see
    # store.mark_aspa_checked's aspa_confirmed field, already tracked).

    lines.append(_section("IPV6 COVERAGE (adoption signal only -- no IPv6 testing yet)"))
    lines.append(
        f"{data.ipv6_asns_with_routes} of {data.total_asns} in-scope ASNs have >=1 "
        "RIS-observed IPv6-originated prefix. "
        f"{data.ipv6_probes_working} of {data.ipv6_probes_total} connected Atlas probes "
        f"work over IPv6 ({data.ipv6_probes_capable_not_working} more are IPv6-capable but "
        "tagged as not working). Adoption tracking only -- this project deliberately isn't "
        "testing IPv6 corridors yet; queued until adoption has advanced further (see TODO "
        "below)."
    )
    lines.append(f"{'CC':<4} {'Name':<24} {'ASNs':>5} {'w/ IPv6':>8}")
    lines.append(_rule())
    for e in data.ipv6_economies:
        if e.asns_with_ipv6 == 0:
            continue
        lines.append(f"{e.cc:<4} {e.name:<24.24} {e.asn_count:>5} {e.asns_with_ipv6:>8}")
    if not any(e.asns_with_ipv6 for e in data.ipv6_economies):
        lines.append("(no in-scope ASN has an RIS-observed IPv6 prefix yet)")
    # TODO: IPv6 corridor testing (traceroute/RIS validation over v6) --
    # deliberately deferred per the project owner until adoption advances
    # further. Revisit this once the ASN/probe counts above look
    # meaningfully higher.

    lines.append(_section("IXPS (registered exchanges, this project's confirmed classification)"))
    header = (
        f"{'Name':<28} {'City':<16} {'CC':<4} {'In fishbowl':<12} {'Members':>7}  Economies"
    )
    lines.append(header)
    lines.append(_rule())
    for ix in data.ixps:
        in_fishbowl_str = str(ix.in_fishbowl)
        lines.append(
            f"{ix.name:<28.28} {ix.city:<16.16} {ix.country:<4} "
            f"{in_fishbowl_str:<12} {ix.member_count:>7}  {', '.join(ix.economies)}"
        )

    lines.append(_section("PATHWAY COVERAGE (per economy)"))
    lines.append(
        "How many Atlas probes this economy's own ASNs have ever had registered "
        "(\"Listed\", any status) versus currently Connected (\"Active\" -- zero means it "
        "can never be a traceroute source right now, only ever reached as a target); and "
        "how many of the other 19 in-scope economies still have zero finding connecting "
        "to it. A Listed count above Active is a gap worth closing either way -- a stale "
        "Atlas registration to clean up, or a real host that could be brought back online "
        "-- see the PATHWAYS summary at the top for the region-wide totals this is derived "
        "from."
    )
    header = (
        f"{'CC':<4} {'Name':<32} {'Subregion':<12} {'ASNs':>5} "
        f"{'Listed':>7} {'Active':>7} {'Untested':>9}"
    )
    lines.append(header)
    lines.append(_rule())
    for p in data.pathway_coverage:
        lines.append(
            f"{p.cc:<4} {p.name:<32.32} {p.subregion:<12} "
            f"{p.asn_count:>5} {p.listed_probes:>7} {p.active_probes:>7} {p.untested_pathways:>9}"
        )

    lines.append(
        _section(
            f"APPENDIX: LOW DATA QUALITY ISSUES ({len(data.data_quality_issues)} known, resolved)"
        )
    )
    lines.append(
        "Known problems in this project's underlying sources (APNIC delegation, "
        "PeeringDB, ASPA, etc.) that have already been found, verified, and "
        "corrected for elsewhere in the pipeline -- kept visible here rather than "
        "left implicit, so the counts and tables earlier in this report can be "
        "trusted without re-deriving why they exclude what they exclude."
    )
    if not data.data_quality_issues:
        lines.append("(none recorded yet)")
    for issue in data.data_quality_issues:
        lines.append("")
        lines.append(f"{issue.title}  [{issue.category_label}]")
        lines.append(f"    {issue.description}")

    lines.append(
        _section(
            f"APPENDIX: FULL CORRIDOR DETAIL ({data.pathways_total} pathways -- "
            "see the PATHWAYS summary at the top of this report for the plain counts)"
        )
    )
    lines.append(_section("Confirmed sub-optimal routes (RIS + Atlas both agree)"))
    if not data.confirmed_detours:
        lines.append("(none recorded yet)")
    for detour in data.confirmed_detours:
        lines.append(
            f"{detour['source_cc']} -> {detour['target_cc']} (AS{detour['target_asn']}): "
            f"detours via {detour['detour_ix_name']} ({detour['detour_hub']})"
        )
        lines.append(
            f"    RIS observation count: {detour['ris_observation_count']}  "
            f"[measurement {detour['measurement_id']}]"
        )
        lines.append(f"    {detour['note']}")

    lines.append(_section("Confirmed local transit (RIS + Atlas both agree, stays in-fishbowl)"))
    if not data.confirmed_local_transit:
        lines.append("(none recorded yet)")
    for transit in data.confirmed_local_transit:
        lines.append(
            f"AS{transit['provider_asn']} ({transit['provider_name']}, "
            f"{transit['provider_cc']}) -> AS{transit['customer_asn']} "
            f"({transit['customer_name']}, {transit['customer_cc']})"
        )
        lines.append(
            f"    RIS observation count: {transit['ris_observation_count']}  "
            f"[measurement {transit['measurement_id']}, vantage: {transit['vantage_point_cc']}]"
        )
        lines.append(f"    {transit['note']}")

    lines.append(
        _section("Candidate peering (strong traceroute signal, RIS disagrees -- unconfirmed)")
    )
    if not data.candidate_peering:
        lines.append("(none recorded yet)")
    for candidate in data.candidate_peering:
        lines.append(
            f"AS{candidate['upstream_asn']} ({candidate['upstream_name']}, "
            f"{candidate['upstream_cc']}) -> AS{candidate['target_asn']} "
            f"({candidate['target_name']}, {candidate['target_cc']})"
        )
        lines.append(
            f"    Traceroute agreement: {candidate['probe_agreement']}  "
            f"[measurement {candidate['measurement_id']}, "
            f"vantage: {candidate['vantage_point_cc']}]"
        )
        lines.append(f"    {candidate['note']}")

    lines.append(_section("ABOUT THIS PROJECT"))
    lines.append(FISHBOWL_EXPLANATION)

    lines.append("")
    lines.append(_rule("="))
    return "\n".join(lines)


def write_ascii_report(output_path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    """Build report data, render it, and write it to `output_path`.

    Returns:
        The path the report was written to.
    """
    data = build_report_data()
    text = render_ascii_report(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text + "\n")
    logger.info("Wrote ASCII report to %s", output_path)
    return output_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    write_ascii_report()


if __name__ == "__main__":
    main()
