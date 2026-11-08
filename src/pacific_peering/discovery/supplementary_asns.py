"""In-scope ASNs confirmed real but missing from the APNIC-delegation-based registry.

Per task_plan.md's existing known limitation: `registry.build_registry`
is APNIC-delegation-based only, so an ASN genuinely homed in an
in-scope economy but registered under a *different* RIR (ARIN, RIPE
NCC, etc.) never surfaces there. Confirmed this is a real, live gap —
not just a theoretical one — via RIPEstat's `country-resource-list`
endpoint (which aggregates delegated resources across all RIRs, not
just APNIC): cross-checking all 20 in-scope economies surfaced 11 ASNs
this project's registry was missing entirely.

**Only genuinely verified entries belong here — same restraint as
`supplementary_ixps.py`.** Of those 11, only one held up under direct
verification (real prefixes announced, real PeeringDB IXP presence at
an already-confirmed in-fishbowl exchange): University of Guam. The
other 10 (8 "Marshall Islands", 1 "Palau", 1 "Vanuatu", all RIPE
NCC-registered) were checked and explicitly *not* added — their
holder names (generic "-LTD"/"-LLC" hosting-style names) and PeeringDB
facility data (where present at all) point at opportunistic offshore
incorporation in a permissive jurisdiction, not real local presence.
Concretely: AS62880 ("Marshall Islands") lists facility presence only
in Amsterdam; AS43357 ("Vanuatu", "Owl Limited") lists facilities in
Hong Kong, Osaka, Sydney, Los Angeles, Fremont, and Tallinn — nowhere
near the Pacific at all. A country code on an ASN registration records
where the entity chose to incorporate, not where its network runs —
the same caution this project already applies to PeeringDB's country
field (see AS24013's anycast/hosting-vs-real-location case).

The same gap also applies inside APNIC: an ASN delegated under another
economy's code (AS10025 and AS45411 are both labelled AU) is just as
invisible to the delegation-based registry. Those entries were found by
matching BGP origins against Pacific-labelled address space, added on the
project owner's direction (2026-11-09), and checked against current RDAP
and RIS data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SupplementaryAsn:
    """One ASN this project has confirmed in-scope independently of the APNIC-based registry."""

    asn: int
    country_cc: str
    name: str
    rir: str
    source_url: str
    note: str


SUPPLEMENTARY_ASNS: tuple[SupplementaryAsn, ...] = (
    SupplementaryAsn(
        asn=395400,
        country_cc="GU",
        name="University of Guam",
        rir="ARIN",
        source_url="https://www.peeringdb.com/net/38357",
        note=(
            "Surfaced while investigating AS141682 (ARENA-PAC, an Asia-Pacific "
            "research/education network the project owner pointed at directly) -- "
            "ARENA-PAC's own PeeringDB IXP memberships include GOREX (Piti, Guam, "
            "already a confirmed in-fishbowl exchange), and GOREX's real member "
            "list (via netixlan) turned out to include University of Guam "
            "(AS395400) alongside ARENA-PAC, RouteViews (University of Oregon), "
            "REANNZ (New Zealand's R&E network, out-of-fishbowl), and University "
            "of Hawaii (out-of-fishbowl) -- essentially a small research/education "
            "peering fabric physically in Guam. University of Guam's ASN is real "
            "and clearly Guam-based (originates 192.149.202.0/24 and "
            "168.123.0.0/16 per RIS, physically present at GOREX per PeeringDB) "
            "but registered under ARIN rather than APNIC, so it never appeared in "
            "this project's delegation-based registry at all. Not yet tested by "
            "Atlas: does its own traffic actually use GOREX locally, or does "
            "Guam's academic network traffic detour via Hawaii/NZ despite the "
            "local exchange existing?"
        ),
    ),
    SupplementaryAsn(
        asn=21996,
        country_cc="GU",
        name="GUAMCELL Communications",
        rir="ARIN",
        source_url="https://rdap.arin.net/registry/autnum/21996",
        note=(
            "Owner's direction, 2026-11-09. ARIN registrant address is 219 South "
            "Marine Drive, Tamuning, GU. RIS shows it originating 116.68.0.0/20 and "
            "103.17.112.0/22 more-specifics, which APNIC registers to GUAMCELL with "
            "country GU. The APNIC-delegated AS133071 (GUAMCELL-AS-AP), already in "
            "the registry, originates nothing in RIS, so this is the ASN that "
            "carries Guamcell's routes."
        ),
    ),
    SupplementaryAsn(
        asn=10025,
        country_cc="NU",
        name="The IUSN Foundation",
        rir="APNIC",
        source_url="https://rdap.apnic.net/autnum/10025",
        note=(
            "Owner's direction, 2026-11-09. APNIC's delegated-stats file labels "
            "this ASN AU, so the registry never saw it, but its RDAP record says NU "
            "with contacts at Alofi. RIS shows it originating 202.59.4.0/22, which "
            "APNIC registers to IUSN with country NU."
        ),
    ),
    SupplementaryAsn(
        asn=45411,
        country_cc="PG",
        name="APCS (AS registered to Australia Power Control Systems)",
        rir="APNIC",
        source_url="https://rdap.apnic.net/autnum/45411",
        note=(
            "Owner's direction, 2026-11-09. Unlike the other entries, the holder is "
            "Australian (Bonville NSW) and most of the network is too: 210.79.16.0/20 "
            "is AU wholesale space, kept out of traceroute targets by "
            "atlas.targets.EXCLUDED_TARGET_PREFIXES. It is here because RIS shows it "
            "originating 103.153.158.0/23, which APNIC registers to Asia Pacific "
            "Communication Specialist (PNG) Ltd, whose own AS140935 originates "
            "nothing in RIS. Caveat: listing the whole ASN makes any AS45411 hop "
            "count as in-region, including Australian ones. No cached trace crossed "
            "AS45411 when this was added (0 of 1715 raw measurement files), so "
            "re-check before trusting a finding whose path includes it."
        ),
    ),
)
