# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Project scaffolding: `uv`-managed package layout (`discovery`, `ris`,
  `atlas`, `analysis`, `viz`, `reports` modules), `data/` and `outputs/`
  directories, `.gitignore`.
- `LICENSE` (CC BY-NC-SA 4.0, commercial use requires a separate paid
  license).
- `README.md` project overview and setup instructions.
- `task_plan.md` phased build plan (P0/P1/P2), covering ASN discovery, RIS
  ingestion, RIPE Atlas measurements, scheduling, sub-optimal-routing
  analysis, visualization, and reporting.
- Scope decisions recorded: RIPEstat API as the RIS/ASPATH data source,
  standard APNIC/UN geoscheme economy list for Melanesia/Polynesia/
  Micronesia plus Guam (excluding Australia, New Zealand, Hawaii), monthly
  default update cadence.
- `pacific_peering.discovery`: canonical 20-economy list, an APNIC
  delegated-extended-stats downloader/parser, and a registry builder that
  produces `data/asn_registry.json` (economy -> delegated ASNs). Exposed as
  `pacific-peering-discover-asns`. Found 163 ASNs across all 20 in-scope
  economies on first run.
- `secrets.yaml` (untracked, gitignored) now holds the RIPE Atlas API key
  for the account to be used in Phase 1b measurements.
- `pacific_peering.ris`: a minimal RIPEstat client (`ris-prefixes` +
  `bgp-state`) proving the end-to-end "fish bowl" data flow — registry ASN
  -> originated prefixes -> live AS-paths. Exposed as
  `pacific-peering-ris-smoketest`. First live run against AS9751 (American
  Samoa) returned 993 AS-path observations across 3 prefixes.
- `pacific_peering.ris.bulk`: scales AS-path fetching to the full registry
  (threaded, per-ASN disk cache under `data/ris/raw/`).
- `pacific_peering.discovery.peeringdb` + `pacific_peering.analysis.ixp`:
  real IXP membership per ASN via PeeringDB.
- `pacific_peering.analysis.peering`: observed-neighbor inference from
  AS-path adjacency.
