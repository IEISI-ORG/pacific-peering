"""Registry of external carriers' individual facilities confirmed to sit inside the fishbowl.

An external carrier (not registered to one of the 20 in-scope
economies) can still operate real, physical infrastructure inside the
study region — a PoP in Guam, say. That doesn't make the carrier's
ASN a fishbowl member: most of its traffic and most of its facilities
sit elsewhere, and treating the whole ASN as in-region would misstate
this project's thesis about out-of-region detours. But a specific hop
confirmed to cross that carrier's specific in-region facility isn't an
out-of-region detour either.

Per the project owner (raised after confirming OneQode's Guam router
on the MP(AS7131)->FJ(AS4638) traceroute): this is a real, load-bearing
distinction, handled the same way as IXP fishbowl classification —
**never auto-applied from an ASN's registration country, and scoped to
the specific confirmed facility, not the whole carrier.** OneQode
(AS140627, registered AU) keeps its other measurements' Sydney/Tokyo/
LA/Hong Kong/Singapore hops classified as ordinary out-of-region
transit; only hops matching its confirmed Guam facility get this
treatment.

Matching a hop to an entry here is evidence-based, not automatic:
a hop counts as hitting a facility below only when its PTR record (or
other direct evidence) matches the `hostname_pattern`, the way the
original OneQode/Guam case was confirmed via
`gu-gnc-rt1-----Vlan756.hk-mgi-rt1.oneqode.net` matching OneQode's own
PeeringDB-listed "RTI Guam GNC" facility.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegionalCarrierFacility:
    """One external carrier's specific facility, confirmed to sit inside the fishbowl."""

    asn: int
    carrier_name: str
    facility_name: str  # PeeringDB-listed name, for cross-reference
    economy_cc: str  # which in-scope economy this facility sits in
    hostname_pattern: str  # substring that identifies a hop's PTR record as this facility
    evidence_note: str


REGIONAL_CARRIER_FACILITIES: tuple[RegionalCarrierFacility, ...] = (
    RegionalCarrierFacility(
        asn=140627,
        carrier_name="OneQode",
        facility_name="RTI Guam GNC",
        economy_cc="GU",
        hostname_pattern="gu-gnc",
        evidence_note=(
            "Confirmed via the MP(AS7131)->FJ(AS4638) traceroute (measurement "
            "211527961): the hop at 103.151.64.207 has PTR record "
            "'gu-gnc-rt1-----Vlan756.hk-mgi-rt1.oneqode.net' -- a router "
            "explicitly named for Guam GNC, matching OneQode's own "
            "PeeringDB-listed facility (net_id 23196) of the same name, "
            "linked onward via a named VLAN to OneQode's Hong Kong router. "
            "OneQode also holds a second real Guam facility (Tata's Piti "
            "Cable Landing Station) not yet matched to a specific confirmed "
            "hop -- add a second entry here if/when a traceroute hits it."
        ),
    ),
    RegionalCarrierFacility(
        asn=6453,
        carrier_name="Tata Communications Ltd",
        facility_name="TATA Communications - Piti Cable Landing Station",
        economy_cc="GU",
        hostname_pattern="piti",
        evidence_note=(
            "Confirmed via the PF(AS9471)->MH(AS24439) traceroute "
            "(measurement 211683854): two hops (180.87.9.2, 180.87.60.178) "
            "have PTR records 'if-bundle-*.qhar*.pv4-piti.as6453.net' -- "
            "routers explicitly named for Piti, matching Tata's own "
            "PeeringDB-listed facility (net_id 437) of the same name -- the "
            "same physical cable-landing-station location OneQode's own "
            "Guam facility list separately references. Surfaced while "
            "auditing the PF->'Tokyo' hub-attribution errors (see "
            "hop_geolocation.py and task_plan.md): the traceroute actually "
            "reaches Los Angeles then this Piti facility, not Tokyo at all."
        ),
    ),
)
