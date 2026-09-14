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
)
