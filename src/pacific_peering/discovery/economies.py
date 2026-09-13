"""Canonical list of in-scope Pacific economies for this project.

Scope: APNIC-covered Oceania economies in Melanesia, Polynesia, and
Micronesia, excluding Australia and New Zealand, excluding Hawaii (part of
the US, not a separate APNIC economy), including Guam. Confirmed with the
project owner as the standard APNIC/UN geoscheme grouping.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Economy:
    """A single in-scope Pacific economy.

    Attributes:
        name: Common name of the economy.
        cc: ISO 3166-1 alpha-2 country code, matching the `cc` field used in
            APNIC's delegated-extended stats file.
        subregion: One of "Melanesia", "Polynesia", "Micronesia".
    """

    name: str
    cc: str
    subregion: str


ECONOMIES: tuple[Economy, ...] = (
    # Melanesia
    Economy("Fiji", "FJ", "Melanesia"),
    Economy("Papua New Guinea", "PG", "Melanesia"),
    Economy("Solomon Islands", "SB", "Melanesia"),
    Economy("Vanuatu", "VU", "Melanesia"),
    Economy("New Caledonia", "NC", "Melanesia"),
    # Polynesia
    Economy("Samoa", "WS", "Polynesia"),
    Economy("Tonga", "TO", "Polynesia"),
    Economy("French Polynesia", "PF", "Polynesia"),
    Economy("Cook Islands", "CK", "Polynesia"),
    Economy("Niue", "NU", "Polynesia"),
    Economy("American Samoa", "AS", "Polynesia"),
    Economy("Wallis and Futuna", "WF", "Polynesia"),
    Economy("Tuvalu", "TV", "Polynesia"),
    # Micronesia (plus Guam, per project scope)
    Economy("Guam", "GU", "Micronesia"),
    Economy("Micronesia, Federated States of", "FM", "Micronesia"),
    Economy("Palau", "PW", "Micronesia"),
    Economy("Marshall Islands", "MH", "Micronesia"),
    Economy("Kiribati", "KI", "Micronesia"),
    Economy("Nauru", "NR", "Micronesia"),
    Economy("Northern Mariana Islands", "MP", "Micronesia"),
)

ECONOMIES_BY_CC: dict[str, Economy] = {economy.cc: economy for economy in ECONOMIES}
