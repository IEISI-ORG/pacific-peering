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
- **163 ASNs** tracked
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

---

## Candidate: AS139759 (an FSM ASN (no PeeringDB org name on record)) -> AS17893 (Palau National Communications Corp)

- All 3 probes show the same clean, contiguous path: the source's own network -> AS139759 -> AS17893, with no external hub in between. But RIS's real neighbor list for AS17893 ({174: 1333, 140627: 139, 6939: 106, 24482: 49, 2500: 5, 18106: 5, 9002: 5, 49544: 5, 35280: 5, 9498: 5, 59105: 2, 9505: 2} -- all global/regional transit ASNs) does not include AS139759, and neither ASN shares a PeeringDB IXP membership, so no shared-fabric corroboration is available either. Not a missing-data artifact: AS17893 has plenty of RIS-visible neighbors, just not this one. Sharpened after fixing traceroute_topology._resolve_address to check IXP-fabric membership independently of ASN resolution: the hop immediately before the final target (103.142.153.18, resolved via PeeringDB netixlan to AS17893 itself) also falls inside Guam IX's registered LAN prefix (103.142.153.0/24) -- direct traceroute corroboration that AS17893 really does have a live interface at Guam IX, matching its PeeringDB-claimed membership there. That confirms AS17893's own presence at an in-fishbowl exchange, but not that AS139759 peers with it there specifically -- AS139759 has zero PeeringDB IXP memberships on record, so its side of this adjacency remains unconfirmed either way. A bulk IRR AS-SET sweep (APNIC-sourced only) surfaced a concrete alternative/complementary hypothesis worth checking before assuming the traceroute's AS139759 hop is the whole story: AS3605 (Guam Cablevision)'s own declared transit AS-SET (AS-KUENTOS-TRANSIT) names all three of Palau's in-scope ASNs (17893, 58932, 133897) directly, plus AS10130 (FSM Telecommunications Corporation) and MARIIX's own exchange ASN (23676) -- i.e. a real, independently-declared Guam-based transit relationship spanning exactly this corridor. Not yet tested by Atlas; queued as a more targeted next traceroute than a second plain FSM->Palau run would be.
- Traceroute agreement: **3/3 probes** (measurement `210986430`,
  vantage point: FM)
- **Not a confirmed finding** — RIS disagrees, so this stays a candidate
  until a second independent corroboration turns up

<!-- SPEAKER NOTE: frame this as the method working as designed, not a
     failure — a clean traceroute alone was never enough to claim a
     finding on this project's own rules -->

---

## The IXP landscape

- **10 in-region exchanges** confirmed:
  CAN'L IX, Fiji-IXP, GOREX, GU-IX, Guam IX, MARIIX, PNG Neutral IX Hagen, PNG Neutral IX Lae, PNG Neutral IX POM, VIX.VU
- **20 out-of-region exchanges** confirmed as destinations for
  in-scope ASNs (Sydney, Tokyo, Frankfurt, Los Angeles, and others)
- Every classification here is an explicit human decision, never
  auto-inferred from a country-code lookup

---

## What this shows

<!-- SPEAKER NOTE: state the takeaway plainly - out-of-region peering is
     not optimal by definition (settled premise, not a hypothesis); these
     are concrete, confirmed instances, not the full extent of it yet -->

- Confirmed: real Pacific-to-Pacific traffic physically routes via Sydney
- Not yet measured: how widespread this is across all 163 ASNs —
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
