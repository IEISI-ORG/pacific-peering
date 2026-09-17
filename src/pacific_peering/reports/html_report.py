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
details.section-toggle {{ margin-top: 2em; }}
details.section-toggle > summary {{ font-size: 1.1rem; font-weight: 600; cursor: pointer;
      border-bottom: 1px solid #e1e0d9; padding-bottom: 0.3em; list-style: none; }}
details.section-toggle > summary::-webkit-details-marker {{ display: none; }}
details.section-toggle > summary::before {{ content: "▶ "; font-size: 0.8em; }}
details.section-toggle[open] > summary::before {{ content: "▼ "; }}
details.section-toggle > summary .count {{ font-weight: 400; color: {_MUTED}; }}
.headline-banner {{ background: #fdecec; border: 1px solid {_CRITICAL}; border-radius: 8px;
              padding: 14px 18px; margin: 1em 0; font-size: 1.05rem; }}
.headline-banner .value {{ font-weight: 700; color: {_CRITICAL}; }}
.stat-row {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 1em 0; }}
.stat-tile {{ background: white; border: 1px solid #e1e0d9; border-radius: 8px;
              padding: 10px 16px; min-width: 140px; }}
.stat-tile .value {{ font-size: 1.4rem; font-weight: 600; }}
.stat-tile .label {{ font-size: 0.78rem; color: {_MUTED}; }}
.stat-tile.red-box {{ background: #fdecec; border-color: {_CRITICAL}; }}
.stat-tile.red-box .value {{ color: {_CRITICAL}; }}
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
.issue-card {{ border-left: 4px solid {_MUTED}; background: #f4f4f2; padding: 10px 14px;
                margin-bottom: 10px; border-radius: 4px; }}
.issue-card .headline {{ font-weight: 600; }}
.issue-card .headline .count {{ font-weight: 400; color: {_MUTED}; font-size: 0.8rem; }}
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
            <td>{html.escape(', '.join(s['dependent_economies']) or '(none)')}</td>
            <td>{html.escape(', '.join(s['vantage_only_economies']) or '(none)')}</td>
            <td>{s['corroboration_count']}</td>
            <td>{'yes' if s['is_regional'] else 'no'}</td>
        </tr>"""
        for s in data.transit_suppliers[:8]
    ) or "<p>(none recorded yet)</p>"

    total_detours = len(data.confirmed_detours)
    subregion_of = {e.cc: e.subregion for e in data.economies}
    regional_hub_rows = "".join(
        f"""<tr>
            <td>{html.escape(h['economy_name'])} ({html.escape(h['economy_cc'])})</td>
            <td>{len(h['dependent_economies'])}</td>
            <td>{h['corroboration_count']}</td>
            <td>{html.escape(', '.join(sorted({subregion_of.get(cc) for cc in h['dependent_economies']} - {None})))}</td>
            <td>{html.escape(', '.join(h['carriers']))}</td>
            <td>{html.escape(', '.join(h['dependent_economies']))}</td>
        </tr>"""
        for h in data.regional_hubs
    ) or "<p>(none recorded yet)</p>"

    external_hub_rows = "".join(
        f"""<tr>
            <td>{html.escape(h['name'])}</td>
            <td>{h['entry_count']}</td>
            <td>{h['entry_count'] / total_detours if total_detours else 0:.0%}</td>
            <td>{h['carrier_count']}</td>
            <td>{html.escape(', '.join(sorted({subregion_of.get(cc) for cc in h['dependent_economies']} - {None})))}</td>
            <td>{html.escape(', '.join(h['dependent_economies']))}</td>
        </tr>"""
        for h in data.external_hubs
    ) or "<p>(none recorded yet)</p>"
    top3_hub_share = (
        sum(h["entry_count"] for h in data.external_hubs[:3]) / total_detours
        if total_detours
        else 0
    )

    satellite_rows = "".join(
        f"""<tr>
            <td>AS{s['asn']}</td><td>{html.escape(s['name'])}</td>
            <td>{html.escape(', '.join(sorted({subregion_of.get(cc) for cc in set(s['ris_economies']) | set(s['traceroute_confirmed_economies'])} - {None})))}</td>
            <td>{html.escape(', '.join(s['ris_economies']) or '(none)')}</td>
            <td>{html.escape(', '.join(s['traceroute_confirmed_economies']) or '(none)')}</td>
            <td>{html.escape(', '.join(s['traceroute_vantage_economies']) or '(none)')}</td>
        </tr>"""
        for s in data.satellite_pathways
    ) or "<p>(none recorded yet)</p>"
    satellite_narrative_items = "".join(
        f"<li>{html.escape(n)}</li>" for n in data.satellite_narrative
    )

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

    pathway_coverage_rows = "".join(
        f"""<tr>
            <td>{html.escape(p.cc)}</td><td>{html.escape(p.name)}</td>
            <td>{html.escape(p.subregion)}</td>
            <td>{p.asn_count}</td><td>{p.active_probes}</td><td>{p.untested_pathways}</td>
        </tr>"""
        for p in data.pathway_coverage
    )

    peeringdb_economy_rows = "".join(
        f"""<tr>
            <td>{html.escape(e.cc)}</td><td>{html.escape(e.name)}</td>
            <td>{e.asn_count}</td><td>{e.on_peeringdb}</td>
            <td>{e.with_facility}</td><td>{e.with_ixp}</td>
        </tr>"""
        for e in data.peeringdb_economies
        if e.on_peeringdb
    ) or "<p>(no in-scope ASN is on PeeringDB)</p>"

    data_quality_issue_blocks = "".join(
        f"""<div class="issue-card">
            <div class="headline">{html.escape(issue.title)}
                <span class="count">[{html.escape(issue.category_label)}]</span></div>
            {_note_block(issue.description)}
        </div>"""
        for issue in data.data_quality_issues
    ) or "<p>(none recorded yet)</p>"

    aspa_economy_rows = "".join(
        f"""<tr>
            <td>{html.escape(e.cc)}</td><td>{html.escape(e.name)}</td>
            <td>{e.asn_count}</td><td>{e.asns_with_aspa}</td>
            <td>{e.unique_upstream_in_fishbowl}</td>
            <td>{e.unique_upstream_out_of_fishbowl}</td>
        </tr>"""
        for e in data.aspa_economies
        if e.asns_with_aspa
    ) or "<p>(no in-scope ASN publishes an ASPA record yet)</p>"

    ipv6_economy_rows = "".join(
        f"""<tr>
            <td>{html.escape(e.cc)}</td><td>{html.escape(e.name)}</td>
            <td>{e.asn_count}</td><td>{e.asns_with_ipv6}</td>
        </tr>"""
        for e in data.ipv6_economies
        if e.asns_with_ipv6
    ) or "<p>(no in-scope ASN has an RIS-observed IPv6 prefix yet)</p>"

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

    <div class="stat-row">
        {_stat_tile(data.pathways_total, "Pathways found (total)")}
        {_stat_tile(data.pathways_internal, "Internal (never leave the fish bowl)")}
        <div class="stat-tile red-box"><div class="value">{data.pathways_external}</div>
            <div class="label">External / Leaves the region</div></div>
    </div>
    <p class="section-intro">Full corridor-by-corridor detail for all
        {data.pathways_total} pathways above is further down this report
        (Confirmed sub-optimal routes / Confirmed local transit / Candidate
        peering), collapsed by default so it doesn't dominate the page &mdash;
        click any of those section headings to expand.</p>

    <div class="stat-row">{stat_tiles}</div>

    <h2>Economies</h2>
    <table>
        <thead><tr><th>CC</th><th>Name</th><th>Subregion</th><th>ASNs</th>
            <th>w/ Neighbor</th><th>w/ IXP</th><th>w/ Facility</th></tr></thead>
        <tbody>{economy_rows}</tbody>
    </table>

    <h2>Findings: transit supplier concentration</h2>
    <p class="section-intro">Ranked by <strong>dependent</strong> economies
        &mdash; those whose own reachability this carrier was confirmed as
        the immediate upstream for &mdash; not by every economy a
        measurement happened to be fired from. <strong>Vantage-only</strong>
        economies merely tested a path through this carrier to reach a
        dependent economy elsewhere; they have no confirmed reliance on it
        themselves. This split exists because a single-island submarine-
        cable operator like SISCC was otherwise misreading as a broad
        regional concentration risk, when almost every economy in its count
        was just a vantage point testing a path to Solomon Islands. Counts
        confirmed, measured corridors only, not total internet exposure:
        most economies are likely multi-homed via paths this project
        hasn't measured. "Regional" marks a carrier itself based in an
        in-scope Pacific economy, rather than an external Tier-1.</p>
    <table>
        <thead><tr><th>ASN</th><th>Carrier</th><th>Dependent economies</th>
            <th>Vantage-only economies</th><th>Corrob.</th>
            <th>Regional</th></tr></thead>
        <tbody>{transit_supplier_rows}</tbody>
    </table>
    <div class="callout"><strong>AS9241 (FINTEL, Fiji)</strong> doesn't
        crack the table above by dependent-economy count (just Tuvalu),
        but is the starkest single-point-of-failure finding this project
        has confirmed: it's Tuvalu's <em>only</em> RIS-observed neighbor of
        consequence, reconfirmed by 8 independent vantage points across
        the region. Every measured path into Tuvalu &mdash; from every
        direction this project has tested &mdash; passes through one
        single carrier.</div>

    <h2>Findings: regional hub concentration</h2>
    <p class="section-intro">Which in-scope Pacific economies serve as a
        real transit waypoint for <strong>other</strong> in-scope
        economies, entirely inside the fishbowl &mdash; the mirror image
        of transit supplier concentration above, but for carriers based
        in the region rather than external Tier-1s. Built from
        <code>ConfirmedLocalTransit</code> entries where the provider and
        customer are different economies. "Corrob." sums each underlying
        relationship's own corroboration depth, so an economy serving two
        economies each reconfirmed many times outranks one serving two
        economies confirmed only once each.</p>
    <table>
        <thead><tr><th>Economy</th><th>Serves</th><th>Corrob.</th>
            <th>Subregions served</th><th>Carriers</th>
            <th>Which economies</th></tr></thead>
        <tbody>{regional_hub_rows}</tbody>
    </table>

    <h2>Findings: external hub concentration</h2>
    <p class="section-intro">The mirror image of the regional hubs above:
        the real external cities where confirmed detours physically leave
        the fishbowl. Every confirmed detour names one
        (<code>detour_hub</code>, set from actual hop evidence or a real
        IXP-LAN address match, never a carrier-level guess). Ranked by
        how many confirmed detours cross there. "Carriers" is how many
        distinct confirmed-upstream ASNs have been observed crossing at
        that city &mdash; a high count means a genuine shared crossroads,
        not one carrier's path repeated.</p>
    <table>
        <thead><tr><th>City</th><th>Entries</th><th>Share</th>
            <th>Carriers</th><th>Subregions reached</th>
            <th>Dependent economies</th></tr></thead>
        <tbody>{external_hub_rows}</tbody>
    </table>
    <div class="callout">Just the top 3 cities above account for
        <strong>{top3_hub_share:.0%}</strong> of every confirmed detour
        this project has recorded &mdash; almost the entire region's
        out-of-fishbowl traffic funnels through three physical places.</div>

    <h2>Findings: satellite operator pathways</h2>
    <p class="section-intro">Which in-scope economies have a known
        relationship to a satellite operator, and how strong the evidence
        is. "RIS economies" is a real, BGP-observed neighbor relationship
        (this project's own fishbowl cache) that no traceroute has
        necessarily confirmed carries traffic; "traceroute-confirmed"
        means an Atlas traceroute has actually been observed transiting
        that operator's network.</p>
    <table>
        <thead><tr><th>ASN</th><th>Operator</th><th>Subregions reached</th>
            <th>RIS economies</th>
            <th>Traceroute-confirmed (served)</th>
            <th>Tested from (vantage points)</th></tr></thead>
        <tbody>{satellite_rows}</tbody>
    </table>
    <div class="callout"><strong>Per-operator evidence summary</strong>,
        computed fresh from the current finding dataclasses every
        regeneration &mdash; &ldquo;served&rdquo; means the economy's own
        reachability was confirmed to depend on this operator;
        &ldquo;vantage points&rdquo; just means a traceroute was fired
        from there, which is a measure of testing breadth, not reach:
        <ul>{satellite_narrative_items}</ul>
    </div>

    <details class="section-toggle">
        <summary>Confirmed sub-optimal routes (RIS + Atlas both agree)
            <span class="count">({len(data.confirmed_detours)})</span></summary>
        {detour_cards}
    </details>

    <details class="section-toggle">
        <summary>Confirmed local transit (RIS + Atlas both agree, stays in-fishbowl)
            <span class="count">({len(data.confirmed_local_transit)})</span></summary>
        {transit_cards}
    </details>

    <details class="section-toggle">
        <summary>Candidate peering (strong traceroute signal, RIS disagrees &mdash; unconfirmed)
            <span class="count">({len(data.candidate_peering)})</span></summary>
        {candidate_cards}
    </details>

    <h2>PeeringDB data quality</h2>
    <p class="section-intro">
        <strong>{data.peeringdb_asns_on_pdb} of {data.total_asns}</strong> in-scope ASNs have a
        PeeringDB <code>net</code> record at all. "Zero facilities"/"zero IXP memberships"
        elsewhere in this report can mean either of two very different things: this ASN was
        never on PeeringDB to begin with, or it <em>is</em> registered and simply declared
        nothing. The two columns below are counted against ASNs that are on PeeringDB, not
        against every in-scope ASN, so they show the real gap rather than re-blending the two.
    </p>
    <table>
        <thead><tr><th>CC</th><th>Name</th><th>ASNs</th><th>On PeeringDB</th>
            <th>w/ Facility</th><th>w/ IXP</th></tr></thead>
        <tbody>{peeringdb_economy_rows}</tbody>
    </table>
    <div class="callout"><strong>AS12684 (SES Astra)</strong> and
        <strong>AS3549</strong> (the former Global Crossing backbone ASN) are both real,
        traceroute-confirmed carriers this project has on record with zero PeeringDB
        facilities &mdash; PeeringDB's own coverage gap, not a measurement gap here.</div>
    <!-- TODO: PeeringDB net-record `updated` staleness (a registered-but-
         abandoned org is weaker evidence than a maintained one) -- deferred,
         not in this pass. -->

    <h2>ASPA progress (RFC 9582 upstream-authorization adoption)</h2>
    <p class="section-intro">
        <strong>{data.aspa_asns_with_record} of {data.total_asns}</strong> in-scope ASNs
        now publish an ASPA record ({data.aspa_global_total_records} total across the
        whole internet, per Cloudflare Radar). Adoption is still early &mdash; absence
        means "not published yet," not "no real upstream." Per economy: how many of its
        own ASNs publish a record, and the distinct upstream ASNs those records declare,
        split by whether the declared provider is itself an in-scope Pacific ASN or an
        external carrier.
    </p>
    <table>
        <thead><tr><th>CC</th><th>Name</th><th>ASNs</th><th>w/ ASPA</th>
            <th>Upstream (in-fishbowl)</th><th>Upstream (external)</th></tr></thead>
        <tbody>{aspa_economy_rows}</tbody>
    </table>
    <!-- TODO: once enough ASPA-confirmed findings exist, add a "certified
         supply" marker to the Confirmed Local Transit / Candidate Peering
         sections above so an ASPA-backed confirmation is visually
         distinguishable from a RIS-agreement-only one (see
         store.mark_aspa_checked's aspa_confirmed field, already tracked). -->

    <h2>IPv6 coverage</h2>
    <p class="section-intro">
        Adoption signal only &mdash; this project deliberately isn't testing IPv6 corridors
        yet, queued until adoption has advanced further.
        <strong>{data.ipv6_asns_with_routes} of {data.total_asns}</strong> in-scope ASNs
        have at least one RIS-observed IPv6-originated prefix.
        <strong>{data.ipv6_probes_working} of {data.ipv6_probes_total}</strong> connected
        Atlas probes work over IPv6 ({data.ipv6_probes_capable_not_working} more are
        IPv6-capable but tagged as not working).
    </p>
    <table>
        <thead><tr><th>CC</th><th>Name</th><th>ASNs</th><th>w/ IPv6</th></tr></thead>
        <tbody>{ipv6_economy_rows}</tbody>
    </table>
    <!-- TODO: IPv6 corridor testing (traceroute/RIS validation over v6) --
         deliberately deferred per the project owner until adoption advances
         further. Revisit once the ASN/probe counts above look meaningfully
         higher. -->

    {viz_html}

    <h2>IXPs</h2>
    <table>
        <thead><tr><th>Name</th><th>City</th><th>CC</th><th>Region</th>
            <th>Members</th></tr></thead>
        <tbody>{ixp_rows}</tbody>
    </table>

    <h2>Pathway coverage</h2>
    <p class="section-intro">How many of this economy's own ASNs have a connected Atlas
        probe (zero means it can never be a traceroute source, only ever reached as a
        target) and how many of the other 19 in-scope economies still have zero finding
        connecting to it &mdash; see the pathway counts at the top of this report for the
        region-wide totals this is derived from.</p>
    <table>
        <thead><tr><th>CC</th><th>Name</th><th>Subregion</th><th>ASNs</th>
            <th>Active probes</th><th>Untested pathways</th></tr></thead>
        <tbody>{pathway_coverage_rows}</tbody>
    </table>

    <h2>Appendix: Low data quality issues
        <span class="count">({len(data.data_quality_issues)} known, resolved)</span></h2>
    <p class="section-intro">Known problems in this project's underlying sources
        (APNIC delegation, PeeringDB, ASPA, etc.) that have already been found,
        verified, and corrected for elsewhere in the pipeline &mdash; kept visible
        here rather than left implicit, so the counts and tables earlier in this
        report can be trusted without re-deriving why they exclude what they
        exclude.</p>
    {data_quality_issue_blocks}

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
