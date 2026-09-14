---
marp: true
theme: default
paginate: true
---

# Pacific Peering

### Mapping regional internet routing across Melanesia, Polynesia, and Micronesia

<!-- SPEAKER NOTE: intro, who you are, why this project exists -->

---

## The question

Does Pacific-to-Pacific internet traffic actually stay in the Pacific,
or does it detour through Australia, the US, or elsewhere?

<!-- SPEAKER NOTE: hook the audience with the concrete cost of this
     (latency, sovereignty, cost) before showing methodology -->

---

## Scope

- **20 economies**: Melanesia, Polynesia, Micronesia + Guam
  (Australia, NZ, Hawaii excluded)
- **164 ASNs** tracked
- Public data (RIPEstat, PeeringDB) + active measurement (RIPE Atlas)

---

## Methodology: the "fish bowl" problem

- RIS + PeeringDB is an outside-looking-in view — we can see paths and
  memberships, but not real internal routing decisions ("we can't get in
  the bowl")
- **Rule: no topology claim on one source alone** — RIS and Atlas must
  both agree before we call something a finding
- PeeringDB is a lead, never ground truth — it can be wrong, stale, or
  simply missing data (e.g. a real Solomon Islands IXP absent from it
  entirely)

<!-- SPEAKER NOTE: this slide is the credibility slide - spend time here -->

---

## Finding: GU -> PG detours via Equinix Sydney

- Guam -> PNG DataCo (AS17828); upstream AS6939 confirmed by RIS+Atlas.
- RIS-observed neighbor count: **1283**
- Confirmed by live Atlas traceroute (measurement `210901499`)
- Both RIS and Atlas agree — this project's bar for a real finding, not a guess
  from one source alone

<!-- SPEAKER NOTE: add the specific hop IP / IXP evidence for this pair here -->

## Finding: NC -> FJ detours via MegaIX Sydney

- New Caledonia -> Telecom Fiji (AS4638); upstream AS45349 confirmed by RIS+Atlas. Also IRR-corroborated: AS45349's own PeeringDB-declared AS-SET (AS45349:AS-TFL-TRANSIT) names AS4638 directly -- a declared transit intention, independently sourced (APNIC), matching what the traceroute actually shows.
- RIS-observed neighbor count: **1669**
- Confirmed by live Atlas traceroute (measurement `210919078`)
- Both RIS and Atlas agree — this project's bar for a real finding, not a guess
  from one source alone

<!-- SPEAKER NOTE: add the specific hop IP / IXP evidence for this pair here -->

## Finding: NC -> FJ detours via Equinix Sydney

- New Caledonia -> Digicel Fiji (AS45355); upstream AS132528 -- per the project owner, the Telstra-operated backbone ASN behind Digicel's Pacific mobile networks, registered in PeeringDB as 'Digicel Australia' -- confirmed by RIS+Atlas with an exact observation-count match (1,326) and a fully contiguous hop chain (AS18200, New Caledonia's own incumbent -> AS132528 at Equinix Sydney, exact netixlan address match -> AS45355). The strongest-evidenced finding in this project so far: also IRR-corroborated on *both* sides -- AS132528's declared AS-SET (AS-132528-PEERS) names AS45355 directly, and AS45355's own declared AS-SET (AS-45355-PEERS) names AS132528 right back -- a mutual, independently-sourced (APNIC) declaration matching the observed adjacency exactly. AS132528 was also seen at this same Equinix Sydney fabric in an earlier, unrelated measurement (210930962, the Zscaler-proxied Fiji probe test) -- two independent measurements, two different vantage points, same exchange presence.
- RIS-observed neighbor count: **1326**
- Confirmed by live Atlas traceroute (measurement `210996533`)
- Both RIS and Atlas agree — this project's bar for a real finding, not a guess
  from one source alone

<!-- SPEAKER NOTE: add the specific hop IP / IXP evidence for this pair here -->

## Finding: GU -> PW detours via AS174 (Cogent Communications), via AS2497 (IIJ, Japan) -- global transit, not a named exchange crossing

