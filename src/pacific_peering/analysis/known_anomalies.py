"""Registry of already-investigated routing-loop locations.

Every entry here was, at some point this project, individually investigated
by checking raw hops, cross-referencing `ixp_lan_registry.json` /
PeeringDB / RIPEstat, and judged to be an ordinary artifact (an IXP fabric
router answering twice at consecutive TTLs, a known satellite-network
loop, a carrier's own internal ECMP noise) rather than a genuine new
anomaly -- see `task_plan.md` for the individual investigations. Once a
location is investigated and understood, reproducing it again is routine,
not worth a fresh escalation every time -- that's the whole point of this
registry: `auto_classify.py` checks a looping address against it before
deciding whether to escalate.

A location is a network prefix, not a single address -- addresses within a
carrier's own loop-prone infrastructure vary (this project caught multiple
distinct addresses inside AS14593/Starlink's own network alone:
206.224.66.23, .25, .27, .29, .31, .51, .53 at various points), so this
checks CIDR containment, not exact-string match.

Update this file (add a `KnownLoopLocation`) whenever `auto_classify.py`
escalates a genuinely new loop and a human/LLM investigation concludes it's
ordinary -- that's the intended growth path, not a one-time seed.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass


@dataclass(frozen=True)
class KnownLoopLocation:
    prefix: str  # CIDR, e.g. "45.127.172.0/22"
    description: str  # what this is and why it's ordinary
    asn: int | None = None  # the network operating this space, if known


KNOWN_LOOP_LOCATIONS: tuple[KnownLoopLocation, ...] = (
    KnownLoopLocation(
        "45.127.172.0/22",
        "Equinix Sydney IXP fabric (ix_id 94 in ixp_lan_registry.json, "
        "independently confirmed via peeringdb.com/ix/94). A router "
        "answering twice at consecutive TTLs -- ordinary IXP-fabric "
        "behavior, first identified and corrected from an initial "
        "mischaracterization as a new anomaly, then reproduced routinely "
        "many times afterward.",
    ),
    KnownLoopLocation(
        "125.63.0.0/19",
        "Superloop's (AS38195) own announced prefix -- an ordinary "
        "intra-carrier router artifact within a single already-identified "
        "carrier's network, confirmed via RIPEstat before being treated as "
        "routine.",
        asn=38195,
    ),
    KnownLoopLocation(
        "103.142.98.0/24",
        "SISCC's (AS139609) own address space -- the loop-history address "
        "103.142.98.131 and adjacent addresses (.129) reappear repeatedly "
        "across dozens of corroborations of the SISCC<->AS45891 and "
        "sibling adjacencies, sometimes as a single clean touch, sometimes "
        "as a genuine interleaved loop after a run of silent hops.",
        asn=139609,
    ),
    KnownLoopLocation(
        "206.224.66.0/24",
        "Starlink's (AS14593) own network -- multiple distinct addresses "
        "in this range (.21, .23, .25, .27, .29, .31, .51, .53) have shown "
        "genuine alternating/interleaved loops on different probes over "
        "the course of this project, all inside the same carrier's own "
        "infrastructure. First discovery here was flagged to the project "
        "owner as a genuinely new anomaly before being added to this "
        "registry; reproductions since are routine.",
        asn=14593,
    ),
    KnownLoopLocation(
        "202.170.33.0/24",
        "A genuine 2-node alternating loop inside AS174's (Cogent) own "
        "network, discovered while confirming FINTEL (AS9241) as a "
        "traceroute target itself -- two addresses (.11, .17) interleave, "
        "the target never reached, but the pre-loop resolution (AS174 "
        "itself) still stands.",
        asn=174,
    ),
    KnownLoopLocation(
        "202.1.22.0/24",
        "BNL Tarawa's (AS154100) own address space, seen recurring in the "
        "Starlink-fronted downstream chain to Kiribati -- addresses here "
        "(.25, .29) sometimes appear as the post-loop recovery point "
        "rather than the loop itself, confirming the chain rather than "
        "contradicting it.",
        asn=154100,
    ),
    KnownLoopLocation(
        "184.104.0.0/15",
        "Hurricane Electric's (AS6939) global backbone loopback range -- "
        "confirmed via RIPEstat network-info (the whole /15 is what's "
        "actually announced for both addresses seen). Two distinct "
        "addresses within it (.192.252, .192.136) each answered twice at "
        "consecutive TTLs on GU-sourced corridors transiting HE en route "
        "further into the Pacific; both traces continued past the loop to "
        "real subsequent hops rather than dead-ending, consistent with an "
        "ordinary backbone double-answer rather than a genuine block.",
        asn=6939,
    ),
    KnownLoopLocation(
        "209.120.128.0/17",
        "GTT Communications' (AS3257, formerly Tinet) own backbone -- "
        "confirmed via RIPEstat network-info. Seen as a same-address "
        "double-answer at consecutive TTLs immediately after a Cogent "
        "(AS174) hop on an MP(AS7131)-sourced corridor to French "
        "Polynesia, then a dead end -- an ordinary backbone-router "
        "artifact at the edge of RIS visibility, not a genuine new "
        "anomaly.",
        asn=3257,
    ),
    KnownLoopLocation(
        "103.57.234.0/24",
        "AS7131's (MTC, Northern Mariana Islands -- WHOIS netname "
        "MTC-MP) own aggregation/upstream address space -- confirmed via "
        "RIPEstat network-info and WHOIS. This is the *source* carrier's "
        "own router (not a third party): the same address (.234.1) "
        "appears as an ordinary single-touch hop on GU(AS3605)-sourced "
        "corridors that transit it, and only doubled up at consecutive "
        "TTLs on one MP(AS7131)-sourced corridor -- an intra-carrier "
        "artifact at the network's own edge, not a genuine new anomaly.",
        asn=7131,
    ),
)


def classify_loop_address(address: str) -> KnownLoopLocation | None:
    """Return the matching `KnownLoopLocation` for this address, if any.

    `None` means this address doesn't match anything this project has
    already investigated -- `auto_classify.py` treats that as a genuine
    escalation trigger, not something to file and move past silently.
    """
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return None
    for loc in KNOWN_LOOP_LOCATIONS:
        if ip in ipaddress.ip_network(loc.prefix):
            return loc
    return None
