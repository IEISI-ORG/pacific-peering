"""Deterministic SVG output for the committed figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

_HASH_SALT = "pacific-peering"


def save_svg(fig: Figure, output_path: Path) -> Path:
    """Save `fig` so an unchanged figure re-renders byte-identical.

    matplotlib otherwise stamps the render time (`<dc:date>`) and salts
    clip-path ids randomly, so every regeneration of a committed SVG was a
    ~1000-line diff even when the figure hadn't changed.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"svg.hashsalt": _HASH_SALT}):
        fig.savefig(output_path, bbox_inches="tight", dpi=150, metadata={"Date": None})
    return output_path
