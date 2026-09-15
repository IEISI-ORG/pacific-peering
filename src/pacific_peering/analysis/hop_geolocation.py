"""Resolve a traceroute hop's real-world location from its router hostname.

Per the project owner: **router naming is far more reliable than picking
a facility off a carrier's PeeringDB list.** A carrier's PeeringDB
`netfac` entries describe everywhere that ASN has *some* presence — not
where any specific traceroute hop actually sits. Assigning a detour's
map location by picking one of the carrier's known cities (rather than
checking the hop itself) is how the PF->"Tokyo" mislabeling happened:
Cogent's and Tata's own router hostnames on those exact measurements
resolved to Los Angeles/San Francisco/Portland and Los Angeles/Guam
respectively — nowhere near Japan — but Tokyo got reused anyway because
it was a real, already-verified location *for that carrier*, just not
for that hop.

This module fixes that by geolocating hops from their own PTR records
instead. Most Tier-1/regional backbones embed a location token in
every router hostname (an IATA airport code, or a named city/facility
string) — reading that token is a much stronger signal than any
carrier-level fact. But there's no universal standard: every carrier
invents its own convention, so this can't be a generic decoder. It's a
hand-curated, evidence-gated pattern table, extended only when a hop
is actually resolved and checked during this project's own analysis —
never auto-generated from a generic IATA code list (a 3-letter
substring match without curation is a false-positive machine). Same
governance principle as `ixp_lan_registry.py` and
`regional_carrier_facilities.py`: real evidence only, scoped narrowly,
nothing assumed.
"""

from __future__ import annotations

import re
import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class HopLocation:
    """A real-world location a hop's hostname pattern is confirmed to indicate."""

    city: str
    economy_cc: str | None  # set only if one of the 20 in-scope economies (e.g. "GU")
    matched_pattern: str
    evidence_note: str


# Each pattern requires the token to sit at a hostname-segment boundary
# (bounded by '.', '-', or string start/end) to cut false-positive risk
# from an unbounded substring match.
_KNOWN_PATTERNS: tuple[tuple[re.Pattern[str], HopLocation], ...] = (
    (
        re.compile(r"(?:^|[.\-])lax\d*(?:[.\-]|$)", re.I),
        HopLocation(
            city="Los Angeles",
            economy_cc=None,
            matched_pattern="lax",
            evidence_note=(
                "Confirmed via Cogent (lax01.atlas.cogentco.com, measurement "
                "211668556, PF->AS9751)."
            ),
        ),
    ),
    (
        re.compile(r"(?:^|[.\-])losangeles(?:[.\-]|$)", re.I),
        HopLocation(
            city="Los Angeles",
            economy_cc=None,
            matched_pattern="losangeles",
            evidence_note=(
                "Confirmed via Tata (lvw-losangeles, measurement 211683854, "
                "PF->AS24439) -- Tata spells the city out rather than using "
                "Cogent's 'lax' IATA-code convention, hence a separate pattern."
            ),
        ),
    ),
    (
        re.compile(r"(?:^|[.\-])sjc\d*(?:[.\-]|$)", re.I),
        HopLocation(
            city="San Jose",
            economy_cc=None,
            matched_pattern="sjc",
            evidence_note=(
                "Confirmed via Cogent (sjc13.atlas.cogentco.com, measurement "
                "211976890, PG->AS45879) -- Cogent's IATA-code convention for "
                "San Jose, distinct from the 'lax'/'sfo'/'pdx' codes already "
                "on record."
            ),
        ),
    ),
    (
        re.compile(r"(?:^|[.\-])sfo\d*(?:[.\-]|$)", re.I),
        HopLocation(
            city="San Francisco",
            economy_cc=None,
            matched_pattern="sfo",
            evidence_note=(
                "Confirmed via Cogent (sfo01.atlas.cogentco.com, measurement "
                "211668556, PF->AS9751)."
            ),
        ),
    ),
    (
        re.compile(r"(?:^|[.\-])pdx\d*(?:[.\-]|$)", re.I),
        HopLocation(
            city="Portland",
            economy_cc=None,
            matched_pattern="pdx",
            evidence_note=(
                "Confirmed via Cogent (pdx02.atlas.cogentco.com, measurement "
                "211668556, PF->AS9751)."
            ),
        ),
    ),
    (
        re.compile(r"(?:^|[.\-])piti(?:[.\-]|$)", re.I),
        HopLocation(
            city="Piti, Guam",
            economy_cc="GU",
            matched_pattern="piti",
            evidence_note=(
                "Confirmed via Tata (pv4-piti, measurement 211683854, "
                "PF->AS24439) -- the same real cable-landing-station location "
                "already confirmed for OneQode's Guam facility."
            ),
        ),
    ),
    (
        re.compile(r"(?:^|[.\-])gu-gnc(?:[.\-]|$)", re.I),
        HopLocation(
            city="Guam",
            economy_cc="GU",
            matched_pattern="gu-gnc",
            evidence_note=(
                "Confirmed via OneQode (gu-gnc-rt1, measurement 211527961, "
                "MP->AS4638), matching OneQode's PeeringDB-listed 'RTI Guam "
                "GNC' facility exactly -- see analysis.regional_carrier_facilities."
            ),
        ),
    ),
    (
        re.compile(r"(?:^|[.\-])hk-mgi(?:[.\-]|$)", re.I),
        HopLocation(
            city="Hong Kong",
            economy_cc=None,
            matched_pattern="hk-mgi",
            evidence_note=(
                "Confirmed via OneQode (hk-mgi-rt1, measurement 211527961, "
                "MP->AS4638)."
            ),
        ),
    ),
)


def resolve_hostname(hostname: str) -> HopLocation | None:
    """Match a router hostname against the curated pattern table.

    Returns `None` rather than guessing when no known pattern matches --
    an unrecognized hostname is real information (this project hasn't
    seen this carrier's naming convention yet), not something to paper
    over with a carrier-level facility guess.
    """
    for pattern, location in _KNOWN_PATTERNS:
        if pattern.search(hostname):
            return location
    return None


def geolocate_hop(ip: str) -> HopLocation | None:
    """Reverse-resolve `ip` to a hostname, then match it against known patterns.

    Returns `None` on a PTR lookup failure (no reverse record) or when
    the hostname doesn't match any curated pattern -- both are genuine
    "we don't know" results, not errors to paper over.
    """
    try:
        hostname = socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror, OSError):
        return None
    return resolve_hostname(hostname)
