"""Confirmed sub-optimal-routing findings: real detours through an out-of-fishbowl IXP.

Curated by hand from this project's actual triangulation results (RIS +
Atlas both agreeing — Validation Rule 1), not auto-derived generically
yet: only a handful of measurements exist so far, and building a
generic auto-extraction pipeline before there's enough data to justify
one would be premature. Extend this list as more measurements get
triangulated.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfirmedDetour:
    """One real traceroute-confirmed detour through an out-of-fishbowl exchange."""

    source_cc: str
    target_cc: str
    target_asn: int
    detour_ix_name: str
    detour_hub: str  # key into discovery.economy_coordinates.EXTERNAL_HUB_LATLON
    measurement_id: int
    ris_observation_count: int
    note: str


CONFIRMED_DETOURS: tuple[ConfirmedDetour, ...] = (
    ConfirmedDetour(
        source_cc="GU",
        target_cc="PG",
        target_asn=17828,
        detour_ix_name="Equinix Sydney",
        detour_hub="Sydney",
        measurement_id=210901499,
        ris_observation_count=1283,
        note="Guam -> PNG DataCo (AS17828); upstream AS6939 confirmed by RIS+Atlas.",
    ),
    ConfirmedDetour(
        source_cc="NC",
        target_cc="FJ",
        target_asn=4638,
        detour_ix_name="MegaIX Sydney",
        detour_hub="Sydney",
        measurement_id=210919078,
        ris_observation_count=1669,
        note=(
            "New Caledonia -> Telecom Fiji (AS4638); upstream AS45349 confirmed "
            "by RIS+Atlas. Also IRR-corroborated: AS45349's own PeeringDB-declared "
            "AS-SET (AS45349:AS-TFL-TRANSIT) names AS4638 directly -- a declared "
            "transit intention, independently sourced (APNIC), matching what the "
            "traceroute actually shows."
        ),
    ),
    ConfirmedDetour(
        source_cc="NC",
        target_cc="FJ",
        target_asn=45355,
        detour_ix_name="Equinix Sydney",
        detour_hub="Sydney",
        measurement_id=210996533,
        ris_observation_count=1326,
        note=(
            "New Caledonia -> Digicel Fiji (AS45355); upstream AS132528 -- per the "
            "project owner, the Telstra-operated backbone ASN behind Digicel's "
            "Pacific mobile networks, registered in PeeringDB as 'Digicel "
            "Australia' -- confirmed by RIS+Atlas with an exact observation-count "
            "match (1,326) and a fully contiguous hop chain (AS18200, New "
            "Caledonia's own incumbent -> AS132528 at Equinix Sydney, exact "
            "netixlan address match -> AS45355). The strongest-evidenced finding "
            "in this project so far: also IRR-corroborated on *both* sides -- "
            "AS132528's declared AS-SET (AS-132528-PEERS) names AS45355 directly, "
            "and AS45355's own declared AS-SET (AS-45355-PEERS) names AS132528 "
            "right back -- a mutual, independently-sourced (APNIC) declaration "
            "matching the observed adjacency exactly. AS132528 was also seen at "
            "this same Equinix Sydney fabric in an earlier, unrelated measurement "
            "(210930962, the Zscaler-proxied Fiji probe test) -- two independent "
            "measurements, two different vantage points, same exchange presence."
        ),
    ),
)
