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

from pacific_peering.reports.data import ReportData, build_report_data

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("outputs/reports/report.html")

# Same tokens as the Phase 1e visualizations (dataviz skill's validated palette).
_INK = "#0b0b0b"
_MUTED = "#898781"
_SURFACE = "#fcfcfb"
_GOOD = "#0ca30c"
_CRITICAL = "#d03b3b"
_SUBREGION_COLOR = {"Melanesia": "#2a78d6", "Polynesia": "#eb6834", "Micronesia": "#1baf7a"}

_CSS = f"""
body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background: {_SURFACE};
        color: {_INK}; margin: 0; padding: 24px; line-height: 1.5; }}
.wrap {{ max-width: 980px; margin: 0 auto; }}
h1 {{ font-size: 1.5rem; margin-bottom: 0.2em; }}
.meta {{ color: {_MUTED}; font-size: 0.85rem; margin-bottom: 1.5em; }}
h2 {{ font-size: 1.1rem; border-bottom: 1px solid #e1e0d9; padding-bottom: 0.3em;
      margin-top: 2em; }}
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
.bool-true {{ color: {_GOOD}; font-weight: 600; }}
.bool-false {{ color: {_CRITICAL}; }}
.viz-figure {{ margin: 1.5em 0; }}
.viz-figure img {{ max-width: 100%; border: 1px solid #e1e0d9; border-radius: 6px; }}
.viz-figure figcaption {{ color: {_MUTED}; font-size: 0.8rem; margin-top: 6px; }}
"""


def _stat_tile(value: object, label: str) -> str:
    return (
        f'<div class="stat-tile"><div class="value">{html.escape(str(value))}</div>'
        f'<div class="label">{html.escape(label)}</div></div>'
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

    detour_cards = "".join(
        f"""<div class="detour-card">
            <div class="headline">{html.escape(d['source_cc'])} -&gt; {html.escape(d['target_cc'])}
                (AS{d['target_asn']}): detours via {html.escape(d['detour_ix_name'])}
                ({html.escape(d['detour_hub'])})</div>
            <div>RIS observation count: {d['ris_observation_count']}
                &middot; measurement {d['measurement_id']}</div>
            <div class="note">{html.escape(d['note'])}</div>
        </div>"""
        for d in data.confirmed_detours
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

    <div class="stat-row">{stat_tiles}</div>

    <h2>Confirmed sub-optimal routes (RIS + Atlas both agree)</h2>
    {detour_cards}

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
