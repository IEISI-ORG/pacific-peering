"""Approximate lat/lon for each in-scope economy's capital/main city.

City-level accuracy, not per-ASN geolocation — good enough for a
regional overview map, not for claiming a specific network's precise
location. Used by `viz.geographic` to plot economies and draw routes.
"""

from __future__ import annotations

ECONOMY_LATLON: dict[str, tuple[float, float]] = {
    "FJ": (-18.1416, 178.4419),  # Suva
    "PG": (-9.4438, 147.1803),  # Port Moresby
    "SB": (-9.4280, 159.9498),  # Honiara
    "VU": (-17.7404, 168.3219),  # Port Vila
    "NC": (-22.2758, 166.4580),  # Nouméa
    "WS": (-13.8506, -171.7513),  # Apia
    "TO": (-21.1789, -175.1982),  # Nuku'alofa
    "PF": (-17.5516, -149.5585),  # Papeete
    "CK": (-21.2078, -159.7750),  # Avarua
    "NU": (-19.0545, -169.9187),  # Alofi
    "AS": (-14.2756, -170.7020),  # Pago Pago
    "WF": (-13.2825, -176.1743),  # Mata-Utu
    "TV": (-8.5211, 179.1962),  # Funafuti
    "GU": (13.4745, 144.7504),  # Hagåtña
    "FM": (6.9147, 158.1610),  # Palikir
    "PW": (7.5006, 134.6242),  # Ngerulmud
    "MH": (7.1164, 171.1858),  # Majuro
    "KI": (1.3382, 173.0176),  # Tarawa
    "NR": (-0.5477, 166.9209),  # Yaren
    "MP": (15.1780, 145.7500),  # Saipan
}

# Reference points outside the 20 in-scope economies, needed to draw
# confirmed out-of-fishbowl detour hubs on the same map.
EXTERNAL_HUB_LATLON: dict[str, tuple[float, float]] = {
    "Sydney": (-33.8688, 151.2093),
}
