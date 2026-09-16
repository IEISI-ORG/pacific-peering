"""HTML report renderer (Phase 1f).

Renders the exact same `ReportData` the ASCII report uses — per Phase
1f's spec, both formats come from one shared structure so they can't
disagree — as a single self-contained HTML file, with the Phase 1e
visualizations embedded alongside the tables (the ASCII report can't
show those; this is where the fuller picture belongs).
"""

from __future__ import annotations

import html
import logging
from pathlib import Path

from pacific_peering.reports.data import FISHBOWL_EXPLANATION, ReportData, build_report_data

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("outputs/reports/report.html")

# Same tokens as the Phase 1e visualizations (dataviz skill's validated palette).
_INK = "#0b0b0b"
_MUTED = "#898781"
_SURFACE = "#fcfcfb"
_GOOD = "#0ca30c"
_CRITICAL = "#d03b3b"
_WARNING = "#fab219"
_SUBREGION_COLOR = {"Melanesia": "#2a78d6", "Polynesia": "#eb6834", "Micronesia": "#1baf7a"}

_CSS = f"""
body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background: {_SURFACE};
        color: {_INK}; margin: 0; padding: 24px; line-height: 1.5; }}
.wrap {{ max-width: 980px; margin: 0 auto; }}
h1 {{ font-size: 1.5rem; margin-bottom: 0.2em; }}
.meta {{ color: {_MUTED}; font-size: 0.85rem; margin-bottom: 1.5em; }}
h2 {{ font-size: 1.1rem; border-bottom: 1px solid #e1e0d9; padding-bottom: 0.3em;
      margin-top: 2em; }}
.headline-banner {{ background: #fdecec; border: 1px solid {_CRITICAL}; border-radius: 8px;
              padding: 14px 18px; margin: 1em 0; font-size: 1.05rem; }}
.headline-banner .value {{ font-weight: 700; color: {_CRITICAL}; }}
.stat-row {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 1em 0; }}
.stat-tile {{ background: white; border: 1px solid #e1e0d9; border-radius: 8px;
              padding: 10px 16px; min-width: 140px; }}
.stat-tile .value {{ font-size: 1.4rem; font-weight: 600; }}
.stat-tile .label {{ font-size: 0.78rem; color: {_MUTED}; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; }}
th, td {{ text-align: left; padding: 5px 8px; border-bottom: 1px solid #e1e0d9; }}
th {{ color: {_MUTED}; font-weight: 600; font-size: 0.78rem; text-transform: uppercase; }}
tr:hover {{ background: #f5f4f0; }}
.subregion-dot {{ display: inline-block; width: 9px; height: 9px; border-radius: 50%;
                   margin-right: 6px; }}
.detour-card {{ border-left: 4px solid {_CRITICAL}; background: #fdf1f0; padding: 10px 14px;
                margin-bottom: 10px; border-radius: 4px; }}
.detour-card .headline {{ font-weight: 600; }}
.detour-card .note {{ color: {_MUTED}; font-size: 0.85rem; margin-top: 4px; }}
.transit-card {{ border-left: 4px solid {_GOOD}; background: #f0faf0; padding: 10px 14px;
                margin-bottom: 10px; border-radius: 4px; }}
.transit-card .headline {{ font-weight: 600; }}
.transit-card .note {{ color: {_MUTED}; font-size: 0.85rem; margin-top: 4px; }}
.candidate-card {{ border-left: 4px solid {_WARNING}; background: #fef8e8; padding: 10px 14px;
                margin-bottom: 10px; border-radius: 4px; }}
.candidate-card .headline {{ font-weight: 600; }}
.candidate-card .note {{ color: {_MUTED}; font-size: 0.85rem; margin-top: 4px; }}
.note summary {{ cursor: pointer; user-select: none; }}
.note summary:hover {{ color: {_INK}; }}
.note[open] summary {{ margin-bottom: 6px; }}
.bool-true {{ color: {_GOOD}; font-weight: 600; }}
.bool-false {{ color: {_CRITICAL}; }}
.section-intro {{ color: {_MUTED}; font-size: 0.88rem; margin: 0.4em 0 1em; max-width: 780px; }}
.callout {{ border-left: 4px solid {_WARNING}; background: #fef8e8; padding: 10px 14px;
            border-radius: 4px; margin: 1em 0; font-size: 0.88rem; }}
.viz-figure {{ margin: 1.5em 0; }}
.viz-figure img {{ max-width: 100%; border: 1px solid #e1e0d9; border-radius: 6px; }}
.viz-figure figcaption {{ color: {_MUTED}; font-size: 0.8rem; margin-top: 6px; }}
footer.about {{ margin-top: 2.5em; padding-top: 1em; border-top: 1px solid #e1e0d9;
                color: {_MUTED}; font-size: 0.82rem; line-height: 1.6; }}
footer.about h2 {{ border-bottom: none; margin-top: 0; font-size: 0.95rem; color: {_INK}; }}
"""


