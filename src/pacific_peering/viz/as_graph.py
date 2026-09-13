"""AS-level dependency graph (Phase 1e): who peers with whom, and where it leaves the region.

Built directly from Phase 1a's RIS-observed neighbor data (`fishbowl.json`),
not invented — includes both layers actually present in that data:
same-economy hub-and-spoke (smaller local ISPs peering with their
national incumbent, e.g. several New Caledonia ASNs -> AS18200 O.P.T.)
and star-out edges to major external transit providers. Edge color
*is* the project's core distinction: green for an edge that stays
inside the fishbowl, red for one that leaves it — an ASN-to-ASN edge
where one endpoint isn't one of the 163 in-scope ASNs necessarily
crosses out of the study region.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

from pacific_peering.analysis.fishbowl import DEFAULT_SUMMARY_PATH

DEFAULT_OUTPUT_PATH = Path("outputs/viz/as_graph.svg")
DEFAULT_TOP_N_EXTERNAL = 15

_SUBREGION_COLOR = {
    "Melanesia": "#2a78d6",
    "Polynesia": "#eb6834",
    "Micronesia": "#1baf7a",
}
_EXTERNAL_COLOR = "#898781"
_EDGE_GOOD = "#0ca30c"
_EDGE_LEAVES = "#d03b3b"


def build_as_graph(
    fishbowl_path: Path = DEFAULT_SUMMARY_PATH, top_n_external: int = DEFAULT_TOP_N_EXTERNAL
) -> nx.Graph:
    """Build the AS-level graph: all in-scope ASNs plus the top-N external ASNs by weight.

    Args:
        fishbowl_path: Path to Phase 1a's `fishbowl.json`.
        top_n_external: Cap on how many external (out-of-registry) ASNs
            to include as nodes, by aggregate RIS-observation weight —
            keeps the graph legible; every in-scope ASN is included
            regardless of degree (an isolated node is itself information).

    Returns:
        A networkx Graph with node attrs `kind` ("economy"/"external"),
        `cc`/`subregion` (economy nodes only), and edge attr `weight`.
    """
    fishbowl = json.loads(fishbowl_path.read_text())
    in_scope = set(int(asn) for asn in fishbowl)

    external_weight: dict[int, int] = {}
    for entry in fishbowl.values():
        for neighbor, count in entry["neighbors"].items():
            neighbor_asn = int(neighbor)
            if neighbor_asn not in in_scope:
                external_weight[neighbor_asn] = external_weight.get(neighbor_asn, 0) + count
    top_external = {
        asn for asn, _w in sorted(external_weight.items(), key=lambda kv: -kv[1])[:top_n_external]
    }

    graph = nx.Graph()
    for asn_str, entry in fishbowl.items():
        asn = int(asn_str)
        graph.add_node(
            asn, kind="economy", cc=entry["economy"]["cc"], subregion=entry["economy"]["subregion"]
        )

    for asn_str, entry in fishbowl.items():
        asn = int(asn_str)
        for neighbor, count in entry["neighbors"].items():
            neighbor_asn = int(neighbor)
            if neighbor_asn in in_scope:
                graph.add_edge(asn, neighbor_asn, weight=count, leaves_fishbowl=False)
            elif neighbor_asn in top_external:
                graph.add_node(neighbor_asn, kind="external")
                graph.add_edge(asn, neighbor_asn, weight=count, leaves_fishbowl=True)

    return graph


def plot_as_graph(graph: nx.Graph, output_path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    """Render the AS-graph and save it to `output_path`.

    Returns:
        The path the figure was saved to.
    """
    isolated = [n for n in graph.nodes if graph.degree(n) == 0]
    connected = graph.subgraph([n for n in graph.nodes if graph.degree(n) > 0])

    fig, ax = plt.subplots(figsize=(14, 14))
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")

    pos = nx.spring_layout(connected, k=0.6, seed=42, weight=None)

    good_edges = [(u, v) for u, v, d in connected.edges(data=True) if not d["leaves_fishbowl"]]
    leaving_edges = [(u, v) for u, v, d in connected.edges(data=True) if d["leaves_fishbowl"]]
    nx.draw_networkx_edges(
        connected, pos, edgelist=good_edges, edge_color=_EDGE_GOOD, width=1.2, ax=ax
    )
    nx.draw_networkx_edges(
        connected, pos, edgelist=leaving_edges, edge_color=_EDGE_LEAVES, width=0.5, alpha=0.5, ax=ax
    )

    economy_nodes = [n for n, d in connected.nodes(data=True) if d["kind"] == "economy"]
    external_nodes = [n for n, d in connected.nodes(data=True) if d["kind"] == "external"]
    economy_colors = [_SUBREGION_COLOR[connected.nodes[n]["subregion"]] for n in economy_nodes]

    nx.draw_networkx_nodes(
        connected, pos, nodelist=economy_nodes, node_color=economy_colors, node_size=70, ax=ax
    )
    nx.draw_networkx_nodes(
        connected,
        pos,
        nodelist=external_nodes,
        node_color=_EXTERNAL_COLOR,
        node_size=160,
        node_shape="s",
        ax=ax,
    )

    # Label external ASNs (always — there are only up to top_n_external of
    # them) and the highest-degree economy ASNs (the actual local hubs,
    # e.g. AS17828/AS18200) — labeling every economy node would be
    # unreadable at this density, but the hubs are the interesting part.
    hub_threshold = 5
    hub_labels = {
        n: str(n) for n in economy_nodes if connected.degree(n) >= hub_threshold
    }
    external_labels = {n: str(n) for n in external_nodes}
    nx.draw_networkx_labels(connected, pos, labels=external_labels, font_size=7, ax=ax)
    nx.draw_networkx_labels(
        connected, pos, labels=hub_labels, font_size=7, font_weight="bold", ax=ax
    )

    ax.set_title(
        "In-scope ASN dependency graph — green edges stay in-region, red edges leave it\n"
        f"(top {DEFAULT_TOP_N_EXTERNAL} external ASNs by weight; bold labels = local hub ASNs, "
        f"degree >= {hub_threshold}; {len(isolated)} ASNs with no observed neighbor omitted)",
        fontsize=11,
        color="#0b0b0b",
        loc="left",
    )
    ax.axis("off")

    legend_handles = [
        plt.Line2D(
            [0], [0], marker="o", color="w", markerfacecolor=color, markersize=8, label=subregion
        )
        for subregion, color in _SUBREGION_COLOR.items()
    ] + [
        plt.Line2D(
            [0], [0], marker="s", color="w", markerfacecolor=_EXTERNAL_COLOR, markersize=8,
            label="external ASN",
        ),
        plt.Line2D([0], [0], color=_EDGE_GOOD, linewidth=2, label="stays in-fishbowl"),
        plt.Line2D([0], [0], color=_EDGE_LEAVES, linewidth=2, label="leaves fishbowl"),
    ]
    ax.legend(handles=legend_handles, loc="lower left", fontsize=8, framealpha=0.9)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return output_path


def main() -> None:
    graph = build_as_graph()
    path = plot_as_graph(graph)
    print(
        f"Wrote AS-graph to {path} "
        f"({graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges)"
    )


if __name__ == "__main__":
    main()
