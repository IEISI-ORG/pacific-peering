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
            "does not actually test that specific IRR lead; the AS10130<->AS132486 "
            "relationship remains untested), show the same striking path: AS139759 "
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
)
