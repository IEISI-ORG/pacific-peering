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
            "finding is as solid as any in the project. "
            "**A third independent confirmation, this time from a genuinely "
            "different source economy** (measurement 211619574, VU/AS9249 -> "
            "PW/AS17893, a fresh VU<->PW pair): AS9249 -> AS38442 (Vodafone "
            "Fiji) -> AS2914 (NTT Communications) -> AS174 (Cogent "
            "Communications) -> AS17893, fully contiguous, no gaps. RIS "
            "agrees with the identical *exact* match (1,333). Notably a "
            "different path into Cogent than either prior Guam-sourced "
            "measurement -- via NTT (AS2914), not AS2497/IIJ -- but landing "
            "on the same ultimate AS174<->AS17893 adjacency. Three "
            "independent measurements, two different source economies, one "
            "identical, exact-match adjacency. "
            "**A fourth independent confirmation, a third distinct source "
            "economy** (measurement 211807422, PG/AS17828 -> PW/AS17893, a "
            "fresh PG<->PW pair): `AS17828 -> AS4826 (Vocus Connect) -> "
            "AS1299 (Telia) -> AS174 (Cogent Communications) -> AS17893`, "
            "fully contiguous. RIS agrees with the identical *exact* match "
            "(1,333). Yet another distinct intermediate carrier into "
            "Cogent -- Telia this time, neither IIJ nor NTT -- reinforcing "
            "that AS174 genuinely is Palau's real Cogent gateway "
            "regardless of which regional carrier's network the traffic "
            "transits first."
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
    ConfirmedDetour(
        source_cc="GU",
        target_cc="WS",
        target_asn=17993,
        detour_ix_name="AS174 (Cogent Communications), via AS3356 (Level 3/Lumen) -- "
        "global transit, not a named exchange crossing",
        detour_hub="Sydney",
        measurement_id=211418048,
        ris_observation_count=1455,
        note=(
            "Guam Cablevision (AS3605) -> Samoa (AS17993) -- pulled from the "
            "corridor backlog's top pick: a fresh GU<->WS economy pair. "
            "Measurement scheduled slowly again (a third occurrence of the "
            "same pattern already seen for AS9241 and AS9471 -- checked "
            "`participant_count` first, confirmed genuinely queued, resolved "
            "on a longer poll; treated as a now-recognized characteristic of "
            "AS3605's probes rather than re-investigated as a fresh anomaly). "
            "Both probes fully contiguous: AS3605 -> AS3356 (Level 3/Lumen) -> "
            "AS174 (Cogent Communications) -> AS17993. Upstream of the target "
            "is AS174, RIS-agreeing with an *exact* match (1,455) -- checked "
            "against AS17993's full neighbor list "
            "(`{174: 1455, 6939: 150, 64073: 10, ...}`): AS174 is overwhelmingly "
            "its dominant relationship. **A fourth AS3605-sourced measurement "
            "landing on Cogent as the target's real upstream** (after "
            "AS17893/Palau and AS9241/FINTEL Fiji via Tokyo/IIJ, and "
            "AS9751/American Samoa also via Tokyo/IIJ) -- this one via Level "
            "3/Lumen instead, no Tokyo hop this time, but the same ultimate "
            "carrier. Cogent is clearly AS3605's real default path to reach "
            "multiple different Pacific island networks, via more than one "
            "specific intermediate route."
        ),
    ),
    ConfirmedDetour(
        source_cc="GU",
        target_cc="MH",
        target_asn=24439,
        detour_ix_name="AS6453 (Tata Communications), via AS2497 (IIJ, Japan) -- global "
        "transit, not a named exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211465536,
        ris_observation_count=997,
        note=(
            "Guam Cablevision (AS3605) -> Marshall Islands NTA ISP (AS24439) -- "
            "pulled from the corridor backlog, immediately after excluding "
            "AS24013 (see task_plan.md: DNS.SB, a global anycast resolver "
            "opportunistically registered under a Solomon Islands country code, "
            "confirmed and excluded rather than tested as a corridor). Checked "
            "AS24439's own holder name directly before testing, given the "
            "session's established caution around Marshall-Islands-registered "
            "ASNs specifically (several already confirmed as offshore shell "
            "companies in `supplementary_asns.py`): \"NTAMAR-AS-AP - MARSHALL "
            "ISLANDS NTA ISP AS\" -- NTA is the Marshall Islands' actual "
            "National Telecommunications Authority, a real incumbent operator, "
            "not a shell; its target IP also resolves inside real APNIC space "
            "(103.202.149.0/24), unlike AS24013's RIPE-region anycast block. No "
            "anomaly here, proceeded normally. "
            "Both probes: AS3605 -> AS2497 (IIJ, Japan) -> AS6453 (Tata "
            "Communications) -- the target ASN itself never resolved (ordinary "
            "ICMP filtering near the destination, the established pattern for "
            "this situation), so RIS is checked against the last ASN the "
            "traceroute did reach, per this project's inbound-style validation "
            "method. RIS agrees with an *exact* match (997) -- checked directly "
            "against AS24439's full neighbor list: AS6453 is its *only* "
            "RIS-observed neighbor at all (997 of 997 total observations), a "
            "complete, exclusive relationship, not a partial one. Another "
            "instance of AS3605 reaching a Pacific destination via Tokyo and "
            "global Tier-1 transit rather than any regional path -- this "
            "session's fourth distinct Tier-1 carrier seen filling this exact "
            "role for AS3605 (Cogent, Telstra domestic+international, and now "
            "Tata)."
        ),
    ),
    ConfirmedDetour(
        source_cc="GU",
        target_cc="TO",
        target_asn=38198,
        detour_ix_name="AS3356 (Level 3/Lumen) + AS4637 (Telstra Global) + AS45355 "
        "(Digicel Fiji) -- global transit, not a named exchange crossing",
        detour_hub="Sydney",
        measurement_id=211478036,
        ris_observation_count=1321,
        note=(
            "Guam Cablevision (AS3605) -> Digicel Tonga (AS38198) -- a fresh "
            "GU<->TO economy pair. Sixth occurrence of the slow-scheduling "
            "pattern (recognized, resolved on a longer poll as before). "
            "Both probes: AS3605 -> AS3356 (Level 3/Lumen) -> AS4637 (Telstra "
            "Global) -> AS45355 (Digicel Fiji) -> AS38198. Upstream of the "
            "target is AS45355, RIS-agreeing with an *exact* match (1,321) -- "
            "checked against AS38198's full neighbor list: AS45355 is its "
            "*only* RIS-observed neighbor at all. "
            "**Checked the traceroute's tail carefully before writing this up "
            "as routine, since it read as more silence than usual**: both "
            "probes actually reach a real, BGP-confirmed AS38198 address "
            "(`202.43.12.5`) one hop after the last AS45355 hop, separated by "
            "exactly one ordinary silent boundary hop (the same routine "
            "pattern seen throughout this session) -- a solid, confirmed "
            "crossing into the target's own network, not a gap. Only *after* "
            "that does the traceroute go fully silent trying to reach the "
            "specific queried address (`202.43.12.1`) itself, all the way to "
            "the final hop -- read as the destination address itself not "
            "responding to traceroute probes at all (common for "
            "security-hardened endpoints), not evidence against the "
            "already-confirmed AS45355<->AS38198 adjacency, which sits before "
            "that silent stretch, not inside it. "
            "**Worth noting in its own right**: Digicel Fiji serving as the "
            "real upstream for Digicel Tonga -- both are regional "
            "subsidiaries of the same corporate parent (Digicel Group). Reads "
            "as intra-corporate regional transit, the same shape as the "
            "Wallis & Futuna -> Orange S.A. relationship, rather than "
            "arm's-length peering between unrelated carriers, though this "
            "traceroute alone doesn't distinguish corporate-internal routing "
            "from an ordinary customer-transit contract between the two."
        ),
    ),
    ConfirmedDetour(
        source_cc="GU",
        target_cc="WF",
        target_asn=45879,
        detour_ix_name="AS5511 (Opentransit Orange S.A.), via AS2497 (IIJ, Japan) -- "
        "global transit, not a named exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211486369,
        ris_observation_count=1665,
        note=(
            "Guam Cablevision (AS3605) -> Orange Wallis & Futuna (AS45879) -- a "
            "fresh GU<->WF economy pair. Seventh occurrence of the "
            "slow-scheduling pattern, resolved on a longer poll as before. "
            "Both probes: AS3605 -> AS2497 (IIJ, Japan) -> AS5511 (Opentransit "
            "Orange S.A.) -- the target itself never resolved (ordinary ICMP "
            "filtering, the established pattern), so RIS is checked against "
            "the last-reached ASN, per this project's inbound-style method. "
            "RIS agrees with an *exact* match (1,665) -- and this is the "
            "identical relationship and identical observation count already "
            "on record from this session's own market-structure analysis: "
            "AS45879's only RIS-observed neighbor at all is AS5511, Orange's "
            "own international backbone ASN, consistent with the operator "
            "itself being a direct Orange Group subsidiary rather than an "
            "independent carrier peering arm's-length. This project's fifth "
            "distinct global carrier now confirmed filling AS3605's "
            "\"reach a Pacific destination via Tokyo\" role (Cogent, Telstra "
            "domestic, Telstra Global, Tata, and now Opentransit Orange)."
        ),
    ),
    ConfirmedDetour(
        source_cc="GU",
        target_cc="SB",
        target_asn=45891,
        detour_ix_name="AS4637 (Telstra Global), via AS2497 (IIJ, Japan) -- global "
        "transit, not a named exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211488835,
        ris_observation_count=1652,
        note=(
            "Guam Cablevision (AS3605) -> Solomon Telekom Co Ltd (AS45891) -- "
            "a fresh GU<->SB economy pair. Checked AS45891's holder name "
            "directly before firing, given this session's now-standard "
            "caution after the AS24013 exclusion: \"SBT-AS-AP - Solomon "
            "Telekom Co Ltd\", a real incumbent, and the target IP resolves "
            "inside real APNIC space (202.1.164.0/24) -- no anomaly. Eighth "
            "occurrence of the slow-scheduling pattern, resolved on a longer "
            "poll as before. "
            "Both probes: AS3605 -> AS2497 (IIJ, Japan) -> AS4637 (Telstra "
            "Global) -> AS139609. The literal target (AS45891) never itself "
            "resolved -- but this is not a sibling-ASN case like the FSM/"
            "ONATI ones: AS139609 is a genuinely different, real entity, "
            "\"Solomon Islands Submarine Cable Company\" (SISCC), the actual "
            "operator of Solomon Islands' international submarine cable "
            "infrastructure. Checked directly: AS45891's *only* RIS-observed "
            "neighbor at all is AS139609 (1,652 observations), an *exact* "
            "match to what this traceroute found -- Solomon Telekom's real, "
            "retail-facing network depends entirely on SISCC's cable "
            "infrastructure for international connectivity, a completely "
            "sensible real-world relationship (retail ISP -> the country's "
            "own submarine cable operator), cleanly confirmed without needing "
            "any sibling-identity substitution."
        ),
    ),
    ConfirmedDetour(
        source_cc="GU",
        target_cc="PF",
        target_asn=55943,
        detour_ix_name="AS3257 (GTT Communications) -- global transit, not a named "
        "exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211499778,
        ris_observation_count=1657,
        note=(
            "Guam Cablevision (AS3605) -> ONATI's other ASN (AS55943, French "
            "Polynesia). GU<->PF had already been tested once this session via "
            "AS9471 (ONATI's primary identity) -- a genuine dead-end reaching "
            "only Hurricane Electric in Tokyo before going dark -- but that "
            "dead-end wasn't added to any dataclass, so it didn't exclude the "
            "economy pair; targeting ONATI's *other* ASN specifically was "
            "worth trying rather than assuming the same result. It wasn't the "
            "same result. Both probes: the target itself never resolved "
            "(ordinary ICMP filtering, the established pattern), but the last "
            "reached ASN is **AS3257 (GTT Communications)** -- a completely "
            "different carrier than the earlier AS9471 attempt's Hurricane "
            "Electric. RIS agrees with an *exact* match (1,657) -- checked "
            "against AS55943's full neighbor list: AS3257 is its dominant "
            "relationship (1,657 of 1,662 total observations). A real, clean "
            "confirmation, distinct in both target identity and carrier from "
            "the earlier dead-end -- illustrating why re-testing a different "
            "ASN within an already-attempted economy can be worth it when the "
            "first attempt was inconclusive rather than confirmed either way."
        ),
    ),
    ConfirmedDetour(
        source_cc="GU",
        target_cc="CK",
        target_asn=152093,
        detour_ix_name="BBIX Tokyo",
        detour_hub="Tokyo",
        measurement_id=211516729,
        ris_observation_count=335,
        note=(
            "Guam Cablevision (AS3605) -> VakaNet Limited (AS152093, Cook "
            "Islands) -- a second, distinct Cook Islands ASN tested from Guam "
            "this session (after AS10131, reached via the in-fishbowl ONATI "
            "transit corroboration). Both probes fully contiguous to AS9507 "
            "(NextHop Pty Ltd, Australia), resolved via PeeringDB netixlan, "
            "crossing **BBIX Tokyo** (out-of-fishbowl) -- a genuine named-"
            "exchange crossing this time, not just global transit. RIS agrees "
            "with an *exact* match (335) -- checked against AS152093's full "
            "neighbor list: AS9507 is its *only* RIS-observed neighbor at all. "
            "Notable contrast with the AS10131 corridor tested from the same "
            "source: that one reaches Cook Islands via an in-fishbowl Pacific "
            "carrier (ONATI); this one reaches a different Cook Islands "
            "operator via a conventional Australia/Tokyo exchange crossing -- "
            "two real, differently-shaped Cook Islands corridors, not a "
            "uniform national pattern."
        ),
    ),
    ConfirmedDetour(
        source_cc="GU",
        target_cc="NR",
        target_asn=152706,
        detour_ix_name="AS6453 (Tata Communications), via AS2497 (IIJ, Japan) -- global "
        "transit, not a named exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211520771,
        ris_observation_count=292,
        note=(
            "Guam Cablevision (AS3605) -> Neotel (AS152706, Nauru). Both "
            "probes fully contiguous to the literal target: AS3605 -> AS2497 "
            "(IIJ, Japan) -> AS6453 (Tata Communications) -> AS152706. RIS "
            "agrees with an *exact* match (292) -- checked against AS152706's "
            "full neighbor list: AS6453 is its dominant relationship (292 of "
            "roughly 333 total observations). This is the **second** distinct "
            "instance of Tata Communications filling AS3605's Tokyo-transit "
            "role this session (after AS24439/Marshall Islands) -- along with "
            "the two earlier Cogent instances (Palau, Fiji/FINTEL, American "
            "Samoa, Samoa) and Telstra's domestic+international pair, Tata is "
            "clearly a second real, recurring carrier in this Guam network's "
            "actual international transit mix, not a one-off."
        ),
    ),
    ConfirmedDetour(
        source_cc="MP",
        target_cc="VU",
        target_asn=9249,
        detour_ix_name="AS4637 (Telstra Global) -- global transit, not a named exchange "
        "crossing",
        detour_hub="Sydney",
        measurement_id=211537368,
        ris_observation_count=1346,
        note=(
            "PTI Pacifica (AS7131, CNMI) -> Telecom Vanuatu (AS9249) -- a fresh "
            "MP<->VU pair, retried against a second target address after the "
            "first AS9249 IP had produced a routing loop for a *different* "
            "target (AS9241) on this same source ASN two tranches earlier -- "
            "worth firing cleanly here rather than assuming the same problem. "
            "It didn't recur: probe 60689 fully contiguous end-to-end -- "
            "AS7131 -> AS6939 (Hurricane Electric) -> AS4637 (Telstra Global) "
            "-> AS38442 (Vodafone Fiji) -> AS9249. Upstream of the target is "
            "AS38442, RIS-agreeing with an *exact* match (1,346) -- this "
            "project's very first confirmed finding, now independently "
            "reinforced a **seventh** time, and the first from CNMI as a "
            "source. Probe 62689 shows the same adjacency but with a gap "
            "right before the literal target (ordinary silence, the "
            "well-established pattern for this specific corridor)."
        ),
    ),
    ConfirmedDetour(
        source_cc="MP",
        target_cc="AS",
        target_asn=9751,
        detour_ix_name="AS11404 (Wave Broadband) -- global transit, not a named exchange "
        "crossing",
        detour_hub="Honolulu",
        measurement_id=211542695,
        ris_observation_count=267,
        note=(
            "PTI Pacifica (AS7131, CNMI) -> American Samoa (AS9751) -- a "
            "fresh MP<->AS pair. First target address (`list_target_ips`' "
            "default first prefix) dead-ended past a private hop; retried "
            "against the next candidate address per the new retry policy and "
            "both probes reached the target cleanly this time. Path: AS7131 "
            "-> AS6939 (Hurricane Electric) -> AS11404 (Wave Broadband) -> "
            "AS9751, contiguous on probe 60689 (probe 62689 shows the same "
            "adjacency but with an unresolved gap before AS6939). Upstream "
            "of the target is AS11404, RIS-agreeing with an *exact* match "
            "(267) -- checked against AS9751's full neighbor list "
            "(`{174: 1055, 3356: 333, 11404: 267}`, already on record from "
            "the earlier AS3605->AS9751 Cogent/Tokyo entry above): AS11404 "
            "is a real, minority-but-genuine relationship, not a fluke. A "
            "**different** carrier reaching the same target than the "
            "existing GU->AS entry (Cogent via Tokyo) -- American Samoa's "
            "real transit mix includes at least two distinct Tier-1/backbone "
            "providers. No IXP crossing observed in this traceroute "
            "(`ixp_crossings` empty for both probes) -- `detour_hub` is "
            "Honolulu on the strength of AS9751's own registered PeeringDB "
            "presence at DRF IX, Honolulu (see its `fishbowl.json` entry), "
            "the standard Pacific cable hub for American Samoa's "
            "international connectivity, not a confirmed crossing point for "
            "*this specific* traceroute -- flagged here explicitly rather "
            "than implied as directly observed."
        ),
    ),
    ConfirmedDetour(
        source_cc="MP",
        target_cc="NC",
        target_asn=17480,
        detour_ix_name="BBIX Tokyo",
        detour_hub="Tokyo",
        measurement_id=211549691,
        ris_observation_count=1665,
        note=(
            "PTI Pacifica (AS7131, CNMI) -> a fresh, distinct New Caledonia "
            "ASN (AS17480) -- reached directly on the first address, no "
            "retry needed. Both probes fully contiguous: AS7131 -> AS38195 "
            "(Superloop, resolved via PeeringDB netixlan) -- crossing "
            "**BBIX Tokyo** (`ixp_crossings` confirms it directly, "
            "`in_fishbowl: false`) -- -> AS18200 (OPT NC, New Caledonia's "
            "own incumbent) -> AS17480. Upstream of the target is AS18200, "
            "RIS-agreeing with an *exact* match (1,665). Doubly "
            "corroborated: AS18200's own full neighbor list also directly "
            "confirms the AS38195 hop itself (`{174: 1156, 38195: 332, "
            "6939: 135, ...}`), not just the final leg. Notably *not* the "
            "same shape as this session's NC->GU Superloop precedent (a "
            "real signal that RIS couldn't corroborate at all, filed "
            "nowhere) -- here Superloop's presence is independently "
            "confirmed on **both** sides of it (into AS18200 from RIS's "
            "own path data, and out of AS18200 to AS17480 with an exact "
            "count match), a clean, fully-confirmed detour rather than an "
            "unfileable one. Also directly explains why: AS17480's own "
            "`fishbowl.json` entry lists a real PeeringDB facility "
            "presence at \"Equinix SY1/SY2 - Sydney\" *and* an IXP "
            "membership at CAN'L IX in Noumea -- but its actual traffic to "
            "reach a source outside New Caledonia in this measurement "
            "transits via its own incumbent (AS18200) and a Tokyo-based "
            "carrier instead, using neither of its own registered regional "
            "presences for this particular path."
        ),
    ),
    ConfirmedDetour(
        source_cc="MP",
        target_cc="PG",
        target_asn=17828,
        detour_ix_name="Equinix Sydney",
        detour_hub="Sydney",
        measurement_id=211552535,
        ris_observation_count=1283,
        note=(
            "PTI Pacifica (AS7131, CNMI) -> PNG DataCo (AS17828) -- a fresh "
            "MP<->PG pair, landing on this project's very first-ever "
            "confirmed finding (originally GU/AS3605->PG/AS17828, "
            "measurement 210901499), now independently reinforced a "
            "**second** time from a genuinely different source economy. "
            "Three probes requested; one (65653) was a complete dead end "
            "from the very first hop (only its own private address "
            "resolved, then total silence for the rest of that probe's own "
            "path) -- checked directly rather than assumed corridor-wide: "
            "the other two probes both worked cleanly, so this reads as a "
            "probe-specific local issue, not a property of the corridor "
            "itself. Both working probes: AS7131 -> AS6939 (Hurricane "
            "Electric) -> [gap] -> AS17828, upstream of target AS6939, "
            "RIS-agreeing with an *exact* match (1,283) -- identical count "
            "to the original finding. **Real IXP crossing confirmed "
            "directly this time** (`ixp_crossings` non-empty for both "
            "probes): probe 60689 shows both AS6939 and AS17828 as members "
            "at the same Equinix Sydney fabric hop; probe 62689 "
            "independently resolves AS17828 itself via a PeeringDB netixlan "
            "match at the same exchange. `has_routing_loop` flagged probe "
            "60689 `True` on a first pass -- checked directly before "
            "trusting it: the 'repeat' is a single near-destination address "
            "(202.165.198.250, inside AS17828's own announced range) "
            "replying at two consecutive hops with stable, non-climbing "
            "RTT (229ms/240ms) right before the literal queried address "
            "goes dark -- the same ordinary near-destination ICMP-silence "
            "shape seen throughout this session, not the AS9241/Hurricane-"
            "Electric loop signature (which showed RTT climbing well past "
            "290ms across *multiple* consecutive hops). A real limit of "
            "the current heuristic worth noting for next time: it only "
            "clears a repeat as safe when the *literal* queried address "
            "appears somewhere in the hops, but a near-destination address "
            "inside the target's own announced range that still isn't the "
            "literal target can trigger a false positive -- caught here by "
            "checking the underlying hop data directly rather than trusting "
            "the flag at face value, not by a code change (no live "
            "second data point to refine against yet, unlike the original "
            "false-positive fix)."
        ),
    ),
    ConfirmedDetour(
        source_cc="MP",
        target_cc="WS",
        target_asn=17993,
        detour_ix_name="Equinix Sydney",
        detour_hub="Sydney",
        measurement_id=211558417,
        ris_observation_count=150,
        note=(
            "PTI Pacifica (AS7131, CNMI) -> Samoa (AS17993) -- a fresh "
            "MP<->WS pair. All 3 probes: AS7131 -> AS6939 (Hurricane "
            "Electric) -> [gap] -> AS17993, upstream of target AS6939, "
            "RIS-agreeing with an *exact* match (150). A **different** "
            "carrier than the existing GU(AS3605)->WS entry (AS174/Cogent "
            "+ AS3356/Level3, count 1,455) -- checked against AS17993's "
            "full neighbor list (`{174: 1455, 6939: 150, 64073: 10, ...}`, "
            "already on record from that earlier entry): AS6939 is a real, "
            "minor-but-genuine relationship, not the dominant one, "
            "confirming Samoa's real transit mix includes at least two "
            "distinct Tier-1 carriers, the same shape already seen for "
            "American Samoa (AS9751, Cogent vs. Wave Broadband). Real IXP "
            "crossing confirmed directly this time -- `ixp_crossings` "
            "non-empty for all 3 probes, all landing on Equinix Sydney "
            "(one shows both AS6939 and AS17993 as members at the same "
            "hop, the other two resolve AS17993 itself there via "
            "PeeringDB netixlan)."
        ),
    ),
    ConfirmedDetour(
        source_cc="MP",
        target_cc="FJ",
        target_asn=24390,
        detour_ix_name="AS140627 (OneQode) -- global transit, not a named exchange "
        "crossing",
        detour_hub="Sydney",
        measurement_id=211564127,
        ris_observation_count=337,
        note=(
            "PTI Pacifica (AS7131, CNMI) -> University of the South "
            "Pacific's own network (AS24390) -- a fresh MP<->FJ pair, and "
            "the first time this project has targeted AS24390 directly as "
            "the destination (it was previously only ever the *source* of "
            "the FJ->VU/AS9249 detour, see the AS24390 entry above). Both "
            "probes: AS7131 -> AS140627 (OneQode) -> AS7575 (AARNet, "
            "Australia's research/education network, resolved via "
            "PeeringDB netixlan) -- the literal target itself never "
            "resolved (ordinary ICMP filtering near the destination, the "
            "established pattern), so RIS is checked against the last "
            "reached ASN, per this project's inbound-style method. RIS "
            "agrees with an *exact* match (337) -- and this is the "
            "identical relationship and count already on record from the "
            "AS24390->AS9249 entry's own note: AS7575 is AS24390's *only* "
            "RIS-observed neighbor at all. No IXP crossing this time "
            "(`ixp_crossings` empty for both probes) -- plain global "
            "transit through OneQode, a carrier already seen once before "
            "this session (AS17893's and AS7131's own fishbowl neighbor "
            "lists both already listed it as a minor relationship)."
        ),
    ),
    ConfirmedDetour(
        source_cc="MP",
        target_cc="MH",
        target_asn=24439,
        detour_ix_name="AS174 (Cogent Communications), via AS6453 (Tata Communications) "
        "-- global transit, not a named exchange crossing",
        detour_hub="Sydney",
        measurement_id=211567329,
        ris_observation_count=997,
        note=(
            "PTI Pacifica (AS7131, CNMI) -> Marshall Islands NTA ISP "
            "(AS24439) -- a fresh MP<->MH pair, landing on the existing "
            "GU(AS3605)->MH `ConfirmedDetour` adjacency (AS6453<->AS24439), "
            "now a second independent confirmation from a different source "
            "economy. All 3 probes: AS7131 -> AS174 (Cogent Communications) "
            "-> AS6453 (Tata Communications) -- the target itself never "
            "resolved (ordinary ICMP filtering near the destination, the "
            "established pattern), so RIS is checked against the last "
            "reached ASN. RIS agrees with an *exact* match (997), "
            "identical to the original finding -- checked directly: AS6453 "
            "is still AS24439's *only* RIS-observed neighbor at all. A "
            "**different** path into Tata than the original (which went via "
            "AS2497/IIJ and Tokyo) -- this one via Cogent directly, no "
            "Tokyo hop. `has_routing_loop` flagged 2 of 3 probes `True` on "
            "a first pass -- checked directly before trusting it, per the "
            "now-established process from the AS17828 case: both "
            "'repeats' are near-destination addresses (`180.87.180.33`, "
            "`209.58.61.40` -- inside Tata's own transit space, not the "
            "literal target) replying at consecutive hops with stable, "
            "non-climbing RTT, the same ordinary noise pattern, not a real "
            "loop."
        ),
    ),
    ConfirmedDetour(
        source_cc="MP",
        target_cc="TO",
        target_asn=38198,
        detour_ix_name="AS6939 (Hurricane Electric) + AS132528 (Digicel Australia/"
        "Telstra-operated backbone) -- global transit, not a named exchange "
        "crossing",
        detour_hub="Sydney",
        measurement_id=211570035,
        ris_observation_count=1321,
        note=(
            "PTI Pacifica (AS7131, CNMI) -> Digicel Tonga (AS38198) -- a "
            "fresh MP<->TO pair, landing on the existing GU(AS3605)->TO "
            "adjacency (AS45355<->AS38198), a second independent "
            "confirmation from a different source economy. Upstream of "
            "the target is AS45355 (Digicel Fiji), RIS-agreeing with an "
            "*exact* match (1,321), identical to the original finding. "
            "Genuinely new detail this time: probe 62689 resolves an "
            "intermediate hop to **AS132528** -- the same Telstra-operated "
            "Digicel-Australia backbone ASN already independently "
            "confirmed at Equinix Sydney in the NC->FJ/AS45355 entry above "
            "-- `ixp_crossings` confirms it directly at that same fabric "
            "again here, a second, unrelated measurement finding the "
            "identical real infrastructure. `has_routing_loop` flagged "
            "probe 60689 `True` -- checked directly per the now-standard "
            "process: a near-destination repeat (`202.43.12.5`, not the "
            "literal target `202.43.12.1`) with stable RTT, the same "
            "known ordinary-noise shape, not a real loop. All 3 probes "
            "eventually reach the same real, BGP-confirmed AS38198 "
            "address (`202.43.12.5`) already established in the original "
            "entry as this corridor's routine final-hop pattern."
        ),
    ),
    ConfirmedDetour(
        source_cc="MP",
        target_cc="WF",
        target_asn=45879,
        detour_ix_name="AS5511 (Opentransit Orange S.A.) -- global transit, not a named "
        "exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211577395,
        ris_observation_count=1665,
        note=(
            "PTI Pacifica (AS7131, CNMI) -> Orange Wallis & Futuna "
            "(AS45879) -- a fresh MP<->WF pair, landing on the existing "
            "GU(AS3605)->WF adjacency (AS5511<->AS45879), a second "
            "independent confirmation from a different source economy. "
            "Upstream of the target is AS5511, RIS-agreeing with an "
            "*exact* match (1,665), identical to the original finding. A "
            "different path into Orange this time: AS7131 -> AS6939 "
            "(Hurricane Electric) -> AS5511 directly, no Tokyo/IIJ hop "
            "unlike the original. Kept `detour_hub` as Tokyo anyway rather "
            "than guessing a new location: checked AS5511's real "
            "PeeringDB-registered facility presence directly (not "
            "assumed) -- four separate Equinix Tokyo data centers "
            "(TY2/TY6/TY7/TY8) and no Sydney presence at all, so Tokyo "
            "remains the best-sourced location for this adjacency even "
            "though this specific traceroute's own path doesn't show a "
            "literal Tokyo hop. `has_routing_loop` flagged probe 60689 "
            "`True` -- checked directly: a single consecutive repeat "
            "(`184.104.208.73`) early in the Hurricane Electric backbone "
            "with only a modest RTT bump (49ms -> 58ms), not the "
            "near-destination or steep-RTT-climb shape of a real loop -- "
            "ordinary noise."
        ),
    ),
    ConfirmedDetour(
        source_cc="MP",
        target_cc="SB",
        target_asn=45891,
        detour_ix_name="IX Australia Sydney (NSW-IX)",
        detour_hub="Sydney",
        measurement_id=211579683,
        ris_observation_count=1652,
        note=(
            "PTI Pacifica (AS7131, CNMI) -> Solomon Telekom Co Ltd "
            "(AS45891) -- a fresh MP<->SB pair, landing on the existing "
            "GU(AS3605)->SB adjacency (AS139609/SISCC<->AS45891), a "
            "second independent confirmation from a different source "
            "economy. Upstream of the target is AS139609 (Solomon Islands "
            "Submarine Cable Company), RIS-agreeing with an *exact* match "
            "(1,652), identical to the original finding. A different "
            "carrier and a genuinely new named exchange this time: AS7131 "
            "-> AS140627 (OneQode, already seen once before for the "
            "FJ/USP corridor) -> AS139609, crossing **IX Australia Sydney "
            "(NSW-IX)** -- `ixp_crossings` confirms it directly for 2 of 3 "
            "probes -- the first time this specific exchange (distinct "
            "from Equinix Sydney and MegaIX Sydney, both already on "
            "record) has appeared in this project. `has_routing_loop` "
            "flagged probe 65653 `True` -- checked directly: two "
            "consecutive-address repeats, both with stable, non-climbing "
            "RTT, the same ordinary noise pattern documented for prior "
            "false positives, not a real loop."
        ),
    ),
    ConfirmedDetour(
        source_cc="MP",
        target_cc="PF",
        target_asn=55943,
        detour_ix_name="AS174 (Cogent Communications), then AS3257 (GTT "
        "Communications) -- global transit, not a named exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211585981,
        ris_observation_count=1657,
        note=(
            "PTI Pacifica (AS7131, CNMI) -> ONATI's other ASN (AS55943, "
            "French Polynesia) -- a fresh MP<->PF pair, landing on the "
            "existing GU(AS3605)->PF adjacency (AS3257/GTT<->AS55943), a "
            "second independent confirmation from a different source "
            "economy. All 3 probes: AS7131 -> AS174 (Cogent Communications) "
            "-> AS3257 (GTT Communications) -- the literal target itself "
            "never resolved (ordinary ICMP filtering near the destination, "
            "the established pattern), so RIS is checked against the last "
            "reached ASN. RIS agrees with an *exact* match (1,657), "
            "identical to the original finding -- AS3257 remains AS55943's "
            "dominant relationship. `has_routing_loop` flagged probe "
            "60689 `True` -- checked directly: two consecutive-address "
            "repeats early in the path, both with modest, stable RTT, the "
            "now-familiar ordinary-noise shape, not a real loop."
        ),
    ),
    ConfirmedDetour(
        source_cc="MP",
        target_cc="CK",
        target_asn=152093,
        detour_ix_name="BBIX Tokyo",
        detour_hub="Tokyo",
        measurement_id=211596810,
        ris_observation_count=335,
        note=(
            "PTI Pacifica (AS7131, CNMI) -> VakaNet Limited (AS152093, "
            "Cook Islands) -- a fresh MP<->CK pair, landing on the "
            "existing GU(AS3605)->CK adjacency (AS9507/NextHop<->AS152093), "
            "a second independent confirmation from a different source "
            "economy. All 3 probes: AS7131 -> AS9507 (NextHop Pty Ltd, "
            "Australia, resolved via PeeringDB netixlan) -- the literal "
            "target itself never resolved (ordinary ICMP filtering near "
            "the destination), so RIS is checked against the last reached "
            "ASN. RIS agrees with an *exact* match (335), identical to the "
            "original finding -- AS9507 remains AS152093's *only* "
            "RIS-observed neighbor at all. **All 3 probes** cross **BBIX "
            "Tokyo** directly this time (`ixp_crossings` confirms it for "
            "every probe), an even stronger direct confirmation than the "
            "original's crossing. `has_routing_loop` flagged probe 60689 "
            "`True` -- checked directly: a single consecutive repeat with "
            "modest, stable RTT, the now-familiar ordinary-noise shape, "
            "not a real loop."
        ),
    ),
    ConfirmedDetour(
        source_cc="VU",
        target_cc="AS",
        target_asn=9751,
        detour_ix_name="Equinix San Jose",
        detour_hub="San Jose",
        measurement_id=211613571,
        ris_observation_count=267,
        note=(
            "Telecom Vanuatu (AS9249) -> American Samoa (AS9751) -- the "
            "first corridor genuinely sourced from AS9249 to reach the "
            "target (the previous AS9249 firing, toward AS9471, dead-ended "
            "on the first address). Path: AS9249 -> AS38442 (Vodafone "
            "Fiji) -> AS4637 (Telstra Global) -> AS11404 (Wave Broadband) "
            "-> AS9751. Upstream of the target is AS11404, RIS-agreeing "
            "with an *exact* match (267) -- landing on the existing "
            "MP(AS7131)->AS adjacency (Wave Broadband<->AS9751), a second "
            "independent confirmation. **A genuine improvement on that "
            "original entry**: this traceroute directly crosses a real, "
            "named exchange -- **Equinix San Jose** (`ixp_crossings` "
            "confirms it, `in_fishbowl: false`) -- where the original "
            "found no IXP crossing at all. A new external hub for this "
            "project (added `\"San Jose\": (37.3382, -121.8863)` to "
            "`economy_coordinates.EXTERNAL_HUB_LATLON`), directly observed "
            "rather than inferred."
        ),
    ),
    ConfirmedDetour(
        source_cc="VU",
        target_cc="MH",
        target_asn=24439,
        detour_ix_name="AS7473 (Singtel), via AS6453 (Tata Communications) -- global "
        "transit, not a named exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211627606,
        ris_observation_count=997,
        note=(
            "Telecom Vanuatu (AS9249) -> Marshall Islands NTA ISP "
            "(AS24439) -- a fresh VU<->MH pair, a third independent "
            "confirmation of the AS6453(Tata)<->AS24439 adjacency (after "
            "the original GU entry via IIJ/Tokyo and the MP entry via "
            "Cogent). Both probes: AS9249 -> AS38442 (Vodafone Fiji) -> "
            "AS7473 (Singapore Telecommunications Ltd) -> AS6453 -- the "
            "target itself never resolved (ordinary ICMP filtering near "
            "the destination), so RIS is checked against the last reached "
            "ASN. RIS agrees with an *exact* match (997), identical to "
            "both prior instances -- AS6453 remains AS24439's *only* "
            "RIS-observed neighbor. A genuinely new intermediate carrier "
            "(Singtel) for this adjacency, not previously seen. No IXP "
            "crossing this time (`ixp_crossings` empty for both probes) -- "
            "checked Singtel's real PeeringDB facility list before "
            "picking a hub: genuine presence at Equinix Tokyo, no Sydney "
            "presence, so kept `detour_hub` as Tokyo, matching the "
            "original entry rather than the Cogent-sourced second one's "
            "Sydney choice."
        ),
    ),
    ConfirmedDetour(
        source_cc="VU",
        target_cc="TO",
        target_asn=38198,
        detour_ix_name="Equinix Sydney (AS132528, Digicel Australia/Telstra-operated "
        "backbone)",
        detour_hub="Sydney",
        measurement_id=211629028,
        ris_observation_count=1321,
        note=(
            "Telecom Vanuatu (AS9249) -> Digicel Tonga (AS38198) -- a "
            "fresh VU<->TO pair, a third independent confirmation of the "
            "AS45355(Digicel Fiji)<->AS38198 adjacency (after the GU entry "
            "via Level 3/Lumen+Telstra Global and the MP entry via "
            "Hurricane Electric). Both probes: AS9249 -> AS38442 "
            "(Vodafone Fiji) -> **AS132528** -> AS45355 -> AS38198. "
            "Upstream of the target is AS45355, RIS-agreeing with the "
            "identical *exact* match (1,321). **A third occurrence of "
            "AS132528 (the Telstra-operated Digicel-Australia backbone) at "
            "Equinix Sydney** -- confirmed directly this time "
            "(`ixp_crossings` non-empty for both probes, unlike the "
            "MP-sourced entry where it only appeared as an intermediate "
            "hop without a direct crossing match). Both probes reach the "
            "same real, BGP-confirmed AS38198 address (`202.43.12.5`) "
            "already established across every prior measurement of this "
            "corridor as its routine final-hop pattern."
        ),
    ),
    ConfirmedDetour(
        source_cc="VU",
        target_cc="WS",
        target_asn=38800,
        detour_ix_name="Equinix Sydney (AS132528, Digicel Australia/Telstra-operated "
        "backbone)",
        detour_hub="Sydney",
        measurement_id=211632578,
        ris_observation_count=1656,
        note=(
            "Telecom Vanuatu (AS9249) -> Digicel Samoa Ltd (AS38800) -- "
            "targeting Digicel Samoa directly, immediately after last "
            "tranche's corridor happened to transit through it on the way "
            "to CSL Samoa (AS38227). Both probes fully contiguous: AS9249 "
            "-> AS38442 (Vodafone Fiji) -> **AS132528** -> AS38800. "
            "Upstream of the target is AS132528 itself directly -- the "
            "**fifth** occurrence of this Telstra-operated Digicel-"
            "Australia backbone ASN at Equinix Sydney this session, but "
            "the *first* time it's the literal immediate upstream of the "
            "target rather than an intermediate waypoint before further "
            "Pacific infrastructure. RIS agrees with an *exact* match "
            "(1,656) -- checked directly against AS38800's full neighbor "
            "list: AS132528 is its *only* RIS-observed neighbor at all "
            "(1,656 of 1,656 total observations), confirming Digicel "
            "Samoa's real international upstream is exclusively Digicel's "
            "own Australia-based backbone. The cleanest, most direct "
            "confirmation yet of this now-well-established infrastructure."
        ),
    ),
    ConfirmedDetour(
        source_cc="VU",
        target_cc="WF",
        target_asn=45879,
        detour_ix_name="AS5511 (Opentransit Orange S.A.) -- global transit, not a named "
        "exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211633489,
        ris_observation_count=1665,
        note=(
            "Telecom Vanuatu (AS9249) -> Orange Wallis & Futuna (AS45879) "
            "-- a fresh VU<->WF pair, a third independent confirmation of "
            "the AS5511(Opentransit Orange)<->AS45879 adjacency (after "
            "the GU entry and the MP entry). Both probes: AS9249 -> "
            "AS38442 (Vodafone Fiji) -> AS4637 (Telstra Global) -> AS5511 "
            "-- the target itself never resolved (ordinary ICMP "
            "filtering near the destination), so RIS is checked against "
            "the last reached ASN. RIS agrees with the identical *exact* "
            "match (1,665). No IXP crossing this time (`ixp_crossings` "
            "empty for both probes) -- kept `detour_hub` as Tokyo, "
            "already verified in the MP-sourced entry against AS5511's "
            "real PeeringDB facility list (four Equinix Tokyo DCs, no "
            "Sydney presence)."
        ),
    ),
    ConfirmedDetour(
        source_cc="VU",
        target_cc="SB",
        target_asn=45891,
        detour_ix_name="MegaIX Sydney",
        detour_hub="Sydney",
        measurement_id=211635580,
        ris_observation_count=1652,
        note=(
            "Telecom Vanuatu (AS9249) -> Solomon Telekom Co Ltd (AS45891) "
            "-- a fresh VU<->SB pair, a third independent confirmation of "
            "the AS139609(SISCC)<->AS45891 adjacency (after the GU entry "
            "and the MP entry via NSW-IX). A notably short, direct path "
            "this time: `AS9249 -> AS38442 (Vodafone Fiji) -> AS139609` "
            "-- the target itself never resolved (ordinary ICMP filtering "
            "near the destination), so RIS is checked against the last "
            "reached ASN. RIS agrees with the identical *exact* match "
            "(1,652). Crosses **MegaIX Sydney** directly (`ixp_crossings` "
            "confirms it for both probes) -- a different named exchange "
            "than the MP-sourced entry's NSW-IX, a third distinct Sydney "
            "fabric now on record for this project (alongside Equinix "
            "Sydney and NSW-IX)."
        ),
    ),
    ConfirmedDetour(
        source_cc="VU",
        target_cc="PF",
        target_asn=55943,
        detour_ix_name="AS4637 (Telstra Global), then AS3257 (GTT Communications) -- "
        "global transit, not a named exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211640827,
        ris_observation_count=1657,
        note=(
            "Telecom Vanuatu (AS9249) -> ONATI's other ASN (AS55943, "
            "French Polynesia) -- a fresh VU<->PF pair, a third "
            "independent confirmation of the AS3257(GTT)<->AS55943 "
            "adjacency (after the GU entry and the MP entry via Cogent). "
            "Both probes: AS9249 -> AS38442 (Vodafone Fiji) -> AS4637 "
            "(Telstra Global) -> AS3257 -- the literal target never "
            "resolved (ordinary ICMP filtering near the destination), so "
            "RIS is checked against the last reached ASN. RIS agrees with "
            "the identical *exact* match (1,657). No IXP crossing this "
            "time (`ixp_crossings` empty for both probes) -- kept "
            "`detour_hub` as Tokyo, already verified against GTT's real "
            "PeeringDB facility list in the MP-sourced entry (genuine "
            "Tokyo and Sydney presence)."
        ),
    ),
    ConfirmedDetour(
        source_cc="VU",
        target_cc="CK",
        target_asn=152093,
        detour_ix_name="Equinix Sydney",
        detour_hub="Sydney",
        measurement_id=211654723,
        ris_observation_count=335,
        note=(
            "Telecom Vanuatu (AS9249) -> VakaNet Limited (AS152093, Cook "
            "Islands) -- a fresh VU<->CK pair, a third independent "
            "confirmation of the AS9507(NextHop)<->AS152093 adjacency "
            "(after the GU entry and the MP entry). The shortest path yet "
            "for this adjacency: `AS9249 -> AS38442 (Vodafone Fiji) -> "
            "AS9507`, upstream of the target directly, RIS-agreeing with "
            "the identical *exact* match (335). Crosses **Equinix Sydney** "
            "directly (`ixp_crossings` confirms it for both probes)."
        ),
    ),
    ConfirmedDetour(
        source_cc="VU",
        target_cc="NR",
        target_asn=152706,
        detour_ix_name="AS4637 (Telstra Global), then AS6453 (Tata "
        "Communications) -- global transit, not a named exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211657025,
        ris_observation_count=292,
        note=(
            "Telecom Vanuatu (AS9249) -> Neotel (AS152706, Nauru) -- a "
            "fresh VU<->NR pair, a second independent confirmation of the "
            "AS6453(Tata)<->AS152706 adjacency (after the GU entry via "
            "IIJ/Tokyo). Path: `AS9249 -> AS38442 (Vodafone Fiji) -> "
            "AS4637 (Telstra Global) -> AS6453`, upstream of the target, "
            "RIS-agreeing with the identical *exact* match (292). No IXP "
            "crossing this time (`ixp_crossings` empty for both probes); "
            "checked Tata's real PeeringDB facility list before keeping "
            "the hub -- genuine presence at both Equinix Tokyo and Sydney, "
            "so kept `detour_hub` as Tokyo, matching the original entry."
        ),
    ),
    ConfirmedDetour(
        source_cc="PF",
        target_cc="AS",
        target_asn=9751,
        detour_ix_name="AS174 (Cogent Communications) -- global transit, not a named "
        "exchange crossing",
        detour_hub="Portland",
        measurement_id=211668556,
        ris_observation_count=1055,
        note=(
            "ONATI (AS9471, French Polynesia) -> American Samoa (AS9751) "
            "-- a fresh PF<->AS pair, the first firing genuinely sourced "
            "from AS9471 to actually reach a target. Third confirmation "
            "for this specific target, via the same ultimate carrier "
            "(Cogent) as the original GU entry, but a different vantage "
            "point than either prior instance (GU/Cogent, VU/Wave "
            "Broadband). All 3 probes: `AS9471 -> AS174 -> AS9751`, "
            "RIS-agreeing with the identical *exact* match (1,055). No "
            "IXP crossing (`ixp_crossings` empty for all three). "
            "**Hub corrected from an original draft's \"Tokyo\"**: the "
            "original choice was carried over from Cogent's real but "
            "generic PeeringDB facility list (Cogent genuinely has both "
            "Tokyo and Sydney presence) without checking what this "
            "specific traceroute's own hops actually show -- caught when "
            "the project owner questioned whether a direct PF-Japan path "
            "was real. Reverse-DNS'd the resolved Cogent hops directly "
            "(via the new `hop_geolocation` module): `be2728.ccr42.lax01."
            "atlas.cogentco.com` -> `be5991.ccr22.sfo01.atlas.cogentco.com` "
            "-> `be2467.ccr51.pdx02.atlas.cogentco.com` -- Los Angeles, "
            "San Francisco, then Portland, entirely US West Coast, "
            "nowhere near Japan. Kept `detour_hub` as Portland, the "
            "last confirmed location before the destination replies."
        ),
    ),
    ConfirmedDetour(
        source_cc="PF",
        target_cc="NC",
        target_asn=17480,
        detour_ix_name="Equinix Sydney",
        detour_hub="Sydney",
        measurement_id=211671233,
        ris_observation_count=1665,
        note=(
            "ONATI (AS9471, French Polynesia) -> a fresh New Caledonia "
            "ASN (AS17480) -- a fresh PF<->NC pair, a second independent "
            "confirmation of the AS18200(OPT NC)<->AS17480 adjacency "
            "(after the MP entry via Superloop/BBIX Tokyo). All 3 probes: "
            "`AS9471 -> AS6939 (Hurricane Electric) -> AS18200 -> "
            "AS17480`, RIS-agreeing with the identical *exact* match "
            "(1,665). **Genuinely different named exchange this time**: "
            "crosses **Equinix Sydney** directly (`ixp_crossings` "
            "confirms it for all 3 probes), not BBIX Tokyo -- and "
            "notably, this *does* match AS17480's own registered "
            "PeeringDB facility presence at Equinix SY1/SY2 Sydney, "
            "unlike the original MP-sourced measurement which crossed "
            "neither of AS17480's own registered regional presences at "
            "all. A nice confirmatory contrast: the same target's real "
            "traffic uses different real infrastructure depending on the "
            "source, and this time it happens to line up with its own "
            "declared Sydney presence."
        ),
    ),
    ConfirmedDetour(
        source_cc="PF",
        target_cc="PG",
        target_asn=17828,
        detour_ix_name="AS6939 (Hurricane Electric) -- global transit, not a named "
        "exchange crossing",
        detour_hub="Sydney",
        measurement_id=211672420,
        ris_observation_count=1283,
        note=(
            "ONATI (AS9471, French Polynesia) -> PNG DataCo (AS17828) -- "
            "a fresh PF<->PG pair, a third independent confirmation of "
            "this project's very first-ever confirmed finding "
            "(AS6939<->AS17828), from a genuinely different source "
            "economy (after GU and MP). All 3 probes: `AS9471 -> AS6939 "
            "-> [gap] -> AS17828`, RIS-agreeing with the identical *exact* "
            "match (1,283). No IXP crossing this time (`ixp_crossings` "
            "empty for all three). All 3 probes reach the same real "
            "near-destination address (`202.165.198.250`) already "
            "established from the GU-sourced entry as this corridor's "
            "routine last-hop pattern before the literal target goes "
            "silent."
        ),
    ),
    ConfirmedDetour(
        source_cc="PF",
        target_cc="PW",
        target_asn=17893,
        detour_ix_name="AS6939 (Hurricane Electric) -- global transit, not a named "
        "exchange crossing",
        detour_hub="Sydney",
        measurement_id=211674609,
        ris_observation_count=106,
        note=(
            "ONATI (AS9471, French Polynesia) -> Palau NCC (AS17893) -- "
            "a fresh PF<->PW pair. All 3 probes: `AS9471 -> AS6939 -> "
            "[gap] -> AS17893` -- the literal target never resolved "
            "(ordinary ICMP filtering near the destination), so RIS is "
            "checked against the last reached ASN. RIS agrees with an "
            "*exact* match (106). **The first direct traceroute "
            "confirmation of this specific adjacency**: AS6939 already "
            "appeared in AS17893's own neighbor list "
            "(`{174: 1333, 140627: 139, 6939: 106, ...}`) as quoted "
            "context in the existing `CandidatePeering` entries for "
            "AS17893, but had never itself been the traceroute-confirmed "
            "upstream until now -- a real, if minor, relationship "
            "(106 of ~1,483 total observations), not noise. No IXP "
            "crossing (`ixp_crossings` empty for all three); checked "
            "Hurricane Electric's real PeeringDB facility list -- "
            "genuine Sydney presence, consistent with the Sydney hub "
            "already used for Hurricane Electric elsewhere in this "
            "project."
        ),
    ),
    ConfirmedDetour(
        source_cc="PF",
        target_cc="WS",
        target_asn=17993,
        detour_ix_name="Equinix Sydney",
        detour_hub="Sydney",
        measurement_id=211677101,
        ris_observation_count=150,
        note=(
            "ONATI (AS9471, French Polynesia) -> Vodafone Samoa Limited "
            "(AS17993) -- a fresh PF<->WS pair, a second independent "
            "confirmation of the AS6939(Hurricane Electric)<->AS17993 "
            "adjacency (after the MP entry). All 3 probes: `AS9471 -> "
            "AS6939 -> AS17993`, RIS-agreeing with the identical *exact* "
            "match (150). Crosses **Equinix Sydney** directly "
            "(`ixp_crossings` confirms it for all three probes) -- the "
            "same exchange as the original entry, now confirmed for the "
            "full probe set."
        ),
    ),
    ConfirmedDetour(
        source_cc="PF",
        target_cc="FJ",
        target_asn=24390,
        detour_ix_name="Any2West",
        detour_hub="Los Angeles",
        measurement_id=211682462,
        ris_observation_count=337,
        note=(
            "ONATI (AS9471, French Polynesia) -> University of the South "
            "Pacific's own network (AS24390) -- a fresh PF<->FJ pair, a "
            "second independent confirmation of the AS7575(AARNet)<->"
            "AS24390 adjacency (after the MP entry via OneQode). This "
            "time via Hurricane Electric (AS6939) directly, and crossing "
            "a **real named exchange**: **Any2West** (`ixp_crossings` "
            "confirms it for all 3 probes) -- Any2West is based in Los "
            "Angeles/Silicon Valley, genuinely distinct from the "
            "existing San Jose hub (~550km away), so added a fifth "
            "external hub (`\"Los Angeles\": (34.0522, -118.2437)`) "
            "rather than conflating the two. RIS agrees with the "
            "identical *exact* match (337)."
        ),
    ),
    ConfirmedDetour(
        source_cc="PF",
        target_cc="MH",
        target_asn=24439,
        detour_ix_name="AS3257 (GTT Communications), via AS6453 (Tata "
        "Communications) -- global transit, not a named exchange crossing",
        detour_hub="Los Angeles",
        measurement_id=211683854,
        ris_observation_count=997,
        note=(
            "ONATI (AS9471, French Polynesia) -> Marshall Islands NTA ISP "
            "(AS24439) -- a fresh PF<->MH pair, a fourth independent "
            "confirmation of the AS6453(Tata)<->AS24439 adjacency (after "
            "GU via IIJ/Tokyo, MP via Cogent, and VU via Singtel). "
            "`AS9471 -> AS3257 (GTT) -> AS6453` -- the target itself "
            "never resolved (ordinary ICMP filtering near the "
            "destination), so RIS is checked against the last reached "
            "ASN. RIS agrees with the identical *exact* match (997). "
            "GTT is a genuinely new intermediate carrier for this "
            "adjacency. No IXP crossing. "
            "**Hub corrected from an original draft's \"Tokyo\"**: the "
            "original choice reused Tata's known Tokyo/Sydney PeeringDB "
            "presence from an earlier NR-sourced entry, without checking "
            "what this specific traceroute's own hops show -- caught when "
            "the project owner questioned whether a direct PF-Japan path "
            "was real. Reverse-DNS'd the resolved Tata hops directly (via "
            "the new `hop_geolocation` module): `ix-bundle-23.qcore2.lvw-"
            "losangeles.as6453.net` -> `if-bundle-41-2.qhar2.pv4-piti."
            "as6453.net` (twice) -- Los Angeles, then **Piti, Guam** -- "
            "not Tokyo at all. The Piti hop is itself a genuine, "
            "PeeringDB-confirmed Tata facility (net_id 437, \"TATA "
            "Communications - Piti Cable Landing Station\"), now recorded "
            "in `analysis/regional_carrier_facilities.py` as Tata's "
            "second confirmed in-fishbowl facility after OneQode's -- but "
            "since the traffic still transits external LA infrastructure "
            "first, this remains a genuine detour rather than a purely "
            "in-region path; kept `detour_hub` as Los Angeles, the "
            "confirmed external touchpoint, with the later Guam leg noted "
            "here rather than driving the hub choice."
        ),
    ),
    ConfirmedDetour(
        source_cc="PF",
        target_cc="TO",
        target_asn=38198,
        detour_ix_name="Equinix Sydney (AS132528, Digicel Australia/Telstra-operated "
        "backbone)",
        detour_hub="Sydney",
        measurement_id=211684890,
        ris_observation_count=1321,
        note=(
            "ONATI (AS9471, French Polynesia) -> Digicel Tonga (AS38198) "
            "-- a fresh PF<->TO pair, a fourth independent confirmation "
            "of the AS45355(Digicel Fiji)<->AS38198 adjacency (after GU, "
            "MP, and VU). All 3 probes: `AS9471 -> AS6939 (Hurricane "
            "Electric) -> AS132528 -> AS45355 -> AS38198`. Upstream of "
            "the target is AS45355, RIS-agreeing with the identical "
            "*exact* match (1,321). **A sixth occurrence of AS132528** "
            "(Digicel Australia/Telstra backbone) at Equinix Sydney this "
            "session, confirmed directly (`ixp_crossings` non-empty for "
            "all 3 probes). All 3 probes reach the same real, "
            "BGP-confirmed AS38198 address (`202.43.12.5`) already "
            "established across every prior measurement of this "
            "corridor."
        ),
    ),
    ConfirmedDetour(
        source_cc="PF",
        target_cc="FM",
        target_asn=45193,
        detour_ix_name="Any2West",
        detour_hub="Los Angeles",
        measurement_id=211689659,
        ris_observation_count=1681,
        note=(
            "ONATI (AS9471, French Polynesia) -> a third FSM "
            "Telecommunications Corporation sibling ASN (AS45193). "
            "All 3 probes: `AS9471 -> AS6939 (Hurricane Electric) -> "
            "AS9246 (Teleguam Holdings/GTA) -> AS139759 -> AS45193`, "
            "fully contiguous -- **the first traceroute this project has "
            "recorded that resolves AS45193 directly**, rather than "
            "stalling on a sibling substitution (the shape every prior "
            "FSM-corridor measurement has shown, all filed as "
            "`CandidatePeering` since RIS couldn't confirm them). This "
            "time the immediate upstream (AS139759) *does* show up in "
            "AS45193's own RIS neighbor list, with an exact match "
            "(1,681) -- RIS confirming the internal FSM sibling backbone "
            "relationship (AS139759<->AS45193) directly, closing out a "
            "pattern that had stayed candidate-only for two prior source "
            "economies (GU, MP) and one prior PF measurement toward "
            "AS38875 earlier in this same tranche. Crosses **Any2West** "
            "(`ixp_crossings` confirms it for all 3 probes, member ASN "
            "9246) -- already verified as a real PeeringDB-declared "
            "Any2West membership for AS9246/GTA when it first surfaced "
            "as a candidate finding minutes earlier."
        ),
    ),
    ConfirmedDetour(
        source_cc="PF",
        target_cc="WF",
        target_asn=45879,
        detour_ix_name="AS5511 (Opentransit Orange S.A.) -- global transit, not a named "
        "exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211691024,
        ris_observation_count=1665,
        note=(
            "ONATI (AS9471, French Polynesia) -> Orange Wallis & Futuna "
            "(AS45879) -- a fresh PF<->WF pair, a fourth independent "
            "confirmation of the AS5511(Opentransit Orange)<->AS45879 "
            "adjacency (after GU, MP, and VU). All 3 probes: `AS9471 -> "
            "AS3257 (GTT) -> AS5511` -- the target itself never resolved "
            "(ordinary ICMP filtering near the destination), so RIS is "
            "checked against the last reached ASN. RIS agrees with the "
            "identical *exact* match (1,665). GTT is a genuinely new "
            "intermediate carrier for this specific corridor. No IXP "
            "crossing (`ixp_crossings` empty for all 3 probes). "
            "**Hub confidence downgraded, not silently kept as fact**: "
            "unlike the Cogent (AS9751) and Tata (AS24439) PF-sourced "
            "entries, this one's resolved Orange hops (`193.251.249.81`, "
            "`81.52.166.62`, `81.52.188.158`) have **no PTR records at "
            "all** -- `hop_geolocation.geolocate_hop` returns `None` for "
            "each, honestly, rather than guessing. \"Tokyo\" here is "
            "*inherited* from AS5511's known PeeringDB facility list, not "
            "independently confirmed by this specific traceroute's own "
            "hops (contrast the sibling GU-sourced entry, whose path "
            "genuinely transits AS2497/IIJ, a real Japanese carrier -- "
            "actual evidence, not an inherited label). RTT jumps "
            "~99ms -> ~263ms at the last resolved hop, consistent with a "
            "long-haul link, but that alone doesn't establish which city. "
            "Kept `detour_hub` as Tokyo for now (still the carrier's own "
            "real, verified presence, and the best available guess absent "
            "contrary evidence), but this entry -- and its MP/VU siblings, "
            "not yet audited the same way -- remain open items for a "
            "future geolocation pass, not settled facts."
        ),
    ),
    ConfirmedDetour(
        source_cc="PF",
        target_cc="SB",
        target_asn=45891,
        detour_ix_name="IX Australia Sydney (NSW-IX)",
        detour_hub="Sydney",
        measurement_id=211693982,
        ris_observation_count=1652,
        note=(
            "ONATI (AS9471, French Polynesia) -> Solomon Telekom Co Ltd "
            "(AS45891) -- a fresh PF<->SB pair, a fourth independent "
            "confirmation of the AS139609(SISCC)<->AS45891 adjacency "
            "(after GU, MP, and VU). All 3 probes: `AS9471 -> AS6939 "
            "(Hurricane Electric) -> AS139609` -- the target itself never "
            "resolved (ordinary ICMP filtering near the destination), so "
            "RIS is checked against the last reached ASN, which is "
            "AS45891's *only* RIS-observed neighbor at all. RIS agrees "
            "with the identical *exact* match (1,652). Crosses **NSW-IX** "
            "directly (`ixp_crossings` confirms it for all 3 probes), the "
            "same named exchange as the original MP-sourced entry -- now "
            "the second confirmation of this specific Sydney fabric for "
            "this corridor, alongside the VU-sourced entry's MegaIX "
            "Sydney crossing."
        ),
    ),
    ConfirmedDetour(
        source_cc="PF",
        target_cc="NR",
        target_asn=140504,
        detour_ix_name="AS12684 (SES ASTRA S.A.) -- satellite operator, global transit, "
        "not a named exchange crossing",
        detour_hub="Los Angeles",
        measurement_id=211706787,
        ris_observation_count=616,
        note=(
            "ONATI (AS9471, French Polynesia) -> a distinct Nauru ASN "
            "(AS140504) -- the exact lead flagged in an earlier VU-sourced "
            "tranche this session. First address dead-ended the same way "
            "as that prior attempt: all 3 probes resolved to AS36149 "
            "(Hawaiian Telcom) with `ris_agrees: False`. Applied the "
            "standing retry policy against a different cached prefix. "
            "**The retry reached AS140504's real relationship directly**: "
            "all 3 probes `AS9471 -> AS6939 (Hurricane Electric) -> "
            "AS36149 (Hawaiian Telcom) -> [gap] -> AS12684`, BGP-resolved "
            "and RIS-agreeing with an *exact* match (616) -- the second "
            "entry in AS140504's own two-relationship RIS neighbor list "
            "(`{132528: 1032, 12684: 616}`), leaving only AS132528 as the "
            "still-untested one. Checked AS12684's holder identity "
            "directly: **SES ASTRA S.A.**, a major geostationary satellite "
            "operator -- the same carrier flagged, but never confirmed, "
            "in an earlier Cook Islands tranche (that attempt stalled at "
            "generic transit and never got close enough to confirm or "
            "deny the relationship; a direct-source test was later ruled "
            "out entirely, since AS12684 has zero connected Atlas probes, "
            "all five ever registered against it Abandoned). **This is "
            "the first traceroute-confirmed SES Astra relationship this "
            "project has recorded**, closing that open thread from the "
            "other direction instead. Hub attribution: checked AS12684's "
            "own PeeringDB record directly first -- zero registered "
            "facilities at all (expected for a satellite operator with no "
            "physical colocation), so attributed the hub from AS36149's "
            "own verified facility list instead (CoreSite LA1/LA2, Los "
            "Angeles) -- the immediately preceding carrier in the "
            "resolved chain. **Caught a real query bug before trusting "
            "any of this**: an initial PeeringDB facility lookup using "
            "`asn=` as the netfac filter silently returned unfiltered, "
            "unrelated global data for both AS12684 and AS36149 -- "
            "re-queried using each network's actual `net_id` (via `/api/"
            "net?asn=`) and got correct, small, verifiable facility lists "
            "instead."
        ),
    ),
    ConfirmedDetour(
        source_cc="CK",
        target_cc="AS",
        target_asn=9751,
        detour_ix_name="AS174 (Cogent Communications) -- global transit, not a named "
        "exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211719803,
        ris_observation_count=1055,
        note=(
            "Cook Islands (AS10131) -> American Samoa (AS9751) -- a fresh "
            "CK<->AS pair, the first firing genuinely sourced from AS10131 "
            "to actually reach a target. Fourth confirmation for this "
            "specific target, via the same ultimate carrier (Cogent) as "
            "the GU and PF entries, but with a notable intermediate hop: "
            "`AS10131 -> AS9471 (ONATI, French Polynesia) -> AS174 -> "
            "AS9751` -- Cook Islands' traffic transits ONATI's own network "
            "before reaching Cogent, the same regional-hub role already "
            "established for ONATI elsewhere this session (Niue, various "
            "FSM/Kiribati corridors). Only 1 of 3 requested probes "
            "returned; checked `participant_count` directly (1, not 3) -- "
            "a genuine single-probe assignment, consistent with every "
            "other AS10131-sourced measurement this session. RIS agrees "
            "with the identical *exact* match (1,055) already on record "
            "for this adjacency. No IXP crossing; kept `detour_hub` as "
            "Tokyo, matching every prior entry for this target."
        ),
    ),
    ConfirmedDetour(
        source_cc="CK",
        target_cc="NC",
        target_asn=17480,
        detour_ix_name="Equinix Sydney",
        detour_hub="Sydney",
        measurement_id=211721420,
        ris_observation_count=1665,
        note=(
            "Cook Islands (AS10131) -> a fresh New Caledonia ASN "
            "(AS17480) -- a fresh CK<->NC pair, a third independent "
            "confirmation of the AS18200(OPT NC)<->AS17480 adjacency "
            "(after the MP entry via BBIX Tokyo and the PF entry via "
            "Equinix Sydney). Only 1 of 3 requested probes returned; "
            "checked `participant_count` directly (1, not 3) -- the same "
            "genuine single-probe pattern as every other AS10131-sourced "
            "measurement this session. Result: `AS10131 -> AS9471 (ONATI, "
            "French Polynesia) -> AS6939 (Hurricane Electric) -> AS18200 "
            "-> AS17480`, fully contiguous, RIS-agreeing with the "
            "identical *exact* match (1,665). Crosses **Equinix Sydney** "
            "directly (`ixp_crossings` confirms it) -- the same exchange "
            "as the PF entry, and the same ONATI-then-Hurricane-Electric "
            "path shape, since Cook Islands' own traffic transits ONATI's "
            "network here too, matching the pattern already seen on the "
            "AS9751 corridor this same tranche cycle."
        ),
    ),
    ConfirmedDetour(
        source_cc="CK",
        target_cc="PG",
        target_asn=17828,
        detour_ix_name="AS6939 (Hurricane Electric) -- global transit, not a named "
        "exchange crossing",
        detour_hub="Sydney",
        measurement_id=211725920,
        ris_observation_count=1283,
        note=(
            "Cook Islands (AS10131) -> PNG DataCo (AS17828) -- a fresh "
            "CK<->PG pair, a fourth independent confirmation of this "
            "project's very first-ever confirmed finding (AS6939<->"
            "AS17828), after GU, MP, and PF. Only 1 of 3 requested probes "
            "returned; checked `participant_count` directly (1, not 3) -- "
            "the same genuine single-probe pattern as every other "
            "AS10131-sourced measurement this session. Result: `AS10131 "
            "-> AS9471 (ONATI, French Polynesia) -> AS6939 -> [gap] -> "
            "AS17828`, RIS-agreeing with the identical *exact* match "
            "(1,283) -- the same ONATI-transit shape already seen on both "
            "the AS9751 and AS17480 corridors this same tranche cycle, "
            "reinforcing ONATI's real role as Cook Islands' de facto "
            "regional gateway. No IXP crossing; kept `detour_hub` as "
            "Sydney, matching the PF entry."
        ),
    ),
    ConfirmedDetour(
        source_cc="CK",
        target_cc="PW",
        target_asn=17893,
        detour_ix_name="BBIX Tokyo",
        detour_hub="Tokyo",
        measurement_id=211728762,
        ris_observation_count=106,
        note=(
            "Cook Islands (AS10131) -> Palau NCC (AS17893) -- a fresh "
            "CK<->PW pair, a second independent confirmation of the "
            "AS6939(Hurricane Electric)<->AS17893 adjacency (after the "
            "PF entry). Only 1 of 3 requested probes returned; checked "
            "`participant_count` directly (1, not 3) -- the same genuine "
            "single-probe pattern as every other AS10131-sourced "
            "measurement this session. **Stronger evidence than the "
            "original entry**: `AS10131 -> AS9471 (ONATI) -> AS6939 -> "
            "AS17893`, fully contiguous -- the literal target resolves "
            "directly this time (the PF entry never reached it, relying "
            "on the last-reached-ASN methodology instead). RIS agrees "
            "with the identical *exact* match (106). **Crosses BBIX "
            "Tokyo directly** (`ixp_crossings` confirms it) -- the "
            "PF entry showed no IXP crossing at all; verified AS17893's "
            "real BBIX Tokyo membership via PeeringDB's netixlan API "
            "before trusting it, matching the exchange's own already-"
            "established presence in this project (e.g. the GU->PW "
            "entry's Tokyo/Cogent detour)."
        ),
    ),
    ConfirmedDetour(
        source_cc="CK",
        target_cc="WS",
        target_asn=17993,
        detour_ix_name="Equinix Sydney",
        detour_hub="Sydney",
        measurement_id=211731055,
        ris_observation_count=150,
        note=(
            "Cook Islands (AS10131) -> Vodafone Samoa Limited (AS17993) "
            "-- a fresh CK<->WS pair, a third independent confirmation "
            "of the AS6939(Hurricane Electric)<->AS17993 adjacency "
            "(after MP and PF). Only 1 of 3 requested probes returned; "
            "checked `participant_count` directly (1, not 3) -- the same "
            "genuine single-probe pattern as every other AS10131-sourced "
            "measurement this session. Result: `AS10131 -> AS9471 (ONATI) "
            "-> AS6939 -> AS17993`, fully contiguous, RIS-agreeing with "
            "the identical *exact* match (150). Crosses **Equinix "
            "Sydney** directly (`ixp_crossings` confirms it) -- the same "
            "exchange as both prior entries, and the same ONATI-transit "
            "shape now seen on every AS10131-sourced corridor tested "
            "this tranche cycle."
        ),
    ),
    ConfirmedDetour(
        source_cc="CK",
        target_cc="FJ",
        target_asn=24390,
        detour_ix_name="Any2West",
        detour_hub="Los Angeles",
        measurement_id=211738209,
        ris_observation_count=337,
        note=(
            "Cook Islands (AS10131) -> University of the South Pacific's "
            "own network (AS24390) -- a fresh CK<->FJ pair, a third "
            "independent confirmation of the AS7575(AARNet)<->AS24390 "
            "adjacency (after MP via OneQode and PF via Hurricane "
            "Electric/Any2West). Only 1 of 3 requested probes returned; "
            "checked `participant_count` directly (1, not 3) -- the same "
            "genuine single-probe pattern as every other AS10131-sourced "
            "measurement this session. Result: `AS10131 -> AS9471 (ONATI) "
            "-> AS6939 (Hurricane Electric) -> AS7575`, target never "
            "resolved (ordinary ICMP filtering), RIS-agreeing with the "
            "identical *exact* match (337). Crosses **Any2West** directly "
            "(`ixp_crossings` confirms it, a real hop-level LAN-prefix "
            "match, not a carrier-level guess) -- the same exchange as "
            "the PF entry, and the same ONATI-transit shape seen on every "
            "AS10131-sourced corridor this tranche cycle."
        ),
    ),
    ConfirmedDetour(
        source_cc="CK",
        target_cc="MH",
        target_asn=24439,
        detour_ix_name="AS3257 (GTT Communications), via AS6453 (Tata "
        "Communications) -- global transit, not a named exchange crossing",
        detour_hub="Los Angeles",
        measurement_id=211741326,
        ris_observation_count=997,
        note=(
            "Cook Islands (AS10131) -> Marshall Islands NTA ISP (AS24439) "
            "-- a fresh CK<->MH pair, a fifth independent confirmation of "
            "the AS6453(Tata)<->AS24439 adjacency (after GU via IIJ, MP "
            "via Cogent, VU via Singtel, and PF via this identical "
            "GTT/Tata chain). Only 1 of 3 requested probes returned; "
            "checked `participant_count` directly (1, not 3) -- the same "
            "genuine single-probe pattern as every other AS10131-sourced "
            "measurement this session. Result: `AS10131 -> AS9471 (ONATI) "
            "-> AS3257 (GTT) -> AS6453`, target never resolved, "
            "RIS-agreeing with the identical *exact* match (997). "
            "**Geolocated with the new `hop_geolocation` module from the "
            "start this time, rather than inheriting a hub label**: the "
            "resolved Tata hops (`64.86.197.98`, `180.87.9.2`, "
            "`180.87.60.178`) are the exact same addresses as the "
            "PF-sourced entry's now-corrected path -- Los Angeles, then "
            "Piti, Guam (Tata's confirmed facility in "
            "`regional_carrier_facilities.py`). Kept `detour_hub` as Los "
            "Angeles, matching the corrected PF entry, not the old "
            "Tokyo mislabeling."
        ),
    ),
    ConfirmedDetour(
        source_cc="CK",
        target_cc="TO",
        target_asn=38198,
        detour_ix_name="Equinix Sydney (AS132528, Digicel Australia/Telstra-operated "
        "backbone)",
        detour_hub="Sydney",
        measurement_id=211743576,
        ris_observation_count=1321,
        note=(
            "Cook Islands (AS10131) -> Digicel Tonga (AS38198) -- a "
            "fresh CK<->TO pair, a fifth independent confirmation of the "
            "AS45355(Digicel Fiji)<->AS38198 adjacency (after GU, MP, VU, "
            "and PF). Only 1 of 3 requested probes returned; checked "
            "`participant_count` directly (1, not 3) -- the same genuine "
            "single-probe pattern as every other AS10131-sourced "
            "measurement this session. Result: `AS10131 -> AS9471 (ONATI) "
            "-> AS6939 (Hurricane Electric) -> AS132528 -> AS45355 -> "
            "AS38198`, RIS-agreeing with the identical *exact* match "
            "(1,321). **A seventh occurrence of AS132528** (Digicel "
            "Australia/Telstra backbone) at Equinix Sydney this session, "
            "confirmed directly via a real hop-level LAN-prefix match "
            "(`ixp_crossings`), not a carrier-facility guess -- unaffected "
            "by the Tokyo-hub issue fixed earlier this tranche cycle."
        ),
    ),
    ConfirmedDetour(
        source_cc="CK",
        target_cc="FM",
        target_asn=45193,
        detour_ix_name="Any2West",
        detour_hub="Los Angeles",
        measurement_id=211749873,
        ris_observation_count=1681,
        note=(
            "Cook Islands (AS10131) -> a third FSM Telecommunications "
            "Corporation sibling ASN (AS45193) -- a fresh CK<->FM pair, "
            "a second independent confirmation of the direct AS139759<->"
            "AS45193 adjacency (after the PF entry). Only 1 of 3 "
            "requested probes returned; checked `participant_count` "
            "directly (1, not 3) -- the same genuine single-probe "
            "pattern as every other AS10131-sourced measurement this "
            "session. Result: `AS10131 -> AS9471 (ONATI) -> AS6939 "
            "(Hurricane Electric) -> AS9246 (Teleguam Holdings/GTA) -> "
            "AS139759 -> AS45193`, fully contiguous -- the literal target "
            "resolves directly again, RIS-agreeing with the identical "
            "*exact* match (1,681). Crosses **Any2West** directly "
            "(`ixp_crossings` confirms it) -- the same exchange as the "
            "PF entry, and the same ONATI-transit shape seen on every "
            "AS10131-sourced corridor this tranche cycle."
        ),
    ),
    ConfirmedDetour(
        source_cc="CK",
        target_cc="WF",
        target_asn=45879,
        detour_ix_name="AS5511 (Opentransit Orange S.A.) -- global transit, not a named "
        "exchange crossing",
        detour_hub="Tokyo",
        measurement_id=211750685,
        ris_observation_count=1665,
        note=(
            "Cook Islands (AS10131) -> Orange Wallis & Futuna (AS45879) "
            "-- a fresh CK<->WF pair, a fifth independent confirmation of "
            "the AS5511(Opentransit Orange)<->AS45879 adjacency (after "
            "GU, MP, VU, PF). Only 1 of 3 requested probes returned; "
            "checked `participant_count` directly (1, not 3) -- the same "
            "genuine single-probe pattern as every other AS10131-sourced "
            "measurement this session. Result: `AS10131 -> AS9471 (ONATI) "
            "-> AS3257 (GTT) -> AS5511`, target never resolved, "
            "RIS-agreeing with the identical *exact* match (1,665). "
            "**Same identical Orange hop addresses as the PF entry** "
            "(`193.251.249.81`, `81.52.166.62`, `81.52.188.158`) -- ran "
            "`hop_geolocation.geolocate_hop` on all three anyway rather "
            "than assuming the earlier `None` result still held; still "
            "`None` for each, confirming no PTR evidence exists for this "
            "carrier chain, not a one-off lookup gap. **Also checked the "
            "MP-sourced sibling entry's own hops while here** (measurement "
            "211577395, previously flagged as not yet audited): its two "
            "distinct Orange-adjacent addresses (`216.66.41.150`, "
            "`57.35.6.64`) also have no PTR records. Across every "
            "non-GU-sourced measurement of this corridor, only the "
            "GU entry has real evidence for its Tokyo claim (via a "
            "genuine IIJ/Japan hop) -- kept `detour_hub` as Tokyo here "
            "too, on the same honestly-downgraded basis as the PF entry: "
            "the carrier's own real, verified presence, not this "
            "specific traceroute's own confirmed geography."
        ),
    ),
    ConfirmedDetour(
        source_cc="CK",
        target_cc="SB",
        target_asn=45891,
        detour_ix_name="IX Australia Sydney (NSW-IX)",
        detour_hub="Sydney",
        measurement_id=211752464,
        ris_observation_count=1652,
        note=(
            "Cook Islands (AS10131) -> Solomon Telekom Co Ltd (AS45891) "
            "-- a fresh CK<->SB pair, a fifth independent confirmation "
            "of the AS139609(SISCC)<->AS45891 adjacency (after GU, MP, "
            "VU, PF). Only 1 of 3 requested probes returned; checked "
            "`participant_count` directly (1, not 3) -- the same "
            "genuine single-probe pattern as every other AS10131-sourced "
            "measurement this session. Result: `AS10131 -> AS9471 "
            "(ONATI) -> AS6939 (Hurricane Electric) -> AS139609` -- the "
            "target itself never resolved (ordinary ICMP filtering), so "
            "RIS is checked against the last reached ASN, which remains "
            "AS45891's *only* RIS-observed neighbor at all. RIS agrees "
            "with the identical *exact* match (1,652). Crosses **NSW-IX** "
            "directly (`ixp_crossings` confirms it, a real hop-level "
            "LAN-prefix match) -- the same exchange as the PF entry."
        ),
    ),
    ConfirmedDetour(
        source_cc="CK",
        target_cc="NR",
        target_asn=140504,
        detour_ix_name="AS12684 (SES ASTRA S.A.) -- satellite operator, global transit, "
        "not a named exchange crossing",
        detour_hub="Los Angeles",
        measurement_id=211765425,
        ris_observation_count=616,
        note=(
            "Cook Islands (AS10131) -> a distinct Nauru ASN (AS140504) "
            "-- a fresh CK<->NR pair, a second independent confirmation "
            "of the AS140504<->AS12684 (SES Astra) relationship (after "
            "PF). Fired directly at the address already confirmed to "
            "reach SES Astra in the PF retry, rather than starting from "
            "a fresh address and possibly needing the retry policy "
            "again. Result: `AS10131 -> AS9471 (ONATI) -> AS6939 "
            "(Hurricane Electric) -> AS36149 (Hawaiian Telcom) -> "
            "AS12684`, **fully contiguous this time** (the PF entry had "
            "a real gap before AS12684) -- the cleanest confirmation yet "
            "of this relationship. RIS agrees with the identical exact "
            "match (616). Kept `detour_hub` as Los Angeles, matching the "
            "PF entry's verified attribution (from AS36149's own real "
            "PeeringDB facility list, since AS12684 itself has zero "
            "registered facilities)."
        ),
    ),
    ConfirmedDetour(
        source_cc="PG",
        target_cc="AS",
        target_asn=9751,
        detour_ix_name="Equinix San Jose",
        detour_hub="San Jose",
        measurement_id=211800054,
        ris_observation_count=267,
        note=(
            "PNG DataCo (AS17828) -> American Samoa (AS9751) -- the "
            "first firing genuinely sourced from PNG DataCo to reach a "
            "target. Third independent confirmation of the "
            "Wave-Broadband(AS11404)<->AS9751 adjacency (after MP and "
            "VU): `AS17828 -> AS4826 (Vocus Connect) -> AS11404`, RIS-"
            "agreeing with the identical *exact* match (267). Crosses "
            "**Equinix San Jose** directly (`ixp_crossings` confirms "
            "it) -- the same exchange as the VU entry, a second "
            "confirmation of this specific crossing."
        ),
    ),
    ConfirmedDetour(
        source_cc="PG",
        target_cc="NC",
        target_asn=17480,
        detour_ix_name="Equinix Sydney",
        detour_hub="Sydney",
        measurement_id=211802668,
        ris_observation_count=1665,
        note=(
            "PNG DataCo (AS17828) -> a fresh New Caledonia ASN "
            "(AS17480) -- a fresh PG<->NC pair, a fourth independent "
            "confirmation of the AS18200(OPT NC)<->AS17480 adjacency "
            "(after MP, PF, CK). `AS17828 -> AS4826 (Vocus Connect) -> "
            "AS18200 -> AS17480`, fully contiguous, RIS-agreeing with "
            "the identical *exact* match (1,665). Crosses Equinix "
            "Sydney directly (`ixp_crossings` confirms it) -- the same "
            "exchange as the CK and PF entries."
        ),
    ),
    ConfirmedDetour(
        source_cc="PG",
        target_cc="FJ",
        target_asn=24390,
        detour_ix_name="AS7575 (AARNet) -- global transit, not a named exchange crossing",
        detour_hub="Sydney",
        measurement_id=211816612,
        ris_observation_count=337,
        note=(
            "PNG DataCo (AS17828) -> University of the South Pacific's "
            "own network (AS24390) -- a fresh PG<->FJ pair, a fourth "
            "independent confirmation of the AS7575(AARNet)<->AS24390 "
            "adjacency (after MP, PF, CK). `AS17828 -> AS4826 (Vocus "
            "Connect) -> AS7575`, target never resolved, RIS-agreeing "
            "with the identical exact match (337). No IXP crossing this "
            "time (`ixp_crossings` empty) -- a direct AARNet hop with "
            "no intermediate Sydney fabric, unlike the CK and PF "
            "entries' Any2West crossings. Kept `detour_hub` as Sydney, "
            "matching AARNet's already-established real presence there."
        ),
    ),
    ConfirmedDetour(
        source_cc="PG",
        target_cc="TO",
        target_asn=38198,
        detour_ix_name="AS1221 (Telstra domestic) -- global transit, not a named "
        "exchange crossing",
        detour_hub="Sydney",
        measurement_id=211962193,
        ris_observation_count=1321,
        note=(
            "PNG DataCo (AS17828) -> Digicel Tonga (AS38198) -- a fresh "
            "PG<->TO pair, a sixth independent confirmation of the "
            "AS45355(Digicel Fiji)<->AS38198 adjacency (after GU, MP, "
            "VU, PF, CK). `AS17828 -> AS4826 (Vocus Connect) -> AS1221 "
            "(Telstra domestic) -> AS45355`, target technically reached "
            "at the end of the chain but with a real unresolved gap "
            "before AS38198 itself. RIS-agreeing with the identical "
            "*exact* match (1,321). **Notably no AS132528 this time** "
            "-- every prior confirmation of this adjacency crossed "
            "AS132528 (Digicel Australia/Telstra backbone) at Equinix "
            "Sydney; this one reaches AS45355 via Telstra's domestic "
            "ASN directly, a genuinely different real path to the same "
            "ultimate carrier relationship. No IXP crossing observed."
        ),
    ),
    ConfirmedDetour(
        source_cc="PG",
        target_cc="MH",
        target_asn=24439,
        detour_ix_name="AS174 (Cogent Communications), via AS6453 (Tata "
        "Communications) -- global transit, not a named exchange crossing",
        detour_hub="Los Angeles",
        measurement_id=211965108,
        ris_observation_count=997,
        note=(
            "PNG DataCo (AS17828) -> Marshall Islands NTA ISP (AS24439) "
            "-- a fresh PG<->MH pair, a sixth independent confirmation "
            "of the AS6453(Tata)<->AS24439 adjacency (after GU, MP, VU, "
            "PF, CK). `AS17828 -> AS4826 (Vocus Connect) -> AS174 "
            "(Cogent) -> AS6453`, target never resolved, RIS-agreeing "
            "with the identical *exact* match (997). **Geolocated with "
            "the `hop_geolocation` module from the start**, per the "
            "established discipline for this specific corridor: the "
            "resolved Tata hops (`64.86.252.141`, `180.87.9.2`, "
            "`180.87.60.178`) are the exact same addresses as the "
            "already-corrected PF and CK entries -- Los Angeles, then "
            "Piti, Guam. Kept `detour_hub` as Los Angeles, matching "
            "those corrected entries. Notable: this is the retry of the "
            "corridor that hit the earlier zero-probes-scheduled "
            "anomaly, now confirming that failure was genuinely "
            "transient."
        ),
    ),
    ConfirmedDetour(
        source_cc="PG",
        target_cc="FM",
        target_asn=45193,
        detour_ix_name="Any2West",
        detour_hub="Los Angeles",
        measurement_id=211971118,
        ris_observation_count=1681,
        note=(
            "PNG DataCo (AS17828) -> a third FSM Telecommunications "
            "Corporation sibling ASN (AS45193) -- a fresh PG<->FM pair, "
            "a third independent confirmation of the direct AS139759<->"
            "AS45193 adjacency (after PF and CK). `AS17828 -> AS4826 "
            "(Vocus Connect) -> AS9246 (Teleguam Holdings/GTA) -> "
            "AS139759 -> AS45193`, fully contiguous -- the literal "
            "target resolves directly again, RIS-agreeing with the "
            "identical *exact* match (1,681). Crosses Any2West directly "
            "-- the same exchange as every prior confirmation of this "
            "relationship."
        ),
    ),
    ConfirmedDetour(
        source_cc="PG",
        target_cc="WF",
        target_asn=45879,
        detour_ix_name="AS174 (Cogent Communications), then AS5511 (Opentransit "
        "Orange S.A.) -- global transit, not a named exchange crossing",
        detour_hub="Los Angeles",
        measurement_id=211976890,
        ris_observation_count=1665,
        note=(
            "PNG DataCo (AS17828) -> Orange Wallis & Futuna (AS45879) -- "
            "a fresh PG<->WF pair, a sixth independent confirmation of "
            "the AS5511(Opentransit Orange)<->AS45879 adjacency (after "
            "GU, MP, VU, PF, CK), and the **first time this corridor has "
            "ever had real geographic evidence for its Orange leg**. "
            "`AS17828 -> AS4826 (Vocus Connect) -> AS174 (Cogent) -> "
            "AS5511`, target never resolved, RIS-agreeing with the "
            "identical *exact* match (1,665). Cogent is a genuinely new "
            "intermediate carrier for this adjacency (after GTT). "
            "**Reverse-DNS'd the Cogent hops directly (via the new "
            "`hop_geolocation` module) rather than inheriting the "
            "existing entries' Tokyo label**: `sjc13.atlas.cogentco.com` "
            "-> `lax01...` -> `lax05...` -> **`orange.lax05.atlas."
            "cogentco.com`** -- a Cogent router explicitly named for "
            "the Orange handoff, located in Los Angeles. Corrected "
            "`detour_hub` to Los Angeles accordingly, on real evidence "
            "rather than the carrier's generic Tokyo presence used "
            "elsewhere in this corridor's other, still-unverified "
            "entries. Added a new `sjc` pattern to `hop_geolocation.py` "
            "(San Jose) while auditing these hops."
        ),
    ),
    ConfirmedDetour(
        source_cc="PG",
        target_cc="SB",
        target_asn=45891,
        detour_ix_name="AS4637 (Telstra Global) -- global transit, not a named "
        "exchange crossing",
        detour_hub="Sydney",
        measurement_id=211978965,
        ris_observation_count=1652,
        note=(
            "PNG DataCo (AS17828) -> Solomon Telekom Co Ltd (AS45891) "
            "-- a fresh PG<->SB pair, a sixth independent confirmation "
            "of the AS139609(SISCC)<->AS45891 adjacency (after GU, MP, "
            "VU, PF, CK). `AS17828 -> AS4826 (Vocus Connect) -> AS1221 "
            "(Telstra domestic) -> AS4637 (Telstra Global) -> AS139609` "
            "-- target never resolved, RIS-agreeing with the identical "
            "*exact* match (1,652). No IXP crossing this time. "
            "**A genuinely new routing-loop location, the fourth "
            "distinct network this session** (after Hurricane "
            "Electric's network, FINTEL's edge, and Starlink's own "
            "network): `has_routing_loop` correctly returned `True`; "
            "checked the raw hops directly and found a single address "
            "(`103.142.98.131`) repeating at hop 11 and hop 14 with "
            "unanswered probes in between. Resolved it directly: it "
            "belongs to **AS139609 (SISCC) itself** -- a real, live "
            "loop at the destination's own network edge, the same "
            "general shape as the FINTEL case but a genuinely "
            "different company's network. The loop sits *after* the "
            "point (hop 10, also AS139609) already used for this "
            "measurement's own RIS agreement, so it doesn't affect the "
            "triangulation result here -- same as the earlier Starlink "
            "loop case."
        ),
    ),
    ConfirmedDetour(
        source_cc="PW",
        target_cc="AS",
        target_asn=9751,
        detour_ix_name="AS174 (Cogent Communications) -- global transit, not a named "
        "exchange crossing",
        detour_hub="Portland",
        measurement_id=211998672,
        ris_observation_count=1055,
        note=(
            "Palau NCC (AS17893) -> American Samoa (AS9751) -- the "
            "first firing genuinely sourced from Palau to reach a "
            "target. Fifth independent confirmation of the "
            "AS174(Cogent)<->AS9751 adjacency (after GU, VU, PF, CK): "
            "`AS17893 -> AS174 -> AS9751`, RIS-agreeing with the "
            "identical *exact* match (1,055). **Geolocated with "
            "`hop_geolocation` from the start**: `lax01` -> `sjc13` -> "
            "`sfo01` -> `pdx01` -> `pdx02` -- the identical US West "
            "Coast chain already established for the corrected PF "
            "entry, ending at Portland. Kept `detour_hub` as Portland, "
            "matching that corrected entry."
        ),
    ),
    ConfirmedDetour(
        source_cc="PW",
        target_cc="NC",
        target_asn=17480,
        detour_ix_name="BBIX Tokyo",
        detour_hub="Tokyo",
        measurement_id=212001808,
        ris_observation_count=1665,
        note=(
            "Palau NCC (AS17893) -> a fresh New Caledonia ASN "
            "(AS17480) -- a fresh PW<->NC pair, a fifth independent "
            "confirmation of the AS18200(OPT NC)<->AS17480 adjacency "
            "(after MP, PF, CK, PG), and the first of the five to cross "
            "**BBIX Tokyo** rather than Equinix Sydney. Only one probe "
            "responded (Palau's usual low-participant-count pattern), "
            "and it went dark after the target's own edge address -- "
            "but `202.171.64.251` resolves directly to AS17480 by RIS "
            "BGP lookup (PTR `canl.nc`), and the immediately preceding "
            "hop `202.87.128.134` resolves directly to AS18200, so the "
            "adjacency is fully contiguous despite the destination IP "
            "itself never answering. `AS17893 -> AS38195 (BBIX Tokyo) "
            "-> AS18200 -> AS17480`, RIS-agreeing with the identical "
            "*exact* match (1,665). The BBIX Tokyo crossing (`ixp_crossings` "
            "confirms it, ix_id 126) is a real IXP-LAN address match, not "
            "a carrier-facility guess -- unlike the Cogent/Tata Tokyo "
            "mislabeling caught earlier this session, this hub is solid."
        ),
    ),
    ConfirmedDetour(
        source_cc="PW",
        target_cc="WS",
        target_asn=17993,
        detour_ix_name="AS174 (Cogent Communications) -- global transit, not a named "
        "exchange crossing",
        detour_hub="Sydney",
        measurement_id=212005827,
        ris_observation_count=1455,
        note=(
            "Palau NCC (AS17893) -> Vodafone Samoa Limited (AS17993) -- a "
            "fresh PW<->WS pair, a second independent confirmation of the "
            "AS174(Cogent)<->AS17993 adjacency (after GU). Only one probe "
            "responded and the destination IP never answered, but the "
            "second-to-last hop resolves directly to AS17993 by RIS BGP "
            "lookup, so the adjacency is fully contiguous. `AS17893 -> "
            "AS174 -> AS17993`, RIS-agreeing with the identical *exact* "
            "match (1,455). **Geolocated with `hop_geolocation` for the "
            "first time on this specific corridor**: the Cogent hops "
            "(`ccr71.syd01.atlas.cogentco.com`, `agr51.syd01.atlas.cogentco.com`) "
            "resolve to Sydney -- confirming, with real hop-level PTR "
            "evidence, the carrier-facility guess the earlier GU entry had "
            "used for the same 'Sydney' hub. Added a new `syd` pattern to "
            "`hop_geolocation.py` from this measurement."
        ),
    ),
)
