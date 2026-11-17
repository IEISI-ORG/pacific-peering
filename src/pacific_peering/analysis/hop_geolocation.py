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
from dataclasses import dataclass

from pacific_peering.analysis.ptr_lookup import reverse_dns


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
        re.compile(r"(?:^|[.\-])syd\d*(?:[.\-]|$)", re.I),
        HopLocation(
            city="Sydney",
            economy_cc=None,
            matched_pattern="syd",
            evidence_note=(
                "Confirmed via Cogent (ccr71.syd01.atlas.cogentco.com and "
                "agr51.syd01.atlas.cogentco.com, measurement 212005827, "
                "PW->AS17993) -- Cogent's IATA-code convention for Sydney, "
                "matching the same city already used (by carrier-facility "
                "guess, not hop evidence) for the earlier GU->AS17993 Cogent "
                "entry; this measurement is the first hop-level confirmation "
                "that guess was actually correct."
            ),
        ),
    ),
    (
        re.compile(r"(?:^|[.\-])nsw(?:[.\-]|$)", re.I),
        HopLocation(
            city="Sydney",
            economy_cc=None,
            matched_pattern="nsw",
            evidence_note=(
                "Confirmed via AARNet (et-3-0-2.pe1.alxd.nsw.aarnet.net.au, "
                "measurement 212013476, PW->AS24390) -- AARNet spells out the "
                "Australian state (New South Wales, i.e. Sydney metro) rather "
                "than using an IATA code, hence a separate pattern from "
                "Cogent's/Telia's 'syd'/'lax' convention. The same hop also "
                "shows the next leg direct to Fiji (`pe1.a.suv.aarnet.net.au` "
                "-- Suva), real hostname confirmation that AARNet's Sydney "
                "presence is the actual detour hub for every AS7575<->AS24390 "
                "entry, not just a carrier-facility guess."
            ),
        ),
    ),
    (
        re.compile(r"(?:^|[.\-])[a-z]{2}\d-tokyo(?:[.\-]|$)", re.I),
        HopLocation(
            city="Tokyo",
            economy_cc=None,
            matched_pattern="tokyo",
            evidence_note=(
                "Confirmed via Tata (if-bundle-16-2.qcore1.tv2-tokyo.as6453.net "
                "and if-ae-51-2.tcore1.tv2-tokyo.as6453.net, measurement "
                "212015972, PW->AS24439) -- Tata's own naming convention "
                "spells the city out directly (preceded by a two-letter+digit "
                "site code, e.g. 'tv2-'), distinct from the 'lax'/'losangeles' "
                "patterns already confirmed for this same carrier on other "
                "source economies. Genuinely different external touchpoint "
                "than the Los Angeles hub used for the PF/CK/PG-sourced "
                "entries on this same AS6453<->AS24439 adjacency -- Palau's "
                "shorter path to Asia routes through Tokyo before Piti, Guam, "
                "rather than through Los Angeles."
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
                "OneQode's Guam router, matching its PeeringDB-listed 'RTI Guam "
                "GNC' facility -- see analysis.regional_carrier_facilities. "
                "Confirmed on 218411496 (GU->AS140627, #272): Guam probes 7662 "
                "and 23039 reach 'jp-cc1-rt2-----Vlan750.gu-gnc-rt1' at 58ms "
                "after BBIX Tokyo at 29ms, i.e. back in Guam on the Tokyo-facing "
                "interface. (211527961's 'gu-gnc-rt1-----Vlan756.hk-mgi-rt1', "
                "cited here until 2026-11-16, is on the Hong Kong router.)"
            ),
        ),
    ),
    (
        re.compile(r"(?:^|[.\-])au-gssyd(?:[.\-]|$)", re.I),
        HopLocation(
            city="Sydney",
            economy_cc=None,
            matched_pattern="au-gssyd",
            evidence_note=(
                "OneQode's Global Switch Sydney router (owner, 2026-11-16). "
                "103.151.64.7 'gu-gnc-rt1-----Vlan780.au-gssyd-rt1' answers Guam "
                "probes at ~70ms, one hop after OneQode Guam at 0.2-0.5ms, and "
                "the next hop is EdgeIX Sydney or IX Australia NSW within 1ms "
                "(223636622, 213458029). 'gssyd' doesn't match the 'syd' "
                "pattern's segment boundary, hence its own entry."
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
    (
        re.compile(r"(?:^|[.\-])syd[op]\d*(?:[.\-].*)?\.telstraglobal\.net$", re.I),
        HopLocation(
            city="Sydney",
            economy_cc=None,
            matched_pattern="telstraglobal sydo/sydp",
            evidence_note=(
                "Telstra Global's Sydney site codes (owner, 2026-11-17). PG probe "
                "50365 reaches sydo-core04/sydo10/sydp10 at ~39ms, 0.1-0.4ms after "
                "Telstra's own oxf-gw30.sydney.telstra.net (211789443, 224429318). "
                "Four-letter site codes don't match the 'syd' pattern's segment "
                "boundary; scoped to telstraglobal.net."
            ),
        ),
    ),
    (
        re.compile(r"(?:^|[.\-])hk(?:th|ck|mi)\d*(?:[.\-].*)?\.telstraglobal\.net$", re.I),
        HopLocation(
            city="Hong Kong",
            economy_cc=None,
            matched_pattern="telstraglobal hkth/hkck/hkmi",
            evidence_note=(
                "Telstra Global's Hong Kong site codes (owner, 2026-11-17). GU probe "
                "65337 reaches hkck-core01 at 58.6ms, 0.1ms after "
                "telstra4-lacp-100g.hkix.net (212458784); on 213187876 hkth12, "
                "hkmi01 and hkck-core01 (165.6-166.8ms) come just before "
                "iij3-10g.hkix.net. Scoped to telstraglobal.net."
            ),
        ),
    ),
    (
        re.compile(r"\.sydney\.telstra\.net$", re.I),
        HopLocation(
            city="Sydney",
            economy_cc=None,
            matched_pattern="telstra.net sydney",
            evidence_note=(
                "Telstra's domestic network names the city (owner, 2026-11-17). "
                "Every cached *.sydney.telstra.net hop sits within ~1ms of a router "
                "already placed in Sydney: VU 64783 sydp-core04 51.6ms -> pad-gw30 "
                "50.9ms (211648499); PG 50365 hay-core30 38.3ms -> sydo-core04 39.7ms "
                "(221438711); TO 11691 AARNet mcqd 109.9ms -> chw-edge903 109.3ms "
                "(212106578). Other telstra.net cities are seen only from non-Pacific "
                "probes and have no hub coordinates, so they are not mapped."
            ),
        ),
    ),
    (
        re.compile(r"\.hkix\.net$", re.I),
        HopLocation(
            city="Hong Kong",
            economy_cc=None,
            matched_pattern="hkix.net",
            evidence_note=(
                "HKIX member-port names (owner, 2026-11-17). GU 65337 reaches "
                "telstra4-lacp-100g at 58.7ms, then Telstra Global hkck-core01 at "
                "58.6ms (212458784); VU 1008536 has hkmi01 166.3ms, iij3-10g 171.6ms, "
                "then IIJ hkg002bb01 170.6ms (213187876)."
            ),
        ),
    ),
)


# OneQode names an interface `<router at the far end>-----<VLAN>.<router it is on>`:
# the two ends of one Guam-Sydney link are `au-gssyd-rt1-----Vlan780.gu-gnc-rt1` and
# `gu-gnc-rt1-----Vlan780.au-gssyd-rt1` (103.151.64.6/.7). Only the router after the
# dot says where the address is (owner, 2026-11-16).
_ONEQODE_INTERFACE = re.compile(r"^[^.]*-----[^.]*\.(?P<router>[^.]+\.oneqode\.net)$", re.I)


def _router_name(hostname: str) -> str:
    """The part of `hostname` that names the router the address is on."""
    match = _ONEQODE_INTERFACE.match(hostname)
    return match.group("router") if match else hostname


def resolve_hostname(hostname: str) -> HopLocation | None:
    """Match a router hostname against the curated pattern table.

    Returns `None` rather than guessing when no known pattern matches --
    an unrecognized hostname is real information (this project hasn't
    seen this carrier's naming convention yet), not something to paper
    over with a carrier-level facility guess. A name that also carries
    the far end of its link (OneQode's interface names) is matched on
    its own router only.
    """
    name = _router_name(hostname)
    for pattern, location in _KNOWN_PATTERNS:
        if pattern.search(name):
            return location
    return None


def geolocate_hop(ip: str) -> HopLocation | None:
    """Reverse-resolve `ip` to a hostname, then match it against known patterns.

    Returns `None` on a PTR lookup failure (no reverse record) or when
    the hostname doesn't match any curated pattern -- both are genuine
    "we don't know" results, not errors to paper over.
    """
    hostname = reverse_dns(ip)  # unbound, rate-capped; see ptr_lookup (2026-11-06)
    return resolve_hostname(hostname) if hostname else None