- Guam (AS3605, Guam Cablevision) -> Palau NCC (AS17893). Sourced directly from AS3605 via ASN-based probe selection (2 connected probes exist -- the project owner asked to test this specifically after two prior tranches could only test it indirectly, via country-based selection that happened to land on other Guam ASNs). Both probes: AS3605 -> AS2497 (IIJ, Japan) -> AS174 (Cogent Communications) -> AS17893, fully contiguous, no gaps. RIS agrees with an *exact* observation-count match (1,333). Different in kind from this project's other three confirmed detours: no hop landed inside any registered IXP LAN prefix (`ixp_crossings` empty for both probes) -- this is plain global Tier-1 transit (Cogent, reached via Japan), not a named-exchange crossing, so `detour_ix_name` records that honestly rather than implying an IXP that isn't there. What makes this the sharpest evidence yet for the project's actual thesis: AS17893 (this exact target) has *confirmed, repeated* local exchange presence at Guam IX (seen in three separate earlier measurements, two different source economies) -- real local peering infrastructure exists for this corridor. AS3605's own traffic to it simply doesn't use it, defaulting instead to a transit path via Tokyo and a global carrier. Not evidence the local exchange is unused in general (a different Guam network's traffic was shown reaching AS17893 via Guam IX in an earlier measurement) -- evidence that at least one real Guam ISP's default route to a real Guam-IX-connected Palau network bypasses the local exchange entirely.
- RIS-observed neighbor count: **1333**
- Confirmed by live Atlas traceroute (measurement `211064438`)
- Both RIS and Atlas agree — this project's bar for a real finding, not a guess
  from one source alone

<!-- SPEAKER NOTE: add the specific hop IP / IXP evidence for this pair here -->

---

## Finding: AS38442 (Vodafone Fiji) -> AS9249 (Telecom Vanuatu)

- All 3 probes (sourced from French Polynesia, the best-covered available vantage point — not itself part of this adjacency) show AS38442 as the last resolved hop before AS9249, matching RIS's independently-observed neighbor count exactly. A real gap remains between AS38442 and AS9249 (checked directly: ordinary ICMP filtering, not an unlisted IXP), so the very last hop isn't proven — but the AS38442 adjacency itself is. Reinforced from the reverse direction by measurement 210970669 (Vanuatu -> FSM/AS38875, sourced from Vanuatu itself): AS38442 is the first resolved hop leaving AS9249's own network, matching this same adjacency from the other side. That measurement's actual target (AS38875) was not confirmed — RIS's only neighbor for AS38875 is AS10130, not the traceroute's last resolved hop (AS139759) — a correct negative result, not a new finding, and recorded here only as corroboration of the existing AS9249<->AS38442 adjacency. Separately, after fixing traceroute_topology._resolve_address to check IXP-fabric membership independently of ASN resolution: for 2 of the original 3 probes (French Polynesia -> AS9249), the hop immediately before AS38442 is AS4637 (Telstra Global), resolved via PeeringDB netixlan, whose address also falls inside Any2West's registered LAN prefix (Los Angeles/Silicon Valley, out-of-fishbowl). This does not touch the AS38442<->AS9249 adjacency itself (still confirmed on its own terms), but it does mean the vantage point's own path to reach Fiji transits a US exchange first -- a real, separate observation about French Polynesia's own upstream routing, not the confirmed finding's two endpoints. Separately, IRR-corroborated: AS38442's own PeeringDB-declared AS-SET (AS38442:AS-ALL) names AS9249 directly among its declared peers -- a declared intention, independently sourced (APNIC), matching this adjacency on a fourth, independent axis alongside RIS, Atlas, and the reverse-direction reinforcement above.
- RIS-observed neighbor count: **1346**
- Confirmed by live Atlas traceroute (measurement `210960114`,
  vantage point: PF)
- Unlike the detour findings above, this stays entirely in-region —
  not everything routes out via Sydney

<!-- SPEAKER NOTE: this is a good-news slide - don't let it get lost after
     the detour findings -->

## Finding: AS154100 (BNL Tarawa) -> AS132486 (Ocean Link Ltd)

