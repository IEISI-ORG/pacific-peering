"""Plain-text (ASCII) report renderer (Phase 1f).

Renders the shared `ReportData` structure — same data the HTML report
uses — as a fixed-width plain-text report suitable for a terminal, an
email body, or a NOG mailing list post.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pacific_peering.reports.data import ReportData, build_report_data

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
