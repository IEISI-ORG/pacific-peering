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
        note="New Caledonia -> Telecom Fiji (AS4638); upstream AS45349 confirmed by RIS+Atlas.",
    ),
)
