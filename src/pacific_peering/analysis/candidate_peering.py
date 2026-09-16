"""Candidate ("possible") peering adjacencies: strong traceroute signal, RIS disagrees.

A third finding shape, distinct from both `confirmed_detours` and
`confirmed_local_transit`. Those two only exist once RIS and Atlas
*agree* (Validation Rule 1) — this module is for the opposite case: a
traceroute-observed adjacency that's clean and repeatable (multiple
probes, contiguous, no gap) but where RIS's independently-observed
neighbor list for the target ASN does not include the traceroute's
upstream hop. That disagreement is itself the finding, per Validation
Rule 4: it's exactly the shape a *real* unlisted/private peering
relationship would take (an adjacency real enough to route traffic, but
never announced where RIS's route collectors can see it) — but it's
equally consistent with a resolution artifact (the hop's address
happens to fall in a block the upstream ASN doesn't fully control).
This module records the possibility without picking one, and without
ever promoting an entry here into `confirmed_local_transit` on its own
say-so — that requires a second independent corroboration (e.g. an
inbound traceroute, a different vantage point, or direct outreach).

First entry: FSM (AS139759) -> Palau (AS17893), first surfaced in a
`/loop` tranche testing a new corridor, then sharpened once
`traceroute_topology._resolve_address` was fixed to check IXP-fabric
membership independently of ASN resolution (see `task_plan.md`) —
AS17893's own hop turned out to sit inside Guam IX's registered LAN,
directly corroborating its PeeringDB-claimed membership there even
though the upstream adjacency itself remains unconfirmed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidatePeering:
    """One traceroute-observed adjacency RIS does not independently confirm."""

    upstream_cc: str
    upstream_asn: int
    upstream_name: str
    target_cc: str
    target_asn: int
    target_name: str
    measurement_id: int
    vantage_point_cc: str  # economy the confirming traceroute was sourced from
    probe_agreement: str  # e.g. "3/3 probes" — how repeatable the observed hop is
    note: str


CANDIDATE_PEERING: tuple[CandidatePeering, ...] = (
    CandidatePeering(
        upstream_cc="FM",
        upstream_asn=139759,
        upstream_name="an FSM ASN (no PeeringDB org name on record)",
        target_cc="PW",
        target_asn=17893,
        target_name="Palau National Communications Corp",
        measurement_id=210986430,
        vantage_point_cc="FM",
        probe_agreement="3/3 probes",
        note=(
            "All 3 probes show the same clean, contiguous path: the source's own "
            "network -> AS139759 -> AS17893, with no external hub in between. But "
            "RIS's real neighbor list for AS17893 ({174: 1333, 140627: 139, 6939: 106, "
            "24482: 49, 2500: 5, 18106: 5, 9002: 5, 49544: 5, 35280: 5, 9498: 5, "
            "59105: 2, 9505: 2} -- all global/regional transit ASNs) does not include "
            "AS139759, and neither ASN shares a PeeringDB IXP membership, so no "
            "shared-fabric corroboration is available either. Not a missing-data "
            "artifact: AS17893 has plenty of RIS-visible neighbors, just not this one. "
            "Sharpened after fixing traceroute_topology._resolve_address to check "
            "IXP-fabric membership independently of ASN resolution: the hop "
            "immediately before the final target (103.142.153.18, resolved via "
            "PeeringDB netixlan to AS17893 itself) also falls inside Guam IX's "
            "registered LAN prefix (103.142.153.0/24) -- direct traceroute "
            "corroboration that AS17893 really does have a live interface at Guam "
            "IX, matching its PeeringDB-claimed membership there. That confirms "
            "AS17893's own presence at an in-fishbowl exchange, but not that "
            "AS139759 peers with it there specifically -- AS139759 has zero "
            "PeeringDB IXP memberships on record, so its side of this adjacency "
            "remains unconfirmed either way. "
            "A bulk IRR AS-SET sweep (APNIC-sourced only) surfaced a concrete "
            "alternative/complementary hypothesis worth checking before assuming "
            "the traceroute's AS139759 hop is the whole story: AS3605 (Guam "
            "Cablevision)'s own declared transit AS-SET (AS-KUENTOS-TRANSIT) names "
            "all three of Palau's in-scope ASNs (17893, 58932, 133897) directly, "
            "plus AS10130 (FSM Telecommunications Corporation) and MARIIX's own "
            "exchange ASN (23676) -- i.e. a real, independently-declared Guam-based "
            "transit relationship spanning exactly this corridor. "
            "Tested more directly with a second measurement (Guam -> AS17893, "
            "measurement 211044785 -- Guam rather than FSM as source, closer to "
            "what the AS3605 lead actually named): all 3 probes again land on the "
            "same GU-IX address (103.142.153.18) confirmed before -- a second, "
            "independent reinforcement of AS17893's Guam IX presence, this time "
            "from a different source economy. The immediate upstream this time is "
            "AS152735 (\"Guam Exchange\", 2 of 3 probes) or AS17456 (\"Pacific Data "
            "Systems\", 1 of 3) -- neither RIS-confirmed as a neighbor of AS17893, "
            "and AS152735's name/AS-SET (\"AS-GUAMIX\") suggests it's Guam IX's own "
            "route-server/infrastructure ASN rather than a distinct peering "
            "relationship, so not treated as a new candidate in its own right. "
            "AS3605 itself did not appear on this path -- the specific lead named "
            "in its AS-SET remains untested; a probe sourced from AS3605 itself, "
            "if Guam's several connected probes ever include one on it, would be "
            "the natural next check."
        ),
    ),
    CandidatePeering(
        upstream_cc="MP",
        upstream_asn=7131,
        upstream_name="PTI Pacifica Inc.",
        target_cc="PW",
        target_asn=17893,
        target_name="Palau National Communications Corp",
        measurement_id=211555952,
        vantage_point_cc="MP",
        probe_agreement="3/3 probes",
        note=(
            "A fresh MP<->PW pair, pulled from the corridor backlog. The "
            "single cleanest result this project has produced from this "
            "source: all 3 probes resolve **directly** AS7131 -> AS17893, "
            "zero intermediate ASN at all, and unusually fast (20-30ms RTT "
            "-- an order of magnitude below every Tokyo/Sydney-detour "
            "finding this session, consistent with a short, genuinely "
            "regional Micronesian path rather than a transpacific one). "
            "But `ris_agrees: false` on both sides: checked each ASN's "
            "full RIS neighbor list directly -- AS7131's "
            "(`{6939: 1502, 1299: 181, 6453: 66, 3356: 58, 174: 43, ...}`) "
            "and AS17893's (`{174: 1333, 140627: 139, 6939: 106, ...}`) -- "
            "neither lists the other at all, so this isn't a fishbowl-scope "
            "artifact (both ends *are* in-fishbowl Pacific ASNs); RIS "
            "genuinely has no visibility into this specific adjacency. "
            "`ixp_crossings` is empty for all 3 probes (no hop lands inside "
            "a registered IXP LAN prefix), but real corroborating context "
            "exists regardless: AS7131 and AS17893 share **two** PeeringDB-"
            "declared IXP memberships in common -- BBIX Tokyo and Guam IX -- "
            "a plausible real venue for exactly this kind of adjacency, even "
            "though this traceroute's own hop addresses don't land inside "
            "either registered LAN prefix directly. Exactly Validation Rule "
            "4's shape: a real, physically-instantiated, fast direct path "
            "that simply isn't announced anywhere RIS's route collectors "
            "can see -- kept as a candidate, not promoted, per the standing "
            "principle that no single traceroute satisfies Validation Rule "
            "1 regardless of how clean it looks."
        ),
    ),
    CandidatePeering(
        upstream_cc="PW",
        upstream_asn=17893,
        upstream_name="Palau National Communications Corp",
        target_cc="GU",
        target_asn=3605,
        target_name="Guam Cablevision, LLC",
        measurement_id=211067648,
        vantage_point_cc="PW",
        probe_agreement="1/1 probe",
        note=(
            "The direct followup to the AS3605 lead above, this time sourced from "
            "Palau itself: a connected Atlas probe on AS17893 was found via the "
            "new ASN probe registry (`atlas.asn_probes`), letting this project "
            "source a traceroute from Palau for the first time all session. "
            "Fired AS17893 -> AS3605's own address directly. Result: the single "
            "cleanest adjacency this project has observed -- fully contiguous, "
            "*zero* gap, immediately AS17893 then AS3605, and the crossing hop "
            "lands inside **GU-IX**'s registered LAN prefix (ix_id 463, in "
            "fishbowl). Unlike most of this project's IXP-crossing evidence, "
            "AS3605's GU-IX membership isn't just inferred from the traceroute -- "
            "PeeringDB independently lists it as a real GU-IX member already. "
            "Still `ris_agrees: false`: AS3605's real RIS neighbor list (22 ASNs, "
            "none of them 17893) doesn't include this adjacency. Given (a) a "
            "fully contiguous single hop with no ambiguity at all, (b) AS3605's "
            "GU-IX presence confirmed independently of this measurement, and (c) "
            "this is exactly the corridor AS3605's own IRR AS-SET declared -- this "
            "reads as the strongest hidden-peering candidate in the project so "
            "far, per Validation Rule 4: a real, physically-instantiated local "
            "peering session at GU-IX that simply isn't announced anywhere RIS's "
            "route collectors can see it. Kept as a candidate, not promoted to "
            "confirmed, on principle -- Validation Rule 1 doesn't bend for how "
            "clean a single traceroute looks, no matter how compelling the "
            "corroborating evidence. The reverse direction (AS3605 sourcing "
            "toward AS17893) is already on record as a *different* finding -- "
            "see `confirmed_detours.CONFIRMED_DETOURS`'s GU->PW entry: AS3605's "
            "own outbound routing uses conventional Tokyo/Cogent transit, not "
            "this GU-IX-local path, a genuine asymmetry rather than a "
            "contradiction."
        ),
    ),
    CandidatePeering(
        upstream_cc="GU",
        upstream_asn=9246,
        upstream_name="Teleguam Holdings, LLC (GTA)",
        target_cc="FM",
        target_asn=38875,
        target_name="FSM Telecommunications Corporation",
        measurement_id=211484664,
        vantage_point_cc="GU",
        probe_agreement="1/1 probe",
        note=(
            "Pulled from the corridor backlog: AS3605 (Guam Cablevision) -> "
            "AS38875 (FSM Telecommunications Corporation), a fresh GU<->FM "
            "economy pair. Only 1 of 3 requested probes returned. Result is "
            "genuinely different in kind from every other AS3605 detour this "
            "session: fully contiguous, and it actually **crosses a real, "
            "in-fishbowl exchange** -- AS3605 -> AS9246 (Teleguam Holdings/GTA, "
            "resolved via PeeringDB netixlan) at **MARIIX** (ix_id 2301, "
            "Mangilao, Guam -- in-fishbowl) -> AS139759. The literal target "
            "(AS38875) never itself resolved; the traceroute lands on "
            "AS139759 instead -- checked directly, and this is not a "
            "different network: AS38875's only RIS-observed neighbor is "
            "AS10130, and AS139759's only RIS-observed neighbor is also "
            "AS10130 -- both are sibling ASNs of the same real operator, FSM "
            "Telecommunications Corporation (confirmed via identical holder "
            "strings, the same pattern already established for ONATI's two "
            "ASNs). Even correcting for that sibling identity, RIS still "
            "doesn't confirm this specific adjacency: neither AS38875 nor "
            "AS139759 lists AS9246 (or AS3605) as a neighbor at all -- both "
            "show only AS10130. A clean, fully contiguous, real-exchange "
            "crossing that RIS simply doesn't corroborate -- exactly "
            "Validation Rule 4's shape: a real, physically-instantiated "
            "connection at an in-fishbowl exchange (Teleguam Holdings is a "
            "confirmed MARIIX member) that isn't announced anywhere RIS's "
            "route collectors can see. Kept as a candidate, not promoted, on "
            "the same principle as every other entry here -- a single clean "
            "traceroute doesn't satisfy Validation Rule 1 no matter how "
            "compelling the corroborating IXP membership evidence is."
        ),
    ),
    CandidatePeering(
        upstream_cc="MP",
        upstream_asn=7131,
        upstream_name="PTI Pacifica Inc.",
        target_cc="FM",
        target_asn=38875,
        target_name="FSM Telecommunications Corporation",
        measurement_id=211572946,
        vantage_point_cc="MP",
        probe_agreement="2/2 probes",
        note=(
            "A fresh MP<->FM pair, pulled from the corridor backlog. "
            "Unusually fast for this source (9-21ms RTT, a genuinely "
            "regional path, not a Tokyo/Sydney detour). Both probes cross "
            "**Guam IX** directly -- `ixp_crossings` confirms it, and "
            "unlike every other IXP crossing this project has recorded, "
            "this one is **in-fishbowl** (`in_fishbowl: true`): the member "
            "ASN is AS10130, itself one of FSM Telecommunications "
            "Corporation's own sibling ASNs (alongside AS38875 and "
            "AS139759, all sharing the same real operator, established "
            "earlier this session). The literal target (AS38875) never "
            "resolved; the traceroute lands on sibling AS139759 instead -- "
            "the same substitution already seen for this operator's other "
            "corridors. Applying the sibling-identity correction and "
            "checking both siblings' own RIS neighbor lists directly: "
            "AS38875's only neighbor is AS10130 (1,014 observations) and "
            "AS139759's only neighbor is also AS10130 (1,009) -- so RIS "
            "*does* confirm the internal FSM sibling relationship crossed "
            "here. But that's not the same as confirming *this* adjacency: "
            "AS10130 itself has zero RIS-observed neighbors on record, and "
            "AS7131's own neighbor list doesn't include AS10130 either -- "
            "so the actual traceroute-observed leg (AS7131 -> AS10130) "
            "remains unconfirmed by RIS from either side, exactly the same "
            "shape as the earlier GU(AS3605)->FM(AS38875) MARIIX entry "
            "above, just at a different in-fishbowl exchange. Kept as a "
            "candidate, not promoted, per Validation Rule 1 -- a real "
            "in-fishbowl crossing and a real sibling-confirmed downstream "
            "relationship still don't add up to RIS confirming the "
            "specific source-to-target leg itself."
        ),
    ),
    CandidatePeering(
        upstream_cc="FJ",
        upstream_asn=38442,
        upstream_name="Vodafone Fiji",
        target_cc="WS",
        target_asn=17993,
        target_name="Vodafone Samoa Limited",
        measurement_id=211622554,
        vantage_point_cc="VU",
        probe_agreement="1/1 probe",
        note=(
            "Sourced from AS9249 (Telecom Vanuatu) toward AS17993 -- a "
            "fresh VU<->WS pair. Clean, direct traceroute: AS9249 -> "
            "AS38442 (Vodafone Fiji) -> AS17993, contiguous. The final hop "
            "resolves via PeeringDB netixlan and lands directly inside "
            "AS17993's own registered LAN prefix at **Equinix Sydney** "
            "(`ixp_crossings` confirms it, AS17993 itself as the member) "
            "-- a real, physically-instantiated presence, not an inferred "
            "one. But `ris_agrees: false` on both sides: checked each "
            "ASN's full RIS neighbor list directly -- AS17993's "
            "(`{174: 1455, 6939: 150, 64073: 10, ...}`) and AS38442's "
            "(`{4637: 707, 7473: 697, 6939: 177, 2914: 46, ...}`) -- "
            "neither lists the other. Not a fishbowl-scope artifact (both "
            "ends are genuinely in-fishbowl Pacific ASNs). **A "
            "particularly well-motivated candidate, holder-name confirmed**: "
            "AS17993 is literally \"Vodafone Samoa Limited\" -- the same "
            "corporate brand as AS38442's \"Vodafone Fiji\", the same "
            "shape as the already-established Digicel Fiji<->Digicel Tonga "
            "intra-corporate transit pattern (see the GU->TO/AS38198 "
            "`ConfirmedDetour` entry). Exactly Validation Rule 4's shape: "
            "a real, physically-instantiated connection at a real exchange "
            "that isn't announced anywhere RIS's route collectors can see "
            "-- kept as a candidate, not promoted, per the standing "
            "principle."
        ),
    ),
    CandidatePeering(
        upstream_cc="GU",
        upstream_asn=9246,
        upstream_name="Teleguam Holdings, LLC (GTA)",
        target_cc="FM",
        target_asn=38875,
        target_name="FSM Telecommunications Corporation",
        measurement_id=211688231,
        vantage_point_cc="PF",
        probe_agreement="3/3 probes",
        note=(
            "A third independent source economy for this project's recurring "
            "FSM sibling-substitution corridor (after GU and MP), this time "
            "sourced from AS9471 (ONATI, French Polynesia). All 3 probes show "
            "the identical clean shape: AS9471 -> AS6939 (Hurricane Electric) "
            "-> AS9246 (Teleguam Holdings/GTA) -> AS139759, contiguous "
            "throughout. The literal target (AS38875) never itself resolved "
            "-- the same substitution already established twice: AS38875's "
            "only RIS-observed neighbor is AS10130, and AS139759's only "
            "RIS-observed neighbor is also AS10130, so both are confirmed "
            "sibling ASNs of the same real operator. `ris_agrees: false` on "
            "the corrected adjacency regardless: neither sibling lists AS9246 "
            "as a neighbor, matching the GU- and MP-sourced instances. "
            "**Genuinely different infrastructure this time**: `ixp_crossings` "
            "confirms AS9246 crosses at **Any2West** (all 3 probes), not "
            "MARIIX (the GU entry) or Guam IX (the MP entry) -- checked "
            "directly via PeeringDB's netixlan API before trusting the "
            "resolution: AS9246 genuinely holds a real Any2West membership "
            "(alongside SIX Seattle, MARIIX, and BBIX Tokyo), so this is a "
            "real, physically-instantiated crossing, not an artifact. Unlike "
            "the prior two entries, Any2West is **out-of-fishbowl** -- the "
            "first time this specific FSM corridor has shown a crossing "
            "outside the region's own exchanges rather than at MARIIX or "
            "Guam IX. Kept as a candidate, not promoted, per the standing "
            "principle: three independent source economies and a "
            "PeeringDB-verified real exchange crossing still don't satisfy "
            "Validation Rule 1 on their own -- RIS's own neighbor lists for "
            "both siblings remain the deciding evidence, and they still "
            "don't include AS9246."
        ),
    ),
    CandidatePeering(
        upstream_cc="GU",
        upstream_asn=9246,
        upstream_name="Teleguam Holdings, LLC (GTA)",
        target_cc="FM",
        target_asn=38875,
        target_name="FSM Telecommunications Corporation",
        measurement_id=211746507,
        vantage_point_cc="CK",
        probe_agreement="1/3 probes",
        note=(
            "A fourth independent source economy for this project's "
            "recurring FSM sibling-substitution corridor (after GU, MP, "
            "and PF), this time sourced from AS10131 (Cook Islands). Only "
            "1 of 3 requested probes returned; checked `participant_count` "
            "directly (1, not 3) -- the same genuine single-probe pattern "
            "as every other AS10131-sourced measurement this session. "
            "Identical shape to the PF-sourced instance: `AS10131 -> "
            "AS9471 (ONATI) -> AS6939 (Hurricane Electric) -> AS9246 "
            "(Teleguam Holdings/GTA) -> AS139759`, contiguous throughout, "
            "the literal target never resolving. `ris_agrees: false` on "
            "the corrected sibling adjacency, matching every prior "
            "instance. Crosses **Any2West** again (`ixp_crossings` "
            "confirms it) -- the same exchange as the PF entry, and the "
            "same ONATI-transit shape seen on every AS10131-sourced "
            "corridor this tranche cycle. Kept as a candidate, not "
            "promoted, per the standing principle."
        ),
    ),
    CandidatePeering(
        upstream_cc="PG",
        upstream_asn=4826,
        upstream_name="Vocus Connect (PNG DataCo's own known upstream)",
        target_cc="WS",
        target_asn=17993,
        target_name="Vodafone Samoa Limited",
        measurement_id=211810792,
        vantage_point_cc="PG",
        probe_agreement="1/1 probe",
        note=(
            "Sourced from AS17828 (PNG DataCo) toward AS17993 -- a fresh "
            "PG<->WS pair. Clean, direct traceroute: AS17828 -> AS4826 "
            "(Vocus Connect) -> AS17993, fully contiguous. The final hop "
            "resolves via PeeringDB netixlan and lands directly inside "
            "AS17993's own registered LAN prefix at **Equinix Sydney** "
            "(`ixp_crossings` confirms it, AS17993 itself as the member) "
            "-- the same real exchange already established for this "
            "target's other candidate entry (VU/AS38442), but via a "
            "genuinely different upstream carrier this time. But "
            "`ris_agrees: false`: checked AS17993's full RIS neighbor "
            "list directly -- `{174: 1455, 6939: 150, 64073: 10, ...}` "
            "-- AS4826 doesn't appear at all (checked AS4826's own "
            "fishbowl entry too: empty neighbor list, no RIS visibility "
            "into it from any direction). Not a fishbowl-scope artifact "
            "(both ends are genuinely in-fishbowl Pacific ASNs). Vocus "
            "Connect is already established elsewhere in this project as "
            "PNG DataCo's own real upstream carrier -- this traceroute "
            "shows that same carrier also reaching a real Equinix Sydney "
            "presence for Vodafone Samoa specifically, a second distinct "
            "carrier now shown crossing at the identical exchange for "
            "this target. Exactly Validation Rule 4's shape: a real, "
            "physically-instantiated connection at a real exchange that "
            "isn't announced anywhere RIS's route collectors can see -- "
            "kept as a candidate, not promoted, per the standing "
            "principle."
        ),
    ),
    CandidatePeering(
        upstream_cc="GU",
        upstream_asn=9246,
        upstream_name="Teleguam Holdings, LLC (GTA)",
        target_cc="FM",
        target_asn=38875,
        target_name="FSM Telecommunications Corporation",
        measurement_id=211968044,
        vantage_point_cc="PG",
        probe_agreement="1/3 probes",
        note=(
            "A fifth independent source economy for this project's "
            "recurring FSM sibling-substitution corridor (after GU, MP, "
            "PF, and CK), this time sourced from AS17828 (PNG DataCo). "
            "Identical shape to every prior instance: `AS17828 -> "
            "AS4826 (Vocus Connect) -> AS9246 (Teleguam Holdings/GTA) "
            "-> AS139759`, contiguous throughout, the literal target "
            "never resolving. `ris_agrees: false` on the corrected "
            "sibling adjacency, matching every prior instance. Crosses "
            "**Any2West** again (`ixp_crossings` confirms it) -- the "
            "same exchange as the PF and CK entries. Kept as a "
            "candidate, not promoted, per the standing principle."
        ),
    ),
    CandidatePeering(
        upstream_cc="PG",
        upstream_asn=1221,
        upstream_name="Telstra Limited (domestic ASN)",
        target_cc="NR",
        target_asn=140504,
        target_name="Digicel Nauru Corporation",
        measurement_id=211992510,
        vantage_point_cc="PG",
        probe_agreement="1/1 probe",
        note=(
            "Sourced from AS17828 (PNG DataCo) toward AS140504 (Digicel "
            "Nauru) -- a fresh PG<->NR pair. Clean, direct traceroute, "
            "fully contiguous: `AS17828 -> AS4826 (Vocus Connect) -> "
            "AS1221 (Telstra Limited, domestic ASN) -> AS140504`, the "
            "literal target resolving directly -- the first time this "
            "project has reached AS140504 via anything other than its "
            "two already-confirmed relationships (AS132528/Digicel "
            "Australia and AS12684/SES Astra). But `ris_agrees: false`: "
            "checked AS140504's full RIS neighbor list directly -- "
            "`{132528: 1032, 12684: 616}` -- AS1221 doesn't appear at "
            "all (checked AS1221's own fishbowl entry too: empty "
            "neighbor list, no RIS visibility into it from any "
            "direction). Not a fishbowl-scope artifact (both ends are "
            "genuinely in-fishbowl Pacific/Nauru ASNs -- Telstra itself "
            "isn't in-fishbowl, but the shape matches Validation Rule "
            "4 regardless). Notable: AS1221 and AS132528 (AS140504's "
            "real dominant neighbor) are both Telstra-operated -- a "
            "genuinely different ASN of the same corporate family "
            "reaching the same target directly, rather than the "
            "already-confirmed backbone ASN specifically. Kept as a "
            "candidate, not promoted, per the standing principle."
        ),
    ),
    CandidatePeering(
        upstream_cc="PW",
        upstream_asn=17893,
        upstream_name="Palau National Communications Corp",
        target_cc="NR",
        target_asn=55722,
        target_name="Cenpac Net Inc",
        measurement_id=212035683,
        vantage_point_cc="PW",
        probe_agreement="3/3 probes",
        note=(
            "Sourced from AS17893 (Palau NCC) toward AS55722 (Cenpac "
            "Net, Nauru) -- a fresh PW<->NR pair. All 3 probes show the "
            "same clean, contiguous, two-hop path: the source's own "
            "network -> a resolved address landing directly inside "
            "AS55722's own registered LAN prefix at **Guam IX** "
            "(`ixp_crossings` confirms it, AS55722 itself as the "
            "member, ix_id 4494, in-fishbowl) -- no intermediate "
            "transit carrier hop at all. But `ris_agrees: false`: "
            "checked AS55722's full RIS neighbor list directly -- "
            "`{7131: 1528}` -- AS17893 doesn't appear (AS7131/PTI "
            "Pacifica is its only real RIS-observed neighbor, already "
            "confirmed as its upstream in `confirmed_local_transit`). "
            "Not a missing-data artifact: both AS17893 and AS55722 "
            "independently claim PeeringDB membership at Guam IX (`ix_id "
            "4494`), so this is real shared-fabric corroboration on top "
            "of the traceroute evidence, matching this module's very "
            "first entry (FSM->Palau) in shape. A distinct finding from "
            "the already-confirmed AS7131<->AS55722 relationship, not a "
            "duplicate of it. Kept as a candidate, not promoted, per the "
            "standing principle."
        ),
    ),
)
