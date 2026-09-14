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