- A domestic (intra-Kiribati) adjacency, not a cross-economy one -- surfaced incidentally while testing an FM->KI corridor flagged by the IRR sweep two tranches ago (AS10130's declared transit AS-SET names AS132486 directly). All 3 probes, sourced from FSM (country-based selection -- landed on AS139759, *not* AS10130, so this measurement does not actually test that specific IRR lead. Checked directly whether AS10130 could be targeted specifically: RIPE Atlas's own probe registry shows zero connected probes on AS10130, and only one ever registered against it in total (probe 26163, status Abandoned) -- so the AS10130<->AS132486 relationship isn't just untested, it currently *cannot* be tested via Atlas at all, regardless of probe-selection method), show the same striking path: AS139759 -> AS9246 (GTA/Teleguam, Guam) -> AS7578/AS137409 (GSL Networks, Australia) -> **AS14593 (SpaceX Starlink)** -> AS154100 (BNL Tarawa) -> [one-hop ICMP-filtered gap] -> target (AS132486) never resolved. RIS's neighbor list for AS132486 lists AS154100 with an exact matching count (362) -- a real, confirmed adjacency, but between two Kiribati ASNs, not evidence either way about FM<->KI peering. The genuinely new, notable observation is the path itself: this FSM-sourced traffic's route to Kiribati transits Guam, an Australian carrier, and Starlink's satellite network before ever reaching a Kiribati-registered ASN -- not recorded as a confirmed detour (no traceroute hop landed inside any registered IXP LAN prefix; this is a plain carrier-to-carrier transit chain across the open internet, not a named-exchange crossing this project's ConfirmedDetour shape is built to capture), but real color worth keeping on record.
- RIS-observed neighbor count: **362**
- Confirmed by live Atlas traceroute (measurement `211020366`,
  vantage point: FM)
- Unlike the detour findings above, this stays entirely in-region —
  not everything routes out via Sydney

<!-- SPEAKER NOTE: this is a good-news slide - don't let it get lost after
     the detour findings -->

## Finding: AS3605 (Guam Cablevision, LLC) -> AS395400 (University of Guam)

- A domestic (intra-Guam) adjacency, surfaced while testing the actual question this measurement was built for: does University of Guam's own traffic really use GOREX locally (per the project owner's ask), given its confirmed presence there? Targeted University of Guam's own GOREX netixlan address (192.35.145.18) directly from a Guam-sourced probe. Of 3 probes: one resolved nothing at all; one (probe 7385) transited AS152735 then AS7131 (Northern Mariana Islands) before going dark, RIS disagreeing (not a finding); the third (probe 329) resolved cleanly to AS3605 (Guam Cablevision) as the last hop before the target -- RIS's neighbor list for AS395400 lists AS3605 with an *exact* matching count (1,091), a real confirmed adjacency in its own right. But the actual question -- does this traffic cross GOREX's own fabric -- comes back negative: none of the 3 probes showed a hop inside GOREX's registered LAN prefix (192.35.145.0/24) before going dark. Read honestly, this doesn't confirm GOREX goes unused (ICMP filtering right at the target, or at the exchange's own switch fabric, could explain it just as well as the traffic genuinely bypassing GOREX) -- it's inconclusive on the motivating question, while still yielding this separate, real, confirmed finding along the way.
- RIS-observed neighbor count: **1091**
- Confirmed by live Atlas traceroute (measurement `211038772`,
  vantage point: GU)
- Unlike the detour findings above, this stays entirely in-region —
  not everything routes out via Sydney

<!-- SPEAKER NOTE: this is a good-news slide - don't let it get lost after
     the detour findings -->

---

## Candidate: AS139759 (an FSM ASN (no PeeringDB org name on record)) -> AS17893 (Palau National Communications Corp)

- All 3 probes show the same clean, contiguous path: the source's own network -> AS139759 -> AS17893, with no external hub in between. But RIS's real neighbor list for AS17893 ({174: 1333, 140627: 139, 6939: 106, 24482: 49, 2500: 5, 18106: 5, 9002: 5, 49544: 5, 35280: 5, 9498: 5, 59105: 2, 9505: 2} -- all global/regional transit ASNs) does not include AS139759, and neither ASN shares a PeeringDB IXP membership, so no shared-fabric corroboration is available either. Not a missing-data artifact: AS17893 has plenty of RIS-visible neighbors, just not this one. Sharpened after fixing traceroute_topology._resolve_address to check IXP-fabric membership independently of ASN resolution: the hop immediately before the final target (103.142.153.18, resolved via PeeringDB netixlan to AS17893 itself) also falls inside Guam IX's registered LAN prefix (103.142.153.0/24) -- direct traceroute corroboration that AS17893 really does have a live interface at Guam IX, matching its PeeringDB-claimed membership there. That confirms AS17893's own presence at an in-fishbowl exchange, but not that AS139759 peers with it there specifically -- AS139759 has zero PeeringDB IXP memberships on record, so its side of this adjacency remains unconfirmed either way. A bulk IRR AS-SET sweep (APNIC-sourced only) surfaced a concrete alternative/complementary hypothesis worth checking before assuming the traceroute's AS139759 hop is the whole story: AS3605 (Guam Cablevision)'s own declared transit AS-SET (AS-KUENTOS-TRANSIT) names all three of Palau's in-scope ASNs (17893, 58932, 133897) directly, plus AS10130 (FSM Telecommunications Corporation) and MARIIX's own exchange ASN (23676) -- i.e. a real, independently-declared Guam-based transit relationship spanning exactly this corridor. Tested more directly with a second measurement (Guam -> AS17893, measurement 211044785 -- Guam rather than FSM as source, closer to what the AS3605 lead actually named): all 3 probes again land on the same GU-IX address (103.142.153.18) confirmed before -- a second, independent reinforcement of AS17893's Guam IX presence, this time from a different source economy. The immediate upstream this time is AS152735 ("Guam Exchange", 2 of 3 probes) or AS17456 ("Pacific Data Systems", 1 of 3) -- neither RIS-confirmed as a neighbor of AS17893, and AS152735's name/AS-SET ("AS-GUAMIX") suggests it's Guam IX's own route-server/infrastructure ASN rather than a distinct peering relationship, so not treated as a new candidate in its own right. AS3605 itself did not appear on this path -- the specific lead named in its AS-SET remains untested; a probe sourced from AS3605 itself, if Guam's several connected probes ever include one on it, would be the natural next check.
- Traceroute agreement: **3/3 probes** (measurement `210986430`,
  vantage point: FM)
