"""Satellite operators this project has checked for, with their orbit.

Hand-curated, a small and stable set: RIS and PeeringDB data carry no
reliable "this ASN is a satellite operator" signal. The orbit matters for
reading latency: a geostationary (GEO) hop adds about half a second of
round trip on its own (the echo crosses roughly 36,000 km four times), a
low-earth-orbit (LEO) hop only tens of milliseconds. SES runs both GEO
(Astra and others) and MEO (O3b) fleets, and one AS covers both.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SatelliteOperator:
    name: str
    orbit: str  # "GEO", "LEO", or "GEO or MEO" when one AS runs both


SATELLITE_OPERATORS: dict[int, SatelliteOperator] = {
    14593: SatelliteOperator("SpaceX Starlink", "LEO"),
    12684: SatelliteOperator("SES ASTRA S.A.", "GEO or MEO"),
    135409: SatelliteOperator("Kacific Broadband Satellites", "GEO"),
}