def _stat_tile(value: object, label: str) -> str:
    return (
        f'<div class="stat-tile"><div class="value">{html.escape(str(value))}</div>'
        f'<div class="label">{html.escape(label)}</div></div>'
    )


_NOTE_PREVIEW_LEN = 160


def _note_block(note: str) -> str:
    """Render a note as a collapsed `<details>` block with a short preview.

    Notes accumulate one paragraph per independent corroboration as a
    corridor gets re-tested from new vantage points — some now run to
    several thousand characters. Full text stays in the page (and in
    `report.txt`, unabridged) but collapsed by default via native
    HTML5 `<details>`, no JS required, so the page doesn't render as
    one continuous wall of text.
    """
    escaped = html.escape(note)
    preview = note.split(". ", 1)[0]
    if len(preview) > _NOTE_PREVIEW_LEN:
        preview = preview[:_NOTE_PREVIEW_LEN].rsplit(" ", 1)[0]
    preview_escaped = html.escape(preview)
    ellipsis = "…" if len(preview) < len(note) else ""
    return (
        f'<details class="note"><summary>{preview_escaped}{ellipsis}</summary>'
        f"{escaped}</details>"
    )


def _bool_cell(value: bool | str) -> str:
    if value is True:
        return '<span class="bool-true">in-fishbowl</span>'
    if value is False:
        return '<span class="bool-false">out-of-fishbowl</span>'
    return f"<span>{html.escape(str(value))}</span>"