- **Not a confirmed finding** — RIS disagrees, so this stays a candidate
  until a second independent corroboration turns up

<!-- SPEAKER NOTE: frame this as the method working as designed, not a
     failure — a clean traceroute alone was never enough to claim a
     finding on this project's own rules -->

## Candidate: AS17893 (Palau National Communications Corp) -> AS3605 (Guam Cablevision, LLC)

- The direct followup to the AS3605 lead above, this time sourced from Palau itself: a connected Atlas probe on AS17893 was found via the new ASN probe registry (`atlas.asn_probes`), letting this project source a traceroute from Palau for the first time all session. Fired AS17893 -> AS3605's own address directly. Result: the single cleanest adjacency this project has observed -- fully contiguous, *zero* gap, immediately AS17893 then AS3605, and the crossing hop lands inside **GU-IX**'s registered LAN prefix (ix_id 463, in fishbowl). Unlike most of this project's IXP-crossing evidence, AS3605's GU-IX membership isn't just inferred from the traceroute -- PeeringDB independently lists it as a real GU-IX member already. Still `ris_agrees: false`: AS3605's real RIS neighbor list (22 ASNs, none of them 17893) doesn't include this adjacency. Given (a) a fully contiguous single hop with no ambiguity at all, (b) AS3605's GU-IX presence confirmed independently of this measurement, and (c) this is exactly the corridor AS3605's own IRR AS-SET declared -- this reads as the strongest hidden-peering candidate in the project so far, per Validation Rule 4: a real, physically-instantiated local peering session at GU-IX that simply isn't announced anywhere RIS's route collectors can see it. Kept as a candidate, not promoted to confirmed, on principle -- Validation Rule 1 doesn't bend for how clean a single traceroute looks, no matter how compelling the corroborating evidence.
- Traceroute agreement: **1/1 probe** (measurement `211067648`,
  vantage point: PW)
- **Not a confirmed finding** — RIS disagrees, so this stays a candidate
  until a second independent corroboration turns up

<!-- SPEAKER NOTE: frame this as the method working as designed, not a
     failure — a clean traceroute alone was never enough to claim a
     finding on this project's own rules -->

---

## The IXP landscape

- **10 in-region exchanges** confirmed:
  CAN'L IX, Fiji-IXP, GOREX, GU-IX, Guam IX, MARIIX, PNG Neutral IX Hagen, PNG Neutral IX Lae, PNG Neutral IX POM, VIX.VU
- **21 out-of-region exchanges** confirmed as destinations for
  in-scope ASNs (Sydney, Tokyo, Frankfurt, Los Angeles, and others)
- Every classification here is an explicit human decision, never
  auto-inferred from a country-code lookup

---

## What this shows

<!-- SPEAKER NOTE: state the takeaway plainly - out-of-region peering is
     not optimal by definition (settled premise, not a hypothesis); these
     are concrete, confirmed instances, not the full extent of it yet -->

- Confirmed: real Pacific-to-Pacific traffic physically routes via Sydney
- Not yet measured: how widespread this is across all 164 ASNs —
  only a handful of AS pairs have been triangulated so far
- Atlas probe coverage itself is a limiting factor: several economies have
  zero connected probes

---

## Next steps

- Broaden the triangulated AS-pair sample
- Pursue a native (non-proxied) Atlas vantage point in economies that
  currently lack one
- [Add venue-specific next steps here]

---

## Thank you

- Project: `IEISI-ORG/pacific-peering` on GitHub
- Full methodology and findings: `task_plan.md` in the repo
- Support: buymeacoffee.com/terrysweetser

<!-- SPEAKER NOTE: Q&A -->
