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
