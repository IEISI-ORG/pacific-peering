"""Re-rendering an unchanged figure gives a byte-identical SVG.

matplotlib stamps the render time (`<dc:date>`) and salts clip-path ids
randomly, so every regeneration rewrote ~1000 lines of the committed SVGs
even when the map itself hadn't changed.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402

from pacific_peering.viz.as_graph import plot_as_graph  # noqa: E402


def test_as_graph_svg_is_byte_identical_across_renders(tmp_path: Path) -> None:
    graph = nx.Graph()
    graph.add_node("FJ", kind="economy", subregion="Melanesia")
    graph.add_node("TO", kind="economy", subregion="Polynesia")
    graph.add_node("AU", kind="external")
    graph.add_node("WF", kind="economy", subregion="Polynesia")
    graph.add_edge("FJ", "TO", leaves_fishbowl=False)
    graph.add_edge("FJ", "AU", leaves_fishbowl=True)

    first = plot_as_graph(graph, tmp_path / "a.svg").read_bytes()
    second = plot_as_graph(graph, tmp_path / "b.svg").read_bytes()

    assert first == second
    assert b"<dc:date>" not in first


def test_save_svg_leaves_global_rcparams_alone(tmp_path: Path) -> None:
    from pacific_peering.viz import save_svg

    before = plt.rcParams["svg.hashsalt"]
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    save_svg(fig, tmp_path / "x.svg")

    assert plt.rcParams["svg.hashsalt"] == before
