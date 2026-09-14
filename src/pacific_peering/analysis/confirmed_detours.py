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
        note=(
            "New Caledonia -> Telecom Fiji (AS4638); upstream AS45349 confirmed "
            "by RIS+Atlas. Also IRR-corroborated: AS45349's own PeeringDB-declared "
            "AS-SET (AS45349:AS-TFL-TRANSIT) names AS4638 directly -- a declared "
            "transit intention, independently sourced (APNIC), matching what the "
            "traceroute actually shows."
        ),
    ),
    ConfirmedDetour(
        source_cc="NC",
        target_cc="FJ",
        target_asn=45355,
        detour_ix_name="Equinix Sydney",
        detour_hub="Sydney",
        measurement_id=210996533,
        ris_observation_count=1326,
        note=(
            "New Caledonia -> Digicel Fiji (AS45355); upstream AS132528 -- per the "
            "project owner, the Telstra-operated backbone ASN behind Digicel's "
            "Pacific mobile networks, registered in PeeringDB as 'Digicel "
            "Australia' -- confirmed by RIS+Atlas with an exact observation-count "
            "match (1,326) and a fully contiguous hop chain (AS18200, New "
            "Caledonia's own incumbent -> AS132528 at Equinix Sydney, exact "
            "netixlan address match -> AS45355). The strongest-evidenced finding "
            "in this project so far: also IRR-corroborated on *both* sides -- "
            "AS132528's declared AS-SET (AS-132528-PEERS) names AS45355 directly, "
            "and AS45355's own declared AS-SET (AS-45355-PEERS) names AS132528 "
            "right back -- a mutual, independently-sourced (APNIC) declaration "
            "matching the observed adjacency exactly. AS132528 was also seen at "
            "this same Equinix Sydney fabric in an earlier, unrelated measurement "
            "(210930962, the Zscaler-proxied Fiji probe test) -- two independent "
            "measurements, two different vantage points, same exchange presence."
        ),
    ),
    ConfirmedDetour(
        source_cc="GU",
        target_cc="PW",
        target_asn=17893,
        detour_ix_name="AS174 (Cogent Communications), via AS2497 (IIJ, Japan) -- global "
        "transit, not a named exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211064438,
        ris_observation_count=1333,
        note=(
            "Guam (AS3605, Guam Cablevision) -> Palau NCC (AS17893). Sourced "
            "directly from AS3605 via ASN-based probe selection (2 connected "
            "probes exist -- the project owner asked to test this specifically "
            "after two prior tranches could only test it indirectly, via "
            "country-based selection that happened to land on other Guam ASNs). "
            "Both probes: AS3605 -> AS2497 (IIJ, Japan) -> AS174 (Cogent "
            "Communications) -> AS17893, fully contiguous, no gaps. RIS agrees "
            "with an *exact* observation-count match (1,333). Different in kind "
            "from this project's other three confirmed detours: no hop landed "
            "inside any registered IXP LAN prefix (`ixp_crossings` empty for both "
            "probes) -- this is plain global Tier-1 transit (Cogent, reached via "
            "Japan), not a named-exchange crossing, so `detour_ix_name` records "
            "that honestly rather than implying an IXP that isn't there. What "
            "makes this the sharpest evidence yet for the project's actual thesis: "
            "AS17893 (this exact target) has *confirmed, repeated* local exchange "
            "presence at Guam IX (seen in three separate earlier measurements, two "
            "different source economies) -- real local peering infrastructure "
            "exists for this corridor. AS3605's own traffic to it simply doesn't "
            "use it, defaulting instead to a transit path via Tokyo and a global "
            "carrier. Not evidence the local exchange is unused in general (a "
            "different Guam network's traffic was shown reaching AS17893 via "
            "Guam IX in an earlier measurement) -- evidence that at least one real "
            "Guam ISP's default route to a real Guam-IX-connected Palau network "
            "bypasses the local exchange entirely. "
            "**Independently reproduced by a second, later measurement** "
            "(211181370, same AS3605->AS17893 corridor, fired from a later `/loop` "
            "tranche before checking this entry already existed -- a real process "
            "miss, but the result itself is useful corroboration, not wasted): "
            "both responding probes again show the identical path (AS3605 -> "
            "AS2497 -> AS174 -> AS17893) and the identical exact RIS observation "
            "count (1,333). Two independent measurements, same result -- this "
            "finding is as solid as any in the project."
        ),
    ),
    ConfirmedDetour(
        source_cc="FJ",
        target_cc="VU",
        target_asn=9249,
        detour_ix_name="MegaIX Sydney",
        detour_hub="Sydney",
        measurement_id=211239396,
        ris_observation_count=1346,
        note=(
            "Fiji -> Telecom Vanuatu (AS9249), but sourced from a genuinely "
            "different, institutionally-motivated vantage point: AS24390, the "
            "University of the South Pacific's own network (Fiji-based, but "
            "with a real campus in Vanuatu -- Emalus Campus -- making this an "
            "actual inter-campus corridor, not an arbitrary ASN pair). Picked "
            "from the ASN probe registry precisely because AS24390's only "
            "RIS-observed neighbor at all is AS7575 (AARNet, Australia's "
            "research/education network) -- worth testing directly rather than "
            "assumed, given ARENA-PAC/GOREX's Pacific-research-network "
            "relevance surfaced earlier this session. Confirmed: the path runs "
            "AS24390 -> AS7575 (AARNet) -> AS38442 (Vodafone Fiji, resolved via "
            "PeeringDB netixlan) -> crosses MegaIX Sydney -> AS9249. Upstream "
            "of the target is AS38442, matching RIS's independently-observed "
            "count *exactly* (1,346) -- the identical count already on record "
            "for this project's very first confirmed finding "
            "(AS38442<->AS9249, see confirmed_local_transit.py), now "
            "independently reinforced from a third vantage point and a "
            "genuinely different source network. The final hop (AS38442's own "
            "address to AS9249's) shows `contiguous: false`, but checked "
            "directly against the raw hop data before accepting that at face "
            "value: hop 11 returned no address at all (a true ICMP timeout, "
            "not a private-address artifact the recent RFC1918 fix would "
            "catch), so this is a genuine unresolved final hop, not a "
            "resolver limitation -- consistent with how this exact adjacency's "
            "last leg has read in every prior measurement of it. **The real, "
            "new finding here isn't the AS38442<->AS9249 adjacency itself "
            "(already this project's most solid) -- it's that a Pacific "
            "regional university's own inter-campus traffic, between two "
            "islands roughly 1,100km apart, detours all the way out to "
            "Australia and back rather than routing directly within the "
            "region**, exactly the kind of sub-optimal transpacific routing "
            "this project exists to document. Only 1 of 3 requested probes "
            "returned in time; not re-fired for the other two, since the one "
            "result already lands on an extremely well-characterized "
            "adjacency with an exact RIS match -- a small-tranche judgment "
            "call, not a data gap that changes the finding."
        ),
    ),
    ConfirmedDetour(
        source_cc="NC",
        target_cc="VU",
        target_asn=9249,
        detour_ix_name="Equinix Sydney",
        detour_hub="Sydney",
        measurement_id=211285266,
        ris_observation_count=1346,
        note=(
            "New Caledonia -> Telecom Vanuatu (AS9249), sourced from AS56089 "
            "(OFFRATEL) -- a third distinct NC carrier tested this session "
            "(after the incumbent OPT NC/AS18200 and the independent ISP "
            "Nautile/AS45345 last tranche), continuing the same question with "
            "a fresh target: does every NC carrier's international traffic "
            "detour via Australia/NZ, regardless of destination or which "
            "local ISP originates it? A genuinely untested economy pair "
            "(NC<->VU) before this measurement. Grepped first, per the "
            "standing process rule: confirmed untested. "
            "Result: fully contiguous, zero gaps, all 6 hops resolved cleanly "
            "-- AS56089 -> AS18200 (OPT NC) -> AS4648 (Spark NZ, New "
            "Zealand's largest telecom, resolved via PeeringDB netixlan at "
            "Equinix Sydney) -> AS6939 (Hurricane Electric, also present at "
            "the same Equinix Sydney fabric) -> AS4637 (Telstra Global) -> "
            "AS38442 (Vodafone Fiji) -> AS9249. Upstream of the target is "
            "AS38442, RIS-agreeing with an *exact* match (1,346) -- the "
            "identical count on record for this project's very first "
            "confirmed finding (AS38442<->AS9249), now independently "
            "reinforced a **fourth** time, from a fourth distinct vantage "
            "point/source network. Notable in its own right: this is the "
            "first measurement this session to show New Zealand (Spark NZ) "
            "as a transit waypoint rather than just Australia -- the "
            "detour pattern isn't Australia-specific, it's \"whichever "
            "Oceania hub happens to sit on the path,\" consistent with this "
            "project's Fish Bowl framing (AU/NZ both excluded from the study "
            "region, both acting as external hubs the region's traffic "
            "routes through). Only 1 of 3 requested probes returned in time; "
            "not re-fired, same small-tranche judgment call as the USP/AS9249 "
            "measurement -- the one result is already clean and exactly "
            "RIS-matched."
        ),
    ),
    ConfirmedDetour(
        source_cc="PG",
        target_cc="VU",
        target_asn=9249,
        detour_ix_name="Telstra (AS1221 domestic + AS4637 Telstra Global) -- "
        "global transit, not a named exchange crossing",
        detour_hub="Sydney",
        measurement_id=211299647,
        ris_observation_count=1346,
        note=(
            "PNG DataCo (AS17828) -> Telecom Vanuatu (AS9249) -- a genuinely "
            "untested economy pair before this measurement (PG<->VU, both "
            "Melanesian), picked to check whether regional Melanesian traffic "
            "stays in-region or detours externally like every other corridor "
            "tested this session. Grepped first: confirmed untested. "
            "Result: fully contiguous, zero gaps -- AS17828 -> AS4826 (Vocus "
            "Connect, already established as PNG DataCo's own upstream from "
            "an earlier tranche) -> AS1221 (Telstra Limited, Australia's "
            "domestic backbone) -> AS4637 (Telstra Global, the international "
            "arm of the same company) -> AS38442 (Vodafone Fiji) -> AS9249. "
            "Upstream of the target is AS38442, RIS-agreeing with an *exact* "
            "match (1,346) -- this project's very first confirmed finding, "
            "now independently reinforced a **fifth** time, from a fifth "
            "distinct vantage point. Different in kind from the NC-sourced "
            "detours to the same target: no hop landed inside any registered "
            "IXP LAN prefix this time (`ixp_crossings` empty) -- straight "
            "Tier-1 transit through Telstra's own network (its domestic and "
            "international ASNs both appearing back-to-back) rather than a "
            "named-exchange crossing, so `detour_ix_name` records that "
            "honestly rather than implying an IXP that isn't there, same "
            "convention already used for the AS3605->AS17893 Tokyo/Cogent "
            "entry. Five independent measurements, five different source "
            "networks, one identical destination adjacency -- AS38442's role "
            "as Fiji's real gateway to Vanuatu is about as solidly "
            "established as any single fact in this project."
        ),
    ),
    ConfirmedDetour(
        source_cc="GU",
        target_cc="FJ",
        target_asn=9241,
        detour_ix_name="AS174 (Cogent Communications), via AS2497 (IIJ, Japan) -- global "
        "transit, not a named exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211316239,
        ris_observation_count=830,
        note=(
            "Guam (AS3605, Guam Cablevision) -> FINTEL (AS9241, Fiji "
            "International Telecommunications Ltd) -- pulled from the "
            "maintained corridor backlog's top pick (the first hourly `/loop` "
            "firing to run against it): a genuinely untested GU<->FJ economy "
            "pair despite both being among the most-characterized economies "
            "in the project. The measurement itself ran unusually slowly to "
            "schedule (stuck at `Scheduled` status for several minutes before "
            "any probe activity, versus the usual 5-15 seconds) -- checked "
            "directly rather than assumed transient: `participant_count: 2` "
            "confirmed both of AS3605's connected probes were queued, and a "
            "second, longer poll resolved cleanly with both probes returning "
            "-- an ordinary Atlas-side scheduling delay, not a network "
            "anomaly, so not escalated under the standing consult-the-owner "
            "order (which is for strange *routing*, not platform latency). "
            "Result: AS3605 -> AS2497 (IIJ, Japan) -> AS174 (Cogent "
            "Communications) -> AS9241, the same Tokyo/Cogent global-transit "
            "shape already seen for AS3605's Palau corridor (see the GU->PW "
            "entry above) -- this project's second example of AS3605 reaching "
            "an in-scope target via Cogent through Japan rather than any "
            "regional path. Upstream of the target is AS174, RIS-agreeing "
            "with an *exact* match (830) -- and checked against AS9241's full "
            "neighbor list directly: AS174 is its single largest RIS-observed "
            "relationship (830 of ~1,700 total observations across all three "
            "of its neighbors), not a minor or coincidental one. One of two "
            "probes (329) was fully contiguous end-to-end; the other (64953) "
            "showed a gap immediately at the source hop too, but the "
            "RIS-agreeing upstream adjacency itself is identical and "
            "unambiguous on both."
        ),
    ),
    ConfirmedDetour(
        source_cc="GU",
        target_cc="VU",
        target_asn=9249,
        detour_ix_name="Level 3/Lumen (AS3356) + AS4637 (Telstra Global) -- global "
        "transit, not a named exchange crossing",
        detour_hub="Sydney",
        measurement_id=211334940,
        ris_observation_count=1346,
        note=(
            "Guam Cablevision (AS3605) -> Telecom Vanuatu (AS9249) -- pulled "
            "from the corridor backlog's top pick: a genuinely untested "
            "GU<->VU economy pair. Both probes: AS3605 -> AS3356 (Level "
            "3/Lumen) -> AS4637 (Telstra Global) -> AS38442 (Vodafone Fiji) "
            "-> AS9249. Upstream of the target is AS38442, RIS-agreeing with "
            "an *exact* match (1,346) -- this project's very first confirmed "
            "finding, now independently reinforced a **sixth** time, from a "
            "sixth distinct source network (after AS18200/OPT NC, "
            "AS45345/Nautile, AS56089/OFFRATEL, AS24390/USP, and "
            "AS17828/PNG DataCo). The final AS38442->AS9249 leg shows a "
            "single silent (non-responding) hop immediately before the "
            "target on both probes -- checked directly, not assumed: the "
            "same ordinary ICMP-filtering-right-at-the-destination pattern "
            "already seen in essentially every measurement that has ever "
            "targeted AS9249 this session, not a new or unusual gap. No IXP "
            "crossing this time (`ixp_crossings` empty) -- plain Tier-1 "
            "transit (Level 3/Lumen then Telstra Global), the same "
            "no-named-exchange shape as the AS17828->AS9249 and "
            "AS3605->AS9241 entries. Six independent, differently-sourced "
            "measurements landing on one identical adjacency, all with exact "
            "observation-count matches, is about as strong a single fact as "
            "this project has produced."
        ),
    ),
    ConfirmedDetour(
        source_cc="GU",
        target_cc="AS",
        target_asn=9751,
        detour_ix_name="AS174 (Cogent Communications), via AS2497 (IIJ, Japan) -- global "
        "transit, not a named exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211371732,
        ris_observation_count=1055,
        note=(
            "Guam Cablevision (AS3605) -> American Samoa (AS9751) -- pulled "
            "from the corridor backlog's top pick: a fresh GU<->AS economy "
            "pair. American Samoa itself has zero connected Atlas probes "
            "(unchanged all session), so this is the only direction this "
            "corridor can currently be tested from. Both probes fully "
            "contiguous end-to-end: AS3605 -> AS2497 (IIJ, Japan) -> AS174 "
            "(Cogent Communications) -> AS9751. Upstream of the target is "
            "AS174, RIS-agreeing with an *exact* match (1,055) -- checked "
            "directly against AS9751's full neighbor list "
            "(`{174: 1055, 3356: 333, 11404: 267}`): AS174 is its single "
            "largest relationship, not a minor one. **This is now the "
            "*third* instance of the identical AS3605 -> Tokyo (AS2497/IIJ) "
            "-> Cogent shape this session** (after AS17893/Palau and "
            "AS9241/FINTEL Fiji) -- no longer just a one-off pattern but a "
            "real, repeated signature of how this specific Guam carrier "
            "routes to multiple different Pacific destinations: via Japan "
            "and global Tier-1 transit, not any regional path, regardless of "
            "which island it's reaching."
        ),
    ),
)
