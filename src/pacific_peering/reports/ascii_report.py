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
                f"    Traceroute-confirmed: "
                f"{', '.join(sat['traceroute_confirmed_economies']) or '(none)'}"
            )
    lines.append("")
    lines.append(
        "**The Kacific gap**: Kacific Broadband Satellites (AS135409), a "
        "real PeeringDB-registered Pacific-focused GEO satellite ISP, has "
        "RIS-observed BGP relationships with at least three in-scope "
        "economies (Papua New Guinea, Tonga, and -- visible only from "
        "Kacific's own neighbor list, not from the target's side, a real "
        "instance of RIS's asymmetric visibility -- Solomon Islands). "
        "Despite that, **no traceroute this project has ever run has "
        "touched Kacific's network at all**. AS38201 (Tonga, Kacific-"
        "linked) sits untested in the current corridor backlog -- a "
        "natural next target if a Kacific-transiting path is ever going "
        "to surface. Starlink and SES ASTRA, by contrast, have both been "
        "directly traceroute-confirmed (Tuvalu/Kiribati for Starlink; "
        "Cook Islands/Nauru for SES ASTRA)."
    )

    lines.append(_section("CONFIRMED SUB-OPTIMAL ROUTES (RIS + Atlas both agree)"))
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

    lines.append(_section("CONFIRMED LOCAL TRANSIT (RIS + Atlas both agree, stays in-fishbowl)"))
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
        _section("CANDIDATE PEERING (strong traceroute signal, RIS disagrees -- unconfirmed)")
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

    lines.append(_section("IXPS (registered exchanges, this project's confirmed classification)"))
    header = f"{'Name':<28} {'City':<16} {'CC':<4} {'In fishbowl':<12} {'Members':>7}"
    lines.append(header)
    lines.append(_rule())
    for ix in data.ixps:
        in_fishbowl_str = str(ix.in_fishbowl)
        lines.append(
            f"{ix.name:<28.28} {ix.city:<16.16} {ix.country:<4} "
            f"{in_fishbowl_str:<12} {ix.member_count:>7}"
        )

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
