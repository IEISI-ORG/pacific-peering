"""Confirmed real intra-region ("in-fishbowl") transit relationships.

The counterpart to `confirmed_detours.py`: that module records real
detours through an out-of-fishbowl exchange (the sub-optimal-routing
findings this project exists to document); this one records the
opposite — an ASN-to-ASN adjacency confirmed by both RIS and Atlas
where *both* ends are in-scope ASNs, meaning at least this leg of the
journey stays entirely within the study region. Also hand-curated, same
reason as `confirmed_detours.py`: only a handful of measurements exist
so far.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfirmedLocalTransit:
    """One real intra-fishbowl transit relationship, confirmed by RIS + Atlas."""

    provider_cc: str
    provider_asn: int
    provider_name: str
    customer_cc: str
    customer_asn: int
    customer_name: str
    measurement_id: int
    vantage_point_cc: str  # economy the confirming traceroute was sourced from
    ris_observation_count: int
    note: str


CONFIRMED_LOCAL_TRANSIT: tuple[ConfirmedLocalTransit, ...] = (
    ConfirmedLocalTransit(
        provider_cc="FJ",
        provider_asn=38442,
        provider_name="Vodafone Fiji",
        customer_cc="VU",
        customer_asn=9249,
        customer_name="Telecom Vanuatu",
        measurement_id=210960114,
        vantage_point_cc="PF",
        ris_observation_count=1346,
        note=(
            "All 3 probes (sourced from French Polynesia, the best-covered "
            "available vantage point — not itself part of this adjacency) "
            "show AS38442 as the last resolved hop before AS9249, matching "
            "RIS's independently-observed neighbor count exactly. A real "
            "gap remains between AS38442 and AS9249 (checked directly: "
            "ordinary ICMP filtering, not an unlisted IXP), so the very "
            "last hop isn't proven — but the AS38442 adjacency itself is. "
            "Reinforced from the reverse direction by measurement 210970669 "
            "(Vanuatu -> FSM/AS38875, sourced from Vanuatu itself): AS38442 "
            "is the first resolved hop leaving AS9249's own network, "
            "matching this same adjacency from the other side. That "
            "measurement's actual target (AS38875) was not confirmed — "
            "RIS's only neighbor for AS38875 is AS10130, not the traceroute's "
            "last resolved hop (AS139759) — a correct negative result, not "
            "a new finding, and recorded here only as corroboration of the "
            "existing AS9249<->AS38442 adjacency. "
            "Separately, after fixing traceroute_topology._resolve_address to "
            "check IXP-fabric membership independently of ASN resolution: for "
            "2 of the original 3 probes (French Polynesia -> AS9249), the hop "
            "immediately before AS38442 is AS4637 (Telstra Global), resolved "
            "via PeeringDB netixlan, whose address also falls inside Any2West's "
            "registered LAN prefix (Los Angeles/Silicon Valley, out-of-fishbowl). "
            "This does not touch the AS38442<->AS9249 adjacency itself (still "
            "confirmed on its own terms), but it does mean the vantage point's "
            "own path to reach Fiji transits a US exchange first -- a real, "
            "separate observation about French Polynesia's own upstream routing, "
            "not the confirmed finding's two endpoints. "
            "Separately, IRR-corroborated: AS38442's own PeeringDB-declared AS-SET "
            "(AS38442:AS-ALL) names AS9249 directly among its declared peers -- a "
            "declared intention, independently sourced (APNIC), matching this "
            "adjacency on a fourth, independent axis alongside RIS, Atlas, and the "
            "reverse-direction reinforcement above."
        ),
    ),
    ConfirmedLocalTransit(
        provider_cc="KI",
        provider_asn=154100,
        provider_name="BNL Tarawa",
        customer_cc="KI",
        customer_asn=132486,
        customer_name="Ocean Link Ltd",
        measurement_id=211020366,
        vantage_point_cc="FM",
        ris_observation_count=362,
        note=(
            "A domestic (intra-Kiribati) adjacency, not a cross-economy one -- "
            "surfaced incidentally while testing an FM->KI corridor flagged by the "
            "IRR sweep two tranches ago (AS10130's declared transit AS-SET names "
            "AS132486 directly). All 3 probes, sourced from FSM (country-based "
            "selection -- landed on AS139759, *not* AS10130, so this measurement "
            "does not actually test that specific IRR lead. Checked directly "
            "whether AS10130 could be targeted specifically: RIPE Atlas's own probe "
            "registry shows zero connected probes on AS10130, and only one ever "
            "registered against it in total (probe 26163, status Abandoned) -- so "
            "the AS10130<->AS132486 relationship isn't just untested, it currently "
            "*cannot* be tested via Atlas at all, regardless of probe-selection "
            "method), show the same striking path: AS139759 "
            "-> AS9246 (GTA/Teleguam, Guam) -> AS7578/AS137409 (GSL Networks, "
            "Australia) -> **AS14593 (SpaceX Starlink)** -> AS154100 (BNL Tarawa) -> "
            "[one-hop ICMP-filtered gap] -> target (AS132486) never resolved. RIS's "
            "neighbor list for AS132486 lists AS154100 with an exact matching count "
            "(362) -- a real, confirmed adjacency, but between two Kiribati ASNs, "
            "not evidence either way about FM<->KI peering. The genuinely new, "
            "notable observation is the path itself: this FSM-sourced traffic's "
            "route to Kiribati transits Guam, an Australian carrier, and Starlink's "
            "satellite network before ever reaching a Kiribati-registered ASN -- not "
            "recorded as a confirmed detour (no traceroute hop landed inside any "
            "registered IXP LAN prefix; this is a plain carrier-to-carrier transit "
            "chain across the open internet, not a named-exchange crossing this "
            "project's ConfirmedDetour shape is built to capture), but real color "
            "worth keeping on record."
        ),
    ),
    ConfirmedLocalTransit(
        provider_cc="GU",
        provider_asn=3605,
        provider_name="Guam Cablevision, LLC",
        customer_cc="GU",
        customer_asn=395400,
        customer_name="University of Guam",
        measurement_id=211038772,
        vantage_point_cc="GU",
        ris_observation_count=1091,
        note=(
            "A domestic (intra-Guam) adjacency, surfaced while testing the actual "
            "question this measurement was built for: does University of Guam's "
            "own traffic really use GOREX locally (per the project owner's ask), "
            "given its confirmed presence there? Targeted University of Guam's own "
            "GOREX netixlan address (192.35.145.18) directly from a Guam-sourced "
            "probe. Of 3 probes: one resolved nothing at all; one (probe 7385) "
            "transited AS152735 then AS7131 (Northern Mariana Islands) before going "
            "dark, RIS disagreeing (not a finding); the third (probe 329) resolved "
            "cleanly to AS3605 (Guam Cablevision) as the last hop before the target "
            "-- RIS's neighbor list for AS395400 lists AS3605 with an *exact* "
            "matching count (1,091), a real confirmed adjacency in its own right. "
            "But the actual question -- does this traffic cross GOREX's own fabric "
            "-- comes back negative: none of the 3 probes showed a hop inside "
            "GOREX's registered LAN prefix (192.35.145.0/24) before going dark. Read "
            "honestly, this doesn't confirm GOREX goes unused (ICMP filtering right "
            "at the target, or at the exchange's own switch fabric, could explain "
            "it just as well as the traffic genuinely bypassing GOREX) -- it's "
            "inconclusive on the motivating question, while still yielding this "
            "separate, real, confirmed finding along the way. "
            "Reinforced a third time, from a genuinely distant vantage point: "
            "sourced directly from AS141682 (ARENA-PAC, the Pacific research/"
            "education network the project owner pointed at) toward this same "
            "target. Both probes fully contiguous end-to-end: AS141682 -> AS2500 "
            "(WIDE Project, Japan) -> AS2497 (IIJ, Japan) -> AS3605 -> AS395400, "
            "landing on this exact adjacency again with the same 1,091-observation "
            "match. Notable in its own right: ARENA-PAC and University of Guam are "
            "both *confirmed* GOREX members (see the candidate-peering module's "
            "AS3605<->AS17893 entry for how GOREX's real membership was mapped), "
            "yet this traceroute between two of GOREX's own members still doesn't "
            "cross GOREX -- it goes via Japan and Guam Cablevision instead. The "
            "same pattern as the AS3605->Cogent/Tokyo confirmed detour: a real "
            "local exchange exists and has real, confirmed members, but real "
            "measured traffic between those members doesn't necessarily use it."
        ),
    ),
    ConfirmedLocalTransit(
        provider_cc="PF",
        provider_asn=9471,
        provider_name="ONATI (Office des Postes et Telecommunications)",
        customer_cc="NU",
        customer_asn=55885,
        customer_name="No. 1 Commercial Center",
        measurement_id=211091699,
        vantage_point_cc="NU",
        ris_observation_count=1662,
        note=(
            "Niue's only RIS-observed neighbor at all is AS55943 (1,662 "
            "observations) -- also ONATI, French Polynesia's telecom incumbent, "
            "just a second ASN of the same operator (both PeeringDB and RIPEstat "
            "list AS9471 and AS55943 under the identical holder name, 'ONATI-AS-AP "
            "- ONATI'; AS9471's own RIS neighbor list independently confirms "
            "AS55943 with 1,838 observations, proving the sibling relationship, "
            "not just a name coincidence). Sourced directly from Niue's own "
            "connected Atlas probe (found via the ASN probe registry) toward "
            "AS55943 specifically: the traceroute resolved cleanly and contiguously "
            "to AS9471 -- ONATI's *other* ASN -- before going dark short of the "
            "literal target. `check_neighbor_agreement` reports `ris_agrees: "
            "false` on a strict reading (AS9471 isn't literally in AS55943's own "
            "neighbor list), but read correctly this is the same real-world "
            "relationship RIS already confirmed for Niue, observed via ONATI's "
            "other identity -- recorded as confirmed on that basis, with the "
            "nuance stated plainly rather than either overclaiming a literal "
            "ASN-for-ASN match or discarding a real, well-evidenced finding over "
            "a technicality of which of one company's two ASNs a hop resolved to."
        ),
    ),
    ConfirmedLocalTransit(
        provider_cc="FJ",
        provider_asn=9241,
        provider_name="FINTEL (Fiji International Telecommunications Ltd)",
        customer_cc="TV",
        customer_asn=23917,
        customer_name="Tuvalu Telecommunications Corporation",
        measurement_id=211111376,
        vantage_point_cc="TV",
        ris_observation_count=1009,
        note=(
            "Tuvalu tested for the first time this session, via the ASN probe "
            "registry. AS23917 has only two RIS-observed neighbors at all -- "
            "AS9241/FINTEL (1,009 observations, dominant) and AS14593/SpaceX "
            "Starlink (714) -- so this was the obvious first test. Sourced "
            "directly from Tuvalu's own probe toward FINTEL: fully contiguous, "
            "a direct single AS-level hop, no gap. "
            "This is also what motivated a real fix to `check_neighbor_agreement`: "
            "the original check only looked at the *target*'s (FINTEL's) own "
            "RIS neighbor list, which doesn't mention AS23917 at all -- RIS "
            "visibility between a small leaf network and a much larger regional "
            "carrier isn't always symmetric. Fixed to check both directions; "
            "Tuvalu's own list settles it unambiguously (1,009 of its only ~1,700 "
            "total observations -- clearly the dominant relationship, not noise). "
            "Verified the fix causes no regressions: re-ran all 20 measurements "
            "this project has ever fired under the fixed logic, and every "
            "previously-confirmed count stayed exactly the same."
        ),
    ),
)
