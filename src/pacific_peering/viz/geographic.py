"""Geographic map of confirmed sub-optimal-routing detours (Phase 1e).

Plots every in-scope economy at its capital city, plus any out-of-
fishbowl hub involved in a confirmed detour (currently just Sydney),
and draws each `ConfirmedDetour` as an actual bent path (source -> hub
-> target) next to a dashed straight line showing what a direct route
would look like — the visual form of this project's central finding.

No basemap/coastline library (avoids a heavy new dependency like
cartopy for a first version) — a plain lat/lon scatter is enough to
make the point; add real map tiles later if this needs to look more
polished for a presentation.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from pacific_peering.analysis.confirmed_detours import CONFIRMED_DETOURS
from pacific_peering.discovery.economies import ECONOMIES_BY_CC
from pacific_peering.discovery.economy_coordinates import ECONOMY_LATLON, EXTERNAL_HUB_LATLON

DEFAULT_OUTPUT_PATH = Path("outputs/viz/geographic_detours.svg")

# dataviz skill's validated categorical slots 1/2/3 (blue/orange/aqua) —
# the set that clears all-pairs CVD floors, appropriate for a scatter.
_SUBREGION_COLOR = {
    "Melanesia": "#2a78d6",
    "Polynesia": "#eb6834",
    "Micronesia": "#1baf7a",
}
_STATUS_CRITICAL = "#d03b3b"
_MUTED = "#898781"
_INK = "#0b0b0b"


def _shifted_lon(lon: float) -> float:
    """Shift negative Pacific longitudes onto a continuous ~130-215 range.

    Several in-scope economies sit just east of the antimeridian
    (e.g. Samoa at -171.75) while most sit just west of it (e.g. Fiji
    at 178.44) — plotting raw longitude would split them to opposite
    ends of the chart despite being geographically close.
    """
    return lon if lon > 0 else lon + 360


def plot_confirmed_detours(output_path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    """Render the geographic detour map and save it to `output_path`.

    Returns:
        The path the figure was saved to.
    """
    fig, ax = plt.subplots(figsize=(11, 7))
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")

    for cc, (lat, lon) in ECONOMY_LATLON.items():
        economy = ECONOMIES_BY_CC[cc]
        color = _SUBREGION_COLOR[economy.subregion]
        x = _shifted_lon(lon)
        ax.scatter([x], [lat], s=70, color=color, zorder=3, edgecolors="white", linewidths=0.6)
        ax.annotate(
            cc, (x, lat), textcoords="offset points", xytext=(5, 4), fontsize=8, color=_INK
        )

    for hub_name, (lat, lon) in EXTERNAL_HUB_LATLON.items():
        x = _shifted_lon(lon)
        ax.scatter(
            [x], [lat], s=110, color=_STATUS_CRITICAL, marker="s", zorder=3, edgecolors="white"
        )
        ax.annotate(
            hub_name,
            (x, lat),
            textcoords="offset points",
            xytext=(6, -10),
            fontsize=8,
            color=_STATUS_CRITICAL,
            fontweight="bold",
        )

    for detour in CONFIRMED_DETOURS:
        src_lat, src_lon = ECONOMY_LATLON[detour.source_cc]
        tgt_lat, tgt_lon = ECONOMY_LATLON[detour.target_cc]
        hub_lat, hub_lon = EXTERNAL_HUB_LATLON[detour.detour_hub]
        sx, tx, hx = _shifted_lon(src_lon), _shifted_lon(tgt_lon), _shifted_lon(hub_lon)

        # Direct route, for comparison: dashed, muted.
        ax.plot(
            [sx, tx], [src_lat, tgt_lat], linestyle="--", linewidth=1.2, color=_MUTED, zorder=1
        )
        # Actual confirmed path: solid, flagged.
        ax.plot(
            [sx, hx, tx],
            [src_lat, hub_lat, tgt_lat],
            linestyle="-",
            linewidth=1.8,
            color=_STATUS_CRITICAL,
            zorder=2,
        )

    ax.set_xlabel("longitude (shifted east of antimeridian)", color=_MUTED, fontsize=9)
    ax.set_ylabel("latitude", color=_MUTED, fontsize=9)
    ax.tick_params(colors=_MUTED, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("#e1e0d9")
    ax.grid(True, color="#e1e0d9", linewidth=0.6)
    ax.set_title(
        "Confirmed detours through out-of-fishbowl exchanges\n"
        "(solid red = actual traceroute-confirmed path; dashed = direct-line comparison)",
        fontsize=11,
        color=_INK,
        loc="left",
    )

    legend_handles = [
        plt.Line2D(
            [0], [0], marker="o", color="w", markerfacecolor=color, markersize=9, label=subregion
        )
        for subregion, color in _SUBREGION_COLOR.items()
    ]
    legend_handles.append(
        plt.Line2D(
            [0],
            [0],
            marker="s",
            color="w",
            markerfacecolor=_STATUS_CRITICAL,
            markersize=9,
            label="out-of-fishbowl hub",
        )
    )
    ax.legend(handles=legend_handles, loc="lower left", fontsize=8, framealpha=0.9)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return output_path


def main() -> None:
    path = plot_confirmed_detours()
    print(f"Wrote geographic detour map to {path}")


if __name__ == "__main__":
    main()