def render_html_report(data: ReportData, viz_dir: Path | None = Path("../viz")) -> str:
    """Render `data` as a single self-contained HTML page.

    Args:
        data: The shared report data structure.
        viz_dir: Relative path (from the report file's own location) to
            the Phase 1e visualization SVGs, or None to skip embedding
            them (e.g. if they haven't been generated yet).

    Returns:
        The full HTML document as a string.
    """
    stat_tiles = "".join(
        [
            _stat_tile(data.total_economies, "Economies in scope"),
            _stat_tile(data.total_asns, "ASNs in scope"),
            _stat_tile(data.asns_with_neighbors, "ASNs w/ RIS neighbor"),
            _stat_tile(data.asns_with_ixp, "ASNs w/ IXP membership"),
            _stat_tile(data.asns_with_facility, "ASNs w/ facility presence"),
            _stat_tile(
                f"{data.ixp_registry_in_fishbowl}/{data.ixp_registry_out_of_fishbowl}",
                "IXPs in/out of fishbowl",
            ),
        ]
    )

    transit_supplier_rows = "".join(
        f"""<tr>
            <td>AS{s['asn']}</td><td>{html.escape(s['name'])}</td>
            <td>{len(s['economies'])}</td>
            <td>{len(s['economies']) / data.total_economies:.0%}</td>
            <td>{s['corroboration_count']}</td>
            <td>{'yes' if s['is_regional'] else 'no'}</td>
            <td>{html.escape(', '.join(s['economies']))}</td>
        </tr>"""
        for s in data.transit_suppliers[:8]
    ) or "<p>(none recorded yet)</p>"

    satellite_rows = "".join(
        f"""<tr>
            <td>AS{s['asn']}</td><td>{html.escape(s['name'])}</td>
            <td>{html.escape(', '.join(s['ris_economies']) or '(none)')}</td>
            <td>{html.escape(', '.join(s['traceroute_confirmed_economies']) or '(none)')}</td>
        </tr>"""
        for s in data.satellite_pathways
    ) or "<p>(none recorded yet)</p>"

    detour_cards = "".join(
        f"""<div class="detour-card">
            <div class="headline">{html.escape(d['source_cc'])} -&gt; {html.escape(d['target_cc'])}
                (AS{d['target_asn']}): detours via {html.escape(d['detour_ix_name'])}
                ({html.escape(d['detour_hub'])})</div>
            <div>RIS observation count: {d['ris_observation_count']}
                &middot; measurement {d['measurement_id']}</div>
            {_note_block(d['note'])}
        </div>"""
        for d in data.confirmed_detours
    ) or "<p>(none recorded yet)</p>"

    transit_cards = "".join(
        f"""<div class="transit-card">
            <div class="headline">AS{t['provider_asn']} ({html.escape(t['provider_name'])},
                {html.escape(t['provider_cc'])}) -&gt; AS{t['customer_asn']}
                ({html.escape(t['customer_name'])}, {html.escape(t['customer_cc'])})</div>
            <div>RIS observation count: {t['ris_observation_count']}
                &middot; measurement {t['measurement_id']}
                &middot; vantage point {html.escape(t['vantage_point_cc'])}</div>
            {_note_block(t['note'])}
        </div>"""
        for t in data.confirmed_local_transit
    ) or "<p>(none recorded yet)</p>"

    candidate_cards = "".join(
        f"""<div class="candidate-card">
            <div class="headline">AS{c['upstream_asn']} ({html.escape(c['upstream_name'])},
                {html.escape(c['upstream_cc'])}) -&gt; AS{c['target_asn']}
                ({html.escape(c['target_name'])}, {html.escape(c['target_cc'])})</div>
            <div>Traceroute agreement: {html.escape(c['probe_agreement'])}
                &middot; measurement {c['measurement_id']}
                &middot; vantage point {html.escape(c['vantage_point_cc'])}</div>
            {_note_block(c['note'])}
        </div>"""
        for c in data.candidate_peering
    ) or "<p>(none recorded yet)</p>"

    economy_rows = "".join(
        f"""<tr>
            <td><span class="subregion-dot" style="background:{_SUBREGION_COLOR[e.subregion]}">
                </span>{html.escape(e.cc)}</td>
            <td>{html.escape(e.name)}</td>
            <td>{html.escape(e.subregion)}</td>
            <td>{e.asn_count}</td><td>{e.asns_with_neighbors}</td>
            <td>{e.asns_with_ixp}</td><td>{e.asns_with_facility}</td>
        </tr>"""
        for e in data.economies
    )

    ixp_rows = "".join(
        f"""<tr>
            <td>{html.escape(ix.name)}</td><td>{html.escape(ix.city)}</td>
            <td>{html.escape(ix.country)}</td><td>{_bool_cell(ix.in_fishbowl)}</td>
            <td>{ix.member_count}</td>
        </tr>"""
        for ix in data.ixps
    )

    viz_html = ""
    if viz_dir is not None:
        viz_html = f"""
        <h2>Visualizations</h2>
        <figure class="viz-figure">
            <img src="{viz_dir}/geographic_detours.svg" alt="Geographic map of confirmed detours">
            <figcaption>Confirmed detours: solid red = actual traceroute-confirmed path,
                dashed = direct-line comparison.</figcaption>
        </figure>
        <figure class="viz-figure">
            <img src="{viz_dir}/as_graph.svg" alt="AS dependency graph">
            <figcaption>ASN dependency graph: green edges stay in-fishbowl,
                red edges leave it.</figcaption>
        </figure>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Pacific Peering Report</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
    <h1>Pacific Peering — Regional Routing Report</h1>
    <div class="meta">Generated {html.escape(data.generated_at)}</div>

    <div class="headline-banner">
        <span class="value">{data.ixp_registry_out_of_fishbowl_share:.0%}</span>
        of the real peering points this region's own networks use sit
        <strong>outside</strong> the fish bowl
        ({data.ixp_registry_out_of_fishbowl} of
        {data.ixp_registry_in_fishbowl + data.ixp_registry_out_of_fishbowl})
    </div>

    <div class="stat-row">{stat_tiles}</div>

    <h2>Findings: transit supplier concentration</h2>
    <p class="section-intro">How many in-scope economies have at least one
        traceroute-confirmed corridor &mdash; as either the tested vantage
        point or the reachability target &mdash; that depends on a single
        carrier (RIS + Atlas confirmed immediate upstream). Counts
        confirmed, measured corridors only, not total internet exposure:
        most economies are likely multi-homed via paths this project
        hasn't measured. "Regional" marks a carrier itself based in an
        in-scope Pacific economy, rather than an external Tier-1.</p>
    <table>
        <thead><tr><th>ASN</th><th>Carrier</th><th>Economies</th><th>Share</th>
            <th>Corrob.</th><th>Regional</th><th>Which economies</th></tr></thead>
        <tbody>{transit_supplier_rows}</tbody>
    </table>
    <div class="callout">Two carriers don't crack the table above by raw
        economy count, but are the starkest single-point-of-failure
        findings this project has confirmed: <strong>AS9241 (FINTEL,
        Fiji)</strong> is Tuvalu's <em>only</em> RIS-observed neighbor of
        consequence, reconfirmed by 8 independent vantage points across
        the region; <strong>AS9471 (ONATI, French Polynesia)</strong>
        plays the identical role for Niue, also reconfirmed 8 times. For
        both, every measured path into that economy &mdash; from every
        direction this project has tested &mdash; passes through one
        single carrier.</div>

    <h2>Findings: satellite operator pathways</h2>
    <p class="section-intro">Which in-scope economies have a known
        relationship to a satellite operator, and how strong the evidence
        is. "RIS economies" is a real, BGP-observed neighbor relationship
        (this project's own fishbowl cache) that no traceroute has
        necessarily confirmed carries traffic; "traceroute-confirmed"
        means an Atlas traceroute has actually been observed transiting
        that operator's network.</p>
    <table>
        <thead><tr><th>ASN</th><th>Operator</th><th>RIS economies</th>
            <th>Traceroute-confirmed economies</th></tr></thead>
        <tbody>{satellite_rows}</tbody>
    </table>
    <div class="callout"><strong>The Kacific gap</strong>: Kacific
        Broadband Satellites (AS135409), a real PeeringDB-registered
        Pacific-focused GEO satellite ISP, has RIS-observed BGP
        relationships with at least three in-scope economies (Papua New
        Guinea, Tonga, and &mdash; visible only from Kacific's own
        neighbor list, not from the target's side, a real instance of
        RIS's asymmetric visibility &mdash; Solomon Islands). Despite
        that, <strong>no traceroute this project has ever run has touched
        Kacific's network at all</strong>. AS38201 (Tonga, Kacific-linked)
        sits untested in the current corridor backlog &mdash; a natural
        next target if a Kacific-transiting path is ever going to
        surface. Starlink and SES ASTRA, by contrast, have both been
        directly traceroute-confirmed (Tuvalu/Kiribati for Starlink;
        Cook Islands/Nauru for SES ASTRA).</div>

    <h2>Confirmed sub-optimal routes (RIS + Atlas both agree)</h2>
    {detour_cards}

    <h2>Confirmed local transit (RIS + Atlas both agree, stays in-fishbowl)</h2>
    {transit_cards}

    <h2>Candidate peering (strong traceroute signal, RIS disagrees &mdash; unconfirmed)</h2>
    {candidate_cards}

    {viz_html}

    <h2>Economies</h2>
    <table>
        <thead><tr><th>CC</th><th>Name</th><th>Subregion</th><th>ASNs</th>
            <th>w/ Neighbor</th><th>w/ IXP</th><th>w/ Facility</th></tr></thead>
        <tbody>{economy_rows}</tbody>
    </table>

    <h2>IXPs</h2>
    <table>
        <thead><tr><th>Name</th><th>City</th><th>CC</th><th>Region</th>
            <th>Members</th></tr></thead>
        <tbody>{ixp_rows}</tbody>
    </table>

    <footer class="about">
        <h2>About this project</h2>
        <p>{html.escape(FISHBOWL_EXPLANATION)}</p>
    </footer>
</div>
</body>
</html>
"""


def write_html_report(
    output_path: Path = DEFAULT_OUTPUT_PATH, viz_dir: Path | None = Path("../viz")
) -> Path:
    """Build report data, render it, and write it to `output_path`.

    Returns:
        The path the report was written to.
    """
    data = build_report_data()
    text = render_html_report(data, viz_dir=viz_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text)
    logger.info("Wrote HTML report to %s", output_path)
    return output_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    write_html_report()


if __name__ == "__main__":
    main()