- `pacific_peering.analysis.fishbowl`: combines all of the above into
  `data/analysis/fishbowl.json`. Exposed as `pacific-peering-fishbowl`.
  First full run: 163 ASNs, 119,342 AS-path observations, 124 ASNs with an
  observed neighbor, 38 ASNs with confirmed IXP presence (MARIIX, Guam IX,
  PNG Neutral IX, CAN'L IX, VIX.VU among them).
- `pacific_peering.atlas`: RIPE Atlas client (`secrets.py`, `client.py`,
  `targets.py`, `probes.py`, `smoketest.py`). Entry points
  `pacific-peering-atlas-coverage` and `pacific-peering-atlas-smoketest`.
  Found that 5 of 20 in-scope economies (American Samoa, Nauru, Solomon
  Islands, Wallis & Futuna, Samoa) have zero connected Atlas probes, and
  that ASN-based probe selection fails for most in-scope ASNs — added
  country-based selection as the practical fallback.
- First live Atlas traceroute (measurement 210901499, Guam -> PNG DataCo):
  ground-truthed the Phase 1a Sydney-hub finding — all 3 probes' paths hit
  the exact IP (`45.127.172.31`) recorded as AS17828's Equinix Sydney port
  before reaching PNG DataCo's own network. First finding to move from
  "fish bowl signal" to "Atlas-confirmed."
- `pacific_peering.ris.ripestat.resolve_ip_to_asns` + `pacific_peering.
  analysis.traceroute_topology`: resolves traceroute hops to ASNs and
  checks them against RIS-observed neighbors. Entry point
  `pacific-peering-triangulate`. First result: all 3 Guam probes agree
  AS6939 (Hurricane Electric) is AS17828's immediate upstream, matching
  RIS's independently-observed count of 1,283 — the project's first
  ASN-to-ASN adjacency confirmed by both sources.
- `atlas.client.TracerouteHop` now captures per-hop RTT.
  `pacific_peering.analysis.feasibility`: great-circle distance,
  speed-of-light-in-fiber floor, direct-vs-relay RTT comparison. Entry
  point `pacific-peering-feasibility`. Applied to measurement 210901499:
  observed RTT is 8.5-9.1x the direct Guam->PNG physical floor but only
  2.7-2.9x the via-Sydney-relay floor — quantitative support (not proof)
  for the Sydney-detour finding, on top of the earlier exact-IP match.
- `atlas.smoketest.run_inbound_smoketest` (external vantage point tracing
  *in* to an in-scope ASN — the missing direction). Entry point
  `pacific-peering-atlas-inbound-smoketest`.
- Fixed a real bug: Atlas rejects measurement descriptions containing
  `<`/`>` outright ("Text contains disallowed characters") — this, not a
  propagation delay, was the cause of an earlier "transient" 400 wrongly
  blamed on timing. `create_traceroute_measurement` now validates this
  upfront and raises `ValueError` instead of a confusing 400.
- `analysis.traceroute_topology.check_neighbor_agreement` now handles the
  common case where a traceroute never reaches a hop resolving to the
  target ASN (ICMP filtering near the destination): it compares RIS
  against the last ASN actually reached instead of giving up.
- First inbound result (US -> AS17828, measurement 210913838): both
  probes independently corroborate real RIS-observed neighbors —
  AS58453 (China Mobile International, 129 RIS observations) and AS4637
  (Telstra Global, 214 RIS observations, AS17828's 2nd-largest). AS17828
  now has three RIS+Atlas-confirmed neighbors (AS6939, AS4637, AS58453)
  from three vantage points across both directions.
- `discovery.peeringdb.resolve_ip_via_netixlan`: exact-IP PeeringDB
  lookup, used as a fallback when RIPEstat's BGP-based IP-to-ASN
  resolution returns nothing (common for IXP fabric addresses). Retries
  with backoff on 429 before degrading to "unresolved."
- Fixed a real bug this uncovered: `traceroute_topology`'s AS-sequence
  extraction silently collapsed unresolved hops, which could make a
  non-adjacent ASN look directly adjacent to the target. It now tracks
  hop-to-hop contiguity explicitly and refuses to imply adjacency across
  a gap. Caught via New Caledonia -> Fiji (measurement 210919078): the
  fix correctly resolved MegaIX Sydney's fabric to AS45349 (Telecom Fiji
  Ltd) via the new PeeringDB fallback, matching RIS's independently
  observed neighbor (1,669 observations) exactly — a second
  RIS+Atlas-confirmed adjacency, via a second corridor and a second
  Sydney exchange.
- `analysis.ip_resolution_cache.IpResolutionCache`: persistent JSON cache
  for IP-to-ASN resolution (positive and negative results), wired into
  `traceroute_topology`. Verified via a cold-cache re-run of all three
  measurements: results held, and the NC -> Fiji case actually improved
  (all 3 probes now agree on AS45349, vs. 1 of 3 before hitting
  PeeringDB's rate limit).
- `discovery.supplementary_ixps.SUPPLEMENTARY_IXPS`: this project's own
  record for IXPs confirmed real but absent/incomplete in PeeringDB.
  Seeded with the Solomon Islands Internet Exchange Peering Point
  (SIIXP, operated by TCSI) — resolves Validation Rule 5, the last
  blocked validation item.
- `analysis.ixp_lan_registry`: IXP LAN subnet registry, tagged
  in-fishbowl/out-of-fishbowl. Governance rule: newly discovered
  exchanges are never auto-classified — written as `"TBA"` until
  explicitly confirmed via `confirm_ixp_region`/`add_or_confirm_ixp`.
  30 exchanges registered (29 from `fishbowl.json` + GOREX, added fresh
  since it wasn't linked to any known ASN yet); 3 confirmed in-fishbowl
  (CAN'L IX, Guam IX, GOREX), 27 awaiting confirmation.
- `discovery.peeringdb.fetch_ixp_prefixes` and `fetch_facility_presence`
  (with retry-on-429, after hitting PeeringDB's rate limit again).
  Wired the registry into `traceroute_topology` as a third hop-resolution
  tier (exchange known, member ASN not) — regression-clean against all
  three existing measurements.
- `fishbowl.py` now also captures real colocation facility presence
  (22 of 163 ASNs). Notable: AS24013 (Solomon Islands) shows facilities
  in LA, Fremont, Hong Kong (x2), Osaka (x2), Sydney, and Tallinn,
  Estonia — six facilities, five countries, three continents — strong
  additional evidence for the anycast/hosting-misattribution hypothesis
  already flagged for this ASN.
- Project owner confirmed 10 of the 30 registered exchanges as
  in-fishbowl (CAN'L IX, Guam IX, GOREX, Fiji-IXP, PNG Neutral IX x3,
  VIX.VU, GU-IX, MARIIX); 20 remain TBA.
- Tested the "does Suva show more local peers than PeeringDB's 3 known
  Fiji-IXP members" question (measurement 210930962) and found the
  test unanswerable with the current vantage point: Fiji's one
  connected Atlas probe sits behind AS53813 (Zscaler, a corporate VPN
  gateway), and the traceroute shows Zscaler tunneling to its own
  Sydney PoP before handing off to Digicel Fiji's backbone — never
  touching Fiji-IXP at all. Explicitly excluded from the Australia-hub
  evidence pile (a VPN vendor's routing choice, not an ISP's).
- Project owner confirmed the remaining 20 TBA exchanges as
  out-of-fishbowl. IXP LAN registry fully resolved: 30 exchanges, 10
  in-fishbowl, 20 out-of-fishbowl, 0 TBA.
- `pacific_peering.pipeline` (Phase 1c): recurring orchestrator
  (discovery -> fishbowl -> IXP LAN registry), versioned manifests
  under `outputs/runs/` (now tracked in git). Deliberately does not
  fire Atlas measurements automatically (credits + AS-pair selection
  need a human). First run caught a real bug: rebuilding the IXP LAN
  registry was silently dropping GOREX (added outside the normal
  fishbowl-derived set) — fixed so rebuilds only ever add to the
  existing registry, never discard from it.
- Project owner asked whether to wire the pipeline into a GitHub
  Actions cron; chose manual-only for now. Phase 1c complete as scoped.
- `viz/geographic.py` now also plots `CONFIRMED_LOCAL_TRANSIT` (solid
  green line, provider -> customer economy) alongside the existing
  detour lines — it had fallen behind the reports, which already
  covered both finding types. Verified by rendering to PNG and looking
  at it before calling it done, same as every other viz change.
- Tested a new corridor (Vanuatu -> FSM/AS38875, measurement 210970669).
  Reinforced the AS9249<->AS38442 finding from the reverse direction
  (updated its note rather than duplicating the entry). The actual
  target, AS38875, was correctly *not* confirmed — RIS's only neighbor
  for it is AS10130, not the traceroute's last resolved hop — recorded
  as a genuine negative result, not discarded.
- `analysis.confirmed_local_transit.CONFIRMED_LOCAL_TRANSIT`: the
  positive-finding counterpart to `confirmed_detours` (provider/customer
  ASN pair, both in-fishbowl). Seeded with AS38442 (Vodafone Fiji) ->
  AS9249 (Telecom Vanuatu). Wired into `ReportData` and all three report
  renderers (new ASCII section, green HTML card, new presentation slide
  with a speaker note not to let it get lost after the detour findings).
  Caught and fixed a real Markdown heading bug in the presentation slide
  (a literal newline mid-heading) by actually regenerating and reading
  the output, not just the source.
- Fixed a real crash: `ris.ripestat.resolve_ip_to_asns` had no retry or
  timeout handling — one slow RIPEstat response mid-analysis threw an
  uncaught `ReadTimeout` and killed the whole run. Now retries transient
  network errors with backoff and degrades to unresolved, matching the
  pattern already used for PeeringDB's 429s.
- Fourth RIS+Atlas-confirmed adjacency, and a new kind of finding: French
  Polynesia -> Vanuatu (AS9249) traceroute confirms **AS38442 (Vodafone
  Fiji)** as the last hop before the target, matching RIS's exact
  neighbor count (1,346). Unlike the first three, this is real
  intra-region transit, not a Sydney detour. Checked the remaining gap
  before the destination directly (hypothesized VIX.VU, wasn't it — just
  ordinary ICMP filtering) rather than overreach past what's confirmed.
- Phase 2b complete: docstring audit across all of `src/pacific_peering/`
  (AST-based, not eyeballed). Added module docstrings to all 7 package
  `__init__.py` files, docstrings on a handful of dataclasses/TypedDicts
  and `IpResolutionCache`'s accessor methods, and gave the leftover
  `uv init` placeholder package docstring/message a real purpose.
  Verified by re-running the audit, syntax-checking every file, and
  importing all six subpackages plus running the bare `pacific-peering`
  command. All of P1 and P2 are now complete (2c/changelog discipline
  stays ongoing, not a one-time task).
- Phase 2a complete: `reports/presentation.py` (Marp-compatible Markdown
  slide deck skeleton, same `ReportData` as the other reports). Entry
  point `pacific-peering-presentation`. Real numbers plugged into a
  conference-talk structure, with explicit speaker-note placeholders for
  judgment calls only the presenter can make.
- Phase 2b started: rewrote `README.md` (was still the Phase 0a
  scaffolding version) — a findings section stating both confirmed
  detours, the real project layout, and a usage section listing every
  entry point grouped by what it does.
- Phase 1f complete: `reports/data.py` (`build_report_data` ->
  `ReportData`, the single structure both report formats render from),
  `reports/ascii_report.py`, and `reports/html_report.py` (embeds the
  Phase 1e visualizations). Entry points `pacific-peering-report-ascii`
  and `pacific-peering-report-html`. HTML output verified by rendering
  it in headless Chromium and reviewing the actual screenshot, not just
  the markup. P1 (core pipeline) is now fully complete, 1a-1f.
- Phase 1e (visualization): `discovery.economy_coordinates`,
  `analysis.confirmed_detours`, and two chart modules under `viz/` —
  `geographic.py` (confirmed detours as bent paths vs. a direct-line
  comparison) and `as_graph.py` (full RIS-neighbor graph, green edges
  stay in-fishbowl, red leave it). Entry points
  `pacific-peering-viz-detours` and `pacific-peering-viz-as-graph`.
  Found 92 real intra-fishbowl RIS-neighbor edges (domestic hub-and-
  spoke: smaller ASNs getting transit from a national incumbent in the
  same economy) — not previously written up, and contrary to this
  graph's original assumption that such edges would be rare.
- Fixed a real regression in `analysis.ixp_lan_registry.build_ixp_lan_registry`:
  a rate-limited PeeringDB `ixpfx` refetch during a routine rebuild was silently
  overwriting already-known-good `prefixes` with `[]` (the same class
  of bug as the earlier GOREX/`in_fishbowl`-dropping issue, just in a
  different field). Caught by treating a scheduled pipeline run as a
  regression check rather than trusting a clean exit code: 3 exchanges
  (including GU-IX, a confirmed in-fishbowl exchange the traceroute
  classifier depends on) had lost their real subnet data. Fixed by
  keeping the existing prefixes whenever a fresh fetch comes back empty
  but prior data exists on record. Re-fetched and restored the 3
  already-lost entries directly, then re-ran the rebuild to verify —
  PeeringDB rate-limited again (4 different exchanges this time) and
  the fix correctly preserved all of them; a follow-up check confirmed
  0 of 30 exchanges have empty prefixes.
- Tested a new corridor: FSM -> Palau (AS17893, Palau NCC), measurement
  210986430. All 3 probes show a clean direct path (source's own network
  -> AS139759, an FSM ASN -> AS17893, no external hub in between) but
  RIS's real neighbor list for AS17893 doesn't include AS139759, and
  neither ASN shares a PeeringDB IXP. Recorded as a candidate hidden
  peering, not a confirmed finding — Validation Rule 1 requires RIS and
  Atlas to agree, and here they genuinely don't (not a missing-data
  artifact: AS17893 has plenty of RIS-visible neighbors, just not this
  one). Deliberately not given its own dataclass/module yet, same
  restraint as the earlier AS38875 negative result.
- Fixed a real gap in `traceroute_topology._resolve_address`: it only
  checked the IXP LAN registry when BGP *and* PeeringDB netixlan both
  failed to resolve an ASN, silently discarding cases where an address
  resolves to a real member ASN *and* also sits inside a known
  exchange's LAN. Found by re-examining the FSM->Palau candidate: its
  second-to-last hop resolved cleanly via netixlan to AS17893, but also
  falls inside Guam IX's registered LAN prefix -- direct traceroute
  corroboration of AS17893's PeeringDB-claimed Guam IX membership that
  the old logic never surfaced. Now checks IXP-fabric membership
  unconditionally. Verified by clearing the entire IP resolution cache
  and re-running all 7 measurements this project has fired: the two
  existing confirmed detours gained explicit LAN-prefix corroboration,
  and a new observation surfaced on the confirmed FJ->VU local-transit
  measurement (2 of 3 probes transit AS4637/Telstra Global at Any2West,
  Los Angeles, before reaching AS38442) -- folded into that finding's
  note as an addendum about the vantage point's own path, not a change
  to the confirmed adjacency itself.
- `analysis.candidate_peering` (`CANDIDATE_PEERING`): a third finding
  shape alongside confirmed detours/local-transit -- a clean, repeatable
  traceroute adjacency that RIS does not independently confirm, recorded
  as a candidate rather than forced into either existing category.
  Wired into all three report formats (new amber "warning"-colored
  section/card/slide) and the geographic map (dashed amber line),
  verified by rendering each.
- `discovery.peeringdb.fetch_ixp_members`, `atlas.targets.pick_ixp_member_target`,
  and `atlas.smoketest.run_ixp_member_probe`: a new active data-gathering
  method -- traceroute directly at a known PeeringDB member's peering-LAN
  address, rather than only noticing an IXP crossing incidentally.
  First real test (French Polynesia -> Fiji-IXP's AS38442 address,
  measurement 210990245): reached AS3257 (GTT) and went dark before the
  target -- an honest inconclusive result, but proves the method fires
  correctly end-to-end.
- Generalized `pick_ixp_member_target`/`run_ixp_member_probe`'s
  `exclude_asn` to `exclude_asns` (one ASN or a set), to walk through an
  exchange's full membership. Probed Fiji-IXP's other two members
  (AS45349, AS45355) from the same PF vantage point: all three members
  now show byte-for-byte identical intermediate hops, dying at AS3257
  (GTT) every time -- read honestly as one fact observed three times
  (PF's own fixed outbound route gets filtered before reaching Fiji-IXP
  at all), not three independent results, and not a finding about
  Fiji-IXP either way. Concrete argument for the next report below: this
  corridor needs a different vantage point, not a smarter probe choice
  among ones already known to be unusable.
- `reports.probe_gap_report` (`pacific-peering-report-probe-gaps`): a
  new single-purpose text report -- where to request a new RIPE Atlas
  probe next, kept deliberately separate from the findings-oriented
  reports and meant for its own (weekly) run cadence. Re-fetches live
  probe coverage every run, groups economies into zero/fragile(1)/
  adequate(2+) tiers, flags economies already load-bearing for a
  confirmed/candidate finding, and carries a small hand-curated known-
  issues note (Fiji's confirmed Zscaler-proxy problem). Verified by
  running it live: 5/20 economies have zero connected probes, 10/20
  have exactly one (four of them already central to real findings), 5/20
  adequately covered -- matching prior hand-verified figures.
- `discovery.peeringdb.fetch_irr_as_set_names` and new `discovery.irr`
  (`resolve_as_set`): a fourth lead source alongside RIS, PeeringDB
  IXP/facility membership, and Atlas -- a network's own IRR AS-SET
  declared peering/transit intentions. Per explicit project-owner
  instruction, only APNIC-sourced objects are trusted: queries
  whois.apnic.net directly (not a third-party mirror like RADB) and
  every response's `source:` field must read exactly APNIC or the
  object is treated as unresolved. Verified the rejection actually
  works by querying a known RADB/ARIN-sourced object and confirming it
  comes back empty with a warning, not silently used.
- Third confirmed detour: New Caledonia -> Digicel Fiji (AS45355) via
  Equinix Sydney (measurement 210996533), upstream AS132528 (the
  Telstra-operated backbone behind Digicel's Pacific mobile networks,
  per the project owner). The strongest-evidenced finding so far --
  RIS agrees with an exact 1,326-observation match, Atlas shows a fully
  contiguous 3/3-probe hop chain through an exact PeeringDB netixlan
  address match at Equinix Sydney, and IRR-corroborated on *both* sides
  (AS132528's and AS45355's own declared AS-SETs name each other
  directly). Also added the same IRR corroboration to the two existing
  confirmed findings (AS45349's AS-SET names AS4638; AS38442's names
  AS9249).
- Ran the deferred bulk IRR sweep: 36 of 163 in-scope ASNs have a
  declared irr_as_set; resolved all 36 (APNIC-only), handling
  multi-name fields and SOURCE:: prefixes PeeringDB's raw field can
  carry. Cross-referenced against the in-scope ASN list -- most matches
  are same-economy domestic hub-and-spoke (reinforcing the existing
  AS-graph finding), but surfaced several new cross-economy leads:
  AS3605 (Guam Cablevision) declares transit with all three Palau ASNs
  plus FSM's AS10130 (folded into the FSM->Palau candidate's note as an
  alternative hypothesis); AS10130 declares transit with a Kiribati ASN
  (a brand-new FM<->KI lead); AS45355 (Digicel Fiji) declares peers in
  Nauru, Vanuatu, and Tonga; French Polynesia's AS55943 and Samoa's
  AS38800 both declare a Niue ASN. None fired as new Atlas measurements
  this tranche -- a data-gathering/cross-referencing pass, queued for
  future targeted tests rather than tested all at once.
- `analysis.irr_leads` (`pacific-peering-irr-leads`): the IRR AS-SET
  sweep turned into real, persisted infrastructure (`data/analysis/
  irr_as_sets.json`), wired into `pipeline.run_pipeline` as a fourth
  step so a monthly pipeline run refreshes it automatically, per
  explicit project-owner instruction. Fixed a real bug hit on the first
  live run: `fetch_irr_as_set_names` had no retry/timeout handling and
  crashed on a single slow PeeringDB response -- now retries 429s and
  network errors with backoff, same pattern as this project's other
  PeeringDB calls, skipping (not crashing on) a chunk that still fails.
- `reports.data.FISHBOWL_EXPLANATION`: one shared "what is the fish
  bowl" explanation, added as a footer to the ASCII report, HTML report,
  and probe-gap report (not the presentation, which already has a full
  methodology slide covering the same ground) -- for a reader landing
  on any of them without prior context, including an external one.
- `outputs/reports/` and `outputs/viz/` are now tracked in git (matching
  the existing `outputs/runs/` exception), and the current generated
  reports/visualizations are committed for the first time.
- New confirmed local-transit entry: AS154100 (BNL Tarawa) <-> AS132486
  (Ocean Link Ltd), both Kiribati -- RIS agrees with an exact
  362-observation match. Surfaced while testing the FM<->Kiribati IRR
  lead from two tranches ago; country-based probe selection landed on
  a different FSM ASN (AS139759, not AS10130), so that specific IRR
  lead remains untested. The real, novel finding is the path itself:
  FSM-sourced traffic to Kiribati transits Guam, an Australian carrier
  (GSL Networks), and **Starlink** before reaching a Kiribati-registered
  network -- this project's first observed satellite-constellation hop.
  Not filed as a confirmed detour (no named-IXP crossing, a plain
  carrier-to-carrier chain instead).
- Recovered two Atlas measurement results after the backgrounded
  wait-and-fetch step was killed twice by an unrelated environment
  memory issue (a shared host running several other heavyweight
  services) -- since real Atlas credits had already been spent by the
  time each kill happened, re-ran the recovery step in the foreground
  rather than writing the data off as lost.
- Checked directly whether AS10130 has a usable Atlas probe (per the
  project owner's ask): zero currently connected, and only one ever
  registered against it in total (Abandoned). The AS10130<->AS132486
  IRR lead isn't just untested -- it currently can't be tested via
  Atlas at all, by any probe-selection method. Folded into the
  AS154100<->AS132486 confirmed-transit entry's note.
- Investigated AS141682 (ARENA-PAC, a Pacific research/education
  network) per the project owner: real, peers at GOREX (Guam, already
  in-fishbowl) and BBIX Singapore. Checking GOREX's real membership
  surfaced University of Guam (AS395400) -- real, physically present,
  but registered under ARIN rather than APNIC, so it never appeared in
  this project's APNIC-delegation-based registry.
- New `discovery.supplementary_asns` (mirroring the existing
  `supplementary_ixps` pattern): real in-scope ASNs delegated under a
  different RIR, merged into `registry.build_registry`. Seeded with
  University of Guam after a live cross-RIR audit (RIPEstat's
  `country-resource-list` against all 20 economies) surfaced 11
  candidate ASNs across 4 economies; only this one held up under direct
  verification. The other 10 (8 Marshall Islands, 1 Palau, 1 Vanuatu,
  all RIPE NCC-registered) were checked and confirmed *not* real --
  generic hosting-company holder names, facilities nowhere near the
  Pacific (one is Amsterdam-only, another is Hong Kong/Osaka/Sydney/LA/
  Fremont/Tallinn), independently corroborated by bgp.tools (below).
- Fixed a real data-loss bug in `analysis.irr_leads.build_irr_leads`,
  caught live while propagating the University of Guam addition through
  the pipeline: an un-guarded PeeringDB rate-limited chunk silently
  dropped 3 of 36 previously-good entries. Same fix already applied
  twice to `ixp_lan_registry` -- load existing leads first, never let a
  fresh fetch's gaps overwrite already-confirmed data. Restored the 3
  lost entries and re-verified the guard holds.
- New `discovery.bgp_tools`: a secondary, corroboration-only data
  source (bgp.tools), per the project owner. ASN name/class/country
  export, a live global BGP table with visibility counts, and community
  tags (`uni`, `satnet`, `vpsh`, `vpn`, etc.) -- all cached locally per
  bgp.tools' own posted cache-window guidance, with the required
  identifying User-Agent. Used immediately to independently corroborate
  the ASN-registry findings above: bgp.tools classifies all 10 rejected
  ASNs as non-"Eyeball", and AS43357 ("Owl Limited") carries both the
  `vpsh` and `vpn` community tags -- a third source agreeing it's a
  hosting/VPN provider, not a real Vanuatu ISP.
- Confirmed JPIX Tokyo (ix_id 30) as out-of-fishbowl, per the project
  owner. Zero exchanges remain unconfirmed (10 in-fishbowl, 21
  out-of-fishbowl, 0 TBA, of 31 total).
- Tested University of Guam's traffic against GOREX directly (per the
  project owner), targeting its own GOREX netixlan address from a
  Guam-sourced probe. New confirmed local-transit entry: AS3605 (Guam
  Cablevision) <-> AS395400 (University of Guam), RIS agreeing with an
  exact 1,091-observation match. The actual motivating question --
  does this traffic cross GOREX's own fabric -- came back inconclusive:
  no hop landed inside GOREX's registered LAN prefix before the trail
  went dark, recorded honestly as such rather than stretched to fit.
- Wired up the PeeringDB API key (read-only, per the project owner).
  New `discovery.secrets.load_peeringdb_api_key` (mirrors the existing
  Atlas-key pattern exactly); `discovery.peeringdb` centralized on a
  new `_get()` helper across all 8 of its request call sites, attaching
  the key when present and degrading to unauthenticated otherwise.
  Verified the header is attached correctly (without ever printing the
  key) and re-ran the full pipeline to check the actual motivation:
  a real but partial improvement -- the `net` endpoint hit zero
  rate-limit warnings this run (every prior run hit at least one), but
  `ixpfx` still got rate-limited twice (fewer than the usual 3-4,
  not zero). The existing "never discard already-confirmed data on a
  failed refetch" protections in `ixp_lan_registry`/`irr_leads` caught
  it correctly regardless -- verified no data was lost.
- Tested the queued AS3605<->Palau IRR lead from Guam (not FSM, which
  couldn't actually test it). Result: a second independent
  reinforcement of AS17893's Guam IX presence, landing on the same
  address confirmed twice before now from a different source economy
  -- not a new confirmed adjacency (the immediate upstream, "Guam
  Exchange"/AS152735, looks like Guam IX's own infrastructure ASN, not
  a distinct peer). AS3605 itself didn't appear on this path; the
  specific lead remains untested. Folded into the existing
  AS139759<->AS17893 candidate's note rather than creating a
  near-duplicate entry.
- Fourth confirmed detour, sourced directly from AS3605 (2 connected
  Atlas probes exist, unlike AS10130/AS395400): Guam (AS3605) ->
  AS2497 (IIJ, Japan) -> AS174 (Cogent Communications) -> Palau NCC
  (AS17893), RIS agreeing with an exact 1,333-observation match. A new
  shape for this project -- plain global Tier-1 transit via Tokyo, not
  a named-exchange crossing (labeled honestly as such). The sharpest
  evidence yet for the project's thesis: this exact target has
  confirmed, repeated local exchange presence at Guam IX, and this
  Guam ISP's default route to it simply doesn't use it. New "Tokyo"
  entry in `discovery.economy_coordinates.EXTERNAL_HUB_LATLON` to plot
  it; rendered and checked before calling it done.
- New `atlas.asn_probes` (`pacific-peering-atlas-asn-probes`): a
  persisted, monthly-refreshed record of which specific in-scope ASNs
  have a connected Atlas probe -- replaces three separate ad-hoc live
  checks this session with one lookup. Realized the existing per-economy
  probe-coverage query already returns each probe's own ASN, so this
  needs the same 20 API calls already being made, not 164. Wired into
  `pipeline.run_pipeline` as a fifth step. Verified against this
  session's own prior findings: matches exactly. Ran the full pipeline
  end-to-end afterward -- zero rate-limit warnings this run, no data
  lost.
- New candidate peering entry, the cleanest adjacency this project has
  observed: AS17893 (Palau NCC, sourced directly -- the new ASN probe
  registry found a connected probe on it) -> AS3605 (Guam Cablevision),
  a single fully-contiguous hop crossing GU-IX. AS3605's GU-IX
  membership is independently confirmed via PeeringDB, and this is
  exactly the corridor AS3605's own IRR AS-SET named two tranches ago
  -- the strongest hidden-peering candidate in the project so far, but
  RIS still disagrees, so kept a candidate rather than promoted.
- Recorded a durable methodology note per the project owner: use known
  "edge of the fishbowl" chokepoints (Hawaii, Sydney, Tokyo -- all
  three now empirically confirmed as real transit points this session)
  as external vantage points to triangulate Pacific routing from
  outside-in. Checked live probe availability on every external
  chokepoint ASN already identified: University of Hawaii has 1
  connected probe (notably the same ASN already confirmed as a GOREX
  member) -- queued as the natural next edge-to-edge test.
- Fired the queued Hawaii->Guam/GOREX test, plus a matching one sourced
  from ARENA-PAC itself (also had 2 connected probes). Hawaii (AS6360)
  -> University of Guam: RIS agrees exactly (40 observations) but a
  real gap remains before the target, and no GOREX crossing -- not
  added as a new entry (Hawaii is out-of-scope and this isn't an
  intra-Pacific detour, just Guam's real external connectivity).
  ARENA-PAC -> University of Guam: fully contiguous both probes, via
  WIDE Project and IIJ (Japan) then Guam Cablevision -- a third
  independent reinforcement of the existing AS3605<->AS395400 finding,
  folded into its note. Notable: ARENA-PAC and University of Guam are
  both confirmed GOREX members, yet this path between them still
  doesn't cross GOREX -- same pattern as the AS3605->Cogent detour.
- New confirmed local-transit entry: Niue (AS55885), tested for the
  first time all session via the ASN probe registry. RIS shows exactly
  one neighbor (AS55943, 1,662 observations) -- settling which of two
  competing IRR leads (from Samoa and French Polynesia) was real before
  any traceroute was needed. The traceroute itself resolved cleanly to
  AS9471, a sibling ASN of the same operator (ONATI, French Polynesia's
  telecom incumbent -- confirmed via matching PeeringDB holder names
  and AS9471's own RIS-confirmed 1,838-observation link to AS55943).
  Recorded with the ASN-identity nuance stated plainly. Also recovered
  from another environment memory-kill mid-measurement, same pattern
  and fix as before (measurement already created server-side; re-ran
  the results-fetch in the foreground).
- Fixed a real, generalizable gap in
  `traceroute_topology.check_neighbor_agreement`: it only ever checked
  the *target* ASN's own RIS neighbor list for the upstream, missing
  cases where RIS visibility is asymmetric (a small leaf network's own
  AS-path data shows a dominant upstream clearly, but that upstream's
  much larger, more globally-aggregated neighbor list doesn't surface
  that one specific downstream). Surfaced by testing Tuvalu (AS23917)
  for the first time: a fully contiguous, direct traceroute hop to
  AS9241 (FINTEL, Fiji) that RIS's own numbers overwhelmingly support
  from Tuvalu's side (1,009 of ~1,700 total observations) still came
  back `ris_agrees: false`. New `_bidirectional_ris_check` checks both
  directions. Re-ran all 20 measurements this project has ever fired
  under the fix: every previously-confirmed count stayed exactly the
  same (zero regressions), and the fix automatically re-derived the
  Niue<->ONATI relationship already reasoned through by hand last
  tranche, independent confirmation it generalizes correctly.
- New confirmed local-transit entry: FINTEL (AS9241, Fiji) <-> Tuvalu
  Telecommunications Corporation (AS23917), Tuvalu's first test this
  session, RIS agreeing with 1,009 observations once the bidirectional
  fix above was in place. Also noted in passing: Cook Islands' dominant
  RIS neighbor is AS12684 (SES Astra, a geostationary satellite
  operator) -- a second real satellite-transit finding, not chased
  further this tranche.
- Fired the queued Cook Islands -> SES Astra test. Honestly
  inconclusive: real gaps throughout (AS10131 -> AS9471/ONATI -> AS6939/
  Hurricane Electric -> target never resolved), no contiguous chain
  anywhere. Not added as a new finding -- the trail goes cold at a
  generic transit carrier, nowhere near SES Astra's own network, and
  the ONATI hop reappearing doesn't freshly confirm that relationship
  either (a real gap sits between AS10131 and it in this traceroute).
- Checked whether AS12684 (SES Astra) has a usable Atlas probe: zero
  connected, all 5 ever registered are Abandoned. Sourcing from it
  isn't possible right now by any method -- closes out this corridor.
- Tested AS17828 (PNG DataCo, this project's first-ever confirmed
  detour target) as a source for the first time. Result splits into
  two real findings, documented in full rather than forced into one
  category: PNG DataCo -> AS4826 (Vocus Connect, Australia) is a solid
  RIS+Atlas-confirmed adjacency (202 observations, exact match); the
  next leg, AS4826 -> AS3605 (Guam Cablevision), crosses Any2West (Los
  Angeles) with AS3605's presence there confirmed via an exact
  PeeringDB netixlan match, but RIS doesn't confirm that specific pair.
  Not filed as a new ConfirmedDetour (would overstate the unconfirmed
  Any2West leg) or CandidatePeering entry (would understate the
  genuinely solid PNG<->Vocus relationship) -- the confirmation sits on
  the first leg of a three-ASN chain, not the leg before the target the
  way every existing entry's evidence does.
- Added a second, independent IXP discovery path: direct per-economy
  PeeringDB search (`discovery.peeringdb.fetch_ixp_by_country`), merged
  into `build_ixp_lan_registry` alongside the existing
  membership-derived path. Answers "do we have all IXPs now?" -- a
  direct search across all 20 economies found exactly the same 10
  exchanges already confirmed in-fishbowl, zero gaps. Caught and fixed
  a real 429 bug on the function's first live pipeline run (no
  retry/backoff, unlike every sibling PeeringDB call); pipeline now
  runs clean (31 exchanges, 10 in-fishbowl, 0 empty prefixes). This
  runs on every pipeline cycle going forward, not a one-time check.
- Sourced AS3605 (Guam Cablevision) toward AS17893 (Palau NCC) using
  its now-connected Atlas probes -- then discovered this exact corridor
  was already confirmed in an earlier tranche (measurement 211064438,
  in `confirmed_detours.py`). Corrected course before compounding the
  duplicate: added the new measurement (211181370) as a corroboration
  note on the existing entry instead (identical path, identical exact
  RIS observation count -- real added confidence) and reverted a
  draft addendum that would have mis-framed it as new/unconfirmed
  content in `candidate_peering.py`. Process note added to
  task_plan.md: grep existing findings for an ASN pair before firing a
  new measurement toward it.
- Applied that new process rule immediately: grepped for AS58932 and
  AS133897 (the other two Palau ASNs in AS3605's declared AS-SET)
  first, confirmed neither was tested, then sourced AS3605 toward
  AS58932 (measurement 211185048). Real, clean, new finding: AS3605 is
  immediately adjacent to AS58932 with zero intermediate hops (RIS
  exact match, 664 observations) -- a completely different shape from
  the AS17893 corridor's Tokyo/Cogent transit path, despite both being
  named in the same IRR AS-SET. Added as a new ConfirmedLocalTransit
  entry. AS133897 (100% single-neighbor RIS signal toward AS3605) is
  flagged as the obvious next check, left untested this tranche on
  purpose.
- Fired that flagged next check: AS3605 -> AS133897 (measurement
  211193440), confirmed exactly as its RIS signal predicted (AS3605
  was AS133897's *only* RIS-observed neighbor -- 662/662 observations,
  the strongest single-neighbor signal in the project). Zero
  intermediate hops, exact RIS match. Added as a new
  ConfirmedLocalTransit entry. This completes the test of all three
  Palau ASNs named in AS3605's own IRR AS-SET: one (AS17893) reached
  via global transit, two (AS58932, AS133897) reached directly -- a
  real, mixed picture of one carrier's declared relationships, not a
  uniform one.
- Gave `discovery.bgp_tools.fetch_prefix_visibility` its first real
  exercise: cross-checked all 16 RIS-cached originated prefixes for
  AS3605/AS17893/AS58932/AS133897 against bgp.tools' independent
  global table dump. Complete agreement, zero discrepancies, healthy
  visibility counts (744-2802) throughout -- the first cross-source
  corroboration of this project's prefix-targeting data, not just a
  topology cross-check. AS3605/AS17893 also showed extra prefixes
  bgp.tools sees that RIS's deliberately-capped 5-prefix cache
  doesn't -- expected, not a discrepancy.
- Sourced AS9471 (ONATI, French Polynesia) as a traceroute source for
  the first time -- it has 6 connected Atlas probes, the most in the
  registry, but had only ever been a confirmed endpoint before.
  Targeted AS10131 (Cook Islands), whose own RIS data already showed
  ONATI's sibling ASN (AS55943) as its second-largest neighbor (658
  observations). Result looked inconclusive at first read
  (`contiguous: false`) but turned out to be a resolver limitation,
  not a real gap: the "unresolved" hops were all RFC1918 private
  addresses inside AS9471's own network, confirmed directly via
  RIPEstat rather than assumed. Read correctly, this is a direct
  single-AS-hop path, RIS-confirmed via the same sibling-ASN
  relationship already established for the Niue corridor. Added as a
  new ConfirmedLocalTransit entry. Flagged (not fixed) a generalizable
  resolver gap: private-address hops and genuinely-unresolvable hops
  are currently treated identically, though they mean different
  things.
- Fixed that flagged resolver gap, per the project owner's direct
  guidance: RFC1918/link-local addresses can never resolve to a real
  ASN globally, so `extract_as_sequence` now treats them as fully
  transparent instead of gap-inducing (`traceroute_topology.py`).
  Checked before the IP resolution cache too, so stale
  identically-cached entries from before this distinction existed
  don't mask the fix. Verified via full regression across all 26
  measurements this project has ever fired: zero `ris_agrees` changes
  anywhere, `contiguous` correctly flips false->true in exactly 4
  (the motivating case, 3 already-inconclusive dead-ends, and one
  already-confirmed finding). That last one required a real
  correction: the AS38442<->AS9249 (Fiji<->Vanuatu) entry's note had
  attributed its final-hop gap to "ordinary ICMP filtering" -- actually
  a single RFC1918 hop. Corrected in place; the measurement is now
  fully contiguous end to end, strengthening rather than changing
  this project's very first confirmed finding.
- Sourced AS24390 (University of the South Pacific, Fiji -- with a real
  campus in Vanuatu) for the first time, targeting AS9249 (Telecom
  Vanuatu). New ConfirmedDetour: USP's own inter-campus traffic
  detours via AARNet (Australia) and MegaIX Sydney rather than routing
  directly, landing on the exact same AS38442<->AS9249 adjacency
  (1,346 observations, exact RIS match) already this project's most
  solid finding -- now independently reinforced a third time, from a
  third vantage point. The real story is the detour itself: two
  islands ~1,100km apart, routed via Australia.
- Replaced the standing hourly `/loop` job with a more directive one
  (find + confirm + document + ship a corridor each firing). First
  firing: sourced AS7131 (Northern Mariana Islands, PTI Pacifica Inc.)
  for the first time, targeting its only Pacific-relevant RIS
  neighbor, AS152735 (Guam Exchange, 381 observations). Unanimous,
  clean, zero-hop result across all 3 probes, exact RIS match -- the
  first-ever traceroute confirmation involving Northern Mariana
  Islands. Added as a new ConfirmedLocalTransit entry.
- Sourced AS45345 (Nautile, an independent New Caledonia ISP, not the
  already-tested incumbent) toward AS3605 (Guam Cablevision) -- a
  previously-untested NC<->GU economy pair. Real signal found (crosses
  Any2West via Superloop/Australia) but RIS disagrees on the specific
  upstream adjacency, so not filed as ConfirmedDetour or
  CandidatePeering -- recorded in full prose in task_plan.md instead,
  matching this project's established restraint for partial-evidence
  chains. Investigated the reported traceroute gap directly: two
  unresolved hops belong to Superloop's own unannounced address space
  (WHOIS-attributable, not RFC1918) -- a real but distinct resolver
  edge case, flagged (not code-fixed) for a future tranche. Durable
  takeaway: a second, independent NC carrier also routes its
  Guam-directed traffic via Australia, reinforcing this project's
  broader NC routing pattern.
- Turned the manual Superloop-style gap investigation into a reusable
  helper. `ris/ripestat.py`: `fetch_routing_visibility` (RIS
  BGP-visibility check) and `fetch_whois_inetnum` (allocation record).
  `discovery/bgp_tools.py`: `is_prefix_routed_by_asn` (does a
  suspected operator route this specific address?). New
  `analysis/hop_investigation.py`: `investigate_unresolved_hop`
  orchestrates all three, kept deliberately separate from the
  automatic resolver (per the earlier decision not to add a
  WHOIS-based resolver tier off one occurrence) -- a tool to reach for
  deliberately, not a silent gap-to-confirmed upgrade. New entry point
  `pacific-peering-investigate-hop`. Verified against both the real
  Superloop case (matches the manual finding exactly) and a known-
  routed address (correctly returns the opposite answer).
- Added standing order to task_plan.md's Working Agreements: consult
  the project owner when data looks strange or routing is doing
  something unusual, including during unattended /loop firings --
  investigate first per this project's own discipline, but surface
  genuine anomalies rather than resolving them solo.
- Sourced AS56089 (OFFRATEL, a third distinct New Caledonia carrier)
  toward AS9249 (Telecom Vanuatu) -- a fresh NC<->VU economy pair.
  Fully contiguous, zero-gap result, exact RIS match (1,346) --
  AS38442<->AS9249 reinforced a fourth time, from a fourth vantage
  point. New color: the first measurement to show New Zealand (Spark
  NZ) as a transit waypoint, not just Australia -- the detour pattern
  is "whichever excluded AU/NZ hub sits on the path," matching the
  Fish Bowl's own excluded-zone definition. Added as a new
  ConfirmedDetour entry.
- Checked the RIPE Atlas credit balance: 95,715,160, net growing
  (+63,569/day, $0 expenditure at this project's usage rate) -- no
  concern, nothing flagged.
- Sourced AS17828 (PNG DataCo) toward AS9249 (Telecom Vanuatu) -- a
  fresh PG<->VU economy pair, both Melanesian. Fully contiguous,
  zero-gap result, exact RIS match (1,346) -- AS38442<->AS9249
  reinforced a fifth time, from a fifth distinct source network via
  Telstra's domestic and international ASNs back-to-back (no IXP
  crossing this time, plain Tier-1 transit). Added as a new
  ConfirmedDetour entry.
- Replaced ad-hoc "find the next unknown corridor" reasoning with a
  systematic, maintained backlog. New `analysis/corridor_backlog.py`:
  `tested_pairs.json` (authoritative dedup record, any outcome) +
  `corridor_backlog_snapshot.json` (diffed each run to flag genuinely
  new probes/RIS relationships), both gitignored generated state; new
  committed `corridor_backlog.md` (top 100 by priority). Backfilled 17
  known ASN pairs from this session's history. Wired an 8-hourly cron
  job to regenerate the backlog and a replaced hourly job to pull from
  it and mark pairs tested -- the concrete form of the project owner's
  "keep track of new probes and RIS changes" standing order.
- Proved the new system end-to-end: fired its top live pick, AS3605
  (Guam Cablevision) -> AS4638 (Telecom Fiji), a genuinely untested
  GU<->FJ pair. Result inconclusive but honest -- non-response near
  the destination (ordinary ICMP filtering, not the RFC1918/Superloop
  resolver cases), and RIS shows AS4638's real upstream is AS45349
  (already an existing confirmed detour), not the AS4637 this
  traceroute reached. Not filed in any dataclass, matching this
  project's established dead-end handling. Called
  mark_corridor_tested(3605, 4638) -- confirmed via a full regenerate
  that the pair correctly drops out of the backlog afterward.
- First hourly firing under the new backlog system: sourced AS3605
  toward AS9241 (FINTEL, Fiji). Measurement scheduled unusually slowly
  (checked directly, confirmed as ordinary Atlas latency, not a
  network anomaly -- not escalated). Result: AS3605 -> AS2497 (IIJ,
  Japan) -> AS174 (Cogent) -> AS9241, exact RIS match (830, AS9241's
  largest neighbor) -- the same Tokyo/Cogent transit shape already
  seen for AS3605's Palau corridor. Added as a new ConfirmedDetour
  entry; marked the pair tested; backlog regenerated (1378 -> 1330,
  the whole GU<->FJ economy pair now excluded).
- Second hourly firing: sourced AS3605 toward AS9249 (Telecom
  Vanuatu) -- a fresh GU<->VU pair. Converges onto AS38442<->AS9249
  again, now confirmed from a sixth distinct source network. Added as
  a new ConfirmedDetour entry (its own source economy, matching the
  NC->VU/PG->VU pattern); marked tested; backlog regenerated
  (1330 -> 1293).
- Third hourly firing: sourced AS3605 toward AS9471 (ONATI, French
  Polynesia) -- a fresh GU<->PF pair. Measurement scheduled slowly
  again (same pattern as the AS9241 firing, same non-anomalous
  explanation, resolved on a longer poll). Result: a genuine
  dead-end -- neither probe reached AS9471 or its sibling AS55943,
  stopping at Hurricane Electric in Tokyo instead. Not filed in any
  dataclass; marked tested regardless.
- Fourth hourly firing: sourced AS3605 toward AS9751 (American
  Samoa) -- a fresh GU<->AS pair. Fully contiguous, exact RIS match
  (1,055) via AS174 (Cogent). Third instance of the identical AS3605
  -> Tokyo/IIJ -> Cogent shape this session (after Palau and Fiji/
  FINTEL) -- a real, repeated routing signature, not a one-off. Added
  as a new ConfirmedDetour entry; marked tested; backlog regenerated
  (1293 -> 1285).
- Fifth hourly firing: sourced AS3605 toward AS10131 (Cook Islands)
  -- a fresh GU<->CK pair. Landed on the already-confirmed
  AS9471<->AS10131 adjacency, but as an intermediate transit hop this
  time, not the source -- and AS9471 (ONATI) is itself an in-scope
  Pacific carrier, not an external AU/NZ/JP/US hub the way every
  other detour waypoint has been. Real evidence ONATI transits other
  economies' traffic, not just its own. Not a new entry -- added as a
  corroboration note on the existing ConfirmedLocalTransit entry;
  marked tested; backlog regenerated (1285 -> 1283).
- Sixth hourly firing: sourced AS3605 toward AS17993 (Samoa) -- a
  fresh GU<->WS pair. Third occurrence of the slow-scheduling pattern
  (now recognized, not re-investigated). Fully contiguous, exact RIS
  match (1,455) via AS174 (Cogent), this time via Level 3/Lumen
  instead of Tokyo/IIJ -- the fourth AS3605-sourced measurement to
  land on Cogent as the real upstream, via a different intermediate
  route. Added as a new ConfirmedDetour entry; marked tested; backlog
  regenerated (1283 -> 1265).
- Seventh hourly firing: sourced AS3605 toward AS23917 (Tuvalu) -- a
  fresh GU<->TV pair. Landed on the already-confirmed AS9241<->AS23917
  (FINTEL<->Tuvalu) adjacency, same shape as last hour's ONATI
  corroboration -- FINTEL, an in-fishbowl Fiji carrier, transiting
  Guam's traffic. Second distinct case of a regional hub within the
  fishbowl this session. Not a new entry -- corroboration note added;
  marked tested; backlog regenerated (1265 -> 1263).
- Eighth hourly firing: the flagged AS24013 anomaly arrived.
  Investigated before firing anything -- target IP resolved to RIPE-
  region space, WHOIS confirmed AS24013 is DNS.SB (a global anycast
  DNS resolver), not a Solomon Islands ISP, matching the Germany-only-
  IXP anomaly flagged in Phase 1a and the same pattern as 8 already-
  excluded Marshall Islands shell ASNs. Consulted the project owner
  rather than resolving alone; decision: exclude from the registry.
  New `discovery/excluded_asns.py` (symmetric counterpart to
  `supplementary_asns.py`), wired into `registry.build_registry()`.
  Rebuilt the registry (164 -> 163 ASNs) and fishbowl.json live,
  confirmed AS24013 gone from both, regenerated the corridor backlog
  (1263 -> 1248). Then completed the actual corridor test: AS3605 ->
  AS24439 (Marshall Islands NTA, verified as the real incumbent
  operator, not a shell, before testing). Result: RIS-confirmed via
  the last-resolved-ASN method, exact match (997) via AS6453 (Tata
  Communications) -- AS24439's only RIS neighbor at all. Added as a
  new ConfirmedDetour entry; marked tested; backlog regenerated
  (1248 -> 1242).
- Ninth hourly firing: sourced AS3605 toward AS38198 (Digicel Tonga)
  -- a fresh GU<->TO pair. Both probes actually cross into the target
  network (a real, BGP-confirmed AS38198 address one hop past Digicel
  Fiji), then go silent trying to reach the specific queried address
  -- checked the raw hops directly before treating that as routine,
  confirmed the adjacency itself sits before the silent stretch, not
  inside it. Exact RIS match (1,321) via AS45355 (Digicel Fiji, its
  only neighbor) -- both Digicel regional subsidiaries, likely
  intra-corporate transit, same shape as the Wallis & Futuna->Orange
  relationship. Added as a new ConfirmedDetour entry; marked tested;
  backlog regenerated (1242 -> 1230).
- Sourced AS3605 toward AS38875 (FSM Telecommunications Corporation)
  -- a fresh GU<->FM pair. First AS3605 detour this session to
  actually cross an in-fishbowl exchange: AS3605 -> AS9246 (Teleguam
  Holdings/GTA) at MARIIX -> AS139759 (a confirmed sibling ASN of the
  literal target, same operator as AS38875). RIS doesn't corroborate
  the specific adjacency even correcting for the sibling identity --
  a clean, real exchange crossing kept as a new CandidatePeering
  entry, not ConfirmedDetour. Marked tested; backlog regenerated
  (1230 -> 1208).
- Sourced AS3605 toward AS45879 (Orange Wallis & Futuna) -- a fresh
  GU<->WF pair. Exact RIS match (1,665) via AS5511 (Opentransit
  Orange S.A.), identical to the relationship already found during
  this session's market-concentration analysis -- the operator is a
  direct Orange Group subsidiary on its own parent's backbone. Fifth
  distinct global carrier confirmed filling AS3605's Tokyo-transit
  role. Added as a new ConfirmedDetour entry; marked tested; backlog
  regenerated (1208 -> 1205).
- Replaced the hourly corridor-testing job with a 10-minute cadence
  (`/loop 10m`), per the project owner's request -- flagged the
  overlap with the existing hourly job first, confirmed replacement.
  Ran immediately: sourced AS3605 toward AS45891 (Solomon Telekom) --
  a fresh GU<->SB pair, holder name verified as a real incumbent
  before firing. Exact RIS match (1,652) via AS4637 (Telstra Global)
  -> AS139609 (Solomon Islands Submarine Cable Company, SISCC) --
  AS45891's only RIS neighbor, a clean confirmation with no
  sibling-ASN reasoning needed. Added as a new ConfirmedDetour entry;
  marked tested; backlog regenerated (1205 -> 1178).
- First firing under the 10-minute cadence: sourced AS3605 toward
  AS55722 (Cenpac Net Inc, Nauru) -- a fresh GU<->NR pair. Genuine
  dead-end (weaker than usual -- no intermediate carrier ever
  resolved, not just silence near the destination). Real lead
  surfaced anyway: AS55722's only RIS neighbor is AS7131 (PTI
  Pacifica, Northern Mariana Islands), already a confirmed source
  this session -- flagged for a future firing to test that actual
  relationship instead of an arbitrary pair. Not filed in any
  dataclass; marked tested regardless.
- Immediate follow-through: sourced AS7131 (PTI Pacifica, CNMI)
  directly toward AS55722 (Nauru). Traceroute physically short and
  only 1/3 probes returned, but the resolved upstream is the literal
  source ASN, and RIS confirms it exactly (1,528 observations,
  AS55722's only neighbor) -- Validation Rule 1 satisfied directly.
  Corrects the earlier AS3605 attempt: PTI Pacifica, not Guam
  Cablevision, is Nauru's real upstream. Added as a new
  ConfirmedLocalTransit entry; marked tested; backlog regenerated
  (1178 -> 1173).
- Sourced AS3605 toward AS55885 (Niue) -- a fresh GU<->NU pair.
  Fully contiguous to the literal target via AS9471 (ONATI), landing
  on the already-confirmed Niue<->ONATI relationship (third
  independent-source confirmation of it this session). Added as a
  corroboration note, not a new entry; marked tested; backlog
  regenerated (1173 -> 1171).
- Sourced AS3605 toward AS55943 (ONATI's other ASN, French
  Polynesia) -- GU<->PF had a dead-end via AS9471 earlier this
  session, but that never excluded the economy pair, so retesting the
  sibling ASN was worthwhile. Real, different result: exact RIS match
  (1,657) via AS3257 (GTT Communications), a completely different
  carrier than the earlier dead-end. Added as a new ConfirmedDetour
  entry; marked tested; backlog regenerated (1171 -> 1151).
- Sourced AS3605 toward AS132486 (Ocean Link Ltd, Kiribati) -- a
  fresh GU<->KI pair. Reproduced the exact same Australia->Starlink
  satellite chain already documented for the FSM->Kiribati corridor,
  landing on the identical AS154100<->AS132486 adjacency (exact RIS
  match, 362). Two unrelated, distant sources now confirm the same
  ingress pattern -- real evidence it's Kiribati's actual general
  routing behavior, not one source's quirk. Added as a corroboration
  note, not a new entry; marked tested; backlog regenerated
  (1151 -> 1150).
- Sourced AS3605 toward AS134783 (ATHKL's other ASN, Kiribati) --
  third instance of the identical Australia/Starlink chain, but this
  time a genuinely new adjacency: AS154100 (BNL Tarawa) is AS134783's
  own dominant RIS neighbor too (exact match, 1,392), a second
  distinct Kiribati ASN confirmed reachable through it. Added as a
  new ConfirmedLocalTransit entry; marked tested; backlog regenerated
  (1150 -> 1149).
- Sourced AS3605 toward AS140504 (Digicel Nauru Corporation) -- a
  fresh GU<->NR pair. Real signal (crosses Level 3/Global Crossing)
  but RIS disagrees, and the upstream isn't a Pacific network -- fits
  neither ConfirmedDetour nor CandidatePeering, same reasoning as the
  NC->GU Superloop case. Real color: AS140504's actual neighbors are
  AS132528 (the same Digicel-family Telstra backbone ASN already seen
  for Digicel Fiji) and AS12684 (SES Astra, no connected probes).
  Not filed in any dataclass; marked tested regardless.
- Sourced AS3605 toward AS141368 ("ICT", Nauru) -- a fresh GU<->NR
  pair. Same weak dead-end pattern as the earlier AS55722 attempt.
  Real lead surfaced: AS141368's only RIS neighbor is AS55722, whose
  own real upstream (AS7131/PTI Pacifica) was directly confirmed two
  tranches ago -- flagged for a future firing to test AS7131 ->
  AS141368 directly. Not filed in any dataclass; marked tested
  regardless.
- Sourced AS3605 toward AS152093 (VakaNet Limited, Cook Islands) -- a
  second, distinct CK ASN tested from Guam. Fully contiguous, exact
  RIS match (335) via AS9507 (NextHop Pty Ltd, Australia), crossing
  BBIX Tokyo -- a genuine named-exchange crossing, unlike the earlier
  AS10131 corridor's in-fishbowl ONATI transit. Two real, differently
  -shaped Cook Islands corridors now on record. Added as a new
  ConfirmedDetour entry; marked tested; backlog regenerated to 1136.
- Sourced AS3605 toward AS152706 (Neotel, Nauru) -- closing out a run
  of three Nauru dead-ends with a clean confirmation. Fully
  contiguous, exact RIS match (292) via AS6453 (Tata Communications)
  -- the second distinct instance of Tata this session, a real
  recurring carrier in this Guam network's transit mix. Added as a
  new ConfirmedDetour entry; marked tested; backlog regenerated
  (1136 -> 1127).
- Sourced AS3605 toward AS154100 (BNL Tarawa itself, Kiribati) --
  targeting the provider ASN behind two already-confirmed intra-
  Kiribati relationships directly. Cleanest confirmation yet: AS14593
  (Starlink) is BNL Tarawa's only RIS neighbor, exact match (361).
  Deliberately not filed as a new ConfirmedDetour -- Starlink has no
  fixed terrestrial hub to map, unlike every other detour on record.
  Added as a sharpening note on the existing entry instead. Marked
  tested; backlog regenerated (1127 -> 1126). Notable: the next live
  pick is now sourced from AS7131, not AS3605 -- the backlog is
  diversifying sources as its cheap AS3605 targets run out.
- First firing sourced from a diversified ASN: AS7131 (PTI Pacifica,
  CNMI) toward AS4638 (Telecom Fiji) -- a fresh MP<->FJ pair. Real
  path (via Telstra Global) but RIS disagrees; the gap turned out to
  be the exact same 202.137.178.x unresolved zone already flagged
  back in loop tranche 5, not a new anomaly. AS4637 is an external
  carrier, not a Pacific network, so doesn't fit CandidatePeering
  either. Not filed in any dataclass; marked tested regardless.
- Sourced AS7131 toward AS9241 (FINTEL, Fiji) -- a fresh MP<->FJ
  pair. Complete, ordinary dead-end: zero hops resolved to any ASN,
  only RFC1918 hops then total silence, same pattern already seen a
  few times this session. Not filed in any dataclass; marked tested
  regardless.
- **Correction, prompted by the project owner's own direct field
  testing**: the AS7131->AS9241 "ordinary dead-end" above was wrong.
  Retried against a different AS9241 prefix's address (the original
  `pick_target_ip` only ever surfaces the first cached prefix) and
  found a real routing loop entirely inside AS6939 (Hurricane
  Electric)'s backbone -- the same address repeating across
  consecutive hops, RTT climbing past 300ms, never reaching AS9241 at
  all. Confirmed via RIPEstat that all three repeating addresses
  belong to AS6939.
- feat(atlas): add `list_target_ips` (every cached prefix's address,
  not just the first) and `has_routing_loop` (repeat-plus-never-
  reached-target heuristic) to `atlas/targets.py`, exported from
  `atlas/__init__.py`. Built directly off the correction above so
  future dead-end corridors get retried against an alternate address
  instead of being written off. First version of `has_routing_loop`
  flagged any consecutive repeat and produced a live false positive
  against a real successful traceroute (one benign repeated hop,
  ECMP noise); refined to require the target never appearing in the
  hops at all, re-verified against both real measurements.
- feat(analysis): confirm MP(AS7131, CNMI)->VU(AS9249, Telecom
  Vanuatu) via AS38442 (Vodafone Fiji) -- a fresh MP<->VU pair, and
  the corridor actually queued next this tranche. RIS agrees exactly
  (1,346) -- the project's very first confirmed finding, now
  independently reinforced a seventh time, first time from CNMI as
  source. Backlog: 1126 -> 1113 (both AS9241 and AS9249 marked
  tested).
- Sourced AS7131 toward AS9471 (French Polynesia) -- a fresh MP<->PF
  pair. First address dead-ended past a private hop
  (`has_routing_loop` correctly said "not a loop"); retried with the
  next `list_target_ips` candidate per the new policy and it reached
  the target cleanly on both probes -- confirms the first address's
  silence was address-specific, not structural. RIS disagrees, but
  for a legible reason: the observed upstream is AS6939 (Hurricane
  Electric), an external carrier outside `fishbowl.json`'s
  Pacific-only scope, and AS9471's only fishbowl neighbor is its own
  sibling AS55943. Same shape as the NC->GU Superloop precedent --
  real signal, doesn't fit either dataclass. Not filed; marked
  tested. Backlog: 1113 -> 1111.
- feat(analysis): confirm MP(AS7131, CNMI)->AS(AS9751, American
  Samoa) via AS11404 (Wave Broadband) -- a fresh MP<->AS pair,
  retried against a second address after the first dead-ended past a
  private hop. RIS agrees exactly (267), matching AS9751's own
  fishbowl neighbor list already on record from the existing
  GU(AS3605)->AS9751 Cogent/Tokyo entry -- a genuinely different
  carrier confirmed reaching the same target. Added "Honolulu" to
  `economy_coordinates.EXTERNAL_HUB_LATLON` (new hub, sourced from
  AS9751's own registered DRF IX Honolulu PeeringDB presence, not a
  directly-observed crossing in this traceroute -- noted explicitly
  in the entry). Backlog: 1111 -> 1109.
- Sourced AS7131 toward AS10131 (Cook Islands) -- a fresh MP<->CK
  pair, reached directly on the first address. Landed on an
  already-confirmed adjacency (AS9471/ONATI -> AS10131), now a third
  independently-corroborated source economy for it (after ONATI's
  own vantage point and Guam). RIS "disagrees" on the literal AS9471
  number for the same reason as every prior instance: the real
  confirmation is via ONATI's sibling ASN, AS55943 (658, exact
  match). Extended the existing `ConfirmedLocalTransit` entry's note
  rather than duplicating; entry count unchanged (11). Backlog:
  1109 -> 1107.
- feat(analysis): confirm MP(AS7131, CNMI)->NC(AS17480) via BBIX
  Tokyo (Superloop, AS38195, into AS18200/OPT NC). A retried second
  address dead-ended, but re-triangulating the *first* address's
  attempt showed it had already reached the target cleanly -- a
  raw-hop skim isn't a substitute for running the actual
  triangulation before writing a corridor off. RIS agrees exactly
  (1,665) on AS18200->AS17480, and AS18200's own neighbor list
  independently confirms the AS38195 hop too (332). Unlike this
  session's earlier NC->GU Superloop dead end (unfileable, RIS
  silent), this one is doubly corroborated on both sides -- a clean
  ConfirmedDetour. Backlog: 1107 -> 1090.
- feat(analysis): confirm MP(AS7131, CNMI)->PG(AS17828) via Equinix
  Sydney -- a second independent confirmation of this project's
  very first-ever finding (AS6939<->AS17828), from a genuinely
  different source economy. RIS agrees exactly (1,283), and
  `ixp_crossings` directly confirms both ASNs as members at the same
  Sydney fabric hop this time. One of three probes was a
  probe-specific dead end from the first hop, unrelated to the
  corridor. `has_routing_loop` false-positived on a near-destination
  (but not literal-target) repeated address with stable RTT -- caught
  by checking the raw hops directly, documented as a known heuristic
  limit rather than silently patched (no second data point yet to
  refine against). Backlog: 1090 -> 1060.
- feat(analysis): add MP(AS7131)->PW(AS17893) as a new
  `CandidatePeering` entry -- a direct, single-hop, 3/3-probe-clean
  traceroute (unusually fast RTT, ~20-30ms) with no intermediate ASN
  at all, but RIS confirms it from neither side. Both ends are
  in-fishbowl Pacific ASNs, so not a fishbowl-scope artifact; AS7131
  and AS17893 do share two real PeeringDB IXP memberships (BBIX
  Tokyo, Guam IX) as plausible context, though this traceroute
  itself doesn't land inside either registered LAN. Kept as
  candidate, not promoted, per Validation Rule 1. Backlog:
  1060 -> 1056.
- feat(analysis): confirm MP(AS7131, CNMI)->WS(AS17993, Samoa) via
  Equinix Sydney (Hurricane Electric, AS6939). A different carrier
  than the existing GU->WS entry's dominant AS174/Cogent relationship
  -- RIS agrees exactly (150), matching AS17993's own neighbor list
  already on record from that earlier entry. Real IXP crossing
  confirmed directly (`ixp_crossings` non-empty, Equinix Sydney, all
  3 probes). Ninth occurrence of AS7131's slow-scheduling pattern,
  resolved on a longer background poll. Backlog: 1056 -> 1050.
- Sourced AS7131 toward AS23917 (Tuvalu) -- a fresh MP<->TV pair,
  landing on the existing FINTEL(AS9241)<->Tuvalu adjacency, now a
  third independent corroboration. Same exact RIS match (1,009) but
  a genuinely new upstream path into FINTEL this time: AS6939 ->
  AS4648 (Spark NZ), crossing Equinix Los Angeles -- neither the hub
  nor the carrier had appeared for this adjacency before. Extended
  the existing `ConfirmedLocalTransit` entry's note rather than
  duplicating; entry count unchanged (11). One of three probes was a
  probe-specific dead end, unrelated to the corridor. Backlog:
  1050 -> 1048.
- feat(analysis): confirm MP(AS7131, CNMI)->FJ(AS24390, USP) via
  AS140627 (OneQode) -> AS7575 (AARNet). First time AS24390 has been
  targeted directly as a destination rather than only as a source
  (see the existing FJ->VU/AS9249 entry). RIS agrees exactly (337)
  via the last-reached-ASN method -- the identical AS7575 count
  already on record from that entry's own note, now independently
  confirmed from the opposite direction. Backlog: 1048 -> 1035.
- feat(analysis): confirm MP(AS7131, CNMI)->MH(AS24439) via AS174
  (Cogent) -> AS6453 (Tata Communications) -- second independent
  confirmation of the existing GU->MH adjacency, via a different
  path (Cogent direct, not the original's IIJ/Tokyo route). RIS
  agrees exactly (997) via the last-reached-ASN method. Two of
  three probes false-positived `has_routing_loop` on near-destination
  repeats with stable RTT -- same known heuristic limit documented
  for the AS17828 case, checked directly rather than trusted.
  Backlog: 1035 -> 1033.
- feat(analysis): confirm MP(AS7131, CNMI)->TO(AS38198, Digicel
  Tonga) -- second independent confirmation of the existing GU->TO
  adjacency (AS45355/Digicel Fiji<->AS38198). RIS agrees exactly
  (1,321). New detail: an intermediate hop resolves to AS132528, the
  Telstra-operated Digicel-Australia backbone ASN already confirmed
  at Equinix Sydney in the NC->FJ/AS45355 entry -- a second,
  unrelated measurement finding the same real infrastructure. One
  probe false-positived `has_routing_loop` on a near-destination
  repeat, same known pattern. Backlog: 1033 -> 1029.
- feat(analysis): add MP(AS7131)->FM(AS38875) as a new
  `CandidatePeering` entry -- an unusually fast (9-21ms), genuinely
  regional path crossing Guam IX directly, the first *in-fishbowl*
  IXP crossing this project has recorded. RIS confirms the internal
  FSM sibling relationship crossed there (AS10130<->AS38875/AS139759,
  both siblings list AS10130 as their only neighbor) but not the
  actual AS7131->AS10130 leg itself -- same shape as the existing
  GU->FM MARIIX candidate entry, at a different exchange. Kept as
  candidate per Validation Rule 1. Backlog: 1029 -> 1023.
- feat(analysis): confirm MP(AS7131, CNMI)->WF(AS45879, Orange
  Wallis & Futuna) -- second independent confirmation of the
  existing GU->WF adjacency (AS5511/Opentransit Orange<->AS45879).
  RIS agrees exactly (1,665), via Hurricane Electric directly this
  time rather than the original's Tokyo/IIJ path. Verified the
  "Tokyo" hub still holds by checking AS5511's real PeeringDB
  facility list directly (four Equinix Tokyo DCs, no Sydney
  presence) rather than reusing it on assumption. One probe
  false-positived `has_routing_loop` on a modest, non-climbing RTT
  repeat. Backlog: 1023 -> 1022.
- feat(analysis): confirm MP(AS7131, CNMI)->SB(AS45891, Solomon
  Telekom) -- second independent confirmation of the existing GU->SB
  adjacency (AS139609/SISCC<->AS45891). RIS agrees exactly (1,652),
  via OneQode this time. Crosses a genuinely new named exchange for
  this project: IX Australia Sydney (NSW-IX), distinct from Equinix
  Sydney and MegaIX Sydney already on record. One probe
  false-positived `has_routing_loop`; a transient Atlas API read
  timeout mid-poll resolved on retry. Backlog: 1022 -> 1013.
- Sourced AS7131 toward AS55885 (Niue) -- a fresh MP<->NU pair,
  landing on the existing Niue<->ONATI adjacency, now a fourth
  independent corroboration. Same sibling-ASN basis (AS55943, 1,662,
  exact match), but Telia (AS1299) and Tata (AS6453) both appear for
  this adjacency for the first time. Extended the existing
  `ConfirmedLocalTransit` entry's note rather than duplicating; entry
  count unchanged (11). Backlog: 1013 -> 1011. Notable: the next live
  pick is now sourced from AS9249 (Vanuatu), not AS7131 -- the same
  source-diversification pattern seen once before with AS3605.
- feat(analysis): confirm MP(AS7131, CNMI)->PF(AS55943, ONATI's
  other ASN) -- second independent confirmation of the existing
  GU->PF adjacency (AS3257/GTT<->AS55943). RIS agrees exactly
  (1,657), via Cogent this time. Verified "Tokyo" still holds by
  checking GTT's real PeeringDB facility list (genuine Tokyo and
  Sydney presence) before reusing it. One probe false-positived
  `has_routing_loop` on modest stable-RTT repeats. Backlog:
  1011 -> 1007.
- Sourced AS7131 toward AS132486 (Kiribati) -- a fresh MP<->KI pair,
  landing on the well-established Kiribati Starlink-chain pattern
  (AS7578/GSL -> AS14593/Starlink -> AS154100/BNL Tarawa), now a
  third independent reproduction after FSM and Guam. Identical exact
  RIS match (362). Extended the existing `ConfirmedLocalTransit`
  entry's note rather than duplicating; entry count unchanged (11).
  One of three probes was a probe-specific dead end. Backlog:
  1007 -> 1006.
- Sourced AS7131 toward AS134783 (a distinct Kiribati ASN, ATHKL) --
  a fresh MP<->KI pair, same Australia/Starlink chain shape but a
  different, already-separately-confirmed adjacency than AS132486
  (AS154100/BNL Tarawa<->AS134783, exact RIS match 1,392, not 362).
  Second independent corroboration of this specific adjacency (after
  Guam). Extended the existing `ConfirmedLocalTransit` entry's note
  rather than duplicating; entry count unchanged (11). Backlog:
  1006 -> 1005.
- feat(analysis): confirm MP(AS7131, CNMI)->CK(AS152093, VakaNet) --
  second independent confirmation of the existing GU->CK adjacency
  (AS9507/NextHop<->AS152093). RIS agrees exactly (335). All 3 probes
  cross BBIX Tokyo directly this time, an even stronger confirmation
  than the original's crossing. One probe false-positived
  `has_routing_loop` on a modest stable-RTT repeat. Backlog:
  1005 -> 1004.
- Sourced AS7131 toward AS154100 (BNL Tarawa itself, targeted
  directly rather than a downstream customer) -- a fresh MP<->KI
  pair. 2 of 3 probes resolve cleanly to AS14593 (Starlink) as the
  literal last-reached ASN, identical RIS match (361) to the
  existing "sharpest, most direct" GU-sourced confirmation. Third
  distinct source (CNMI, after Guam) for this specific direct
  relationship. Extended that entry's paragraph rather than
  duplicating; entry count unchanged (11). Backlog: 1004 -> 1003.
- Sourced AS9249 (Telecom Vanuatu) toward AS9471 (ONATI, French
  Polynesia) -- the first firing genuinely sourced from AS9249,
  source diversification having fully shifted off AS7131. Only 1
  connected probe available. First address dead-ended; retry reached
  the target and landed on the same shape already established for
  the earlier AS7131->AS9471 tranche: AS6939 (Hurricane Electric)
  immediately upstream, RIS disagrees, AS9471's fishbowl neighbor
  list only shows its ONATI sibling. Not filed in any dataclass, per
  that precedent. Backlog: 1003 -> 1001.
- feat(analysis): confirm VU(AS9249)->AS(AS9751) via Equinix San
  Jose -- second independent confirmation of the existing
  MP->AS/AS9751 adjacency (Wave Broadband). RIS agrees exactly
  (267). Improves on the original entry: this traceroute directly
  crosses a real named exchange (Equinix San Jose) where the
  original found no crossing at all. Added a fourth external hub
  (San Jose) to `economy_coordinates.EXTERNAL_HUB_LATLON`. Backlog:
  1001 -> 999.
- Sourced AS9249 toward AS10131 (Telecom Cook Islands) -- a fresh
  VU<->CK pair, landing on the well-established ONATI<->Cook-Islands
  sibling-ASN adjacency, now a fourth independent reinforcement
  (after ONATI's own vantage point, Guam, and CNMI). Extended the
  existing `ConfirmedLocalTransit` entry's note rather than
  duplicating; entry count unchanged (11). Backlog: 999 -> 997.
- Sourced AS9249 toward AS17893 (Palau NCC) -- a fresh VU<->PW pair,
  landing on this project's very first confirmed finding
  (AS174/Cogent<->AS17893), now confirmed from a genuinely different
  source economy (Vanuatu) for the first time, not just a repeat
  from Guam. Identical exact RIS match (1,333), via a different path
  into Cogent (NTT instead of IIJ/Tokyo). Extended the existing
  `ConfirmedDetour` entry's note rather than duplicating; entry
  count unchanged (31). Backlog: 997 -> 995.
- feat(analysis): add VU(AS9249)->WS(AS17993) CandidatePeering --
  Vodafone Fiji directly reaching Vodafone Samoa, a clean contiguous
  traceroute crossing a real Equinix Sydney presence (AS17993 as the
  IXP member, confirmed via PeeringDB netixlan). RIS disagrees from
  both sides despite both ends being in-fishbowl. Holder-name
  confirmed as the same corporate brand on both ends, the same shape
  as the established Digicel Fiji<->Digicel Tonga intra-corporate
  pattern -- a well-motivated candidate, kept per Validation Rule 1.
  Backlog: 995 -> 988.
