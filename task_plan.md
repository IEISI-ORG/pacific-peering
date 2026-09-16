# Task Plan: Pacific Peering

## Goal
Build a system that discovers every active ASN homed in Melanesia, Polynesia, and Micronesia (APNIC Oceania economies, excluding Australia/NZ, excluding Hawaii, including Guam), maps their full AS-paths and IXP peering using RIS data and RIPE Atlas traceroutes, runs on a recurring schedule, and produces analysis, visualizations, and reports identifying sub-optimal transpacific routing.

## Scope Notes (from GOALS.md)
- Region: APNIC-covered Oceania economies minus AU/NZ, minus Hawaii, plus Guam.
- Core data sources: public RIS (RIPE RIS / RouteViews) for ASPATHs, RIPE Atlas for active traceroute measurement.
- Core analysis: peering relationships, IXP routing, sub-optimal transpacific routing detected via triangulation of sources/destinations.
- Cadence: recurring, either 7-day or monthly resolution, ongoing (not a one-shot run).
- Outputs: ASCII + HTML reports, visualizations, a conference/NOG presentation skeleton, full docs, changelog, README, CC-BY-SA-NC license (commercial use paid), buymeacoffee donation link.

## Phases

### P0 — Foundation (must handle now)
- [x] Phase 0a: Repo scaffolding — directory layout (`src/`, `data/`, `outputs/`, `docs/`), `pyproject.toml` via `uv`, `.gitignore`, `LICENSE` (CC-BY-SA-NC + commercial-use clause), `README.md` skeleton, buymeacoffee link placeholder, `CHANGELOG.md` seeded.
- [x] Phase 0b: Region/ASN discovery — enumerate APNIC economies in scope (Melanesia/Polynesia/Micronesia + Guam, excl Hawaii/AU/NZ), pull delegated-stats + PeeringDB/RDAP data, produce a canonical ASN registry file (economy -> ASNs).
- [x] Phase 0c: RIS ingestion groundwork — pick source (RIPE RIS RIBs/updates vs RouteViews vs RIPEstat API), write minimal downloader + parser proving we can pull ASPATHs for one in-scope ASN end-to-end.

### P1 — Core pipeline (this pass)
- [x] Phase 1a: Full RIS analysis module — build the "fish bowl" view: all observed ASPATHs touching in-scope ASNs, peering-relationship inference, IXP-hop detection.
- [x] Phase 1b: RIPE Atlas measurement code — create/manage traceroute measurements between relevant probes/anchors for in-scope AS pairs; store raw + parsed results.
- [x] Phase 1c: Scheduling/automation — recurring job (7-day or monthly) that re-runs discovery + RIS pull + Atlas measurements, versions each run's output directory, is safe to re-run/resume. **Local orchestrator done and idempotent. Project owner explicitly chose manual-only for now over a GitHub Actions cron — revisit real scheduling later, not a gap to fill silently.**
- [ ] Phase 1d: Sub-optimal routing analysis — triangulate source/destination pairs to flag transpacific paths that detour outside the region (e.g., via US/AU) when a more direct path should exist. **Settled premise, per the project owner: peering that lands outside the study area — AU, NZ, or the US — is not optimal, by definition.** That is not a hypothesis this project tests; it's a given. What's still open is establishing the specific instances and degree, which is what Phase 1b's Atlas traceroutes are for (see Fish Bowl Limitations). Candidate instances already surfaced from Phase 1a's `fishbowl.json`, awaiting Atlas corroboration on the specifics:
  - **Australia as the de facto peering hub — ✅ ground-truthed by Atlas (Phase 1b).** Equinix Sydney + MegaIX Sydney together account for the single largest IXP cluster in the whole dataset (9 + 6 = 15 memberships), reaching more distinct in-scope economies (Cook Islands, Fiji, French Polynesia, New Caledonia, PNG, Samoa, Tonga) than any actual in-region IXP. Phase 1b's first live traceroute (Guam -> PNG, measurement 210901499) confirmed this directly: all 3 probes' paths hit `45.127.172.31` — the exact IP recorded for AS17828's Equinix Sydney port — before reaching PNG DataCo's own network. Still to do: repeat across more AS pairs/economies to establish how widespread this is, not just that it happens at least once.
  - **AS24013 (Solomon Islands) — anycast/hosting location vs. real network location, compounded by a confirmed PeeringDB gap.** PeeringDB shows 7 IXP memberships, all in Germany (DE-CIX/LOCIX Frankfurt, Düsseldorf, Hamburg, Munich) plus one in Sydney, none in the Pacific. Per the project owner: this is a known pattern where anycast/hosting presence (e.g. a CDN or DNS anycast node advertised from Frankfurt) gets recorded as "the network's" IXP membership, when it has nothing to do with where that network's actual Solomon Islands traffic transits — a caution about *attributing* the finding correctly, not about the AU/NZ/US-is-suboptimal premise. **Compounding factor, confirmed by the project owner: the Solomon Islands has a real, working local IXP that PeeringDB doesn't list at all** — so "AS24013 shows zero in-region IXP presence" was never a clean read of reality; it's an artifact of PeeringDB's incompleteness on top of the anycast/hosting issue. ✅ **Identified and recorded (see Rule 5 resolution below): Solomon Islands Internet Exchange Peering Point (SIIXP), operated by TCSI (the Solomon Islands telecom regulator).** Still needed: an Atlas traceroute check to sort out what's actually happening with AS24013 specifically — blocked on Solomon Islands having zero connected Atlas probes (Phase 1b finding), so this needs either a new probe in-country or a different corroboration method.
  - **Engineering follow-through from the Validation Rules above**: (a) build the actual ASN-to-ASN adjacency maps from Phase 1a's RIS neighbor data and Phase 1b's Atlas results, keeping only edges both sources agree on; (b) add a latency/hop-count feasibility check before accepting any such edge; (c) run inbound traceroutes (external vantage points -> each in-scope ASN), not just the outbound direction done so far; (d) use ASN-to-ASN traceroutes to hunt for peering relationships absent from both RIS and PeeringDB, and to spot-check existing PeeringDB IXP claims against real hop evidence; (e) start a supplementary list of known-but-PeeringDB-unlisted regional IXPs, seeded with the Solomon Islands one.
- [x] Phase 1e: Visualization — pathway maps (geographic + AS-graph) highlighting missing/indirect routes.
- [x] Phase 1f: Reporting — generate ASCII report and HTML report from the same underlying analysis output, per run.

### P2 — Polish and dissemination (can wait)
- [x] Phase 2a: Presentation skeleton — slide/outline template for NOGs and conferences, pulling from the latest report.
- [x] Phase 2b: Documentation pass — docstrings/module docs for all code, comprehensive README fleshed out beyond skeleton.
- [ ] Phase 2c: Changelog discipline — keep `CHANGELOG.md` narrating the project's journey as phases land (ongoing, not a single task).
- [ ] Phase 2d: "Tube map" style diagram — a London-Underground-style schematic of the confirmed corridors (economies as stations, confirmed/candidate relationships as lines, external detour hubs as interchange stations), as an alternative/companion to the geographic SVG map for presentation use. Requested by the project owner; not yet scoped (renderer choice, whether it's auto-generated from the same dataclasses or hand-laid-out).

## Fish Bowl Limitations (why the project calls it that)
RIS + PeeringDB data is an outside-looking-in view: we can see AS-paths as reported by RIS's vantage points and IXP memberships as self-reported to PeeringDB, but we can't get in the bowl — no visibility into a network's actual internal forwarding decisions, and no guarantee that what we see from outside matches what really happens to a given packet. Concretely:
- RIS-observed "neighbors" (Phase 1a) are only the AS-path adjacency seen by whichever RIS collector peers happened to have a route — vantage-point bias, not ground truth on real traffic paths.
- PeeringDB `netixlan` membership records where a network's *equipment* sits at an IXP, which is not necessarily where that network's *actual regional traffic* transits — see the AS24013 case below.
- **This is exactly why Phase 1b (RIPE Atlas traceroutes) is required, not optional**: it's the only way to ground-truth what the RIS/PeeringDB "fish bowl" view suggests. Neither source alone is sufficient; the project's sub-optimal-routing conclusions (Phase 1d) should be built on triangulation between both, not RIS/PeeringDB alone.

**Note on what is and isn't in question**: per the project owner, peering that lands outside the study area — in AU, NZ, or the US — is *not optimal* by definition; that premise is settled, not a hypothesis this project is testing. What Atlas corroboration is for is establishing the specific instances and degree (which paths, how much traffic, how consistently) so the report has real evidence behind the premise, not to re-litigate whether out-of-region peering counts as sub-optimal in the first place.

## Validation Rules (how a topology claim earns its way into a report)
Set by the project owner after Phase 1b's first live result. These rules govern every future ASN-to-ASN or IXP claim, not just the ones already found:

1. **No topology assumption stands on one source alone.** An ASN-to-ASN adjacency only counts as established once *both* RIS (Phase 1a neighbor inference) and an Atlas traceroute agree on it. RIS-only or Atlas-only evidence is a lead to chase, not a finding to report.
2. **Even a two-source match must pass a feasibility check.** Latency and hop count have to be physically plausible for the claimed path (e.g. an RTT too low for the implied geographic distance, or a hop count inconsistent with the claimed route, invalidates the inference regardless of source agreement) — this is the check that catches things like anycast/CDN artifacts (the AS24013 case) before they're mistaken for the network's real path.
3. **The fish bowl needs both directions.** Everything run so far is outbound (a Pacific-hosted or Pacific-country probe tracing *out* to a target). The metaphor also requires **inbound** traceroutes: from vantage points *outside* the Pacific, tracing *in* to each in-scope ASN — this is the only way to see how external traffic actually arrives, which may differ from how it looks going the other way.
4. **ASN-to-ASN traceroutes (both directions, wherever probes allow) are the discovery mechanism for hidden peering** — relationships that never surface in RIS-observed neighbor counts or in PeeringDB at all — and are also the cross-check for every PeeringDB IXP membership claim (does a traceroute actually show a hop inside that IXP's known peering-LAN prefix, the way 45.127.172.31 did for AS17828/Equinix Sydney).
5. **PeeringDB is a lead, never ground truth.** It can be wrong, stale, or simply missing data. Confirmed concrete case, per the project owner: **the Solomon Islands has a working local IXP that is not listed in PeeringDB at all.** This means the earlier AS24013 read (Phase 1a/1d: "no in-region IXP presence, only Germany") is incomplete, not necessarily wrong — a real local exchange can exist entirely outside PeeringDB's data. Practical implication: this project needs its own supplementary list of known-but-unlisted regional IXPs (starting with the Solomons one) rather than treating PeeringDB's absence-of-a-record as absence-of-a-fact.

## Key Questions
1. ~~RIS data source~~ — resolved: RIPEstat API.
2. ~~Atlas credit budget~~ — resolved (after a false start): the first key in `secrets.yaml` showed a 0 balance (contradicting the ~100M figure given earlier) — turned out to be the wrong key/account. Corrected key confirmed via live `/api/v2/credits/` check: **current_balance: 95,635,574**. Still open: which probes/anchors exist in-region vs need requesting — partially answered by Phase 1b's coverage check (5 of 20 economies have zero connected probes; see Status).
3. ~~Exact economy list~~ — resolved: standard APNIC/UN geoscheme list.
4. ~~Update cadence~~ — resolved: monthly default, configurable.

## Decisions Made
- Using `planning-with-files` for persistent tracking given the project's multi-phase, ongoing (not one-shot) nature.
- Following user's default Python stack preferences (uv for packages) where they don't conflict with this being a data/network-research project rather than an ML project (Hydra/Trainer defaults are likely not relevant here).
- RIS/ASPATH data source: **RIPEstat API** — chosen for lower integration cost over raw MRT dumps from RIS/RouteViews. Revisit if RIPEstat rate limits or data gaps block the "fish bowl" analysis.
- Economy/ASN scope: standard APNIC/UN geoscheme lists for Melanesia, Polynesia, Micronesia, **plus Guam, minus Hawaii/AU/NZ**. Working list: Fiji, PNG, Solomon Islands, Vanuatu, New Caledonia, Samoa, Tonga, French Polynesia, Guam, FSM, Palau, Marshall Islands, Kiribati, Nauru, Tuvalu, Cook Islands, Niue, American Samoa, Wallis and Futuna, N. Mariana Islands. ASNs per economy to be derived from APNIC delegated-stats/PeeringDB in Phase 0b.
- Default update cadence: **monthly**, implemented as a configurable parameter (not hardcoded) so it can be tightened to weekly later without a redesign.
- **External carriers can have specific in-region facilities without the whole carrier being in-fishbowl.** Per the project owner: OneQode (AS140627, registered AU) has a confirmed real facility in Guam (PTR-record-verified "RTI Guam GNC"); traceroute hops matching that specific facility count as in-fishbowl, but OneQode's other PoPs (Sydney, Tokyo, LA, Hong Kong, Singapore) don't. Implemented as a new hand-curated registry, `analysis/regional_carrier_facilities.py`, evidence-gated the same way as `ixp_lan_registry.py` (see the full governance-decision writeup further down this file).

## Working Agreements (apply for the rest of this project, including inside the `/loop`)
- **Commit and push after each major change** — not just when explicitly asked in the moment. A "major change" is a completed unit of work (a new module, a real finding, a plan/methodology update worth preserving), not every intermediate edit within one.
- **Never leak credentials or private data.** Never read `secrets.yaml`'s value into a response, never print/log the Atlas API key, never let it end up in a commit — verify `git status`/`git diff` before every commit if there's any chance a secret-bearing file changed.
- **When data looks strange or routing is doing something unusual, consult the project owner** — including inside an unattended `/loop` firing, not just when they're actively chatting. Investigate first (this project's own established discipline: check the raw hop data, cross-check via RIPEstat/WHOIS/bgp.tools, don't accept `contiguous: false` or a surprising number at face value), but don't resolve a genuinely anomalous or ambiguous result purely on my own judgment and quietly move to the next tranche -- surface it plainly (in the response if live, or clearly flagged in task_plan.md/CHANGELOG.md for the owner to see on return if not) rather than let a loop firing paper over something that needs a domain expert's read.
- **Corridor selection is now systematic, not ad-hoc.** Per the project owner's explicit direction: maintain a real todo list of untested corridors (`analysis/corridor_backlog.py`, human-readable output at `corridor_backlog.md`) rather than re-deriving the candidate space from memory each hourly tranche. The hourly `/loop` job (currently `33ab3487`) pulls its corridor via `pick_next_corridor()`/`corridor_backlog.md` and calls `mark_corridor_tested()` on the pair afterward regardless of outcome. A separate 8-hourly job (`db93405c`, `17 */8 * * *`) regenerates the backlog via `pacific-peering-corridor-backlog`, diffing against the last snapshot to flag genuinely **new** probes and **new** RIS-observed relationships as high-priority candidates -- the "keep track of new probes and RIS changes" standing order, made concrete rather than left as a vague intention. `tested_pairs.json`/`corridor_backlog_snapshot.json` (both `data/analysis/`, gitignored) are the persisted state; `corridor_backlog.md` (repo root, committed) is the human-visible artifact.

## Errors Encountered
(none yet)

## Secrets
- `secrets.yaml` (repo root) holds the RIPE Atlas API key. Added to `.gitignore` (`secrets.yaml` + `*.secret.yaml`), confirmed untracked. Never commit it or echo its contents. Loaded via `atlas/secrets.py` (`yaml.safe_load`). Live-verified balance: **95,635,574 credits** (see Key Questions #2 for the account-mismatch history — the figure quoted here was wrong once already, so treat this line, not memory, as current).

## Status
**Quick orientation (read this first; full log below):** P0 and Phase 1a/1b are done and committed. Active work is Phase 1d's validation build-out (see Validation Rules + Phase 1d's "Engineering follow-through" bullet) — triangulated RIS+Atlas adjacency maps, feasibility checks, inbound traceroutes, hidden-peering discovery, PeeringDB cross-checks, and a supplementary unlisted-IXP list. Phase 1c (scheduling/automation) is queued behind that, not urgent yet. This file is being worked via a self-paced `/loop` (small tranches per iteration) — re-read this orientation line and the last 1-2 Status entries before starting each tranche, rather than assuming context carries over.

**Phase 0b complete.** Added `discovery/economies.py` (canonical 20-economy list with subregion tags), `discovery/apnic_stats.py` (downloads + parses APNIC's `delegated-apnic-extended-latest` file), `discovery/registry.py` (builds `data/asn_registry.json`, entry point `pacific-peering-discover-asns`). Ran end-to-end: **163 ASNs across 20 economies**, all economies non-empty (PNG=39 largest, Niue/Wallis&Futuna=1 smallest).

Known limitation (by design for now, not a bug): this registry is APNIC-delegation-based only — it reflects which ASNs are *directly delegated* to each economy, not which are *actively announcing routes* or *homed* there in practice (some economies use ASNs delegated elsewhere, e.g. via upstream/RIR transfer). Cross-checking against live RIS announcements (Phase 1a) and PeeringDB org data is the natural follow-up, not required to unblock later phases.

Not yet added: PeeringDB enrichment (org names, IXP presence) — deferred; the delegated-stats pull alone was enough to produce a usable registry, and pulling PeeringDB now would be scope creep ahead of Phase 1a where it's actually needed.

**Phase 0c complete.** Added `ris/ripestat.py` (`fetch_originated_prefixes` via RIPEstat's `ris-prefixes` call, `fetch_bgp_state` via `bgp-state`, `fetch_aspaths_for_asn` chaining the two) and `ris/smoketest.py` (loads `data/asn_registry.json`, picks the first in-scope ASN, pulls live AS-paths), entry point `pacific-peering-ris-smoketest`.

Ran live end-to-end: AS9751 (American Samoa) → 3 originated prefixes → **993 AS-path observations** from RIS vantage points, each path correctly terminating in AS9751. Confirms the "fish bowl" data flow (registry → ASN → prefixes → AS-paths) works over the public RIPEstat API with no auth needed.

**P0 (Foundation) is now fully complete** — repo scaffolded, ASN registry built, RIS pipeline proven end-to-end. All commits still pending (user asked to commit later).

**Phase 1a complete.** Added:
- `ris/bulk.py` — scales the Phase 0c single-ASN proof to all 163 registry ASNs, with a bounded thread pool (8 workers) and per-ASN disk caching (`data/ris/raw/<asn>.json`) so re-runs skip already-fetched ASNs by default.
- `analysis/peering.py` — infers observed neighbors per ASN from AS-path adjacency (collapsing prepending), not a full relationship-classification algorithm (that's out of scope for now).
- `discovery/peeringdb.py` + `analysis/ixp.py` — real IXP membership per ASN via PeeringDB's `netixlan`/`ix` endpoints (batched `asn__in` queries). Chose this over trying to detect IXP hops from AS-paths, since route-server ASNs generally don't appear in paths — PeeringDB membership is the actually-reliable signal.
- `analysis/fishbowl.py` — orchestrates all of the above into `data/analysis/fishbowl.json` (per-ASN: economy, path/prefix counts, observed neighbors, IXP memberships). Entry point `pacific-peering-fishbowl`.

Ran end-to-end against the full registry (~84s wall clock): **163 ASNs, 119,342 AS-path observations, 124 ASNs with ≥1 observed neighbor, 38 ASNs with ≥1 real IXP membership** (e.g. AS7131/Northern Mariana Islands leans on AS6939 Hurricane Electric for 78% of observed paths; regional IXPs found include MARIIX, Guam IX, PNG Neutral IX, CAN'L IX, VIX.VU).

Deliberate scope limit: capped at 5 prefixes/ASN to bound load on the public RIPEstat API for this pass — full-prefix coverage is a refinement, not required to prove the pipeline. `data/` (raw cache + fishbowl.json, ~14MB) stays gitignored as generated data.

IXP-membership breakdown (38 ASNs, 29 distinct IXPs) surfaced two candidate findings for Phase 1d — see that phase's entry for detail: the Sydney IXP cluster outweighing any in-region exchange, and AS24013's Germany-only IXP records (likely anycast/hosting presence, not real network location — flagged by the project owner as a worked example of why Atlas ground-truth is needed). See "Fish Bowl Limitations" above for why neither of these should be reported as conclusions yet.

**Phase 1b complete**, including a live end-to-end proof. Added:
- `atlas/secrets.py` — loads the API key from `secrets.yaml` (`ripe_atlas_key`), never logged.
- `atlas/client.py` — `create_traceroute_measurement` (one-off traceroutes, generic `source_type`/`source_value` probe selector), `wait_for_results` (polls until terminal status), `parse_traceroute_results`.
- `atlas/targets.py` — picks a destination IP by reusing Phase 1a's cached RIS prefixes (no extra RIPEstat calls needed).
- `atlas/probes.py` — checks connected-probe counts per in-scope economy; `pick_best_covered_economy` for automatic source selection.
- `atlas/smoketest.py` — end-to-end one-off traceroute test. Entry points `pacific-peering-atlas-coverage` and `pacific-peering-atlas-smoketest`.

**Real, durable finding, independent of the credit false-start below**: Atlas probe coverage in-region is very sparse. `pacific-peering-atlas-coverage` (`data/atlas/probe_coverage.json`) shows **5 of 20 in-scope economies have zero connected Atlas probes** (American Samoa, Nauru, Solomon Islands, Wallis & Futuna, Samoa), and most of the rest have only 1-2. Fiji specifically: every historic probe on AS4638 is Abandoned/Disconnected/Written Off; its only connected probe today sits on a different, unrelated ASN. This is why the client had to support country-based probe selection (`source_type="country"`) as a fallback — ASN-based selection (the original design) hard-fails with "Your selected ASN is not covered by our network" for most in-scope ASNs. This coverage gap belongs in the final report as its own limitation, and answers part of Key Question 2 (which economies would need new probes requested, if the project wants better coverage later).

**Credit false-start (resolved)**: the key originally in `secrets.yaml` showed a 0 balance, not the ~100M reported earlier, and belonged to an account with 4,294 prior measurements including an apparently-unrelated recurring RPKI-monitoring workload — turned out to be the wrong account/key. Neither of the two failed attempts on that key created or charged anything. The project owner corrected the key; live-verified balance on the corrected key is now **95,635,574**.

**First live traceroute — first fully ground-truthed finding.** Measurement 210901499: 3 probes in Guam (source, auto-selected as best-covered economy) → a PNG DataCo (AS17828) address (103.49.207.1). All three probes' paths converge onto Hurricane Electric (AS6939) backbone addresses (184.104.x.x) and then hit **45.127.172.31 before reaching PNG DataCo's own address space (202.165.198.250)**. `45.127.172.31` is the *exact* IP Phase 1a's PeeringDB data recorded for AS17828's Equinix Sydney port. This is a real traceroute confirming, independently of RIS/PeeringDB, that Guam-to-PNG traffic physically detours through Sydney — the first Phase 1d candidate finding to graduate from "fish bowl signal" to "ground-truthed via Atlas," exactly the corroboration loop the Fish Bowl Limitations section calls for. Raw + parsed results saved to `data/atlas/raw/210901499.json` / `data/atlas/parsed/210901499.json`.

~~Observed oddity (not yet root-caused, not blocking)~~ — **root-caused in loop tranche 3, correcting the record: this was never a propagation-delay fluke.** The first `pacific-peering-atlas-smoketest` run failed because its description string contained a `->` arrow, which Atlas's API rejects outright ("Text contains disallowed characters") — confirmed by direct A/B testing (`"arrow test A -> B"` → 400; `"plain no special chars test"` → 201, same target, same call). My retry succeeded only because I happened to type a plain debug string with no arrow, not because of timing. Fixed properly this tranche — see below.

Next: Phase 1c — scheduling/automation (recurring discovery + RIS + Atlas runs), or extend Phase 1b's one-ASN-pair proof into a real AS-pair measurement campaign across the registry.

---

**[Loop tranche 1 — plan review + first triangulation result.]** Working via a self-paced hourly `/loop` (job `551adf11`) per the project owner's instruction: "over the plan and then when finished start gathering data and validating the methods, iterate slowly with small tranches of work each loop."

*Plan review*: fixed a stale line in `## Secrets` (was still citing the old wrong ~100M credit figure), added the "Quick orientation" pointer at the top of this Status section so later tranches don't have to re-read the whole log to get oriented.

*Solomon Islands IXP claim — checked, not yet confirmed.* Searched for the working local IXP the project owner mentioned (not listed on PeeringDB). Found: (a) a Medium post on this exact topic by the project owner's own account, but Medium returned 403 to automated fetch — couldn't read it; (b) **PeeringDB's own `/api/ix?country=SB` returns zero results, and PCH's independent global IXP directory also lists Solomon Islands under "countries without IXPs."** Two independent public catalogs, zero corroboration. This doesn't mean the project owner is wrong — an informal or very new exchange could easily predate both catalogs — but per the Validation Rules just written, this needs the project owner's specifics (name, location, participant ASNs) rather than a fabricated entry. **Open item, needs project owner input**: what is the Solomon Islands IXP called, and can the project owner link/describe it (or fix the Medium link if that's the source)?

*Built: the first real triangulation checker (Validation Rule 1, in code).* Added `ris.ripestat.resolve_ip_to_asns` (RIPEstat's `network-info` call — confirmed it correctly resolves ordinary hops, e.g. `184.104.192.252` -> AS6939 Hurricane Electric, `202.165.198.250` -> AS17828 PNG DataCo; confirmed it returns *no* ASN for `45.127.172.31`, the Equinix Sydney peering-LAN address from Phase 1b's finding — expected, since IXP fabric addresses are frequently not globally routed, and itself a useful "this hop is probably IXP fabric" signal rather than a failure). Added `analysis/traceroute_topology.py` (`resolve_traceroute_hops`, `extract_as_sequence`, `check_neighbor_agreement`, `analyze_measurement`), entry point `pacific-peering-triangulate`.

**Ran it against Phase 1b's real measurement (210901499, Guam -> PNG DataCo). Result: all 3 probes agree the AS immediately upstream of AS17828 is AS6939 (Hurricane Electric) — and RIS independently observed the exact same adjacency 1,283 times (AS17828's single largest RIS-observed neighbor).** This is the project's first ASN-to-ASN adjacency to satisfy Validation Rule 1 (both RIS and Atlas agree) — a stronger, more specific result than the Sydney-hub finding, since it names the actual upstream AS rather than just the IXP. Saved to `data/analysis/triangulation/210901499.json`.

Not done yet (deliberately left for later tranches, not oversights): Validation Rule 2's latency/hop-count feasibility check (no code yet), Rule 3's inbound-traceroute direction (only outbound tested so far), and Rule 5's supplementary unlisted-IXP list (blocked on the Solomons open item above). Nothing committed this tranche — holding to "only commit when the user explicitly asks," even in loop mode.

---

**[Loop tranche 2 — Validation Rule 2, quantitatively.]** This firing was job `551adf11`'s scheduled hourly run (confirmed via CronList before doing anything — no new scheduling needed, the fixed-interval loop is already active).

*Extended the Atlas parser to capture RTT*: `atlas/client.py`'s `TracerouteHop` now carries `min_rtt_ms` (minimum across a hop's replies — the standard convention, since the minimum sample is closest to pure propagation delay). Backfilled `data/atlas/parsed/210901499.json` from the already-fetched raw JSON (no new Atlas credits spent).

*Built `analysis/feasibility.py`* (Validation Rule 2): `great_circle_km` (haversine), `min_feasible_rtt_ms` (speed-of-light-in-fiber floor, ~2/3 c — a hard physical lower bound, real paths are only ever slower), `check_path_feasibility`, `compare_direct_vs_relay` (checks an observed RTT against both a direct path and a named single-relay detour), `analyze_measurement_feasibility` (applies this to every probe in a stored measurement), entry point `pacific-peering-feasibility`.

**Ran it on measurement 210901499 (Guam -> PNG DataCo) using each probe's last-responding-hop RTT (~219-233ms) against direct Guam->PNG (2,559km) vs. Guam->Sydney->PNG (8,052km):**
- Direct-path physical floor: 25.6ms. Observed RTT is **8.5-9.1x** that floor.
- Via-Sydney-relay physical floor: 80.6ms. Observed RTT is only **2.7-2.9x** that floor.

A real-world fiber path typically runs 1.3-2x its physical floor (equipment, non-great-circle cable routes, processing). ~2.7-2.9x for the Sydney-relay hypothesis is a plausible real-world overhead; ~8.5-9x for the "direct" hypothesis is not — that gap is itself evidence, on top of the exact-IP match from tranche/Phase 1b, that the path is not direct. **Caveat, stated deliberately rather than overclaimed: this is "consistent with, and quantitatively supportive of" the Sydney-detour finding, not proof** — real Pacific submarine cable geography doesn't follow great circles, so some of both ratios reflects real cable-route geography we haven't modeled, not just "detour or not." Saved to `data/analysis/feasibility/210901499.json`.

Validation Rules status: Rule 1 (two-source agreement) ✅ done for one adjacency; Rule 2 (feasibility) ✅ code done, applied once; Rule 3 (inbound direction) and Rule 5 (supplementary IXP list, still blocked on the Solomons specifics) remain for later tranches. Nothing committed yet this tranche — will follow the "commit and push after each major change" working agreement before this turn ends.

---

**[Loop tranche 3 — Validation Rule 3 (inbound direction), plus a real bug found and fixed.]** Confirmed via `CronList` this was job `551adf11`'s scheduled hourly fire before doing anything.

*Built the inbound counterpart to Phase 1b's outbound smoke test.* Refactored `atlas/smoketest.py`: extracted a shared `_fire_and_persist` helper, kept `run_smoketest` (outbound: in-region source, unchanged behavior) and added `run_inbound_smoketest` (source = an external country outside the study region *and* outside AU/NZ — defaults to `US` — targeting an in-scope ASN). New entry point `pacific-peering-atlas-inbound-smoketest`.

*Found and fixed a real bug, not a flaky retry.* The first inbound run failed with a 400. Rather than accept another "must be transient" guess, I did a proper A/B test against the live API: `"arrow test A -> B"` → 400 "Text contains disallowed characters"; `"plain no special chars test"` → 201 (same target, same call). **The `->` arrow in measurement descriptions is what Atlas was rejecting all along — this is also the real explanation for tranche 1's "propagation delay" theory, which was wrong; I've corrected that note above.** Fixed both `run_smoketest` and `run_inbound_smoketest` to use "to" instead of "->", and added a guard in `atlas/client.create_traceroute_measurement` that raises `ValueError` immediately if a description contains `<`/`>`, so this fails loudly and instantly for any future caller instead of a confusing 400 three calls deep.

**Ran the fixed inbound test: US -> AS17828 (measurement 210913838), 2 of 3 requested probes returned in time.** Neither probe's traceroute actually reached a hop that resolved to AS17828 itself (normal — ICMP filtering near a destination is common), which exposed a real gap in `check_neighbor_agreement`: it only compared RIS against the hop *immediately before a resolved target_asn*, so it had nothing to say when the target never resolved at all. Fixed: when the target ASN never appears in the resolved sequence, the checker now compares RIS against the *last ASN the traceroute did reach* — weaker evidence than a direct hit, but still real corroboration, and clearly labeled as such in the output (`note` field).

**With that fix, both inbound probes independently corroborate real RIS-observed neighbors of AS17828 — via two more carriers than the outbound test found:**
- Probe 1016555 (via AS16509, Amazon): reached AS58453 (**China Mobile International**) before going dark — RIS independently observed this exact adjacency 129 times.
- Probe 50972 (via AS6128, AS3356/Lumen): reached AS4637 (**Telstra Global**) before going dark — RIS independently observed this exact adjacency 214 times, AS17828's *second*-largest RIS neighbor.

Re-ran the original outbound measurement (210901499) through the updated checker as a regression check — AS6939/Hurricane Electric result unchanged, confirming the fix didn't break the earlier finding. **AS17828 now has three independently RIS+Atlas-confirmed neighbors (AS6939, AS4637, AS58453), found from three different vantage points across two directions** — the strongest triangulated picture in the project so far. Telstra Global (AS4637) showing up again, this time from the inbound/US direction rather than the outbound/Guam direction, is an independent line of evidence for the Australia-hub finding, not a repeat of the same one.

Validation Rules status update: Rule 3 (inbound direction) ✅ done, with a real result. Rule 5 (supplementary IXP list) still blocked on your Solomon Islands specifics — everything else is now unblocked. Committing and pushing this tranche now, per the working agreement.

---

**[Loop tranche 4 — a real methodology bug, caught by real data, fixed same tranche.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

*Broadened beyond AS17828*: added an optional `source_cc` override to `run_smoketest` so a specific corridor can be tested deliberately instead of always auto-picking the best-covered economy. Ran **New Caledonia -> Fiji** (measurement 210919078, source NC has 5 connected probes, target AS4638/Telecom Fiji): all 3 probes reached the destination.

*Found a real bug in my own triangulation code, not just in the data.* All three probes' paths hit `103.26.68.83` right after leaving New Caledonia — a hop that resolved to *no* ASN via RIPEstat's BGP-based lookup, same as the earlier IXP-fabric pattern. My existing code silently dropped that hop and treated `AS18200` (O.P.T. New Caledonia, the last BGP-resolved ASN before the gap) as if it were directly adjacent to `AS4638` — RIS disagreed (AS4638's only RIS-observed neighbor is AS45349, not AS18200), which I almost logged as "hidden peering discovered." **Before accepting that, I checked the IP directly against PeeringDB's `netixlan` table (`?ipaddr4=103.26.68.83`) and it isn't unresolved at all — it belongs to AS45349, "Telecom Fiji Ltd," registered at MegaIX Sydney.** RIS's actual neighbor and this IP's actual owner are the *same ASN*. My code's "last resolved ASN before an unresolved gap = adjacent to target" logic was wrong; the true intermediate hop was knowable, just not from the BGP-only resolver I'd built.

**Fixed properly, not patched over:**
- `discovery/peeringdb.py`: added `resolve_ip_via_netixlan` (exact-IP lookup against PeeringDB's `netixlan` table) as a fallback when RIPEstat's BGP-based resolution returns nothing — with retry-with-backoff on 429 (PeeringDB rate-limited us mid-tranche from all the ad-hoc lookups; it now degrades to "unresolved" after 2 retries instead of crashing the whole analysis).
- `analysis/traceroute_topology.py`: `HopResolution` now records *which* resolver worked (`"bgp"` or `"peeringdb_netixlan"`). `extract_as_sequence` now tracks **contiguity** — whether a resolved ASN is truly hop-adjacent to the previous one, or separated by 1+ unresolved hops — instead of silently collapsing gaps. `check_neighbor_agreement` now reports `contiguous` and refuses to imply direct adjacency across a gap; when a gap exists, it says so explicitly instead of asserting a specific (potentially wrong) neighbor.

**Result, once correctly resolved: a second real ASN-to-ASN adjacency confirmed by both RIS and Atlas, via a second corridor and a second Sydney exchange.** Probe 33674's path: NC -> AS18200 (O.P.T. NC) -> [MegaIX Sydney fabric, resolved via PeeringDB] -> **AS45349 (Telecom Fiji Ltd)** -> AS4638. RIS independently lists AS45349 as AS4638's *only* observed neighbor (1,669 observations) — full agreement. The other two probes hit PeeringDB's rate limit on the same lookup and correctly came back as "gap, not confirmed" rather than a false positive — the fix working exactly as intended even when the enrichment step fails.

Regression check: re-ran both earlier measurements (210901499, 210913838) through the updated checker — all three original findings (AS6939, AS4637, AS58453) unchanged, and 210901499's final hop now *also* resolves cleanly via the netixlan fallback (to AS17828 itself), strengthening rather than changing that result.

**Takeaway for how this project should read its own traceroute analysis going forward: any "hidden peering" claim from `check_neighbor_agreement` must have `contiguous: true` before it means anything.** A `false` there isn't evidence of hidden peering — it's evidence the resolver couldn't see far enough, exactly as it should be labeled per the Validation Rules' "no topology claim on one source alone" spirit, now extended to "no topology claim across an unresolved gap either."

Not done yet: PeeringDB's rate limiting under repeated ad-hoc lookups suggests Phase 1c's eventual bulk/recurring analysis should cache netixlan lookups locally rather than re-querying per hop per run — noted for that phase, not fixed now (would be premature given no bulk campaign exists yet). Rule 5 (Solomon Islands IXP) still the only blocked item. Committing and pushing this tranche now.

---

**[Loop tranche 5 — closed out tranche 4's own TODO: a persistent IP-resolution cache.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire. Deliberately lighter tranche than 3/4 (no new Atlas measurements, no new credits spent) — infrastructure, not a new finding.

Added `analysis/ip_resolution_cache.py` (`IpResolutionCache`, JSON-backed, keyed by IP) and wired it into `traceroute_topology._resolve_address`/`resolve_traceroute_hops`: both positive *and negative* resolutions are cached, since a confirmed-unresolvable address (private/CGNAT) getting re-queried forever is as wasteful as re-resolving a real one.

Verified by deleting the cache and re-running all three existing measurements (210901499, 210913838, 210919078) end-to-end (~87s cold). Results: all prior findings held, and **210919078 (NC -> Fiji) actually improved** — all 3 probes now agree on AS45349 (previously only 1 of 3 resolved before hitting PeeringDB's rate limit in tranche 4). Correctly still reports `contiguous: false` for that adjacency though — there's a genuine second unresolved gap between AS45349 and AS4638 itself (the `202.137.178.x` hops), so even with RIS agreeing on AS45349, the checker won't claim proven direct adjacency. That's the gap-tracking from tranche 4 doing exactly its job: agreement with RIS plus a resolved intermediate ASN is still not the same as a fully contiguous, gap-free hop chain, and the output doesn't blur that distinction.

Cache now holds 63 IPs (43 resolved, 20 confirmed-unresolved) from a single cold run across 3 measurements — small, but already saves real re-querying for any future measurement that reuses common backbone/IXP addresses (which, per the findings so far, is most of them — AS6939, Sydney IXP fabric, etc. keep recurring).

Rule 5 (Solomon Islands IXP) still the only blocked item. Committing and pushing this tranche now.

---

**Rule 5 resolved (outside the loop — the project owner supplied the source directly).** Owner provided https://www.tcsi.org.sb/index.php/about/commissioner-s-welcome, confirming the exchange live. Fetched and checked before recording anything: the page itself names it **Solomon Islands Internet Exchange Peering Point (SIIXP)**, operated by **TCSI (Telecommunications Commission Solomon Islands)**, established to "complement the submarine cable and allow local content caching." Being precise about what the source actually says vs. what's being taken on the owner's authority: the page's own language describes TCSI *establishing* SIIXP and appears to date from ~2019 — it documents the establishment effort, not a today's-date live-status confirmation. **The live confirmation is the project owner's first-hand knowledge, recorded as such, not inferred from the page's wording** (consistent with the "treat this user's domain claims as credible" memory guidance, but the distinction is still worth keeping straight in the record).

Added `discovery/supplementary_ixps.py` (`SUPPLEMENTARY_IXPS`, `SupplementaryIxp` dataclass) — this project's own record for IXPs confirmed real but absent/incomplete in PeeringDB, seeded with SIIXP. Not yet known: specific participant ASNs or exact location — both need either an Atlas probe actually located in the Solomon Islands (currently zero connected, per Phase 1b) or direct outreach to TCSI; noted in the entry rather than guessed.

**Validation Rules 1 through 5 all now have working code and at least one real result or entry.** No validation-rule item remains blocked. Phase 1d's engineering follow-through list (task_plan.md, Phase 1d bullet) is essentially done for a first pass; next real decision is whether to broaden the AS-pair sample further, move to Phase 1c (scheduling/automation), or start Phase 1e/1f (visualization/reporting) to make the accumulated findings legible outside this plan file.

## Next Tranche, Specified: IXP LAN Subnet Registry (queued by the project owner)
Per the project owner: it will be prudent to record IXP LAN subnets themselves (not just individual member IPs) so any traceroute hop landing in one can be clearly classified as "this is a peering/IXP crossing," even when the exact member ASN can't be pinned down. Checked feasibility before recording this as a plan (not just an idea): **PeeringDB's `ixpfx` endpoint gives exactly this** — confirmed live, e.g. `ix_id=780` (MegaIX Sydney) -> `103.26.68.0/23`, `ix_id=94` (Equinix Sydney) -> `45.127.172.0/22`. Both already-found hop IPs (`103.26.68.83`, `45.127.172.31`) fall cleanly inside their respective exchange's registered LAN prefix.

Design for whichever tranche picks this up:
1. `discovery/peeringdb.py`: add `fetch_ixp_prefixes(ix_ids) -> dict[int, list[str]]` (batched, IPv4 + IPv6 prefixes per `ix_id`, via `ixpfx?ix_id__in=...`).
2. Persist a local registry (`data/analysis/ixp_lan_prefixes.json`), seeded from every IXP already seen in `fishbowl.json`'s IXP memberships (the ~29 distinct exchanges from Phase 1a), with room to grow as more IXPs get discovered.
3. A classifier, e.g. `classify_ixp_fabric(ip) -> {ix_id, ix_name} | None`, checking the IP against every known LAN prefix (`ipaddress.ip_address(ip) in ipaddress.ip_network(prefix)`).
4. Wire into `traceroute_topology`'s hop resolution as a distinct third category, alongside the existing "BGP-resolved ASN" / "PeeringDB netixlan member" tiers: a hop can now be explicitly labeled **"confirmed IXP fabric crossing, exchange known, exact member ASN not"** rather than folding into a bare unresolved gap. This is a real, separate piece of information `HopResolution`/`AsHop` don't currently carry — right now, a hop that's IXP fabric but has no specific netixlan record for that address looks identical to a hop that's just genuinely unresolved/private, which understates what we actually know.
5. **Critical refinement, per the project owner: tag every IXP in the registry with whether it's inside or outside the fishbowl** (i.e., whether the exchange's `country` is one of this project's 20 in-scope economies — cross-reference against `discovery.economies.ECONOMIES_BY_CC`). This isn't a nice-to-have, it's the actual point: an in-region IXP hit (e.g. Fiji-IXP, Suva) is a clean, direct marker of **local peering working as intended**; an out-of-region IXP hit (e.g. Equinix Sydney, MegaIX Sydney — Australia is explicitly out of scope) is a marker of the **out-of-region-detour pattern the whole project exists to document**. The classifier's output should carry this distinction explicitly (e.g. `in_fishbowl: bool` or `region: "in-scope" | "out-of-scope"` alongside `ix_name`) — not left for a human to infer per-exchange every time it comes up in analysis.

Not implemented yet — this entry exists so the next tranche can execute directly without re-deriving the design.

**Project owner flagged a specific record to make sure this covers: https://www.peeringdb.com/ix/3085 (Fiji-IXP, Suva, operated by the Telecommunications Authority of Fiji).** Checked: this one is already in Phase 1a's `fishbowl.json` (3 members — AS38442, AS45349, AS45355, all Fiji) and its netixlan records are public, so the "seed from fishbowl.json" step in the design above already covers it without special-casing. Confirmed its LAN prefix too, ready for when the registry gets built: **103.147.194.0/23**. Worth carrying into the eventual write-up: **AS45349 is a member of both Fiji-IXP (local, Suva) and MegaIX Sydney (per loop tranche 4)** — a real case of a Pacific operator with genuine local peering infrastructure that still also peers remotely in Sydney. Local IXP presence existing doesn't mean all of that operator's peering stays local; both can be true at once.

**Follow-up, per the project owner: https://www.peeringdb.com/net/15380 (AS45349's own PeeringDB `net` record) — worth looking up `net` records directly, not just `netixlan`, for extra context.** Checked, and it's a real upgrade over what Phase 1a captured:
- **`netfac_set` (physical colocation facility presence) is a distinct, stronger signal than IXP membership, and we weren't capturing it at all.** AS45349 has actual equipment in **two Equinix Sydney facilities** (Equinix SY1/SY2 and Equinix SY4) — not just a virtual peering session at a Sydney IXP, real colocated infrastructure. That's a firmer commitment to Sydney than peering alone implies.
- The `net` record's `netixlan_set` confirms **AS45349 sits at three exchanges simultaneously: MegaIX Sydney (`103.26.68.83`), Equinix Sydney (`45.127.172.239` — a different address than AS17828's own Equinix Sydney port, its own separate connection), and Fiji-IXP (`103.147.194.4`, local)**. Two out-of-fishbowl, one in — in one place, more complete than assembling it from separate netixlan calls.
- `irr_as_set: "AS45349:AS-TFL-TRANSIT"` — the "TRANSIT" naming corroborates what was already inferred (this is Telecom Fiji's international/transit-facing ASN, distinct from AS4638's domestic role).
- `info_prefixes4: 150` (vs. AS4638's much smaller footprint) — consistent with AS45349 aggregating more than just Fiji's own address space.

**Added to the queued IXP LAN subnet registry design above: also fetch full `net` records (specifically `netfac_set`) for ASNs of interest, not just `netixlan`, and treat facility presence as a peer signal to IXP membership** — an ASN can be tagged out-of-fishbowl-dependent via colocation even in cases where it has no out-of-region IXP membership at all. Not implemented yet, same as the rest of this section.

**Project owner also pointed at the other two Fiji-IXP participants: https://www.peeringdb.com/net/14065 (AS45355, Digicel Fiji — Fiji-IXP only, no Sydney presence registered) and https://www.peeringdb.com/net/13392 (AS38442, Vodafone Fiji — Fiji-IXP *and* Equinix Sydney *and* MegaIX Sydney).** So of Fiji-IXP's 3 known members, 2 (AS45349 Telecom Fiji, AS38442 Vodafone Fiji) also peer in Sydney; only Digicel Fiji (AS45355) shows as Fiji-IXP-only. Same hybrid local+remote pattern as PNG. **Flagged by the project owner: expect real traceroute data sourced from Suva to show more participants than PeeringDB's 3 registered members** — Fiji has exactly one connected Atlas probe (per Phase 1b's coverage check), so this is a concrete, specific thing to check once that probe is used as a source: not just "does the RIS+PeeringDB view match Atlas," but "does Atlas surface local peers that PeeringDB's Fiji-IXP listing doesn't even claim to have" — a prospective Rule 4/Rule 5 test, not yet run.

---

**[IXP LAN Subnet Registry tranche — implemented, per the project owner's "go ahead."]**

*Governance rule applied as specified, not as an afterthought*: mid-implementation, the project owner clarified that **newly discovered IXPs must never be auto-classified** — this is the very first build of this registry, so every exchange in it counts as "new." Redesigned `IxpLanEntry.in_fishbowl` as a tri-state (`True` / `False` / `"TBA"`) before writing anything: `build_ixp_lan_registry` preserves any already-confirmed classification on rebuild and only ever writes `"TBA"` for an exchange it hasn't seen before — never the country-code heuristic. Added `confirm_ixp_region(ix_id, bool)` as the only intended way a `"TBA"` becomes `True`/`False`, and `add_or_confirm_ixp(ix_id, bool)` for exchanges not yet linked to any known ASN (see GOREX below).

*Built*: `discovery/peeringdb.py` gained `fetch_ixp_prefixes` (per-`ix_id` `ixpfx` lookups — one at a time deliberately, since `ixpfx` records carry `ixlan_id` not `ix_id` and batching risked mis-attribution) and `fetch_facility_presence` (`net_id`-based `netfac` lookups — `netfac` doesn't filter by ASN directly, so this resolves ASN -> net_id via `net` first). Both needed retry-with-backoff added after hitting PeeringDB's rate limit again (a couple dozen sequential per-exchange calls was enough) — `fetch_ixp_prefixes` also got a small delay between requests. `analysis/ixp_lan_registry.py`: `build_ixp_lan_registry`, `load_ixp_lan_registry`, `classify_ixp_fabric`, `confirm_ixp_region`, `add_or_confirm_ixp`. Entry point `pacific-peering-ixp-lan-registry`.

*Wired into `traceroute_topology.py` as a genuine third resolution tier*: `_resolve_address` now tries BGP, then PeeringDB netixlan (exact member), then the new IXP LAN registry (exchange known, member not) — the third tier surfaces as `ixp_context` on `HopResolution` and as an `ixp_crossings` list per probe in `analyze_measurement`'s output, distinct from a bare unresolved gap. `IpResolutionCache` extended to cache this third tier too. Regression-checked against all three existing measurements (210901499, 210913838, 210919078) — all four prior findings held exactly; `ixp_crossings` came back empty for all of them, which is correct (every IXP-fabric hop hit so far *did* resolve to a specific member ASN via netixlan) rather than a sign the new tier is unused — it's simply not been exercised by a "member unknown" case yet.

*Registry built*: 29 exchanges from `fishbowl.json`, all written as `"TBA"` on this first build (per the governance rule above) — then the project owner confirmed three in real time while this was being built: **CAN'L IX (ix/3720, New Caledonia) and Guam IX (ix/4494) as in-fishbowl**, plus **GOREX (ix/2116, Piti, Guam)** — a real exchange not linked to any of our known ASNs yet, added fresh via `add_or_confirm_ixp` rather than silently missed. Registry now: 30 exchanges, 3 confirmed in-fishbowl, 0 confirmed out-of-fishbowl, **27 still awaiting confirmation** (see list below). Full IPv4 prefix coverage achieved for all 30 after a few retry passes around PeeringDB's rate limit.

*Facility presence added to `fishbowl.py`* (regenerated `data/analysis/fishbowl.json`): 22 of 163 ASNs now show real colocation facility presence. **Striking new evidence for the already-flagged AS24013 (Solomon Islands) anycast/hosting hypothesis**: it shows facilities in **Los Angeles, Fremont (Hurricane Electric), Hong Kong (x2), Osaka (x2), Sydney, and Tallinn, Estonia** — six facilities across five countries on three continents. That's a much stronger, more concrete confirmation than the earlier all-Germany-IXP-memberships observation alone: this ASN's PeeringDB footprint is globally scattered in a way no real Solomon Islands network operation would be, consistent with anycast/CDN infrastructure being misattributed to it rather than genuine local network topology.

**Still open — 27 exchanges awaiting the project owner's in/out-of-fishbowl confirmation** (none auto-classified, per the governance rule): ABQIX (Albuquerque, US), Any2West (LA/Silicon Valley, US), BBIX Tokyo (JP), DE-CIX Dusseldorf/Frankfurt/Hamburg/Munich (DE), DRF IX (Honolulu, US), EdgeIX Auckland (NZ), Equinix Los Angeles/San Jose/Singapore/Sydney (US/US/SG/AU), Fiji-IXP (Suva, FJ), GU-IX (Guam, GU), IX Australia Sydney/NSW-IX (AU), JPNAP Tokyo (JP), LOCIX Dusseldorf/Frankfurt (DE), MARIIX (Guam, GU), MegaIX Dusseldorf (DE), MegaIX Sydney (AU), PNG Neutral IX Hagen/Lae/POM (PG), SIX Seattle (US), VIX.VU (Port Vila, VU). Several of these are unambiguous given economies already confirmed in scope (Fiji-IXP=FJ, GU-IX/MARIIX=GU, PNG Neutral IX x3=PG, VIX.VU=VU all match ECONOMIES_BY_CC; the rest are all non-in-scope countries) — flagged here rather than silently applied, exactly as instructed.

**Project owner confirmed 5 more of the unambiguous ones**: Fiji-IXP, PNG Neutral IX (Hagen/Lae/POM), VIX.VU, GU-IX, and MARIIX are all in-fishbowl. Applied via `confirm_ixp_region`. **Registry now: 10 confirmed in-fishbowl (CAN'L IX, Guam IX, GOREX, Fiji-IXP, PNG Neutral IX x3, VIX.VU, GU-IX, MARIIX), 0 confirmed out-of-fishbowl, 20 still TBA** — all remaining TBA entries are the non-in-scope-country exchanges (US/DE/AU/NZ/JP/SG), awaiting confirmation.

---

**[Loop tranche 6 — testing the project owner's Suva-participants prediction, and hitting a real methodological trap.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

*Before running anything*: checked which ASN hosts Fiji's one connected Atlas probe (60575). **It's AS53813 — ZSCALER, INC.**, a corporate security/VPN proxy gateway, not a native Fiji ISP. Flagged this immediately as a likely confound for the intended test (does Suva show more local peers than PeeringDB's 3 known Fiji-IXP members) rather than running it blind and hoping the caveat wouldn't matter.

**Ran it anyway to document what actually happens** (measurement 210930962, FJ -> AS45355/Digicel Fiji): the path goes probe -> Zscaler's own tunnel (`165.225.x`, AS53813) -> **`45.127.173.29`, which resolves via the new IXP LAN registry to Equinix Sydney** -> Digicel Fiji's own backbone (`45.117.x`, AS45355 via BGP) -> destination. **It never touches Fiji-IXP's LAN prefix (`103.147.194.0/23`) at all.**

**Conclusion, stated precisely**: this measurement gives *zero* evidence about real Fiji-to-Fiji local peering — it's entirely an artifact of Zscaler's own global routing architecture (tunnel to nearest metro PoP, which happens to be Sydney, then hand off). The project owner's prediction (more Suva participants than PeeringDB's 3 known members) is **not disproven, just genuinely untested** — this vantage point can't answer that question. **Important explicit exclusion: this Sydney hit must NOT be counted alongside the Australia-hub evidence already gathered (Phase 1d)** — it reflects a corporate VPN vendor's infrastructure choice, unrelated to any Fiji ISP's peering decisions, and would contaminate that evidence pile if conflated with it.

Practical implication for future tranches: testing the Suva-participants question for real needs either a different Fiji-hosted Atlas probe (native ISP, not corporate-proxied — none currently connected) or a non-Atlas method (e.g. direct outreach, or a closer read of RIS-only signals). Not attempted this tranche; noted as the actual blocker, replacing the earlier assumption that the single Fiji probe would suffice.

---

**IXP LAN registry fully resolved.** Project owner confirmed all remaining 20 TBA exchanges as out-of-fishbowl in one batch — every one of them was already in a country outside the 20-economy scope (US/DE/AU/NZ/JP/SG), the exact "unambiguous by scope" set flagged earlier, now explicitly confirmed rather than left to the country-code heuristic. **Registry status: 30 exchanges total, 10 confirmed in-fishbowl, 20 confirmed out-of-fishbowl, 0 TBA.** The governance rule (never auto-classify a newly-discovered exchange) held for the registry's entire life so far — every single classification in it, in or out, was an explicit human confirmation, not an inferred default.

---

**Phase 1c started: pipeline orchestration, and a real bug caught by actually running it.**

Added `pacific_peering/pipeline.py` (`run_pipeline`, entry point `pacific-peering-pipeline`): re-runs ASN discovery -> fish bowl (RIS + IXP + facility presence) -> IXP LAN registry in sequence, catching each step's failure independently (one step's exception doesn't sink the others) and writing a small versioned manifest to `outputs/runs/<timestamp>/manifest.json` — summary counts only, not the full data, to keep history lightweight. Adjusted `.gitignore` so `outputs/runs/` is tracked (small, valuable historical record) while the bulk regenerated data stays ignored.

**Deliberate scope limit, stated explicitly rather than silently narrowed**: this pipeline does **not** fire new RIPE Atlas measurements automatically. Atlas measurements cost real account credits and need a human choosing which AS pairs matter — an automatic recurring job silently spending credits on unreviewed pairs is a materially bigger, less reversible decision than re-running free public APIs (RIPEstat/PeeringDB/APNIC need no auth), and isn't being made without explicit sign-off. Atlas campaigns stay manual (`atlas.smoketest` and friends).

**Ran it, and it immediately caught a real regression**: the first run silently dropped GOREX (the exchange added via `add_or_confirm_ixp`, outside the normal `fishbowl.json`-derived set) — `build_ixp_lan_registry` was building its output dict fresh from only the fishbowl-derived exchanges each time, discarding anything added another way. Confirmed via the manifest (`in_fishbowl: 9`, not the expected 10) before it could go unnoticed. Fixed: the registry now starts from whatever's already on disk and only *adds to* it from `fishbowl.json`, never rebuilds from scratch. Re-ran to confirm: `30 exchanges, 10 in-fishbowl, 20 out-of-fishbowl, 0 TBA` — correct. Removed the buggy run's manifest from `outputs/runs/` rather than keep a known-wrong result as "history."

**Resolved: asked the project owner whether to wire this into a GitHub Actions cron now — answer was manual-only for now.** Decision: keep running `pacific-peering-pipeline` by hand (or via `/loop`) rather than set up automated recurring commits to the repo; revisit real scheduling once there's more confidence in the pipeline's stability. **Phase 1c is complete as scoped** — the orchestrator itself is done, idempotent, and safe to run on a schedule whenever that's actually wanted; only the trigger is deliberately deferred, not missing by oversight.

---

**Phase 1e: Visualization.** Activated the `dataviz` skill before writing any chart code (categorical hues, status colors, and the "render it and look at it" discipline all came from there, not improvised).

Added `discovery/economy_coordinates.py` (capital-city lat/lon for all 20 economies + Sydney as the one external hub needed so far) and `analysis/confirmed_detours.py` (hand-curated — not auto-derived, since only 2 real triangulated detours exist yet: Guam->PNG via Equinix Sydney, NC->Fiji via MegaIX Sydney).

**Two visualizations, both under `viz/`, entry points `pacific-peering-viz-detours` and `pacific-peering-viz-as-graph`:**
- `geographic.py`: plots all 20 economies (colored by subregion, dataviz's validated categorical slots 1-3) plus Sydney, and draws each confirmed detour as a solid red bent path (source -> hub -> target) next to a dashed direct-line comparison — the project's central finding, in one picture. Had to shift negative Polynesian longitudes onto a continuous range first (several economies sit just east of the antimeridian, which would otherwise split them to the opposite edge of the chart from geographically-close neighbors).
- `as_graph.py`: the full RIS-observed neighbor graph for all 163 in-scope ASNs plus the top-15 external ASNs by weight, edge-colored green (stays in-fishbowl) or red (leaves it) — this is the direct visual encoding of the project's core distinction at the ASN level, not just the IXP level. **Surfaced something not previously written up explicitly: 92 real intra-fishbowl RIS-neighbor edges exist** — smaller in-scope ASNs getting transit from a national incumbent within the *same* economy (e.g. several New Caledonia ASNs -> AS18200 O.P.T., several PNG ASNs -> AS17828 PNG DataCo, several Fiji ASNs -> AS4638/AS45355). The original plan for this graph assumed intra-fishbowl edges would be rare/absent; they're not — domestic hub-and-spoke structure is real and worth its own mention in the eventual report, separate from the external-dependency finding.

**Iterated per the skill's step 7 (render and look, don't assume)**: rendered both to PNG for actual visual inspection rather than trusting the SVG source. The geographic map was clean on the first pass. The AS-graph wasn't: external-ASN labels existed but the actual hub ASNs (the interesting nodes) had no labels at all, and ~49 isolated in-scope ASNs (zero observed neighbors) cluttered the layout without adding information. Fixed both: hub ASNs (degree >= 5) now get bold labels, and isolated nodes are dropped from the plotted layout with their count noted in the caption instead of scattered around the image.

Both are static SVG (matplotlib + networkx, no new heavy dependency like cartopy) under `outputs/viz/` — not currently tracked in git (bulk visual output, same treatment as other generated data; the *code* to regenerate them is what's committed).

---

**[Loop tranche — Phase 1f started: shared report data + ASCII renderer.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

Added `reports/data.py` (`build_report_data` -> `ReportData`, assembled from the ASN registry, `fishbowl.json`, the IXP LAN registry, and `analysis.confirmed_detours`) and `reports/ascii_report.py` (`render_ascii_report`, `write_ascii_report`). Per Phase 1f's own spec — "ASCII report and HTML report from the same underlying analysis output" — the HTML renderer due next tranche will consume this exact same `ReportData`, not a separate re-derivation, so the two formats can't drift on what they claim.

Ran it: `outputs/reports/report.txt` — summary stats, the 2 confirmed detours with their RIS observation counts, a per-economy table (ASN/neighbor/IXP/facility counts), and the full 30-exchange IXP table with each one's confirmed in/out-of-fishbowl status. Read through the output; numbers are internally consistent with everything gathered so far (e.g. PNG's 39 ASNs/29 with neighbors/10 with IXP membership lines up with earlier phases' findings).

Next tranche: the HTML report, rendering the same `ReportData`.

---

**[Loop tranche — Phase 1f complete: HTML report added.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

Added `reports/html_report.py` (`render_html_report`, `write_html_report`) — renders the exact same `ReportData` as the ASCII report, as a single self-contained HTML page with stat tiles, the confirmed-detour callouts, and (something the ASCII format can't do) the two Phase 1e visualizations embedded directly via relative `<img>` paths. Entry point `pacific-peering-report-html`.

**Actually rendered and looked at it, not just trusted the markup**: used the headless Chromium already on this machine to screenshot `outputs/reports/report.html` (full page, not just the viewport) rather than assume the HTML was correct. Confirmed clean on the first pass — both embedded SVGs resolved and displayed correctly, the economies/IXP tables rendered with correct data and color-coded in-fishbowl (green) / out-of-fishbowl (red) text, matching what the ASCII report and the underlying data actually say. No fixes needed this time, unlike the AS-graph in Phase 1e — but checked anyway rather than assuming a repeat of last time's clean-first-try geographic map.

**Phase 1f complete.** Both `pacific-peering-report-ascii` and `pacific-peering-report-html` are real, working entry points producing genuinely useful output from this project's actual accumulated data (2 confirmed detours, 163 ASNs, 30 classified IXPs). P1 (the core pipeline) is now fully done: 1a through 1f all checked off. Remaining: P2 (presentation skeleton, docs pass, changelog discipline — the last one already ongoing throughout).

---

**[Loop tranche — Phase 2b started: README rewrite.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire. P1 is fully done, so this tranche moved to P2.

The README was still the early-scaffolding version from Phase 0a ("early scaffolding... not yet implemented" had already been fixed once, but it never got updated again as 15 entry points and two real findings accumulated). Rewrote it: a "Findings so far" section stating both confirmed detours plainly (matches what's in the reports/plan, not a separate claim), the full project layout reflecting `outputs/runs` (tracked) vs `outputs/viz`/`outputs/reports` (gitignored), a real Usage section listing every entry point grouped by what it actually does (pipeline vs. manual Atlas steps vs. viz/reports), and a note that most of the project needs no credentials at all (only Atlas does). Setup/License/Support sections kept as they were, already accurate.

Not done yet: Phase 2a (presentation skeleton) and a docstring audit across all modules (most already have reasonable docstrings from when they were written, but no systematic pass has checked for gaps or drift) — queued for later tranches.

---

**[Loop tranche — Phase 2a complete: presentation skeleton.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

Added `reports/presentation.py` (`render_presentation_skeleton`, `write_presentation_skeleton`) — a third renderer over the same `ReportData` as the ASCII/HTML reports, this time as a Marp-compatible Markdown slide deck (plain Markdown, `---` slide separators, renders in VS Code's Marp extension or `marp-cli` to PDF/PPTX/HTML — a common NOG-talk format, no new heavy dependency needed to produce it). Entry point `pacific-peering-presentation`.

Deliberately a **skeleton**, not finished narration: title/scope/methodology/findings/IXP-landscape/next-steps/thank-you slides, each populated with this project's real numbers (20 economies, 163 ASNs, both confirmed detours with their actual RIS counts and measurement IDs, the 10/20 in/out-of-fishbowl IXP split), but with explicit `<!-- SPEAKER NOTE -->` placeholders for judgment calls only whoever gives the talk can make (audience framing, timing, venue-specific next steps). Caught one redundant phrasing on first render (a finding bullet repeated "AS17828" twice since the note already named it) and fixed it before calling this done.

**P2 status: Phase 2a done. Phase 2b partially done** — the README half is complete, but Phase 2b's other half (a systematic docstring audit across all modules) hasn't happened yet, so 2b's checklist item stays unchecked until that's done too, not marked complete on the README alone.

---

**[Loop tranche — Phase 2b complete: docstring audit.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

Ran a small AST-based script over every file in `src/pacific_peering/` rather than eyeballing each one — checks for a missing module docstring or a missing docstring on any public (non-`_`-prefixed) function or class. First pass found real gaps: **all 7 package `__init__.py` files had no module docstring** (they only re-export via `__all__`), plus a handful of dataclasses/TypedDicts (`EconomyRegistryEntry`, `EconomySummary`, `IxpSummary`) and the `IpResolutionCache` accessor methods (`load`/`set`/`save`) — real, if minor, gaps. `main()` wrapper functions were excluded from the "real gap" list on purpose: a function literally named `main` that logs and calls the module's actual function needs no docstring to be understood, and adding one would just be noise per this project's "no comments that don't add value" rule.

Fixed all of them with one-line, purpose-stating docstrings (each package `__init__.py` now says what that package is for in one line, matching the pattern already used in `analysis/ixp_lan_registry.py`'s module docstring). Also gave the leftover `uv init` placeholder (`src/pacific_peering/__init__.py`'s bare `main()`, still printing "Hello from pacific-peering!" since Phase 0a) a real docstring and a message that actually points somewhere useful, since the project now has 16 real entry points and that stub was the one piece of dead scaffolding nobody had touched since day one.

**Verified, not just linted**: re-ran the audit script to confirm zero remaining gaps, syntax-checked every file, and — the check that actually matters — imported all six top-level subpackages and ran the bare `pacific-peering` command to confirm nothing broke from the edits. All clean.

**Phase 2b complete. All of P1 and P2 are now done.** Remaining per the original plan: Phase 2c (changelog discipline) is not a one-time task — it's been running continuously throughout, and stays ongoing rather than ever getting a checkbox.

---

**[Loop tranche — broadening the AS-pair sample: a real bug fix and a fourth confirmed adjacency.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire. With P1/P2 complete, this tranche picked up the still-open "broaden the AS-pair sample" item from Phase 1d.

New corridor, not tried before: **French Polynesia (source, 7 connected probes) -> Vanuatu (AS9249, Telecom Vanuatu)**, measurement `210960114`.

**Hit a real crash, not just an interesting result**: `analyze_measurement` died mid-run with an uncaught `requests.exceptions.ReadTimeout` — RIPEstat took longer than 30s on one hop and `resolve_ip_to_asns` had no retry/timeout handling at all, unlike the PeeringDB functions (which already learned this lesson around rate limits). One slow response over one hop took down the entire analysis — exactly the kind of fragility a recurring pipeline can't tolerate. Fixed: `resolve_ip_to_asns` now retries transient network errors with backoff and degrades to "unresolved" (empty list) after exhausting retries, matching the pattern already used for PeeringDB's 429s.

**Re-ran cleanly after the fix, and found something new**: all 3 probes' last resolved ASN before the target is **AS38442 (Vodafone Fiji)** — and RIS independently lists AS38442 as AS9249's neighbor with **exactly 1,346 observations**, an exact match. This is the project's **fourth** RIS+Atlas-confirmed adjacency, and a different kind of finding than the first three: not a detour through Sydney, but **real intra-region transit** — a Fiji operator apparently providing upstream connectivity to a Vanuatu operator, entirely within the fishbowl.

**Checked the gap before accepting the story, rather than assuming the best case**: `contiguous: false` for all three probes (a real gap sits between AS38442 and AS9249 itself). Hypothesized this might be VIX.VU (Vanuatu's confirmed in-region IXP) showing up — checked directly rather than assume, and it wasn't: two probes show a bare non-responding hop (`*`), the third shows a private RFC1918 address (`10.200.4.208`, not any known IXP fabric). Ordinary ICMP filtering near the destination, nothing more. The finding stands on what's actually confirmed (the AS38442 adjacency, backed by matching RIS+Atlas counts) without overreaching into what the gap might mean.

Not yet added to `analysis/confirmed_detours.py` — that module is specifically for out-of-fishbowl detours, and this is the opposite (a confirmed in-region adjacency), so it needs its own small home rather than being force-fit into the existing one. Queued for a future tranche rather than done here, to keep this tranche's scope to the bug fix + the finding itself.

---

**[Loop tranche — giving the AS38442->AS9249 finding its own home, threaded through all three reports.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

Added `analysis/confirmed_local_transit.py` (`CONFIRMED_LOCAL_TRANSIT`, `ConfirmedLocalTransit`) — the positive-finding counterpart to `confirmed_detours.py`, tracking a provider/customer ASN pair (both in-fishbowl) rather than a source/hub/target detour shape, since that's what this kind of finding actually looks like. Seeded with the AS38442 (Vodafone Fiji) -> AS9249 (Telecom Vanuatu) adjacency from last tranche, including the vantage-point ASN (the traceroute was sourced from French Polynesia, which isn't itself part of the finding) and the honest caveat about the unresolved gap near the destination.

Wired it into `reports/data.py`'s `ReportData` (a new `confirmed_local_transit` field, assembled the same way as `confirmed_detours`) and all three renderers: a new ASCII section, a green (not red) HTML card styled to visually distinguish it from the detour cards, and a new presentation slide placed right after the detour slides with an explicit speaker note not to let the good-news finding get lost after two "sub-optimal" findings in a row.

**Caught one real bug on render, not on read**: the presentation slide's heading had a literal newline in the middle of the f-string, which breaks Markdown heading syntax — Marp would have rendered the second half as a stray paragraph, not part of the title. Only visible by actually generating the file and reading the output, not by reading the source code (the string looked fine there). Fixed by putting the whole heading on one line.

**Re-verified all three formats after the change**: regenerated ASCII/HTML/presentation, confirmed the ASCII section reads correctly, confirmed the HTML section (via a fresh headless-Chromium screenshot, not just the markup) shows the new green card in the right place with correct data, and confirmed the presentation heading fix. All three formats now cover both kinds of confirmed finding — sub-optimal detours and healthy local transit — not just the detours.

---

**[Loop tranche — another new corridor, and an honest negative result.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire. Continued broadening the AS-pair sample.

New corridor: **Vanuatu (source, 2 connected probes, untested as a source until now) -> FSM (AS38875)**, measurement `210970669`. Both probes' paths: AS9249 (Vanuatu, the source's own network) -> **AS38442 (Vodafone Fiji)** -> AS4637 (Telstra Global) -> AS9246 (GTA/Teleguam, Guam) -> AS139759 (an FSM ASN) -> [ICMP-filtered gap] -> target never resolved.

**Two things came out of this, one reinforcing, one a clean negative result:**
- The AS9249 -> AS38442 hop **reinforces the existing confirmed-local-transit finding from the reverse direction** — last tranche saw AS38442 as the last hop *before* AS9249 (Fiji -> Vanuatu); this tranche shows it as the *first* hop *leaving* AS9249's own network (Vanuatu -> elsewhere). Same adjacency, now confirmed bidirectionally. Updated `confirmed_local_transit.py`'s note to record this rather than opening a redundant second entry for the same pair.
- The measurement's actual target, **AS38875, was not confirmed** — checked RIS directly: AS38875's only observed neighbor is AS10130, not AS139759 (the traceroute's last resolved hop). `ris_agrees: false` was the correct, honest output, not a bug. **Recorded as a real negative result, not silently discarded**: not every AS pair yields a new triangulated finding, and reporting that honestly is part of what makes the positive findings credible — a validation method that never says "not confirmed" isn't actually validating anything.

Also worth noting without over-claiming: AS4637 (Telstra Global) appeared as a transit hop for a *third* time across this project's measurements, but this time via a plain BGP-resolved hop, not a specific named IXP address the way the two confirmed detours were. That's real color (Telstra Global is clearly a heavily-used regional transit provider) but doesn't meet this project's bar for a new "confirmed detour" entry, which specifically requires the named-IXP evidence — noted here rather than quietly added to `confirmed_detours.py` on weaker grounds than the existing two entries.

---

**[Loop tranche — the geographic map had fallen behind the reports.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

Noticed: `viz/geographic.py` only ever plotted `CONFIRMED_DETOURS` — after last tranche's addition of `confirmed_local_transit.py`, the three report formats all cover both kinds of finding, but the map still only showed half the picture. Fixed: added a solid green line between provider/customer economies for each `ConfirmedLocalTransit` entry (matching the red/green convention already used in the HTML report's cards), updated the title and legend to name both line types, and kept the function name/output path stable (`plot_confirmed_detours` / `geographic_detours.svg`) rather than a churn-inducing rename, since the HTML report already references that exact filename and nothing external needed to change.

**Rendered and looked at it before calling it done** (same discipline as every other visualization change this session): converted to PNG, confirmed the new Fiji-Vanuatu green line renders correctly, legend shows all four entries (subregion dots, out-of-fishbowl hub, confirmed detour, confirmed local transit) without collision. Clean on the first pass. Regenerated the HTML report afterward so its embedded copy of the map picks up the change too.

---

**[Loop tranche — regression check found and fixed a real bug: rate-limited refetches were silently wiping known-good IXP prefixes.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

Ran `uv run pacific-peering-pipeline` as a deliberate end-to-end regression check (chosen over another Atlas measurement, to vary the type of work and reduce API/credit load). It completed and reported success overall, but the logs showed `ixpfx` lookups for ix_id 248 (DE-CIX Munich), 267 (DRF IX), and 463 (GU-IX) hit PeeringDB's rate limit and gave up after 3 retries. Given the Phase 1c precedent (GOREX getting dropped from a rebuild), checked directly whether this silently degraded existing data rather than assuming success — it had: all three exchanges' `prefixes` had been overwritten with `[]`, discarding real, previously-fetched subnet data. **This mattered concretely**: GU-IX is a confirmed in-fishbowl exchange, and losing its LAN prefix means `classify_ixp_fabric` can no longer recognize a traceroute hop landing in GU-IX's own subnet — a real capability regression, not just stale metadata.

**Root cause**: `build_ixp_lan_registry` (`analysis/ixp_lan_registry.py`) already protects the `in_fishbowl` field on rebuild (the Phase 1c fix — start from `dict(existing)`, never silently reclassify) but that protection didn't extend to `prefixes`: the per-`ix_id` loop unconditionally set `prefixes=tuple(prefixes_by_ix.get(ix_id, []))`, so a rate-limited fetch's `[]` fallback (a deliberate design choice in `fetch_ixp_prefixes`, so a single stuck exchange doesn't crash the whole rebuild) looked identical to "this exchange genuinely has no prefixes" and overwrote good data with it.

**Fix**: same file, same loop — before writing `prefixes`, if the fresh fetch came back empty *and* the existing on-disk entry already had non-empty prefixes, keep the existing list and log a warning instead of accepting the empty one. An empty result is only trusted when there's no prior data to fall back on (a genuinely new exchange, or one that really has none on record).

**Verified two ways, not just by reading the diff:**
1. Since the 3 exchanges' on-disk data was *already* wiped by the earlier buggy run (the bug had already happened once — the fix only prevents recurrence, it can't retroactively un-wipe data that's already gone), directly re-fetched fresh prefixes for ix_id 248/267/463 via `fetch_ixp_prefixes` (succeeded this time, no rate limit) and patched them back into `data/analysis/ixp_lan_registry.json`: DE-CIX Munich `185.1.208.0/23`, DRF IX `206.197.210.0/25`, GU-IX `202.128.12.0/26`.
2. Re-ran `pacific-peering-ixp-lan-registry` to exercise the fixed code path for real — and PeeringDB rate-limited again mid-run, this time hitting 4 *different* exchanges (ix_id 2332, 2730, 3085, 3322). The fix caught exactly the case it was built for: logs show `"refetch returned no prefixes; keeping N already on record"` for all four, and a final check of the whole registry confirmed **0 of 30 exchanges have empty prefixes** — nothing was lost this time, despite the same rate-limiting happening again in the same run.

Same general lesson as the Phase 1c GOREX bug, applied to a second field: a rebuild step that "refreshes" data from an unreliable upstream source must diff against what's already confirmed good, not blindly trust the latest fetch — especially when the fetch function's own failure mode is indistinguishable from a true empty result.

---

**[Loop tranche — a new corridor, and a genuine "candidate hidden peering" result (RIS disagrees, but the traceroute signal is strong).]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

New corridor, not tried before: **FSM (source, 3 connected probes, untested as a source until now) -> Palau (AS17893, Palau National Communications Corp — a Guam IX + BBIX Tokyo member per PeeringDB)**, measurement `210986430`. Deliberately chosen to also exercise last tranche's GU-IX prefix-restore fix: if the path had actually crossed Guam IX, the (now-repaired) registry would need to catch it.

All 3 probes reached the target directly. The AS-level path for every probe is short and clean: the source's own local network (private/CPE addresses, expected) -> **AS139759** (an FSM ASN, resolved via BGP, contiguous across several hops) -> **AS17893** (Palau NCC, resolved via an exact PeeringDB `netixlan` IP match) as the final hop. No Guam, US, Sydney, or Tokyo ASN appears anywhere in the path — on its face this looks like the cleanest possible direct-peering story yet.

**But `check_neighbor_agreement` correctly returned `ris_agrees: false` for all 3 probes, and this time it isn't a weak/gap-driven negative like the AS38875 case — it's a real, load-bearing disagreement.** Checked directly (not assumed): RIS's actual neighbor list for AS17893 is `{174: 1333, 140627: 139, 6939: 106, 24482: 49, 2500: 5, 18106: 5, 9002: 5, 49544: 5, 35280: 5, 9498: 5, 59105: 2, 9505: 2}` (AS174 Cogent, AS6939 Hurricane Electric, AS2500 WIDE, etc. — global/regional transit providers) — **AS139759 is not in it, at all.** Also checked whether a shared IXP could explain it (PeeringDB cross-check, Validation Rule 4): AS139759 has zero PeeringDB IXP memberships, so no shared-fabric corroboration is possible either.

**This is not being added to `confirmed_local_transit.py`.** Per Validation Rule 1 (RIS and Atlas must *both* agree — no topology claim on one source alone), a traceroute this clean still isn't enough on its own, and the disagreement here is real, not an artifact of missing RIS data (AS17893 has plenty of RIS visibility — just not into this specific adjacency). Two honest readings, both left open rather than picked: (a) genuine unlisted/private peering between AS139759 and AS17893 that RIS's route collectors simply don't see (exactly the "hidden peering" scenario Validation Rule 4 exists to catch), or (b) the traceroute's BGP-based IP-to-ASN resolution for that hop is picking up an address block AS139759 doesn't actually control end-to-end. Not resolving that ambiguity by fiat — recording it here as a **candidate, not a finding**, deliberately not given a dataclass/module of its own (following the same restraint as the AS38875 negative result — a single data point doesn't yet justify new infrastructure; `confirmed_detours.py`/`confirmed_local_transit.py` were only created once there was a real, confirmed entry to hold). A second independent traceroute (a different FSM probe, or an inbound Palau->FSM direction) would be the natural next check if this corridor gets revisited.

---

**[User-directed tranche — three concrete methodology extensions, all suggested directly by the project owner: (1) traceroute straight at known PeeringDB IXP-member addresses to actively hunt for hidden peering, rather than only noticing it incidentally; (2) visualize "candidate/possible" hidden-peering results in the maps and reports, distinct from confirmed findings; (3) treat a RIS/Atlas disagreement on an otherwise-clean traceroute as itself informative — either a data issue or a real hidden transit relationship.]**

**Before building anything new, re-examined the FSM->Palau candidate from last tranche through exactly the lens the project owner described, and found a real bug hiding in data already collected.** The traceroute's second-to-last hop (`103.142.153.18`) had resolved via PeeringDB `netixlan` to AS17893 (Palau NCC) itself — but `_resolve_address` in `analysis/traceroute_topology.py` only ever checked the IXP LAN registry (tier 3) when *neither* BGP nor netixlan could attribute an ASN to an address. Since netixlan already succeeded here, the registry check never ran — silently discarding the fact that `103.142.153.18` *also* falls inside **Guam IX's** registered LAN prefix (`103.142.153.0/24`), direct traceroute corroboration of AS17893's PeeringDB-claimed Guam IX membership. **Fixed**: `_resolve_address` now checks `classify_ixp_fabric` unconditionally (it's a pure local lookup against the already-loaded registry, no API cost — nothing about the fix could re-trigger the PeeringDB rate-limiting fixed two tranches ago), and attaches `ixp_context` alongside whichever ASN resolution tier succeeded, rather than only as an exclusive fallback. `analyze_measurement`'s `ixp_crossings` filter was also updated to stop requiring an *unresolved* ASN (`not h.asns`) — it now surfaces every hop that's inside a known exchange's LAN, and reports which member ASN (if any) was also identified there (`member_asns`).

**Verified by clearing the entire IP resolution cache (127 addresses) and re-running `analyze_measurement` on all 7 measurements this project has ever fired**, not just the one that motivated the fix — the whole point of the bug was that it could have been silently suppressing IXP crossings anywhere, and the only way to know was to actually re-check everywhere:
- **210901499 (GU->PG)** and **210919078 (NC->FJ)**: both already-confirmed detours now show up explicitly in `ixp_crossings` too (Equinix Sydney / MegaIX Sydney respectively, with the correct member ASN attached) — independent corroboration via exact LAN-prefix matching, not a new claim.
- **210930962** (the earlier Zscaler-proxied Fiji probe test): unchanged conclusion, just a previously-unknown member ASN (132528) now resolved at the same already-correctly-excluded Equinix Sydney crossing.
- **210970669 (VU->FSM)**: no crossings, unchanged.
- **210986430 (FM->PW)**: now explicitly shows the Guam IX crossing described above for all 3 probes — folded into `analysis/candidate_peering.py`'s entry (below) as a strengthening detail.
- **210960114 (PF->VU, the confirmed AS38442<->AS9249 local transit)**: a genuinely new observation surfaced — for 2 of 3 probes, the hop immediately before AS38442 is **AS4637 (Telstra Global)**, resolved via netixlan, whose address falls inside **Any2West's** registered LAN prefix (Los Angeles/Silicon Valley, out-of-fishbowl). This doesn't touch the confirmed AS38442<->AS9249 adjacency itself — it's about the vantage point's (French Polynesia's) own upstream path to reach Fiji, not the finding's two endpoints — so it wasn't force-fit into a new detour entry (the existing `ConfirmedDetour` shape models "the destination network's own presence is at a foreign IXP," not "an intermediate transit carrier happens to peer there"; a different shape deserves its own module if this pattern recurs, not a shoehorned one now). Instead, appended as a clearly-scoped addendum to that entry's existing note.

**Built the "candidate/possible peering" category the project owner asked for.** New `analysis/candidate_peering.py` (`CandidatePeering`, `CANDIDATE_PEERING`) — a third finding shape, distinct from both existing ones: not "RIS and Atlas agree" (that's `confirmed_*`), but "the traceroute signal is clean and repeatable, and RIS's disagreement is itself informative, one way or the other" (exactly the framing the project owner gave: *"it is interesting that RIS data may not agree with inbound routes, this indicates either issues or hidden transit relationships"*). Seeded with the sharpened FSM(AS139759)->Palau(AS17893) entry. Wired into every existing surface, verified by actually rendering each, not just reading the diff:
- `reports/data.py`: new `candidate_peering` field on `ReportData`.
- `reports/ascii_report.py`: new "CANDIDATE PEERING" section.
- `reports/html_report.py`: new amber `.candidate-card` style (`#fab219`, the dataviz skill's validated "warning" status color — distinct from the existing red/critical and green/good cards) — confirmed via a fresh headless-Chromium screenshot that it renders correctly and reads clearly next to the other two card types.
- `reports/presentation.py`: a new slide per candidate entry, with a speaker note framing it as "the method working as designed," not a failure.
- `viz/geographic.py`: a dashed amber line per candidate (distinct from solid red/green), legend and title updated to name all three categories — rendered to PNG and checked, no collisions, reads cleanly at a glance.
- `analysis/__init__.py`, `discovery/__init__.py`, `atlas/__init__.py`: new symbols added to each package's explicit `__all__` export list, matching this project's existing convention.

**Built the active data-gathering method itself: traceroute directly at a known PeeringDB member address, instead of waiting for one to show up incidentally.** New `discovery.peeringdb.fetch_ixp_members(ix_id)` (confirmed empirically that PeeringDB's `netixlan` endpoint accepts an `ix_id` filter directly, same as `ixpfx` — no batching-ambiguity workaround needed), `atlas.targets.pick_ixp_member_target(ix_id, exclude_asn=None)` (deterministic lowest-ASN pick, so repeat runs target the same member unless real membership changes), and `atlas.smoketest.run_ixp_member_probe(ix_id, source_cc, exclude_asn=None, probe_count=3)` tying it together.

**Ran the first real test of the new method**: French Polynesia -> Fiji-IXP's member address for AS38442 (`103.147.194.5`, measurement `210990245`). All 3 probes reached **AS3257 (GTT Communications)** and went dark after that (ICMP filtering) — never reaching AS38442 or Fiji-IXP's LAN at all. Checked RIS directly: AS3257 isn't in AS38442's neighbor list either ({4637: 707, 7473: 697, 6939: 177, 2914: 46, ...}), so `ris_agrees: false` is correct, and this is an honest inconclusive result (same shape as the AS38875 case), not a finding either way about Fiji-IXP specifically. **What this tranche's test actually proves is narrower and more useful than a single result**: the new method fires correctly end-to-end (real PeeringDB member lookup -> real targeted traceroute -> correctly-classified analysis output), ready to point at a more promising member/exchange pair in a future tranche without needing to build anything further first.

---

**[User-directed tranche — probe Fiji-IXP's other two members, and add a single-purpose "where do we need more Atlas probes" report.]**

**Generalized `pick_ixp_member_target`/`run_ixp_member_probe`'s `exclude_asn` to `exclude_asns` (accepts one ASN or a set)**, so an exchange's full membership can be walked one measurement at a time (probe one, exclude it, probe the next) rather than only ever excluding a single fixed ASN. Small, backward-incompatible rename accepted deliberately rather than keeping both parameter names — this project is young enough that a clean signature beats a compatibility shim.

**Probed Fiji-IXP's remaining two members from the same vantage point (French Polynesia) as last tranche's AS38442 test, for direct comparability**: AS45349 (`103.147.194.4`, measurement `210992503`) and AS45355 (`103.147.194.10`, measurement `210992951`). **All three of Fiji-IXP's members now show byte-for-byte identical intermediate hops from PF** (`209.120.142.149` -> `89.149.181.141` -> `213.200.127.189` -> `89.149.136.81` -> `89.149.134.145` -> `89.149.133.65`, then dark), landing on **AS3257 (GTT Communications)** every time and never reaching Fiji-IXP's LAN or any of the three target ASNs. Checked RIS directly for both new targets too: AS3257 is in neither AS45349's neighbor list ({4637: 424, 174: 394, 7474: 145, 6939: 85, ...}) nor AS45355's ({132528: 1326, 4637: 333}) — `ris_agrees: false` correctly, for all 3 measurements.

**What three-for-three identical paths actually tells us, read honestly**: this isn't three independent looks at Fiji-IXP — it's the same fact observed three times. French Polynesia's own outbound route toward the Fiji/Melanesia direction is fixed regardless of which specific address within that region is being traced to, and it gets ICMP-filtered at (or just past) GTT Communications every time. **None of the three tests can confirm or rule out real peering at Fiji-IXP for any of its members** — the vantage point itself never gets far enough to see it. This is itself a concrete, load-bearing argument for the probe-gap report built in this same tranche (below): testing Fiji-IXP properly needs a vantage point that isn't PF (already known to die at GTT) and isn't Fiji's own probe either (already known to be Zscaler-proxied, per the earlier finding) — i.e., it needs an actual new probe request, not a smarter choice among the probes that already exist.

**Side note, not chased further this tranche (scope control, flagged for later)**: AS45355's RIS neighbor list includes **AS132528 with 1,326 observations** — the same ASN that showed up at Equinix Sydney in the earlier Zscaler-proxied Fiji test. A real, strong RIS-observed adjacency, untested by Atlas so far. A promising, cheap next candidate if this corridor gets revisited.

**Built the probe-coverage-gap report, the project owner's second ask this tranche**: new `reports/probe_gap_report.py` (`render_probe_gap_report`, `write_probe_gap_report`), entry point `pacific-peering-report-probe-gaps`. Deliberately kept separate from the findings-oriented ASCII/HTML/presentation reports — this one has exactly one job, per the project owner: tell a human where to request a new Atlas probe next, meant to run on its own (weekly) cadence rather than being bundled into the substantive analysis output. Re-fetches live probe coverage every run (20 unauthenticated Atlas API calls, no credits spent) rather than trusting the possibly-stale cached file, since a report whose whole point is current operational status defeats itself if it's showing last month's numbers. Groups economies into zero/fragile(1)/adequate(2+) connected-probe tiers, cross-references each against every confirmed/candidate finding's own economies (flagging e.g. Fiji, PNG, Palau, Vanuatu as already load-bearing for real findings despite thin coverage), and carries a small hand-curated `KNOWN_ISSUES` dict (seeded with Fiji's confirmed Zscaler-proxy problem) — same restrained pattern as this project's other hand-curated structures, only real confirmed issues, nothing speculative.

**Verified by actually running it, not just reading the code**: live output confirms 5/20 economies have zero connected probes (AS, NR, SB, WF, WS), 10/20 have exactly 1 (including FJ, PG, PW, VU — all four correctly flagged as already used in a confirmed/candidate finding, and FJ correctly carries its Zscaler caveat), and 5/20 are adequately covered (FM, GU, KI, NC, PF) — matching the coverage figures already known from earlier tranches, confirming the live re-fetch agrees with what was previously hand-verified.

---

**[User-directed tranche — a fourth data source: IRR AS-SET declared peering/transit intentions, and a new confirmed detour it directly led to.]**

The project owner pointed at a specific real example (`bgp.tools/as/132528`, `bgp.tools/as-set/as-132528-peers`) and named the underlying mechanism: PeeringDB `net` records carry an `irr_as_set` field naming an Internet Routing Registry AS-SET object — a network's own declared list of intended peers/transit, sourced independently of both this project and PeeringDB itself (APNIC, in the trusted case). Framed explicitly as a fourth kind of lead alongside RIS-observed AS-paths, PeeringDB IXP/facility membership, and Atlas traceroutes.

**Built it as two small, focused pieces**: `discovery.peeringdb.fetch_irr_as_set_names(asns)` (a new PeeringDB `net` field read, batched the same way as the existing `_fetch_net_ids`), and new `discovery/irr.py`'s `resolve_as_set(as_set_name)` — a plain WHOIS protocol query (RFC 3912, port 43, via a raw Python socket, no external binary dependency) that parses the `members:` line into direct ASNs and nested as-set names (deliberately not recursively expanded — a first-pass lead, not a full IRR toolchain).

**Critical correction made immediately on the project owner's explicit instruction, before trusting any result**: *"we'll only trust IRR object at APNIC, I know the other IRRs contain invalid and old entries that can not be trusted."* The first version queried `whois.radb.net` (a shared aggregator/mirror) — rewritten to query `whois.apnic.net` directly instead (confirmed empirically to serve the identical objects), and every response's `source:` field is now checked and must read exactly `APNIC`; anything else is treated as unresolved rather than silently trusted. **Verified the guard actually rejects untrusted data, not just that the code looks right**: queried `AS-HURRICANE` (a real RADB-hosted object, `source: RADB`/`ARIN`) through the same function pointed at `whois.radb.net`, and it correctly logged a rejection warning and returned empty rather than using it.

**Resolved the four AS-SETs already relevant to this project's existing/candidate findings, all confirmed `source: APNIC`:**
- **AS132528** (`AS-132528-PEERS`): declares `{132528, 38800, 45355, 140504}` plus several nested as-sets. **AS45355 is directly named** — matching the RIS-observed 1,326-observation adjacency flagged as a promising lead last tranche.
- **AS45355** (`AS-45355-PEERS`): declares `{132528, 140504, 132429, 38198}` back — **a mutual declaration**, both sides naming each other independently.
- **AS38442** (`AS38442:AS-ALL`): declares `{139898, 63945, 24565, 38442, 9249, 151398, 14789, 134783}` — **AS9249 is directly named**, corroborating the existing confirmed local-transit finding (AS38442<->AS9249) on a new, independent axis. Added to that entry's note.
- **AS45349** (`AS45349:AS-TFL-TRANSIT`): declares `{45349, 4638, 135647, 132248, 141470, 141695, 153509}` — **AS4638 is directly named** ("TFL" almost certainly Telecom Fiji Limited), corroborating the existing NC->FJ confirmed detour (which found AS45349 as the upstream to AS4638) on the same new axis. Added to that entry's note.

**Given the strength of the AS132528<->AS45355 lead (RIS + mutual IRR declaration, before any new traceroute), fired a deliberate Atlas test**: New Caledonia (a vantage point already proven to detour via Sydney for Fiji-bound traffic) -> AS45355's own address space (`103.101.240.1`, measurement `210996533`) — not the Fiji-IXP address used two tranches ago, since that path is already known to die at GTT from the PF vantage point; NC hadn't been tried toward this specific ASN. **Result: fully confirmed, and the strongest-evidenced finding in the project so far.** All 3 probes: AS18200 (O.P.T., New Caledonia's own incumbent) -> **AS132528, resolved via exact PeeringDB netixlan address match, which also falls inside Equinix Sydney's registered LAN** -> AS45355 (target). Fully contiguous, no gaps. RIS agrees with an *exact* observation-count match (1,326). Added as a new `ConfirmedDetour` entry (`NC -> FJ (AS45355) via Equinix Sydney`, measurement `210996533`) rather than a candidate — every validation rule is satisfied, and then some: this is the first confirmed finding in the project corroborated on all four axes (RIS, Atlas, PeeringDB/IXP-LAN-prefix, and now mutual IRR-declared intent). Also noted: AS132528 was independently seen at this same Equinix Sydney fabric in an unrelated earlier measurement (`210930962`, the Zscaler-proxied Fiji probe test) — two different vantage points, same exchange presence.

**Verified by regenerating and actually looking at every surface, same discipline as always**: rendered the geographic map (the new NC->FJ line via Sydney correctly overlaps the existing NC->FJ/MegaIX line — expected at this map's country-level geographic granularity, not a bug, since both share the same source/target/hub), screenshotted the HTML report (all three detour cards render correctly, notes readable), and checked the presentation output's new slide heading is a single clean line, not broken Markdown.

**Deliberately not done this tranche (queued, not urgent)**: bulk-fetching `irr_as_set` for all 163 in-scope ASNs and resolving each. This tranche only touched the four ASNs already directly relevant to existing work — a full sweep is a natural next step, but doing it now would be a bigger, less-targeted change than the "iterate slowly, small tranches" discipline calls for, and WHOIS servers deserve the same restraint already learned the hard way with PeeringDB's rate limits.

---

**[Loop tranche — the deferred bulk IRR sweep, done as a data-gathering/validation pass rather than more Atlas measurements, to vary the type of work.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

Ran the sweep deferred last tranche: `fetch_irr_as_set_names` across all 163 in-scope ASNs (a handful of batched, cheap PeeringDB calls) found **36 with a declared `irr_as_set`**. Resolved all 36 via `resolve_as_set` (APNIC-only, already enforced), handling two real-world wrinkles the raw PeeringDB field can contain that the existing code hadn't been exercised against yet: (1) a field can hold **more than one** as-set name, space-separated (e.g. `AS-38800-PEERS AS-38800-CUSTOMER-PEERS`) — split and resolved each; (2) a name can carry an explicit **`SOURCE::`** prefix (e.g. `APNIC::AS132228:AS-ALL`) — confirmed directly that APNIC's own server rejects the prefixed form (`%ERROR:101: no entries found`) but accepts it stripped, so the prefix is now stripped before querying. Paced with a small delay between the ~40 resulting WHOIS queries, same restraint already applied to PeeringDB. **5 of 36 came back with no `source:` line at all (correctly logged and discarded as untrusted, not silently skipped) and 3 more resolved but had an empty `members:` line** — 28 of 36 yielded real, trusted data.

**Cross-referenced every resolved as-set against the 163-ASN in-scope list for in-scope-to-in-scope declared relationships.** Most matches are same-economy domestic hub-and-spoke (e.g. AS18200/O.P.T.'s own as-set names a dozen other New Caledonia ASNs directly) — real, but reinforcing the already-known domestic-hub pattern from Phase 1e's AS-graph (92 RIS-neighbor edges), not new territory. **The genuinely new signal is the handful of cross-economy declarations, none tested by Atlas yet:**
- **AS3605 (Guam Cablevision)'s own `AS-KUENTOS-TRANSIT` names all three of Palau's in-scope ASNs (17893, 58932, 133897) directly, plus AS10130 (FSM Telecommunications Corporation) and MARIIX's own exchange ASN (23676).** Directly relevant to the still-unconfirmed FSM(AS139759)->Palau(AS17893) candidate from three tranches ago — folded into that entry's note as a concrete alternative/complementary hypothesis (a real, independently-declared Guam-based transit relationship spanning exactly this corridor) rather than opening a new candidate entry for a relationship no traceroute has touched yet.
- **AS10130 (FSM Telecommunications Corporation)'s own `AS-10130-TRANSIT` names AS38875, AS45193, AS58524, AS139759 (all four its own FSM siblings) plus AS132486 (Ocean Link Ltd, Kiribati)** — a brand-new FM<->KI lead, untouched by any prior tranche. Notably, this also means **IRR now agrees with RIS** on the AS10130<->AS38875 relationship specifically (RIS's only listed neighbor for AS38875 is AS10130) — the one thing the Vanuatu->FSM traceroute from two tranches back couldn't confirm directly (its last resolved hop before an ICMP-filtered gap was AS139759, not AS10130). Not promoted to confirmed on IRR+RIS alone (Atlas still hasn't directly observed this specific hop) — but a good candidate for a more targeted future retest from a different vantage point.
- **AS45355 (Digicel Fiji)'s own `AS-45355-PEERS`** (already known to include AS132528) **also names AS140504 (Nauru), AS132429 (Vanuatu), and AS38198 (Tonga)** — plausibly Digicel's own multi-country Pacific mobile footprint declared explicitly. Three new FJ<->{NR,VU,TO} leads.
- **AS55943 (French Polynesia)'s own `AS55943:AS-CUSTOMERS` names AS10131 (Cook Islands) and AS55885 (Niue)**; separately **AS38800 (Samoa)'s `AS-38800-CUSTOMER-PEERS` also names AS55885 (Niue)** — new PF<->CK, PF<->NU, and WS<->NU leads, the latter two touching economies with zero/one connected Atlas probes respectively (per the probe-gap report), so not immediately testable, but worth recording for when that changes.
- **AS4638/AS45349 (Fiji)'s own as-sets both name AS141695 (New Caledonia)** — a new FJ<->NC lead distinct from the already-confirmed detour ASNs.

**Deliberately not fired as new Atlas measurements this tranche** — this was a data-gathering and cross-referencing pass, not another round of traceroutes; five real new leads in one sweep is enough to queue thoughtfully rather than spend credits testing all of them at once. The AS3605/Palau one is the most immediately actionable (directly extends existing unconfirmed work); the AS10130->AS132486 (Kiribati) one is the most genuinely novel (an economy pair no prior tranche has looked at in either direction).

**Not turned into new permanent tooling**: the sweep itself was a one-off cross-reference script using the `fetch_irr_as_set_names`/`resolve_as_set` library functions already built last tranche — no new module, since IRR data changes slowly and this doesn't need to run on every pipeline cycle the way discovery/fishbowl do. The durable output is this write-up plus the updated `candidate_peering.py` note, not a new CLI entry point.

---

**[User-directed tranche — a report footer explaining "the fish bowl," the IRR sweep turned into real persisted monthly-refreshed infrastructure (correcting last tranche's own call not to), and the actual generated reports committed to the repo.]**

**The project owner explicitly overrode last tranche's "not turned into new permanent tooling" decision**: asked directly to "get all of those AS-SETs, and make sure to update the AS-SETs each month." Built it properly this time: new `analysis/irr_leads.py` (`build_irr_leads`, `load_irr_leads`, `find_in_scope_relationships`), matching the existing `ixp_lan_registry.py` build/load/persist pattern, persisting to `data/analysis/irr_as_sets.json`. Wired into `pipeline.run_pipeline` as a fourth step (discovery -> fishbowl -> ixp_lan_registry -> **irr_leads**) — the same free-API-only, no-Atlas-credits, safe-to-rerun cadence as the rest of the recurring pipeline, so a monthly pipeline run now refreshes this automatically rather than needing a separate mechanism. New entry point `pacific-peering-irr-leads` for a standalone run. Also added to `analysis/__init__.py`'s exports, matching this project's per-package convention.

**Immediately hit a real bug on the very first live run** (not caught by syntax-checking or the earlier one-off script, which happened not to hit this): `fetch_irr_as_set_names` had no retry/timeout handling at all — a single slow PeeringDB response threw an uncaught `ReadTimeout` and crashed the whole sweep. This is the exact same class of bug already fixed twice elsewhere in this project (PeeringDB rate limits in `fetch_ixp_prefixes`/`resolve_ip_via_netixlan`, and `ris.ripestat.resolve_ip_to_asns`'s uncaught `ReadTimeout`) — a function that talks to an unreliable upstream needs the same guard, and this one had been added without it. Fixed: retries a 429 or any `requests.exceptions.RequestException` with backoff, and a chunk that still fails after retries is skipped and logged rather than crashing the whole sweep.

**Re-ran successfully and verified against the manually-checked results from two tranches ago**: 36 of 163 in-scope ASNs have a declared `irr_as_set`, all resolved and persisted to `data/analysis/irr_as_sets.json` — spot-checked AS45355 and AS3605's entries against the exact values found manually last tranche; identical.

**Added a shared "what is the fish bowl" explanation, per the project owner's ask, to every report a reader (including an external one) might land on without prior context.** New `reports.data.FISHBOWL_EXPLANATION` — one canonical text block, not duplicated per format, covering: the outside-looking-in limit of RIS/PeeringDB data, why Atlas traceroutes are the only way to partially see inside, this project's core validation rule (RIS+Atlas must agree; IRR/PeeringDB support but never substitute), and what "in/out-of-fishbowl" means concretely. Added to `ascii_report.py` (a new "ABOUT THIS PROJECT" section), `html_report.py` (a styled `<footer>`, verified via a fresh headless-Chromium screenshot — reads cleanly, visually separated from the main content by a top border), and `probe_gap_report.py` (plain-text footer — this report is the one most likely headed to an external reader, per the project owner's stated intent to use it when asking RIPE NCC about new probes). Not added to `presentation.py`, which already dedicates a full methodology slide to the same explanation — a footer there would just repeat it.

**Committed the actual generated report outputs to the repo for the first time, per explicit instruction** ("commit the reports as well push"). Until now `outputs/reports/` and `outputs/viz/` were gitignored like the rest of `outputs/*` (only `outputs/runs/`'s manifests were carved out as tracked) — added matching `!outputs/reports/` / `!outputs/viz/` exceptions to `.gitignore`. Regenerated every report and visualization fresh before staging (so the committed snapshot reflects everything built this session, including the new footer and the third confirmed detour from two tranches ago) and checked the actual file list and a secret-string grep before adding anything, per the standing working agreement. **One real, live change surfaced by the fresh regeneration, not a bug**: the probe-gap report now shows **PG (Papua New Guinea) at zero connected probes**, down from 1 (fragile) a few tranches ago — an actual Atlas probe appears to have gone offline since then, exactly the kind of current-state signal this report exists to surface.

---

**[Loop tranche — testing the FM<->Kiribati IRR lead from the bulk sweep; a real Starlink transit hop; and two consecutive Atlas result recoveries after unrelated environment memory kills.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

Fired a traceroute for the most genuinely novel lead from the bulk IRR sweep: FSM -> AS132486 (Ocean Link Ltd, Kiribati), a corridor no prior tranche had tested in either direction (originally surfaced via AS10130's own declared transit AS-SET naming AS132486 directly).

**Hit a real environment issue twice in a row, unrelated to this project's code**: the background shell running the traceroute-and-wait call was killed both times with "system is running low on memory" — `ps`/`free` showed this is a shared host running several unrelated heavyweight services (ClickHouse, Kafka, Elasticsearch, another Claude Code session, many Chrome renderer processes), not anything caused by this lightweight script. Rather than accept the measurement as lost (real Atlas credits had already been spent — the measurement was confirmed created server-side, `211020366`, before each kill), recovered it: re-ran the results-fetching step in the **foreground** rather than backgrounded (the kill looks like the harness's own background-task resource policy, not an OS-level kill of this specific process), which completed cleanly on the first attempt. Worth remembering for future tranches: if a backgrounded Atlas wait gets killed for memory, check whether the measurement was already created (it usually was, by the time `wait_for_results` starts polling) before assuming credits were wasted, and retry the recovery step in the foreground.

**The country-based probe selection landed on a different FSM ASN than intended**: `source_cc="FM"` picks whichever connected probe exists in the economy, which turned out to be hosted on **AS139759**, not AS10130 (the ASN whose IRR-declared AS-SET actually named AS132486). So this measurement does not directly test that specific IRR lead — recorded honestly as such, not overclaimed.

**What it did show is still real and worth keeping on record.** All 3 probes: AS139759 -> AS9246 (GTA/Teleguam, Guam) -> AS7578/AS137409 (GSL Networks, an Australian carrier) -> **AS14593 (SpaceX Starlink)** -> AS154100 (BNL Tarawa, Kiribati) -> a one-hop ICMP-filtered gap -> target (AS132486) never resolved. RIS's neighbor list for AS132486 lists AS154100 with an *exact* matching observation count (362) — a genuine, confirmed adjacency, added to `confirmed_local_transit.py`. **But read exactly what it confirms, not more**: AS154100 and AS132486 are both Kiribati-registered ASNs — this is a domestic (intra-Kiribati) relationship, not evidence either way about FM<->KI peering. The actually novel, notable part is the path itself: FSM-sourced traffic bound for Kiribati transits Guam, an Australian carrier, and a satellite constellation before it ever touches a Kiribati-registered network. Not filed as a `ConfirmedDetour` — no hop landed inside any registered IXP LAN prefix; this is a plain carrier-to-carrier transit chain across the open internet, a different shape than the named-exchange crossings that dataclass is built to capture — but real, useful color, and the first time this project's traceroutes have ever observed a Starlink hop.

**Verified by regenerating and looking at every surface again**: ASCII/HTML sections read correctly; the geographic map correctly draws no visible new line for this entry (both endpoints are the same economy, Kiribati, so the line has zero length — not a bug, just nothing new to show geographically for a same-country adjacency); the presentation's new slide heading is a clean single line.

**Queued, not done this tranche**: an actual test of the AS10130<->AS132486 IRR lead specifically would need either an ASN-targeted probe selection that works for AS10130 (country-based selection can't guarantee which in-country ASN's probe answers), or accepting that FSM's zero-to-few connected probes may not offer a choice at all.

---

**[User-directed follow-up — checked directly whether AS10130 has a usable Atlas probe, per the project owner's ask to "test AS10130 directly if a probe exists."]**

Checked RIPE Atlas's own probe registry directly rather than just retrying with `source_type="asn"` and reading whatever error came back: `GET /api/v2/probes/?asn=10130&status=1` returns **zero currently-connected probes**. Widened the check to every probe ever registered against AS10130 regardless of status: **exactly one, ever** — probe `26163`, status **Abandoned**. Also confirmed empirically that attempting `create_traceroute_measurement(source_type="asn", source_value=10130, ...)` fails outright (`400 Bad Request`), consistent with the zero-connected-probes finding and this project's already-documented pattern (most in-scope ASNs fail ASN-based selection the same way — this is exactly why country-based selection became the practical default in Phase 1b).

**Conclusion, folded into the AS154100<->AS132486 entry's note** (the one this question came from): the AS10130<->AS132486 relationship isn't merely untested by the last tranche's measurement — it currently **cannot** be tested via Atlas at all, by any probe-selection method, until either a new probe gets deployed on AS10130 specifically or the abandoned one comes back online. Worth remembering as a general pattern, not just for this one ASN: an economy showing "adequate" (2+) connected-probe coverage in the probe-gap report (FM currently shows 3) does not mean every individual ASN of interest within that economy is actually reachable — economy-level coverage and per-ASN testability are different questions, and this project's existing tooling only answers the first one directly. Not building new tooling for this distinction right now (a single confirmed instance doesn't yet justify it) — noted here so it's not forgotten if it comes up again.

---

**[User-directed tranche — investigating a PeeringDB network the project owner pointed at (AS141682, ARENA-PAC), which led to a real ASN-registry gap fix, a live cross-RIR audit of all 20 economies, a real data-loss bug caught and fixed in `irr_leads` before it could compound, and a new secondary data source (bgp.tools).]**

**Investigated `peeringdb.com/net/38357` (AS141682, "ARENA-PAC" — Arterial Research and Educational Network in the Asia Pacific).** Real, live: originates `103.161.244.0/23`, RIS shows 331 path observations dominated by AS2500 (WIDE Project, Japan's academic network) as its upstream. Its own PeeringDB IXP memberships include **GOREX** (Piti, Guam — already a confirmed in-fishbowl exchange) and BBIX Singapore, plus facility presence at RTI Guam GNC and Equinix Singapore. Registered under APIDT Infrastructure Pty Ltd (Australia, per RIPEstat and independently confirmed via bgp.tools' own cc=AU) — a real pan-Pacific R&E backbone, not itself one of this project's 20 economies' own delegated ASNs (same category as AS4637/Telstra Global or AS132528/Digicel Australia: relevant external infrastructure, not an in-scope entity to add to the registry).

**Checking GOREX's real membership (via `fetch_ixp_members`) to see who ARENA-PAC actually peers with there surfaced a genuine registry gap.** GOREX's 5 real members: ARENA-PAC, RouteViews (University of Oregon), REANNZ (New Zealand's R&E network, out-of-fishbowl), University of Hawaii (out-of-fishbowl), and **University of Guam (AS395400)**. University of Guam is unambiguously real and Guam-based (originates `192.149.202.0/24` and `168.123.0.0/16`, physically present at GOREX) — but was completely absent from this project's ASN registry. Checked why directly: **AS395400 is registered under ARIN, not APNIC** — and this project's entire ASN-discovery mechanism (`discovery.apnic_stats` + `discovery.registry`) only ever reads APNIC's own delegated-stats file. A real, live instance of the "known limitation" already flagged generically in this file since Phase 0b, now concretely confirmed.

**The project owner asked directly to check for this pattern more broadly ("check for ARIN registrations from US protected territories inside the fishbowl").** Used RIPEstat's `country-resource-list` endpoint (aggregates delegated resources across *all* RIRs, not just APNIC) to cross-check all 20 in-scope economies at once — cheap (20 calls) and precise. Result: **11 ASNs missing from this project's registry across 4 economies** (GU: 1, MH: 8, PW: 1, VU: 1); the other 16 economies, including all three French Pacific territories (NC, PF, WF), showed zero gaps.

**Correcting an assumption before it went further**: the project owner's follow-up guess ("RIPE NCC, that makes sense for French territories") turned out not to match what was actually found — none of MH, PW, or VU are French territories, and the French ones showed no gap at all. Checked each of the 11 candidates individually rather than accepting the country-resource-list attribution at face value (same discipline as the AS24013 anycast/hosting case): only **1 of 11** held up as real presence (University of Guam — verified via its actual GOREX peering). The other **10** (8 "Marshall Islands" + 1 "Palau" + 1 "Vanuatu", all RIPE NCC-registered) show generic hosting-company-style holder names (CenturyNetworks, iSH Transit, ISECLAYER, Apex Node, HDM Solutions, Hyper Data Transit, NALMI, a personal name, and "Owl Limited") and, where PeeringDB has any facility data at all, facilities nowhere near the Pacific (AS62880: Amsterdam only; AS43357/"Owl": Hong Kong, Osaka, Sydney, Los Angeles, Fremont, Tallinn). Marshall Islands in particular is a well-known offshore corporate-registration jurisdiction, unrelated to physical Pacific presence — a country code on an ASN registration records where an entity chose to incorporate, not where its network runs.

**Built `discovery.bgp_tools`, a new *secondary* source, per the project owner pointing at `bgp.tools/kb/api` (and, separately, `bgp.tools/asns.csv` directly).** Explicitly framed and documented as secondary/corroboration-only, same "lead, not ground truth" status as PeeringDB — never used alone to confirm a finding. Two capabilities: `fetch_asn_names` (bgp.tools' ASN name/class/country export — the `class` field, e.g. "Eyeball" vs "Content" vs "Unknown", isn't available from any of this project's other sources) and `fetch_prefix_visibility` (a live global BGP table dump with per-prefix visibility "Hits" counts, streamed and filtered rather than loaded whole — the full file is ~70MB/1.5M rows). Required a real, identifying `User-Agent` per bgp.tools' own terms (generic ones risk being blocked) — asked the project owner what contact to use rather than guessing, given it's committed to a public repo; using the GitHub repo URL. Both endpoints cached locally under `data/bgp_tools/`, respecting bgp.tools' own posted cache-window guidance (24h for the ASN export, ~2h for the table dump).

**Used it immediately as independent corroboration for the 10-vs-1 real/not-real split above**: bgp.tools classifies all 10 rejected ASNs as "Unknown" or "Content" — none as "Eyeball" (a real access/subscriber network) — while its own `cc` field agrees GU for University of Guam. Doesn't add a genuinely independent geolocation signal here (bgp.tools' `cc` field just echoes RIR registration, same limitation already worked around via facility-presence checks), but the `class` field is a real, useful secondary confirmation the other sources don't offer.

**Extended the same tranche with `bgp.tools`'s community tags** (`fetch_tag_list`, `fetch_tag_members`), per the project owner's follow-up pointer. Verified end to end against real tags, not just the API shape: **AS43357 ("Owl Limited", the Vanuatu-claiming ASN already rejected above) is independently community-tagged both `vpsh` (VPS hosting) and `vpn`** — a third independent source now agrees it's a hosting/VPN provider, not a real Vanuatu ISP. Separately, **AS395400 (University of Guam) carries the `uni` tag** (reinforcing the decision to add it), and **AS14593 (SpaceX Starlink, the transit hop from two tranches ago) carries `satnet`** — a clean confirmation the tag data is trustworthy for exactly the kind of network-type question this project keeps running into.

**Fixed `analysis.irr_leads.build_irr_leads` to have the exact same "never silently discard already-confirmed data on rebuild" protection already applied twice to `ixp_lan_registry`.** Caught directly, not theoretically: re-running the full pipeline to propagate the University of Guam addition hit a PeeringDB rate-limited chunk, and the *un-guarded* `irr_leads` module silently dropped 3 of 36 previously-good entries (AS152735/AS-GUAMIX, AS153053, AS154410) from `data/analysis/irr_as_sets.json` — the exact same bug class, just not yet protected in this newer module. Fixed the same way: load existing leads first, and when a fresh fetch is missing an ASN that had one on record, keep the existing entry and log a warning rather than silently losing it. **Verified two ways**: (1) manually re-fetched and restored the 3 already-lost entries (37 total now, including a new one for AS395400 itself — a real declared-but-empty `AS-UNI-OF-GUAM` as-set), (2) re-ran the real CLI entry point again afterward to confirm the guard holds under normal conditions, with no further loss.

**Also surfaced, left correctly unresolved per governance**: propagating University of Guam's real IXP memberships (GOREX, MARIIX, and **JPIX Tokyo**) into `fishbowl.json` brought a new exchange into `ixp_lan_registry` — JPIX Tokyo — written as `TBA`, per this project's standing rule that a newly-discovered IXP is never auto-classified. Awaiting explicit confirmation before it becomes `True`/`False`.

**Verified everything by regenerating and looking at the actual output, same discipline as always**: registry rebuild confirmed 163->164 ASNs with nothing lost from the other 163; full pipeline re-run confirmed fishbowl/ixp_lan_registry/irr_leads all picked up the change cleanly; regenerated all reports/visualizations and confirmed JPIX Tokyo shows correctly as TBA in the IXP table.

**Not done this tranche (queued)**: an Atlas test of whether University of Guam's own traffic actually uses GOREX/MARIIX locally, or detours to Hawaii/NZ/Japan despite the local exchanges existing — a natural, well-motivated next test given Guam already has 9 connected Atlas probes (this project's best-covered economy). Also queued: `fetch_prefix_visibility` was built but not yet exercised against any specific in-scope ASN — a good candidate for a future tranche once there's a concrete question it would answer.

---

**[User-directed follow-up — confirmed JPIX Tokyo as out-of-fishbowl.]** Called `confirm_ixp_region(30, False)`. Verified: `data/analysis/ixp_lan_registry.json`'s entry for ix_id 30 now reads `in_fishbowl: false`, and **zero exchanges remain unconfirmed** (10 in-fishbowl, 21 out-of-fishbowl, 0 TBA — up from 30 total exchanges to 31 this session, all now classified). Regenerated and checked all reports/the map to confirm the change propagated cleanly.

---

**[User-directed follow-up — test University of Guam's traffic against GOREX.]** Checked first whether a connected Atlas probe exists on University of Guam's own ASN (AS395400) specifically, same check already applied to AS10130: zero connected, two ever registered, both Abandoned — same pattern, so sourced from Guam generally instead (9 connected probes, this project's best-covered economy).

Targeted University of Guam's own GOREX netixlan address (`192.35.145.18`, measurement `211038772`) directly from a Guam-sourced probe — the most direct way to ask "does this specific in-fishbowl exchange actually carry this specific network's traffic." Of 3 probes: one resolved nothing; one transited AS152735 then AS7131 (Northern Mariana Islands) before going dark, RIS disagreeing (not a finding); the third resolved cleanly to **AS3605 (Guam Cablevision, LLC)** as the last hop before the target, and RIS's neighbor list for AS395400 lists AS3605 with an **exact matching count (1,091)** — added as a new confirmed local-transit entry, a real domestic-Guam adjacency in its own right.

**But the actual motivating question came back inconclusive, and the note says so plainly rather than stretching the AS3605 result to answer it**: none of the 3 probes showed a hop landing inside GOREX's own registered LAN prefix (`192.35.145.0/24`) before the trail went dark. This doesn't confirm GOREX goes unused — ICMP filtering right at the target or at the exchange's own switch fabric explains the dark ending just as well as the traffic genuinely bypassing GOREX — so it's recorded as inconclusive on the question actually asked, distinct from (and not weakened by) the real AS3605 finding it produced along the way.

Verified by regenerating all reports/the map/presentation and checking the new entry renders correctly; the map draws no new visible line (both endpoints are Guam, same as the earlier Kiribati same-economy case — zero-length, not a bug).

**Noted mid-tranche, not yet actioned**: the project owner is setting up a PeeringDB API key (`secrets.yaml`, not yet added). `discovery.peeringdb` has made every request unauthenticated all session — very likely why PeeringDB's rate limit has been hit repeatedly (three separate fixes this session were needed because of it: `ixp_lan_registry`'s prefix-wiping bug, `irr_leads`'s entry-dropping bug, and the various retry-with-backoff additions). An authenticated key should raise that limit substantially. Queued for as soon as the key is actually in place — not done yet, and `secrets.yaml`'s contents will not be read directly, same handling as the existing Atlas key (loaded and passed as a credential, never logged or echoed).

---

**[User-directed follow-up — wired up the PeeringDB API key.]** New `discovery/secrets.py` (`load_peeringdb_api_key`), mirroring `atlas/secrets.py`'s exact pattern (same `FileNotFoundError`/`KeyError` shape, `secrets.yaml`'s contents never read into a response or logged — checked only its key names, `['ripe_atlas_key', 'peeringdb_api_key']`, never its values). Per the project owner, the key is **read-only** — matches this module's own usage anyway, since it only ever issues GET requests.

`discovery/peeringdb.py` centralized around a new `_get()` helper (replacing all 8 of its direct `requests.get` call sites) that attaches an `Authorization: api-key ...` header once a key is found, cached per-process rather than re-read from disk on every call. Degrades to unauthenticated requests if `secrets.yaml`/the key is missing, rather than raising — this project needs to stay usable by anyone who clones it without a key.

**Verified three ways, not just that it loads**: (1) confirmed the log line `"PeeringDB requests authenticated via secrets.yaml"` appears and a real API call succeeds; (2) confirmed the `Authorization` header is present and correctly formatted (`api-key <value>`) without ever printing the actual key; (3) re-ran the full pipeline to check the thing this was actually meant to fix.

**Honest result on (3): a real but partial improvement, not a complete fix.** The `net` endpoint (used by `irr_leads`) hit **zero** rate-limit warnings this run — every previous run this session reliably hit at least one. But the `ixpfx` endpoint (queried by `ixp_lan_registry`, one `ix_id` at a time, 31 in a row) still got rate-limited twice (`ix_id` 3794 and 4494) even authenticated — fewer than the 3-4 typically hit unauthenticated, but not zero. The already-existing "never let a failed refetch discard already-confirmed data" protections in both modules caught it correctly regardless (kept both exchanges' existing prefixes; verified afterward that 0 of 31 exchanges have empty prefixes and all 37 IRR leads are intact) — those defensive fixes remain load-bearing, not made obsolete by authentication.

---

**[Loop tranche — testing the queued AS3605<->Palau IRR lead properly, sourced from Guam this time rather than FSM.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

Two tranches ago's FSM->Palau test couldn't test AS3605's own declared transit relationship with Palau, since AS3605 (Guam Cablevision) is a *Guam* ISP — testing it needed a Guam-sourced probe, not an FSM one. Fired that directly: Guam -> AS17893 (Palau NCC), measurement `211044785`.

**Result: a second, independent reinforcement of AS17893's Guam IX presence, not a new confirmed adjacency.** All 3 probes reach the target in just 3-4 hops and land on the *exact same* Guam IX address (`103.142.153.18`) already confirmed twice before — this time from a different source economy (GU, not FM), a genuinely independent corroboration. The immediate upstream is AS152735 ("Guam Exchange", 2 of 3 probes) or AS17456 ("Pacific Data Systems", 1 of 3) — neither RIS-confirmed as an AS17893 neighbor, and AS152735's own name and IRR AS-SET ("AS-GUAMIX") strongly suggest it's Guam IX's own route-server/infrastructure ASN rather than a distinct peering relationship — so not given a new candidate entry of its own; folded as reinforcement into the existing AS139759<->AS17893 candidate's note instead of creating near-duplicate entries for what's really the same underlying exchange-fabric evidence.

**AS3605 itself did not appear on this path** — the specific lead its own IRR AS-SET named remains untested. Noted plainly in the entry rather than treated as resolved: testing it directly would need a probe actually hosted on AS3605, which Guam's country-based selection doesn't guarantee (same limitation already documented for AS10130) — queued, not chased further this tranche.

Verified by regenerating all reports and confirming the extended note renders cleanly in ASCII/HTML/presentation.

---

**[User-directed follow-up — sourced directly from AS3605, since a connected probe actually exists; plus a new persisted "good probes" registry, refreshed monthly.]**

Checked first, same pattern as AS10130/AS395400: `GET /probes/?asn=3605&status=1` — **2 connected probes** (329, 64953), a genuinely different answer this time. Fired an ASN-targeted (not country-based) traceroute directly from AS3605 toward Palau NCC (AS17893), measurement `211064438`.

**Result: a real, fully confirmed detour — the fourth in the project, and a new shape.** Both probes: AS3605 -> AS2497 (IIJ, Japan) -> **AS174 (Cogent Communications)** -> AS17893, fully contiguous. RIS agrees with an *exact* observation-count match (1,333 — matching AS17893's own neighbor list, on record since the very first time this ASN was checked several tranches ago). Added as a new `ConfirmedDetour` entry, but honestly labeled as different in kind from the other three: `ixp_crossings` was empty for both probes — this is plain global Tier-1 transit (Cogent, reached via Tokyo), not a named-exchange crossing, so the entry's `detour_ix_name` says that explicitly rather than implying an IXP that isn't there. Added a new `"Tokyo"` entry to `discovery.economy_coordinates.EXTERNAL_HUB_LATLON` to plot it — rendered and checked the map before calling it done; the line reads clearly (Guam's traffic detouring far north to Tokyo before reaching Palau, its next-door neighbor).

**Why this is the sharpest evidence yet for the project's actual thesis**: AS17893 has *confirmed, repeated* local exchange presence at Guam IX — three separate earlier measurements, two different source economies, all landing on the same address. Real local peering infrastructure exists for this exact corridor. AS3605's own default route to it simply doesn't use it. Not proof the exchange goes unused in general (a different Guam network's traffic was shown reaching AS17893 via Guam IX in an earlier measurement) — proof that at least one real Guam ISP's default path to a real Guam-IX-connected Palau network bypasses the local exchange entirely, choosing global transit via Japan instead.

**Second ask this tranche: a persisted, monthly-refreshed record of which specific ASNs have a connected Atlas probe**, so future tranches don't need an ad-hoc live API check every time (done three separate times this session already, for AS10130, AS395400, and now AS3605). Checked first whether Atlas's `/probes/` endpoint supports batching multiple ASNs in one query — confirmed empirically it doesn't (comma-separated `asn` returns `400`) — but realized the existing per-economy `country_code` query (already made once per economy, 20 calls total, by `atlas.probes.build_probe_coverage`) already returns each matching probe's own `asn_v4` field, so a full ASN-level registry needs the *same* 20 calls, not 164. New `atlas.asn_probes` (`build_asn_probe_registry`, `load_asn_probe_registry`, `has_connected_probe`), persisted to `data/atlas/asn_probe_registry.json`, wired into `pipeline.run_pipeline` as a fifth step (a read-only Atlas lookup, no credits involved, same free-API-only category as the other four) — refreshes automatically on the existing monthly cadence, no separate scheduling needed. New entry point `pacific-peering-atlas-asn-probes`.

**Verified against this session's own prior ad-hoc findings, not just that it runs**: the registry reports exactly `{3605: [329, 64953], 10130: [], 395400: []}` — matching every live check made earlier in this session exactly. Ran the full 5-step pipeline end-to-end afterward: all steps succeeded, **zero rate-limit warnings anywhere this run** (a first, for what it's worth — possibly the authenticated PeeringDB key helping more consistently, possibly just run-to-run variance; not claiming more than one clean run shows), and confirmed no data was lost (0 of 31 exchanges have empty prefixes, all 37 IRR leads intact).

---

**[Loop tranche — the ASN probe registry immediately paid off: a probe on Palau NCC itself, testing the AS3605 lead from the reverse direction.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

Used the new `atlas.asn_probes` registry (built last tranche) to scan for connected probes on every ASN with one — surfaced something not previously known: **AS17893 (Palau NCC) has its own connected probe (7455)**, meaning this project can finally source a traceroute *from* Palau, not just into it. Fired the natural complementary test to last tranche's AS3605-sourced measurement: AS17893 -> AS3605's own address, directly.

**Result: the cleanest single adjacency this project has ever observed.** One probe, fully contiguous, zero gap: AS17893 immediately followed by AS3605, and the crossing hop lands inside **GU-IX** (ix_id 463, in-fishbowl — a different, earlier exchange than the "Guam IX" ix_id 4494 seen repeatedly elsewhere this session). Checked directly: AS3605's PeeringDB record independently lists GU-IX as a real membership (not just inferred from this traceroute) — and AS3605's own IRR AS-SET is exactly the one that named all three Palau ASNs as a declared transit relationship two tranches ago. Still `ris_agrees: false` (AS3605's real 22-entry RIS neighbor list doesn't include 17893) — added as a new `CandidatePeering` entry, explicitly reasoned as the strongest hidden-peering candidate in the project so far (full contiguity + independently-confirmed exchange membership + matches the exact corridor the IRR lead named), but kept a candidate rather than promoted, on principle: Validation Rule 1 doesn't bend for how clean one traceroute looks.

Verified by regenerating ASCII/HTML/presentation and the map; both candidate entries render correctly (the new PW->GU line is short and visually close to the existing FM->PW one at this map's zoom level — a real rendering-scale limit, not a data bug; the underlying report text is independently confirmed correct).

**Mid-tranche, the project owner gave a substantial piece of forward-looking methodology worth preserving durably rather than losing to chat history**: use known "edge of the fishbowl" chokepoints — Hawaii, Sydney, Tokyo, all three now empirically confirmed as real transit points this session (Hawaii via GOREX's own University of Hawaii membership; Sydney via three confirmed detours; Tokyo via the AS3605->Cogent detour two tranches ago) — as *external* vantage points to triangulate Pacific-internal routing from outside-in, complementing the inside-out tests done so far. Framed explicitly as a large combinatorial space ("N*(N-1)*(N-2)... to use all possible probes in the fishbowl to explore ingress and egress, and find new pathways") — not something to brute-force in one tranche, but worth having real probe-availability data on hand for when a future tranche picks a specific corridor.

**Checked probe availability on every external chokepoint ASN already identified this session, so a future tranche can act immediately rather than re-deriving this**: University of Hawaii (AS6360) has **1** connected probe — directly usable, and notably the same ASN already confirmed as a real GOREX member alongside University of Guam, making "Hawaii -> University of Guam via GOREX" an obvious, well-motivated next edge-to-edge test. IIJ (AS2497, Japan) has 12; Cogent (AS174, global Tier-1) has 12 (though a Cogent-hosted probe could be anywhere in the world, not necessarily Pacific-relevant — would need a specific probe's own geolocation checked, not just the ASN); GTT (AS3257) has 6. Digicel Australia/Telstra backbone (AS132528), Telstra Global (AS4637), and REANNZ (AS38022) all show **zero** connected probes on those specific ASNs — country-based selection into AU/NZ would still work generically, just not pinned to those specific transit networks. French Polynesia's existing 6-probe coverage (AS9471) was also flagged by the project owner as a good triangulation base — already this project's best-covered economy, used as vantage point for the FJ<->VU local-transit finding already.

**Not fired as a new measurement this tranche** — this hour already covered two live traceroutes (this one, and last tranche's AS3605-sourced one); the Hawaii->Guam/GOREX test is well-specified and ready, queued for the next tranche rather than adding a third live measurement to one already-full hour.

---

**[User-directed follow-up — fired the queued Hawaii->Guam/GOREX test, plus a matching test from ARENA-PAC itself (which also turned out to have 2 connected probes).]**

Fired both: AS6360 (University of Hawaii) -> University of Guam (AS395400), and AS141682 (ARENA-PAC) -> the same target, both ASN-sourced directly.

**Hawaii -> Guam (measurement 211075817): a real, RIS-confirmed adjacency, but not fully proven by Atlas alone, and not a GOREX crossing.** AS6360 resolves as the last ASN before an unresolved gap leading to AS395400; RIS's neighbor list for AS395400 lists AS6360 with an *exact* matching count (40) — same "matches exactly, but a real gap remains before the very last hop" shape as the AS38442<->AS9249 finding. Not added as a new dataclass entry: AS6360 is Hawaii, explicitly out-of-scope for this project, and this path doesn't connect two in-region economies (Guam's own external connectivity to Hawaii isn't itself a "detour" by the project's definition — it's simply confirmed real external dependency, expected for an island economy, not sub-optimal intra-Pacific routing). Recorded here in prose as real, useful context: University of Guam's confirmed RIS neighbors now include both AS3605 (Guam, local) and AS6360 (Hawaii, external) — a real multi-homed picture, not a single answer.

**ARENA-PAC -> Guam (measurement 211075819): fully contiguous, both probes, and a third independent reinforcement of the existing AS3605<->AS395400 finding — not a new adjacency.** AS141682 -> AS2500 (WIDE Project, Japan) -> AS2497 (IIJ, Japan) -> AS3605 -> AS395400, landing on the exact same RIS-confirmed 1,091-observation adjacency already in `confirmed_local_transit.py`, now corroborated from a third, genuinely distant vantage point. Folded into that entry's note rather than creating a duplicate. **The notable part**: ARENA-PAC and University of Guam are both confirmed GOREX members (mapped two tranches ago) — yet this traceroute between two of GOREX's own members still doesn't cross GOREX, going via Japan and Guam Cablevision instead. Same pattern as the AS3605->Cogent/Tokyo confirmed detour: a real local exchange, real confirmed members, and real measured traffic between them that still doesn't use it.

Verified by regenerating ASCII/HTML/presentation and confirming the extended note renders correctly.

---

**[Loop tranche — Niue, untouched by this project until now, tested directly using the probe registry; a clean confirmed finding with a real operational nuance.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

Used the ASN probe registry to pick the next genuinely novel corridor: **AS55885 (Niue, "No. 1 Commercial Center") has a connected probe**, and Niue had never been tested as a source or target all session. Checked its real RIS neighbor list first before firing anything — exactly one entry: **AS55943, 1,662 observations** — which two separate IRR-declared leads (from Samoa's AS38800 and French Polynesia's AS55943 itself, both surfaced in the bulk IRR sweep several tranches ago) had pointed at from different directions; RIS settles which one is real before any traceroute was even needed.

**Hit the same environment memory-kill issue as before, recovered the same way**: the measurement was already created server-side (confirmed via the partial log) before the background process was killed; re-ran the results-fetch in the foreground, which completed cleanly.

**Result: a real confirmed adjacency, with a genuine operational nuance worth stating precisely rather than glossing over.** The traceroute (sourced directly from Niue, targeting AS55943) resolved cleanly and contiguously — but to **AS9471**, not the literal target. Checked directly: AS9471 and AS55943 share the exact same PeeringDB/RIPEstat holder name ("ONATI-AS-AP - ONATI", French Polynesia's telecom incumbent), and AS9471's own RIS neighbor list independently confirms AS55943 with 1,838 observations — proving they're sibling ASNs of the same real operator, not a coincidence. `check_neighbor_agreement` reports `ris_agrees: false` on a strict same-ASN reading, since AS9471 isn't literally in AS55943's own neighbor list — but the underlying real-world relationship (Niue <-> ONATI) is the exact one RIS already confirmed via AS55943's 1,662 observations. Added as a new `ConfirmedLocalTransit` entry, with the ASN-identity nuance stated plainly in the note rather than either quietly using whichever ASN made the numbers match or discarding a real, well-evidenced finding over which of one company's two ASNs a hop happened to resolve to.

Verified by regenerating ASCII/HTML/presentation/map; the new NU<->PF line renders clearly and distinctly on the map (unlike the earlier same-economy candidates, this connects two different, well-separated economies).

---

**[Loop tranche — Tuvalu's first test surfaced a real, generalizable gap in `check_neighbor_agreement`, not just a one-off finding; fixed and fully regression-checked.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

Checked Cook Islands (AS10131) and Tuvalu (AS23917) — both have connected probes via the registry, neither tested all session. **Cook Islands' dominant neighbor is AS12684 (SES Astra, a major geostationary satellite operator) — a second real satellite-transit finding for this project, alongside the earlier Starlink one, not chased further this tranche but worth noting.** Tuvalu's RIS neighbor list is short and decisive: exactly two entries, AS9241 (FINTEL, **Fiji's own international carrier — in-scope**, 1,009 of ~1,700 total observations) and AS14593 (Starlink, 714). Fired the obvious first test: Tuvalu -> FINTEL, directly.

**Result: fully contiguous, a direct single AS-level hop, no gap — but `ris_agrees: false`.** Checked why directly rather than accepting it: `check_neighbor_agreement` only ever checked the *target*'s (FINTEL's) own RIS neighbor list, and FINTEL's list — aggregated across a much larger, more globally-visible network — simply doesn't mention AS23917 at all, even though Tuvalu's own list shows FINTEL as its clearly-dominant relationship. **This isn't a one-off quirk — it's the same asymmetric-RIS-visibility pattern already worked around manually for the Niue/ONATI finding last tranche**, just now understood as a real, generalizable gap in the checking function itself rather than something to reason around case by case.

**Fixed `check_neighbor_agreement` (new `_bidirectional_ris_check` helper) to check both directions** — the target's neighbor list for the upstream, *and* the upstream's neighbor list for the target — agreeing if either side shows the relationship. The original one-directional check remains the first-checked path, so any already-confirmed result is structurally guaranteed to return the identical count it always did; only previously-`false` results can newly become `true`, and only when real data on the other side supports it.

**Verified with a full regression check, not just the one motivating case**: re-ran all 20 measurements this project has ever fired under the fixed code. Every previously-confirmed adjacency kept its exact original count — zero regressions. The Tuvalu case now correctly shows `ris_agrees: true` (1,009). And, satisfyingly, **the fix automatically re-derived the exact same Niue<->ONATI relationship** already reasoned through by hand last tranche: measurement `211091699` now shows `ris_agrees: true, count: 1838` fully automatically (the AS9471<->AS55943 sibling-ASN count already used as supporting evidence in that entry's note) — independent confirmation the fix generalizes correctly, not just patches one case.

Added Tuvalu<->FINTEL as a new `ConfirmedLocalTransit` entry. Verified by regenerating all reports/the map; the new FJ<->TV line renders clearly.

---

**[Loop tranche — the queued Cook Islands/SES Astra satellite-transit test, fired and honestly inconclusive.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

Fired the test flagged last tranche: Cook Islands (AS10131) -> AS12684 (SES Astra, a major geostationary satellite operator, dominant in AS10131's own RIS neighbor list with 762 observations). No connected Atlas probe exists on AS12684 itself, so only this one direction was testable.

**Result: real gaps throughout, and the path never got close enough to SES Astra to confirm or deny the relationship directly.** The resolved AS sequence: AS10131 -> AS9471 (**ONATI**, French Polynesia — the same operator confirmed for both the Niue and Cook Islands corridors) -> AS6939 (Hurricane Electric) -> AS12684 (target, never actually resolved as a hop itself — the last resolved ASN was Hurricane Electric, a generic global transit carrier). Every transition shows `contiguous: false` — real unresolved gaps between each resolved AS, not a clean chain. `ris_agrees: false` (checked bidirectionally, per last tranche's fix — no data either direction for AS6939<->AS12684).

**Not added as a new finding.** The ONATI hop reappearing is consistent with AS10131's own RIS data (AS55943/ONATI is its second-place neighbor, 658 observations) but doesn't freshly *confirm* it here — there's a real gap between AS10131 and AS9471 in this specific traceroute, unlike the clean, contiguous Niue case. And the actual motivating question (does Cook Islands really use SES Astra) stays open: the trail goes cold at a generic transit carrier, nowhere near SES Astra's own network. Recorded honestly as inconclusive — real color, not a confirmed or candidate finding, consistent with how this project has treated every other dead-end result (the Fiji-IXP/GTT tests, the original FSM->Palau attempts) rather than stretching a partial path into a claim it doesn't support.

---

**[User-directed follow-up — checked directly whether AS12684 (SES Astra) has a usable Atlas probe, per the project owner's ask.]** Same check already applied to AS10130 and AS395400 earlier this session: **zero currently-connected probes**, and all **5** probes ever registered against it are **Abandoned**. Sourcing directly from SES Astra isn't possible right now, by any probe-selection method — closes out this corridor for the time being. The reverse direction (Cook Islands -> SES Astra, last tranche) remains the only data on record for this pair, and it's honestly inconclusive.

---

**[Loop tranche — PNG DataCo tested as a source for the first time (previously only ever a target), testing symmetry of this project's very first confirmed finding.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire.

AS17828 (PNG DataCo) was this project's first-ever confirmed detour target (GU->PG via Equinix Sydney, Phase 1b). It has a connected probe but had never been used as a *source* — a natural symmetry check: does PNG's own outbound traffic also show out-of-region dependency, or was the original finding one-directional? Fired PNG DataCo -> Guam Cablevision (AS3605, already well-characterized this session).

**Result: fully contiguous, reaches the target directly — and splits into two distinct findings that don't fit any single existing category cleanly, so documented in full rather than forced into one.**

1. **AS17828 (PNG DataCo) -> AS4826 (Vocus Connect International Backbone) is a real, solid, RIS+Atlas-confirmed adjacency**: exact match, 202 observations (PNG DataCo's own RIS neighbor list has carried this figure since Phase 1a). Vocus is Australia-based — out of scope for this project, same category as the already-excluded AU/NZ/Hawaii.
2. **AS4826 -> AS3605 (the actual target) crosses Any2West** (Los Angeles, out-of-fishbowl) — the hop's address resolves via an exact PeeringDB netixlan match to AS3605 itself, so AS3605's presence there is a hard fact, not an inference. But `ris_agrees: false` (checked bidirectionally, per the fix two tranches ago) for the specific AS4826<->AS3605 pair.

**Why this doesn't become a new `ConfirmedDetour` or `CandidatePeering` entry**: the RIS confirmation sits on the *first* leg of a three-ASN chain (source -> intermediate), not the leg immediately before the target the way every existing entry's evidence does — claiming a confirmed "PG detours to Guam via Any2West" would overstate what's actually confirmed (the Any2West leg specifically isn't RIS-backed), while a candidate-peering entry naming Vocus as "upstream" would understate the genuinely solid PG<->Vocus relationship by filing it as unconfirmed. Recorded here in full rather than stretched to fit either existing shape or invented a new one for a single data point — consistent with this project's established restraint (the AS4637/Telstra Global and Starlink transit-chain cases were handled the same way).

**Notable in its own right**: this is AS3605's *third* distinct confirmed-or-independently-verified IXP presence surfaced this session (GU-IX for the Palau corridor, Any2West here, alongside its seven total PeeringDB-listed memberships) — reinforcing that AS3605 (Guam Cablevision) is a genuinely well-connected, multi-exchange regional carrier, not a single-homed network.

---

**[User-directed follow-up — "do we have all IXPs now? With the API key, we can do a per-economy search."]** A real, well-motivated question: `build_ixp_lan_registry` has only ever discovered exchanges *indirectly*, via `fishbowl.json`'s IXP memberships — an exchange only ever surfaces if one of this project's 164 tracked ASNs happens to be a member of it. An exchange with zero tracked-ASN members (a newer one, or one our registry just hasn't reached) would never appear, no matter how real it is. Now that PeeringDB requests are authenticated, a direct per-economy search (`ix?country=<cc>`) is cheap and was worth doing for real, not just discussing.

**Ran it directly against all 20 economies before writing any code**: 12 real exchanges surfaced across 6 economies (FJ, PG, VU, NC, GU, plus zero for the other 14 — including SB, matching the already-known Solomon Islands gap this project separately tracks via `supplementary_ixps.py`). **Cross-checked against the existing registry: zero missing.** Better than that — the 10 unique exchanges this direct search actually returns (some economies have several: PG has 3, GU has 4) **exactly match, ID for ID, this project's entire confirmed in-fishbowl set** built up one manual confirmation at a time across many earlier tranches. A clean, independently-derived validation of all that careful classification work, not a gap-finding exercise after all — though the check itself is still worth having permanently, to catch a *future* new exchange as PeeringDB's own data grows.

**Built it as a proper second discovery path, not a one-off script**: new `discovery.peeringdb.fetch_ixp_by_country` (per-economy `ix` search, one call each) merged into `analysis.ixp_lan_registry.build_ixp_lan_registry` via a new `_collect_ixps_by_country`, alongside the existing membership-based path — both feed the same registry, membership data taking priority on overlap since it carries more fields. A new exchange found only via country search still gets written `TBA`, never auto-confirmed, even though "found via searching within economy X" might seem safe to treat as automatically in-fishbowl — that's exactly the kind of inference the existing governance rule exists to prevent.

**Immediately hit a real bug on the very first live pipeline run — the exact same class already fixed three times this session for sibling functions**: `fetch_ixp_by_country` had no retry/backoff at all, and a `429` on `ix?country=GU` failed the entire `ixp_lan_registry` pipeline step outright (caught by `pipeline.py`'s per-step exception handling, so the other four steps still completed — but this one didn't). Fixed the same way as `fetch_ixp_prefixes`/`fetch_ixp_members`/`fetch_irr_as_set_names` before it: retry with backoff, degrade to skipping just that country after retries exhaust, never crash the whole run.

**Verified by re-running the full pipeline twice** — once to catch the bug live (not hypothetically), once after the fix to confirm it actually resolves it: `ixp_lan_registry` now reports `status: ok` cleanly, same correct result both times (31 exchanges, 10 in-fishbowl, 21 out-of-fishbowl, 0 TBA, 0 exchanges with empty prefixes). This capability now runs automatically every pipeline cycle, same monthly cadence as the other four steps — a permanent, ongoing "do we have all IXPs" check, not a one-time answer.

---

**[Loop tranche — a real process miss this time, caught and corrected honestly rather than buried.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire. Picked up the flagged "natural next check" from the FSM->Palau candidate-peering note: AS3605 (Guam Cablevision) now shows 2 connected Atlas probes in the ASN probe registry, so the specific untested lead — sourcing directly from AS3605 toward AS17893 — was finally testable.

Fired it (measurement 211181370, `create_traceroute_measurement(source_type="asn", source_value=3605, ...)`). Hit the environment's recurring memory-kill issue twice on the results-fetch (both auto-backgrounded by the harness after its own 120s foreground window, then killed by the host's own memory pressure before `wait_for_results`'s 180s internal deadline could return). Fixed by calling `wait_for_results` with an explicit shorter `max_wait=70.0` so the whole script — including the deliberate partial-results fallback — finishes inside the harness's foreground window; completed cleanly with 2 of 3 probes returned.

**Only after running it through the triangulation checker did I realize this exact corridor was already tested and confirmed** — `confirmed_detours.py` already has a `ConfirmedDetour` entry for this same GU(AS3605)->PW(AS17893) pair (measurement 211064438, fired in an earlier tranche after the project owner asked for it specifically), with the identical path (AS3605 -> AS2497/IIJ -> AS174/Cogent -> AS17893) and the identical RIS observation count (1,333). **Should have grepped the existing dataclasses for this ASN pair before firing a new measurement — a real gap in this tranche's own process, not just an interesting coincidence.** Caught it before compounding the mistake: had already drafted a large "asymmetric routing, new finding" addendum to `candidate_peering.py`'s PW->GU entry describing this as new — reverted that (would have duplicated and mis-framed an existing confirmed finding as new/unconfirmed content in the wrong module) and instead added a short, honest corroboration note to the *existing* `confirmed_detours.py` entry: two independent measurements, fired in different tranches, produced the identical path and the identical exact observation count — real added confidence in an already-confirmed finding, not a wasted measurement, just not the new result it looked like at first.

Verified: both edited dataclass modules still import cleanly; regenerated the ASCII and HTML reports and checked the affected sections directly — the GU->PW entry now carries the corroboration note with no duplication, and the PW->GU candidate entry correctly cross-references it instead of restating it. No map regeneration needed (no geographic edge changed, only prose).

**Takeaway for future tranches, stated plainly so it isn't just a private lesson learned quietly**: before firing any new measurement toward a specific ASN pair, grep `confirmed_detours.py`/`confirmed_local_transit.py`/`candidate_peering.py` for both ASNs first — this project has enough accumulated findings now that "surely this hasn't been tested" is no longer a safe assumption to skip checking.

---

**[Loop tranche — applied the new process rule immediately, and it paid off: a genuinely new, clean finding.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire. Picked up the two still-untested Palau ASNs from AS3605's own declared AS-SET (17893 confirmed already, 58932 and 133897 not): grepped `confirmed_detours.py`/`confirmed_local_transit.py`/`candidate_peering.py`/`task_plan.md` for both numbers first, per last tranche's own lesson, and confirmed neither had been tested by a traceroute yet (only ever mentioned in the IRR-lead prose).

Sourced AS3605's own connected probes toward AS58932 (measurement 211185048; kept to one new measurement this tranche, not both, per "small tranches"). Applied last tranche's `max_wait=70.0` fix proactively this time rather than rediscovering the memory-kill issue — completed cleanly in the foreground on the first attempt, no backgrounding, no kill.

**Result: a real, clean, genuinely different finding from the AS17893 corridor.** Both responding probes show AS3605 immediately adjacent to AS58932 -- zero intermediate hops, no external hub, no IXP crossing. RIS agrees with an exact observation-count match (664), and checked AS58932's own RIS neighbor list directly: only two entries total (AS24545: 704, AS3605: 664), so this is one of its two dominant relationships, not a coincidence. Looked up both ASNs' holder names via RIPEstat before writing anything: AS58932 is Palau Mobile Communications Inc., AS133897 is Palau Equipment Co. Inc. Added as a new `ConfirmedLocalTransit` entry (GU/AS3605 -> PW/AS58932).

**Notable, and worth stating plainly**: the same declared AS-SET names both AS17893 (routed via Tokyo/Cogent transit, per the earlier confirmed detour) and AS58932 (routed directly, no transit at all) -- real traffic paths diverging sharply between two customers named in the same IRR declaration. A concrete illustration of why this project treats IRR data as a lead, never ground truth (Validation Rule 5): the declaration is accurate for both, but says nothing about how differently each relationship is actually implemented.

**AS133897 (Palau Equipment Co. Inc.) is now the obvious next check, not just a leftover**: its RIS data shows AS3605 as its *only* neighbor at all -- 662 of 662 observations, a 100% single-neighbor signal, the strongest of any ASN tested this project. Left untested this tranche deliberately (one new measurement per tranche, per the working agreement) -- flagged clearly for the next `/loop` firing.

Verified by regenerating ASCII/HTML reports (new entry renders correctly, no duplication) and the geographic map (SVG re-rendered; now shows 6 green confirmed-local-transit lines, matching the 6 entries in the updated dataclass, up from 5 -- confirmed by counting the rendered `line2d` elements directly rather than assuming the regeneration worked).

---

**[Loop tranche — completed the AS3605 IRR-lead test: fired the flagged AS133897 check, exactly as the RIS signal predicted.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire. Re-grepped for "133897" first (per the now-standing process rule) — still untested, as expected.

Sourced AS3605's own connected probes toward AS133897 (measurement 211193440), using the same `max_wait=70.0` foreground pattern — completed cleanly again, no backgrounding issue. **Result: confirmed exactly as predicted by AS133897's striking RIS signal** (AS3605 was its *only* RIS-observed neighbor at all, 662/662 observations, the strongest single-neighbor signal of any ASN tested this project). Both probes: AS3605 immediately adjacent to AS133897, zero intermediate hops, no external hub, no IXP crossing, exact RIS match (662). Added as a new `ConfirmedLocalTransit` entry.

**This completes the full test of AS3605's declared IRR AS-SET for Palau**, all three named ASNs now traceroute-tested from AS3605's own vantage point, with a consistent and genuinely informative picture: one customer (AS17893) reached via global Tokyo/Cogent transit, two (AS58932, AS133897) reached directly with zero intermediate hops. A real finding in its own right, not just three confirmations: a single Guam carrier's declared relationships to Palau are NOT uniformly implemented — exactly the kind of nuance this project's IRR-as-a-lead validation rule exists to surface rather than assume away.

Verified: module still imports cleanly (7 entries, up from 6); regenerated ASCII/HTML reports (renders correctly); regenerated the geographic map and counted the rendered SVG elements directly — 7 green `line2d` groups plus 1 legend swatch, matching the 7 dataclass entries exactly.

This closes out the AS3605/Palau IRR lead that's been tracked across four separate tranches now (FSM->Palau candidate three tranches ago -> AS17893 corroboration two tranches ago -> AS58932 confirmed last tranche -> AS133897 confirmed this tranche). No further flagged item remains open for this specific corridor.

---

**[Loop tranche — gave `discovery.bgp_tools.fetch_prefix_visibility` its first real workout, against a concrete question.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire. This function has existed since earlier in the session but was never actually exercised — picked a genuinely useful question for it rather than just calling it to say it was called: **does bgp.tools' independent global vantage point (a different data source entirely from RIPEstat/RIS, this project's primary source) agree on the prefixes originated by the four ASNs central to this session's freshest, most-scrutinized findings** (AS3605, AS17893, AS58932, AS133897 -- the just-completed Palau/Guam corridor)?

Fetched bgp.tools' full table dump for the first time this session (~70MB, cached locally per its own posted guidance, 2-hour freshness window) and cross-checked every RIS-cached originated prefix for these four ASNs against it programmatically, not by eyeballing.

**Result: complete agreement, 16 of 16 RIS-cached prefixes independently confirmed by bgp.tools, for all four ASNs, zero discrepancies.** Visibility ("Hits") counts on the matched prefixes range 744-2802 -- comfortably high, no near-zero or suspicious counts that would suggest a leaked, hijacked, or barely-propagated announcement. AS3605 additionally showed 26 more prefixes in bgp.tools' data that RIS's cache didn't include -- expected, not a discrepancy: Phase 1a deliberately capped RIS prefix caching at 5/ASN to bound API load (documented at the time as a scope limit, not a completeness claim), so bgp.tools' fuller picture is exactly the kind of secondary-source value this integration was built for. AS17893 similarly showed 3 extra (including an IPv6 /32 RIS's IPv4-only fetch wouldn't have captured anyway).

**Why this is a real, if modest, validation result and not just busywork**: this project's Validation Rules already require two *topology* sources (RIS + Atlas) to agree before trusting an adjacency claim; this is the first time a third, independent *origination* source has been checked against RIS at all, for any ASN. A clean match across the board is real, if unsurprising, corroboration that this session's RIS-based prefix targeting (which every single traceroute this project has fired ultimately depends on, via `pick_target_ip`) is aimed at real, globally-visible, uncontested announcements -- not, say, a stale or locally-hijacked route that happened to still be in RIS's cache. Not treated as a new topology finding (it says nothing about peering/detours) and not added to any of the three finding dataclasses -- it's a data-quality check, recorded here rather than invented a new module for a single one-off exercise.

---

**[Loop tranche — sourced from AS9471 (ONATI) for the first time, and found a genuinely new wrinkle in the resolver: private-address hops masquerading as an unresolved gap.]** Confirmed via `CronList` this was job `551adf11`'s scheduled fire. Picked from the remaining ASN probe registry: AS9471 (ONATI, French Polynesia) has 6 connected probes -- the most of any ASN tracked -- but had never itself been used as a traceroute *source*, only ever appeared as a confirmed endpoint (the Niue corridor). Checked AS10131 (Cook Islands)'s own RIS neighbor list for a well-motivated target: AS55943 (ONATI's sibling ASN, per the already-established Niue precedent) sits there as its second-largest neighbor (658 observations) -- flagged in passing during the earlier SES Astra tranche but never directly tested. Grepped first (per the standing process rule): untested, confirmed.

Fired AS9471 -> AS10131 (measurement 211227855; `max_wait=70.0` foreground pattern again, clean on the first try, all 3 probes returned). **Result needed real investigation, not just reading `ris_agrees` off the checker's output.** All 3 probes showed almost entirely RFC1918 private-address hops (10.x.x.x, 192.168.x.x) with exactly one public IP in between (103.254.224.70) before landing on AS10131's own address -- `check_neighbor_agreement` reported `contiguous: false, ris_agrees: false`, which on its face looks like an inconclusive result. **Didn't accept that at face value**: resolved 103.254.224.70 directly via RIPEstat (not assumed) -- it belongs to AS9471 itself. So every "gap" hop sits between two points already known to be inside AS9471's own network; there is no real unknown intermediary AS here at all, just private internal addressing the current resolver's gap logic can't distinguish from a genuinely-unresolvable external hop (the distinction the resolver is designed around -- "the true intermediate AS is unknown" -- simply doesn't apply when both endpoints of the gap are the same already-known AS). Cross-checked against the IP resolution cache directly to confirm this wasn't a stale/wrong cache entry -- it resolves the same way independently.

**Read correctly, this is effectively a direct, single-AS-hop path from ONATI to Telecom Cook Islands.** And exactly as established for the Niue corridor, RIS's real confirmation of this relationship comes via AS9471's sibling identity AS55943 (658 observations, an *exact* match to Cook Islands' own RIS data), not the literal AS9471 number the traceroute resolved to. Added as a new `ConfirmedLocalTransit` entry, applying the now-twice-used sibling-ASN reasoning on the same explicit, stated basis as the Niue case rather than treating it as a one-off exception.

**A genuine, generalizable observation for future tranches, not just this one measurement**: this project's traceroute resolver currently treats "private/RFC1918 hop" and "genuinely unresolvable hop" identically (both just fail `_resolve_address` and set `gap_pending`), but they mean very different things -- a private hop inside a network whose public boundary IPs are already known on both sides is not evidence of an unknown intermediary the way an unresolvable public IP is. Not fixed as a code change this tranche (a single occurrence doesn't yet justify a resolver change, and the manual-verification pattern used here — resolve the suspect IP directly, check both boundary ASNs match — is cheap and already established); flagged here so a future tranche can decide whether it recurs often enough to be worth automating.

Verified: module imports cleanly (8 entries, up from 7); regenerated ASCII/HTML reports (renders correctly) and the geographic map (9 `line2d` elements with the green stroke = 8 data lines + 1 legend swatch, matching the 8 dataclass entries).

---

**[Live user guidance, acted on immediately -- fixed the RFC1918 resolver gap flagged as an open question last tranche.]** The project owner responded directly to the AS9471->AS10131 finding: *"the use of RFC1918 address space and it presenting in traceroutes is interesting, obviously, those pacific networks don't [have] enough ipv4 for infrastructure, in simple terms, the best policy is to ignore the RFC1918 hops as it can't resolve to a real ASN globally, also, later in the project, we will have to consider ipv6 routing and adoption: for now ipv4 is everywhere."* Three real pieces of guidance: (1) a domain explanation for *why* private addressing shows up in these traceroutes -- IPv4 scarcity in Pacific network infrastructure, not a resolver quirk to work around case by case; (2) an explicit policy directive -- ignore RFC1918 hops entirely, since they structurally cannot resolve to a real ASN anywhere in the world, not just "unresolved for now"; (3) IPv6 flagged as a real future consideration, explicitly deferred -- IPv4 remains the project's focus for now, so no action taken on that part this tranche.

**Implemented the policy directly** in `analysis/traceroute_topology.py`: new `_is_private_address()` helper (`ipaddress.ip_address(address).is_private`, covering RFC1918 plus link-local/loopback for free). Checked *before* the IP resolution cache is even consulted -- important, not cosmetic: the cache already held stale entries for these exact addresses from before this distinction existed, cached identically to genuinely-unresolved public IPs (`{"asn": null, "source": null}`), and checking privacy first means those stale entries are never read again rather than needing a manual purge. `_resolve_address` now returns `(None, "private", None)` immediately for a private address, skipping any BGP/PeeringDB lookup entirely (also cheaper, not just more correct). `extract_as_sequence` now treats a hop whose `resolution_source == "private"` as fully transparent -- skipped without touching `gap_pending` in either direction -- rather than folding it into the same bucket as a genuinely-unresolvable public hop, which used to manufacture a gap that was never really there.

**Verified two ways, not just re-running the one motivating measurement.** First, re-ran AS9471->AS10131 (211227855) directly: `contiguous` flips from `false` to `true` for all 3 probes, exactly as intended; `ris_agrees` stays `false` on the literal AS9471/AS10131 pair (correctly -- RIS's real confirmation is via the sibling ASN AS55943, a separate and already-established piece of reasoning, not something this fix touches). Second, **ran a full regression check across every measurement this project has ever fired** (26 total, snapshotted before the fix and diffed after): zero changes to any `ris_agrees` verdict anywhere, exactly as expected since the fix only ever removes spurious gaps, never invents new adjacencies. `contiguous` flipped `false` -> `true` in exactly 4 measurements: the motivating one, plus three already-inconclusive Fiji/GTT dead-end tests (210990245, 210992503, 210992951 -- not referenced in any finding module, so no prose needed updating there) and, notably, **one already-confirmed finding's supporting evidence**: AS38442<->AS9249 (Fiji<->Vanuatu, this project's very first `ConfirmedLocalTransit` entry).

**That last one required a real correction, not just a note.** The existing entry had stated the final-hop gap was "checked directly: ordinary ICMP filtering, not an unlisted IXP" -- re-checked against the raw hop data under the new fix and that explanation was wrong: the gap was a single RFC1918 hop (`10.200.4.208`) immediately before AS9249's own address, not ICMP filtering at all. With the fix applied, this measurement is now fully contiguous end to end (AS6939 -> AS4637/Any2West -> AS38442 -> AS9249, zero gaps) -- the adjacency is now proven at the literal last hop, not just inferred from the last *resolved* one. Corrected the entry's note in place rather than leaving a now-known-wrong explanation on the record; this strengthens an already-confirmed finding, it doesn't change its status.

Regenerated ASCII/HTML reports and confirmed both corrected notes render cleanly. No map regeneration needed (no new/changed geographic edges, only prose and a resolver-level correctness fix).

---

**[User-directed follow-up — "check the ASN probe registry for another untested corridor."]** Scanned the 18-ASN registry for sources never yet used: 2200 (Renater, France -- external, not in-scope), 7131 (CNMI), 9249 (Vanuatu), 14593 (Starlink -- external), 17456/152735 (Guam), 17828 (PNG DataCo), 24390 (Fiji), 45345/56089 (New Caledonia), 53813 (Zscaler -- a known proxy artifact, not a real network), 10131 (Cook Islands). Looked up holder names for the unfamiliar ones before picking, rather than guessing from the ASN alone.

**AS24390 turned out to be the University of the South Pacific** -- Fiji-based, but a genuine multi-country regional institution with real campuses across the Pacific (including Emalus Campus in Vanuatu). Its only RIS-observed neighbor is AS7575 (AARNet, Australia's research/education network) -- directly relevant given ARENA-PAC/GOREX's research-network theme from earlier this session, and a well-motivated, institutionally real question: does USP's own Fiji<->Vanuatu inter-campus traffic route directly, or detour externally? Grepped first (per the standing process rule): untested.

Fired AS24390 -> AS9249 (measurement 211239396); only 1 of 3 probes returned in time (a small-tranche judgment call not to re-fire for the rest, given the one result already lands cleanly). **Result: a genuine new `ConfirmedDetour` finding.** Path: AS24390 -> AS7575 (AARNet) -> AS38442 (Vodafone Fiji) -> crosses MegaIX Sydney -> AS9249. Upstream-of-target is AS38442, RIS-agreeing with an *exact* match (1,346) -- the identical count already on record for this project's very first confirmed finding (AS38442<->AS9249). The final hop showed `contiguous: false`; checked directly against the raw hop data before accepting that, per the discipline established this session for exactly this situation -- hop 11 had no address at all (a true ICMP timeout), not a private-address artifact the just-shipped RFC1918 fix would have caught, so this is a legitimate unresolved final hop, not a resolver limitation.

**The real finding isn't the AS38442<->AS9249 adjacency itself** (already this project's most solid, now independently reinforced a third time, from a third vantage point) **-- it's that a Pacific regional university's own inter-campus traffic, between two islands roughly 1,100km apart, detours all the way out to Australia and back** rather than routing directly within the region. Exactly the sub-optimal transpacific routing pattern this project exists to document, and a genuinely fresh, institutionally-grounded example of it. Added as a new `ConfirmedDetour` entry.

Verified: module imports cleanly (5 entries, up from 4); regenerated ASCII/HTML reports and the geographic map (6 red `line2d` elements = 5 data lines + 1 legend swatch, matching the 5 dataclass entries).

---

**[New /loop cadence starts here.]** The project owner replaced the standing hourly job (`551adf11`, "over the plan... iterate slowly with small tranches") with a new one (`e47f6827`, same hourly cadence): *"over new data and find the next unknow corridor, document/log findings, update reports, update git (commit and push)"* -- more directive about the actual per-tranche action (find + confirm + document + ship a corridor each firing) than the prior more open-ended plan-review framing. Confirmed via `AskUserQuestion` before touching anything: session-only (not cloud), and replace rather than run both jobs in parallel (would have doubled up hourly work). Old job deleted via `CronDelete`, new one created via `CronCreate` at the same `:07` offset.

**First firing under the new prompt.** Scanned the ASN probe registry for the next untested-as-source ASN with real Pacific relevance: **AS7131 (Northern Mariana Islands / PTI Pacifica Inc., 3 connected probes)** had never been used as a source all session -- every prior appearance was as an incidental transited hop in someone else's measurement, never deliberately tested. Its own RIS neighbor list is otherwise generic global transit (Hurricane Electric, Arelion, Tata, Lumen, Cogent); the one Pacific-relevant entry, **AS152735 ("Guam Exchange," 381 observations)**, was the obvious pick -- a real, RIS-observed MP<->GU adjacency that had surfaced incidentally during the GOREX/University of Guam test several tranches ago but had never itself been the subject of a deliberate test from either side.

Fired AS7131 -> AS152735 directly (measurement 211241814; `max_wait=70.0` foreground pattern, clean, all 3 probes returned). **Result: unanimous and clean across all 3 probes** -- AS7131 immediately adjacent to AS152735, zero intermediate hops, no external hub, no IXP crossing, exact RIS match (381). **The first-ever traceroute confirmation involving Northern Mariana Islands as either endpoint** -- a genuinely new economy added to this project's confirmed topology, not just a new ASN pair within an already-touched economy. Added as a new `ConfirmedLocalTransit` entry, with the pre-existing open question about AS152735's true nature (real network vs. Guam IX's own route-server/infrastructure ASN, per its "AS-GUAMIX" AS-SET name) stated plainly rather than resolved by assumption -- this traceroute confirms the adjacency, not what kind of network is on the other end of it.

Verified: module imports cleanly (9 entries, up from 8); regenerated ASCII/HTML reports (renders correctly) and the geographic map (10 green `line2d` elements = 9 data lines + 1 legend swatch, matching the 9 dataclass entries). Confirmed MP has map coordinates (`economy_coordinates.py`, Saipan) before assuming the render would work.

---

**[Loop tranche -- second firing under the new prompt. A genuinely new economy pair (NC<->GU) tested, real evidence found, deliberately NOT forced into a dataclass.]** Confirmed via `CronList` this was job `e47f6827`'s scheduled fire.

Reviewed which economy pairs this project has tested so far before picking (not just which ASNs): NC has only ever been tested against FJ. **AS45345 (Nautile, New Caledonia -- 4 connected probes, an independent ISP, not the already-extensively-tested incumbent OPT NC/AS18200)** had never been used as a source; picked it specifically to test whether an *alternate* NC carrier's international routing also goes via Sydney/Australia the same way the incumbent's does, targeting AS3605 (Guam Cablevision) -- a genuinely untested economy pair (NC<->GU) in either direction.

Fired AS45345 -> AS3605 (measurement 211259107, all 3 probes returned). **Result: a real signal, but one that doesn't clear this project's confirmation bar, and was investigated properly rather than either force-fit or dismissed.** Path: AS45345 -> AS18200 (OPT NC, the incumbent -- Nautile still transits it for international reach) -> AS38195 (Superloop, an Australian carrier) -> crosses **Any2West** (confirmed via PeeringDB netixlan, AS3605 independently listed as a real member there) -> AS3605. `ris_agrees: false` -- checked directly against `fishbowl.json`: AS3605's real RIS neighbor list (22 ASNs) does not include AS38195 at all, so this fails Validation Rule 1 outright, not a borderline case.

**Investigated the reported gap before accepting `contiguous: false` at face value, same discipline as every prior tranche with a "gap."** Two hops sit unresolved right before the Any2West crossing (`103.200.13.67`, `103.200.13.168`) -- checked directly via RIPEstat: not RFC1918 (the recent fix correctly doesn't touch them), but WHOIS attribution shows both belong to Superloop's own address space (`netname: SUPERLOOP-AU`), just not currently BGP-announced/globally routed. **Verified rigorously, not just via the absence of an ASN in one lookup, per the project owner's direct follow-up question** ("Superloop has address space in use that is NOT present on global BGP tables?"): RIPEstat's `routing-status` API (not just `network-info`) shows **`ris_peers_seeing: 0` of 325 total RIS peers for both addresses, with `less_specifics: []`** -- literally zero of 325 RIS route collectors have ever seen a BGP announcement covering these addresses, at any prefix length, not just "currently unseen." And it's real, legitimately-allocated space, not a bogon or reserved range: WHOIS's `inetnum` record shows a full /22 (`103.200.12.0-103.200.15.0`) allocated to Superloop with `status: ALLOCATED NON-PORTABLE` -- APNIC gave it to them outright, they simply never announce it. A real, if different, resolver edge case from the AS9471 one: this is unannounced-but-WHOIS-attributable address space inside an already-identified AS's own network, not private addressing -- qualitatively the same "not really an unknown intermediary" situation, but via a different signal (WHOIS netname vs. RFC1918), and **not code-fixed this tranche** -- a single occurrence doesn't justify adding a fuzzier, less rigorous WHOIS-matching resolver tier alongside the exact BGP/netixlan attribution this project has relied on throughout; flagged here for a future tranche to decide if it recurs. Common, well-understood real-world ISP practice, not an anomaly: carriers routinely carve out allocated-but-unannounced space for internal router infrastructure (point-to-point links, loopbacks) that never needs to be reachable from the internet, only ever showing up as a traceroute hop's ICMP-reply source, never as an actual routed destination -- BGP-based resolution (RIS) is structurally blind to this category, not a data-quality gap in this project's own pipeline. **The project owner independently checked bgp.tools directly and found the precise split: Superloop routes only `103.200.14.0/24` and `103.200.15.0/24` out of its full /22.** Cross-checked immediately via this project's own `bgp_tools.fetch_prefix_visibility` integration rather than taking it on trust alone -- exact match: those are the *only* two `103.200.1x.0/24`s AS38195 announces (2,617 `hits` each, strong visibility), and `103.200.13.0/24` (containing both unresolved hop addresses) and `103.200.12.0/24` are absent from the list entirely. **Three fully independent sources now agree on the identical picture** (RIPEstat RIS's 0/325-peer visibility check, WHOIS's /22 allocation record, and bgp.tools' own routed-prefix list): Superloop's allocated /22 is split exactly in half, the top two /24s globally announced, the bottom two not, and this traceroute's hops landed squarely in the unannounced half -- as clean and thoroughly cross-validated an explanation for a "gap" as this project has produced for any finding.

---

**[Loop tranche -- third firing under the new prompt. A clean, fully-confirmed new economy pair, and NZ's first appearance as a transit waypoint.]** Confirmed via `CronList` this was job `e47f6827`'s scheduled fire.

Picked **AS56089 (OFFRATEL, New Caledonia)** -- a third distinct NC carrier tested this session (after the incumbent OPT NC and independent ISP Nautile last tranche), continuing the same live question (does every NC carrier detour externally, regardless of destination?) with a fresh target: **AS9249 (Telecom Vanuatu)**, a genuinely untested NC<->VU economy pair. Grepped first per the standing process rule: confirmed untested.

Fired AS56089 -> AS9249 (measurement 211285266); only 1 of 3 probes returned in time (same small-tranche call as the USP measurement -- not re-fired, the one result is already clean). **Result: fully contiguous, zero gaps, all 6 hops resolved cleanly** -- AS56089 -> AS18200 (OPT NC) -> AS4648 (**Spark NZ**, New Zealand's largest telecom) -> AS6939 (Hurricane Electric, both at Equinix Sydney) -> AS4637 (Telstra Global) -> AS38442 (Vodafone Fiji) -> AS9249. Upstream of the target is AS38442, RIS-agreeing with an *exact* match (1,346) -- this project's very first confirmed finding, now independently reinforced a **fourth** time, from a fourth distinct vantage point.

**Genuinely new color, not just another confirmation of the same adjacency**: this is the first measurement all session to show **New Zealand** (Spark NZ) as a transit waypoint, not just Australia. Sharpens this project's framing: the detour pattern isn't Australia-specific, it's "whichever excluded AU/NZ hub happens to sit on the path" -- exactly matching the Fish Bowl's own definition of the excluded zone (both AU and NZ, not just AU).

Added as a new `ConfirmedDetour` entry. Verified: module imports cleanly (6 entries, up from 5); regenerated ASCII/HTML reports (renders correctly) and the geographic map (7 red `line2d` elements = 6 data lines + 1 legend swatch, matching the 6 dataclass entries).

---

**[User-directed follow-up -- "find the next unknown corridor."]** Checked the RIPE Atlas credit balance first, per the same message thread: **95,715,160**, `estimated_daily_income: 63,569`, `estimated_daily_expenditure: 0`, `estimated_runout_seconds: null` -- balance is net *growing*, not depleting, at this project's actual usage rate. No action needed, nothing anomalous, so nothing to flag under the new standing order.

Picked **AS17828 (PNG DataCo)** -- already has a connected probe, used as a source once before (the earlier Vocus/Any2West split-chain finding) -- targeting **AS9249 (Telecom Vanuatu)**: a genuinely untested economy pair, PG<->VU, both Melanesian. Grepped first: confirmed untested.

Fired AS17828 -> AS9249 (measurement 211299647); again only 1 of 3 probes returned in time (same small-tranche judgment call as the last two "1 of 3" results -- not re-fired). **Result: fully contiguous, zero gaps** -- AS17828 -> AS4826 (Vocus Connect, PNG DataCo's own already-established upstream) -> AS1221 (Telstra Limited, Australia's *domestic* backbone) -> AS4637 (Telstra Global, the *international* arm of the same company) -> AS38442 (Vodafone Fiji) -> AS9249. Upstream of the target is AS38442, RIS-agreeing with an *exact* match (1,346) -- this project's very first confirmed finding, now independently reinforced a **fifth** time, from a fifth distinct vantage point (FSM candidate testing aside, five *confirmed* corroborations of one adjacency, from five different source networks, is unmatched by anything else in this project).

**Different in kind from the NC-sourced detours to the same target**: no hop landed inside any registered IXP LAN prefix this time (`ixp_crossings` empty) -- straight Tier-1 transit through Telstra's own network (its domestic and international ASNs appearing back-to-back) rather than a named-exchange crossing. `detour_ix_name` records that honestly, same convention already established for the AS3605->AS17893 Tokyo/Cogent entry, rather than implying an IXP that isn't there.

Added as a new `ConfirmedDetour` entry. Verified: module imports cleanly (7 entries, up from 6); regenerated ASCII/HTML reports (renders correctly) and the geographic map (8 red `line2d` elements = 7 data lines + 1 legend swatch, matching the 7 dataclass entries).

**Why this isn't filed as a new `ConfirmedDetour` or `CandidatePeering` entry, following the exact restraint already established for the PNG DataCo/Any2West split-chain case several tranches ago**: it has the *shape* of a detour (crosses a real, confirmed out-of-fishbowl exchange) but fails Validation Rule 1's RIS-agreement requirement outright, so it can't be `ConfirmedDetour`. And `CandidatePeering` is specifically for possible hidden peering *between two in-scope Pacific networks* -- AS38195 (Superloop) is an external Australian carrier, not a Pacific network, so this isn't that shape either. Recorded here in full prose instead of stretching either category or inventing a new one for a single data point.

**Real, durable takeaway regardless of dataclass filing**: a second, independent New Caledonia ISP -- not just the incumbent -- also routes its Guam-directed traffic out through Australia (this time via Superloop rather than the AS4637/Telstra Global path seen in other NC measurements) and a real US-based exchange (Any2West) rather than any direct or in-region path. Consistent with, and reinforcing, this project's broader pattern: New Caledonia's transpacific connectivity leans on Australia regardless of which local carrier originates the traffic.

Nothing added to any finding module this tranche; task_plan.md is the durable record. No report/map regeneration needed (no dataclass changed).

---

**[User-directed follow-up -- "add the routed-vs-unrouted /24 check as a reusable helper."]** Turned the manual Superloop investigation (RIPEstat routing-status + WHOIS + bgp.tools, done freehand three times this session now: AS9471->AS10131, then AS45345->AS3605, then re-verified against the project owner's own bgp.tools check) into permanent, reusable infrastructure rather than re-deriving the same three API calls by hand the next time a gap needs explaining.

**Added to `ris/ripestat.py`** (matching its existing retry-with-backoff style exactly): `RoutingVisibility` dataclass + `fetch_routing_visibility(ip)` (wraps `routing-status`, exposes `ris_peers_seeing`/`total_ris_peers`/`less_specifics`, plus an `ever_announced` property); `InetnumInfo` dataclass + `fetch_whois_inetnum(ip)` (wraps `whois`, extracts `inetnum`/`netname`/`descr`/`country`/`status`).

**Added to `discovery/bgp_tools.py`**: `is_prefix_routed_by_asn(asn, address)` -- checks whether a suspected operator's bgp.tools-routed prefix set actually covers a given address, reusing the already-built `fetch_prefix_visibility`. Returns `None` (not `False`) when the ASN routes nothing at all in bgp.tools' table, since that's a different, weaker signal than "routes other things but not this."

**New module, `analysis/hop_investigation.py`**: `investigate_unresolved_hop(address, suspected_asn=None)` orchestrates all three into one `HopInvestigation` result, with a `likely_unannounced_infrastructure` property matching the exact reasoning already applied by hand. **Deliberately kept as a separate, manual-investigation module, not folded into `traceroute_topology._resolve_address`'s automatic resolver** -- consistent with the explicit decision two tranches ago not to add a WHOIS-based resolver tier off a single occurrence; this tool exists for an analyst (or a future tranche) to reach for deliberately, not to silently upgrade a `contiguous: false` gap into a confirmed adjacency. New entry point `pacific-peering-investigate-hop`, demonstrated against the concrete Superloop case by default.

**Verified two ways, not just import-checked.** Ran it live against the real motivating case: both `103.200.13.67` and `103.200.13.168` report `ever_announced=False`, `whois_netname=SUPERLOOP-AU`, `suspected_asn=38195 routes_it=False`, `likely_unannounced_infrastructure=True` -- an exact match to the manual investigation. **Then ran a negative sanity check**, deliberately, against a real known-routed address (`182.173.224.1`, AS3605's own, used throughout this session): `ever_announced=True`, `routes_it=True`, `likely_unannounced_infrastructure=False` -- confirms the helper actually discriminates rather than defaulting to one answer. Both directions correct.

Added exports to `ris/__init__.py`, `analysis/__init__.py`, `discovery/__init__.py`, and the new `pyproject.toml` entry point. Full syntax check across all six touched/new files passes.

---

**[User-directed infrastructure change -- "you should just generate a todo list of unknown corridors and work one per loop, update that list every 8 hours, keep track of new probes and RIS changes as a standing order for testing."]** A real, correctly-diagnosed critique: every prior tranche's "find the next unknown corridor" step was a fresh ad-hoc judgment call, re-scanning the registry and reasoning from memory each time -- didn't scale, and had no way to notice new data (a probe coming online, a new RIS-observed relationship) except by accident. Built the systematic replacement.

**New module, `analysis/corridor_backlog.py`.** Two persisted, gitignored state files under `data/analysis/`: `tested_pairs.json` (every exact `(source_asn, target_asn)` this project has ever deliberately fired a traceroute between, any outcome -- the authoritative dedup record, since `ConfirmedDetour` doesn't even store a source ASN and inconclusive results like the NC->GU Superloop case live only in task_plan.md prose) and `corridor_backlog_snapshot.json` (probe registry + RIS neighbor sets as of the last regeneration, diffed each run to flag what's genuinely *new*). One committed, human-readable artifact: `corridor_backlog.md` at the repo root, capped to the top 100 candidates by priority for readability (new-probe/new-RIS-relationship candidates always sort first), with the full count and a note that the complete set is always live-recomputable.

`enumerate_candidate_corridors()` builds the candidate space: every ASN with a connected probe (source) crossed with every in-scope ASN with cached RIS prefix data (target), same-economy pairs excluded (a different, already-covered category this session), external/proxy ASNs excluded (Renater, Starlink, Zscaler), and anything already covered -- exactly, or at the economy-pair level -- excluded via `tested_pairs.json` plus the three finding dataclasses plus a one-time `SEED_TESTED_ECONOMY_PAIRS` backfill for the prose-only pre-existing results (NC<->GU, FM<->KI, VU<->FM, and the 12 already-dataclass-covered pairs). `pick_next_corridor()` returns the single top pick live, without depending on the markdown file being current. `mark_corridor_tested()` is the write side every future tranche should call.

**Backfilled `tested_pairs.json` with 17 exact ASN pairs from this session's actual history** before the first real run -- everything not already recoverable from `CONFIRMED_LOCAL_TRANSIT`/`CANDIDATE_PEERING`'s stored fields (which `enumerate_candidate_corridors` pulls in automatically). A disclosed limitation, not silently ignored: this backfill is best-effort for the pairs I could confidently reconstruct from memory, not a guaranteed-complete audit of every ASN pair ever touched incidentally as a transited hop -- the "grep before firing" discipline from two tranches ago remains a live safety net on top of this system, not replaced by it.

**Ran it live, twice, not just import-checked.** First run: 1,379 candidates, all flagged new-probe/new-RIS-relationship -- expected first-run artifact (the snapshot starts empty, so everything is "new" relative to nothing) and not a bug, but visually alarming enough in the raw markdown that I capped the displayed list and added an explanatory note directly in the file rather than leave 1,388 lines of noise. Second run (after the snapshot saved): correctly shows 0 new-probe/new-RIS flags, confirming the diff logic actually works, not just the enumeration.

**Wired the standing 8-hour regeneration cadence as an actual cron job**, not just a documented intention: `db93405c` (`17 */8 * * *`) runs `pacific-peering-corridor-backlog`, reviews new-probe/new-RIS flags, commits and pushes `corridor_backlog.md` -- the concrete form of "keep track of new probes and RIS changes as a standing order." **Replaced the hourly job** (`e47f6827` -> `33ab3487`, same `7 * * * *` cadence) with an updated prompt that explicitly pulls from `pick_next_corridor()`/`corridor_backlog.md` and calls `mark_corridor_tested()` afterward, rather than leaving the new process as something a fresh hourly context might not discover on its own.

Top live pick after this tranche: **AS3605 (Guam Cablevision) -> AS4638 (Telecom Fiji)** -- genuinely novel: GU<->FJ has never been directly tested this session, despite both GU and FJ individually being among the most-characterized economies in the project. **Fired it immediately, to prove the system end-to-end rather than just leave it as an untested pick.**

Measurement 211302765, 1 of 3 probes returned. Result: AS3605 -> [gap] -> AS2497 (IIJ, Japan) -> AS4637 (Telstra Global) -> [long silent gap, hops 16 through 254 all non-responding] -> AS4638 (target, replies only at the final hop). `contiguous: false`, `ris_agrees: false`. **Investigated before writing this off, per the standing discipline, but this is ordinary and doesn't need escalation**: the gap right before the target is plain non-response (empty `addresses` on every intervening hop, not a resolved-but-private or resolved-but-unannounced address the way the RFC1918/Superloop cases were) -- the mundane, already-well-precedented "ICMP filtering near the destination" pattern this project has seen many times, not a new resolver edge case. Checked `fishbowl.json` directly: AS4638's *only* RIS-observed neighbor at all is AS45349 (1,669 observations -- already the basis of the existing NC->FJ/MegaIX Sydney confirmed detour), not AS4637. This traceroute genuinely doesn't confirm a new AS4637<->AS4638 relationship -- a real, honest negative result, not a data-quality problem.

Not filed in any dataclass -- matches this project's established treatment of genuine dead-ends (the Fiji-IXP/GTT tests, the Cook Islands/SES Astra case). **Called `mark_corridor_tested(3605, 4638)`** regardless of the inconclusive outcome -- the first live use of the backlog system's write side, confirming the whole loop (pick -> test -> record -> won't be proposed again) actually works, not just the read side. No report/map regeneration needed (no dataclass changed).

---

**[Loop tranche -- first hourly firing to actually run under the new backlog system.]** Confirmed via `CronList` this was job `33ab3487`'s scheduled fire. Pulled the top pick via `pick_next_corridor()`: **AS3605 (Guam Cablevision) -> AS9241 (FINTEL, Fiji)** -- another genuinely untested GU<->FJ pair (the last firing's AS3605->AS4638 pick having been inconclusive and excluded, this is a different target ASN within the same still-open economy pair).

**The measurement itself ran unusually slowly** -- stuck at `Scheduled` status for several minutes with zero probe activity, versus this session's usual 5-15 seconds. **Checked directly before either escalating or quietly retrying**, per the standing discipline: `participant_count: 2` confirmed both of AS3605's connected probes really were queued as participants (not a probe-availability problem), and a second, longer poll resolved cleanly with both returning real results. Read this as an ordinary Atlas-side scheduling delay, not a network anomaly -- the standing consult-the-owner order is specifically for strange *routing* data, and this was platform latency with a normal resolution, so not escalated.

**Result: a real, clean, RIS-confirmed finding.** Both probes: AS3605 -> AS2497 (IIJ, Japan) -> AS174 (Cogent Communications) -> AS9241. Upstream of the target is AS174, RIS-agreeing with an *exact* match (830) -- checked directly against AS9241's full neighbor list (`{174: 830, 4648: 542, 6939: 330}`): AS174 is its single largest relationship, not a minor one. **The same Tokyo/Cogent global-transit shape already seen for AS3605's Palau corridor** -- this project's second example of AS3605 reaching an in-scope target via Cogent through Japan rather than any regional path, real corroborating pattern for how this specific Guam carrier routes internationally. Added as a new `ConfirmedDetour` entry.

Called `mark_corridor_tested(3605, 9241)`. Verified: module imports cleanly (8 entries, up from 7); regenerated ASCII/HTML reports (renders correctly) and the geographic map (9 red `line2d` elements = 8 data lines + 1 legend swatch, matching the 8 dataclass entries). Regenerated the corridor backlog: candidate count dropped 1378 -> 1330 (the larger drop reflects the new `ConfirmedDetour` entry excluding the *entire* GU<->FJ economy pair from future candidates, not just this one ASN pair -- exactly the economy-pair-level dedup this system was designed around).

---

**[Loop tranche -- second hourly firing under the backlog system, normal timing this time.]** Confirmed via `CronList` this was job `33ab3487`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS9249 (Telecom Vanuatu)** -- a fresh GU<->VU economy pair. Measurement scheduled normally this time (Scheduled -> Ongoing within seconds, unlike last firing's slow start), 2 of 3 probes returned.

**Result: converges onto this project's most solid finding, for a sixth time.** Both probes: AS3605 -> AS3356 (Level 3/Lumen) -> AS4637 (Telstra Global) -> AS38442 (Vodafone Fiji) -> AS9249. Upstream of the target is AS38442, RIS-agreeing with an *exact* match (1,346) -- AS38442<->AS9249, now independently confirmed from a **sixth** distinct source network (AS18200/OPT NC, AS45345/Nautile, AS56089/OFFRATEL, AS24390/USP, AS17828/PNG DataCo, and now AS3605/Guam Cablevision). A genuinely new source economy (GU<->VU untested before this), so this earns its own entry rather than folding into an existing one, matching the same pattern already applied to the NC->VU/PG->VU pair.

**Checked the final-hop gap before writing it off as routine, not just assumed** -- a single silent (non-responding) hop immediately before the target on both probes, the exact same pattern seen in essentially every AS9249-targeted measurement this session. No escalation needed; this is well-precedented, not a new or unusual gap.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(3605, 9249)`. Verified: module imports cleanly (9 entries, up from 8); regenerated ASCII/HTML reports (renders correctly) and the geographic map (10 red `line2d` elements = 9 data lines + 1 legend swatch, matching the 9 dataclass entries). Regenerated the corridor backlog: candidate count dropped 1330 -> 1293.

---

**[Loop tranche -- third hourly firing under the backlog system, a genuine dead-end, and a repeat of the "slow scheduling" pattern -- now recognized, not re-investigated from scratch.]** Confirmed via `CronList` this was job `33ab3487`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS9471 (ONATI, French Polynesia)** -- a fresh GU<->PF economy pair.

**Measurement stuck at `Scheduled` for the full 70s window again** -- the same pattern as the AS3605->AS9241 firing two turns ago. Checked `participant_count` directly before assuming (2, both probes genuinely queued, same as last time), then polled again with a longer window: resolved cleanly, both probes returned. Same conclusion as last time -- ordinary Atlas-side scheduling latency, not a network anomaly, not escalated. Two occurrences now, both explained the same way and both self-resolved on a longer poll -- worth noting as a pattern (AS3605's probes specifically seem to schedule slowly sometimes) rather than two unrelated one-offs, but still not "routing doing something unusual" in the sense the standing order is for.

**Result: a genuine dead-end, not a new relationship.** Neither probe ever resolved the target ASN itself -- both reach AS3605 -> AS2497 (IIJ, Japan) -> AS6939 (Hurricane Electric, resolved via PeeringDB netixlan at JPNAP Tokyo) and go dark before reaching ONATI's own network at all. `ris_agrees: false` -- checked and this isn't the sibling-ASN nuance seen for the Niue/Cook Islands ONATI cases (those traceroutes *did* reach AS9471 or AS55943 directly, just under the "other" sibling identity); here the path never reaches either ONATI ASN, stopping at a generic Tokyo transit hop instead. A real, honest negative result -- not filed in any dataclass, matching this project's established dead-end handling.

Called `mark_corridor_tested(3605, 9471)`. No report/map regeneration needed (no dataclass changed).

---

**[Loop tranche -- fourth hourly firing under the backlog system, normal timing, a clean third repeat of a real pattern.]** Confirmed via `CronList` this was job `33ab3487`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS9751 (American Samoa)** -- a fresh GU<->AS economy pair. American Samoa itself has zero connected probes (unchanged all session), so this is the only testable direction. Normal scheduling timing this time.

**Result: fully contiguous on both probes, exact RIS match.** AS3605 -> AS2497 (IIJ, Japan) -> AS174 (Cogent Communications) -> AS9751. Upstream of the target is AS174, RIS-agreeing exactly (1,055) -- checked against AS9751's full neighbor list (`{174: 1055, 3356: 333, 11404: 267}`): its single largest relationship. **This is now the third instance of the identical AS3605 -> Tokyo/IIJ -> Cogent shape this session** (after AS17893/Palau and AS9241/FINTEL Fiji) -- no longer a one-off, a real repeated signature of how this Guam carrier routes to multiple different Pacific destinations regardless of which island it's reaching.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(3605, 9751)`. Verified: module imports cleanly (10 entries, up from 9); regenerated ASCII/HTML reports (renders correctly) and the geographic map (11 red `line2d` elements = 10 data lines + 1 legend swatch, matching the 10 dataclass entries). Regenerated the corridor backlog: candidate count dropped 1293 -> 1285.

---

**[Loop tranche -- fifth hourly firing, a genuinely different shape of finding: an in-fishbowl transit hub, not an external one.]** Confirmed via `CronList` this was job `33ab3487`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS10131 (Cook Islands)** -- a fresh GU<->CK economy pair. Normal scheduling timing.

**Result: both probes fully contiguous, landing on an adjacency this project has already confirmed** -- AS3605 -> AS2497 (IIJ, Japan) -> AS3257 (GTT) -> **AS9471 (ONATI, French Polynesia)** -> AS10131. The final leg is exactly the already-confirmed AS9471<->AS10131 relationship (`confirmed_local_transit.py`, via the sibling-ASN reasoning already established for AS55943). `ris_agrees: false` on the tool's literal-ASN-pair check, same as every prior ONATI case -- expected, not investigated as new.

**What's genuinely different this time, worth calling out rather than treating as a routine repeat**: every other reinforcement of an already-confirmed adjacency this session has landed on the target directly from the SOURCE ASN; here, AS9471 is an *intermediate transit hop*, not the traceroute's source -- and AS9471 is itself an in-scope, in-fishbowl Pacific carrier, not an external AU/NZ/JP/US hub the way every other detour's waypoint has been. Guam's traffic reaches Cook Islands by transiting through French Polynesia's own network for its final leg, not by leaving the region entirely (only the Tokyo/GTT hop to *reach* ONATI crosses external infrastructure). Real, if modest, evidence that ONATI functions as a genuine transit waypoint for other Pacific economies' traffic, not just its own -- a small data point for regional-hub structure *within* the fishbowl, distinct from every "detours out to AU/NZ" finding on record so far.

**Not filed as a new entry** -- the confirmed adjacency is identical to the one already on record, not a new relationship -- but added as a real, independent-source corroboration note to the existing AS9471->AS10131 `ConfirmedLocalTransit` entry. Called `mark_corridor_tested(3605, 10131)`. Verified: module imports cleanly (9 entries, no new entry added); regenerated ASCII/HTML reports (the corroboration text renders correctly). No map regeneration needed (no new/changed geographic edge). Regenerated the corridor backlog: candidate count dropped 1285 -> 1283.

---

**[Loop tranche -- sixth hourly firing, a fourth instance of the AS3605-Cogent pattern via a different intermediate path.]** Confirmed via `CronList` this was job `33ab3487`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS17993 (Samoa)** -- a fresh GU<->WS economy pair.

**Measurement scheduled slowly again -- a third occurrence of the same pattern** now seen for AS9241, AS9471, and this one. Checked `participant_count` first (genuinely queued, same as before), resolved cleanly on a longer poll. Treated as a now-recognized characteristic of AS3605's probes, not re-investigated as a fresh anomaly -- three occurrences, always the same explanation, always self-resolving.

**Result: fully contiguous on both probes, exact RIS match.** AS3605 -> AS3356 (Level 3/Lumen) -> AS174 (Cogent Communications) -> AS17993. Upstream of the target is AS174, RIS-agreeing exactly (1,455) -- checked against AS17993's full neighbor list: AS174 overwhelmingly dominant. **A fourth AS3605-sourced measurement landing on Cogent as the real upstream** (after Palau and Fiji/FINTEL via Tokyo/IIJ, American Samoa also via Tokyo/IIJ) -- this one via Level 3/Lumen instead, no Tokyo hop, but the same ultimate carrier. Cogent is clearly this carrier's real default path to multiple different Pacific destinations, reached via more than one specific intermediate route.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(3605, 17993)`. Verified: module imports cleanly (11 entries, up from 10); regenerated ASCII/HTML reports (renders correctly) and the geographic map (12 red `line2d` elements = 11 data lines + 1 legend swatch, matching the 11 dataclass entries). Regenerated the corridor backlog: candidate count dropped 1283 -> 1265.

---

**[Loop tranche -- seventh hourly firing, a second instance of the in-fishbowl regional-hub pattern.]** Confirmed via `CronList` this was job `33ab3487`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS23917 (Tuvalu)** -- a fresh GU<->TV economy pair. **Fourth occurrence of the slow-scheduling pattern** (now seen for AS9241, AS9471, AS17993, and this one) -- checked `participant_count` first, resolved on a longer poll, same well-understood explanation each time.

**Result: fully contiguous on both probes, landing on another already-confirmed in-fishbowl relationship.** AS3605 -> AS3356 (Level 3/Lumen) -> **AS9241 (FINTEL, Fiji)** -> AS23917. RIS agrees exactly (1,009) -- the identical figure already on record for the confirmed AS9241<->AS23917 (FINTEL<->Tuvalu) adjacency. **The same shape as last hour's AS9471/ONATI<->Cook-Islands corroboration**: FINTEL, an in-scope, in-fishbowl Fiji carrier, transiting a *different* economy's (Guam's) traffic, not just its own. This is now the **second distinct case** of an in-fishbowl Pacific carrier serving as a real regional transit hub this session (ONATI for Guam->Cook-Islands, FINTEL for Guam->Tuvalu) -- no longer a single curiosity but an emerging, recurring pattern worth watching for a third instance.

Not filed as a new entry -- added as a corroboration note to the existing AS9241->AS23917 `ConfirmedLocalTransit` entry. Called `mark_corridor_tested(3605, 23917)`. Verified: module imports cleanly (9 entries, no new entry added); regenerated ASCII/HTML reports (corroboration text renders correctly). No map regeneration needed. Regenerated the corridor backlog: candidate count dropped 1265 -> 1263.

Noted for a future firing, not acted on now: the backlog's next pick is AS3605 -> AS24013 (Solomon Islands) -- AS24013 was flagged much earlier this session for Germany-only PeeringDB IXP records (likely anycast/hosting presence, not a real network location), a genuinely interesting case to watch for when that firing comes up.

---

**[Loop tranche -- eighth hourly firing. The flagged anomaly arrived, investigated properly, and consulted rather than resolved alone -- then a real corridor tested after it.]** Confirmed via `CronList` this was job `33ab3487`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS24013 (Solomon Islands)** -- exactly the flagged corridor noted last tranche.

**Investigated before firing anything, per the standing order.** `pick_target_ip(24013)` resolved to `185.222.222.1` -- RIPE-region address space, immediately suspicious for a nominally APNIC-delegated Solomon Islands ASN. Checked directly: AS24013's holder name is "SB - SB Professional Services", and WHOIS for the target IP shows `inetnum 185.222.222.0/24`, `netname DNS-SB-IPV4-01`, `descr DNS.SB`, `country EU`. **AS24013 is DNS.SB, a global anycast public DNS resolver, not a Solomon Islands ISP** -- confirming and sharpening the Germany-only-IXP anomaly flagged in Phase 1a, and matching the exact pattern already found and excluded for 8 "Marshall Islands" shell ASNs in `supplementary_asns.py`.

**Did not fire a traceroute or resolve this alone -- consulted the project owner directly**, per the standing order, with three concrete options (exclude from the registry, test anyway with a caveat, or just skip this one corridor). **Decision: exclude AS24013 from the ASN registry entirely**, same treatment as the Marshall Islands shells.

**Built the exclusion as proper, documented infrastructure, not a one-off patch.** New `discovery/excluded_asns.py` -- the symmetric counterpart to `supplementary_asns.py`: `EXCLUDED_ASNS`, one verified entry (AS24013, with the full WHOIS/holder evidence chain recorded in its note). Wired into `registry.build_registry()`: after merging in supplementary ASNs, excluded ASNs are removed from their economy's list. **Ran it live, not just import-checked**: `data/asn_registry.json` before showed `SB: [24013, 45891, ...]`; rebuilt registry after shows `SB: [45891, ...]`, confirmed `24013 in registry['SB']['asns']` is `False`. Total ASN count dropped 164 -> 163, matching exactly.

**Propagated the change through the full pipeline, not just the registry file.** `fishbowl.json` still had a stale `24013` entry from before the exclusion -- rebuilt it too (fast, 163/163 from cache) and confirmed the entry is gone. Regenerated the corridor backlog: candidate count dropped 1263 -> 1248 (a larger drop than a single-pair exclusion would cause, since removing an ASN entirely removes every candidate pair it could have participated in, as either source or target).

**Then completed this tranche's actual corridor test**, since the exclusion work itself doesn't fulfill "test it with a traceroute": the backlog's next live pick after the rebuild was **AS3605 -> AS24439 (Marshall Islands)**. Given the session's established caution specifically around Marshall-Islands-registered ASNs, checked its holder name directly before testing rather than assuming either way: "NTAMAR-AS-AP - MARSHALL ISLANDS NTA ISP AS" -- NTA is the Marshall Islands' real National Telecommunications Authority, a genuine incumbent, and its target IP resolves inside real APNIC space, not a RIPE anycast block. No anomaly -- proceeded normally. Fifth occurrence of the slow-scheduling pattern, resolved on a longer poll as before.

**Result: a real, RIS-confirmed finding**, via the established "last-resolved-ASN" method (target itself never responds, ordinary ICMP filtering). AS3605 -> AS2497 (IIJ, Japan) -> AS6453 (Tata Communications), RIS-agreeing with an *exact* match (997) -- checked against AS24439's full neighbor list: AS6453 is its *only* RIS-observed neighbor at all, a complete, exclusive relationship. This session's fourth distinct global Tier-1 carrier seen filling AS3605's "reach a Pacific destination via Tokyo" role (after Cogent, Telstra domestic, Telstra Global -- now Tata).

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(3605, 24439)`. Verified: module imports cleanly (12 entries, up from 11); regenerated ASCII/HTML reports (renders correctly) and the geographic map (13 red `line2d` elements = 12 data lines + 1 legend swatch, matching the 12 dataclass entries). Regenerated the corridor backlog again: candidate count dropped 1248 -> 1242.

---

**[8-hourly regeneration -- job `db93405c`'s first scheduled fire.]** Ran `pacific-peering-corridor-backlog` directly. **Clean, uneventful regeneration**: 1,242 candidates, **0 new-probe and 0 new-RIS-relationship flags** -- exactly matching the count the last hourly tranche left the backlog at, confirming no drift between the two cadences. Nothing to escalate.

**Found and fixed an unrelated, real formatting bug while here**: the previous tranche's writeup (the AS24013 exclusion entry) had literal `\"` sequences leaked into the committed file instead of plain quotes, in three places. Fixed with a direct substitution and verified the surrounding text reads correctly afterward; confirmed `CHANGELOG.md` wasn't affected by the same issue.

---

**[User-directed analysis -- market concentration and "peering elsewhere" for single-telco economies.]** Two direct questions from the project owner, answered with live data, not recalled figures: *"how many economies have a single ASN or single telco?"*, then *"those economies have limited options on local peering, ie none, however are they peering elsewhere?"* Worth a place in the actual report, not just the conversation, per the project owner's request -- recorded here for the reports phase to pick up.

**Market structure, computed live from the current (post-AS24013-exclusion, 163-ASN) registry**:
- **Single-ASN economies (2 of 20)**: Niue (AS55885, "No. 1 Commercial Center") and Wallis and Futuna (AS45879, "Orange Wallis & Futuna").
- **Single-telco economies, checked by fetching every ASN's holder name directly rather than assumed from ASN count alone (2 of 20, same two)**: no other economy is a clean 100% single-operator match -- the next-smallest (Cook Islands, American Samoa, Marshall Islands, Northern Mariana Islands) each have exactly 2 ASNs under two genuinely distinct, unrelated operators.
- **Near-misses, flagged rather than counted as strict matches**: **Tuvalu** (3 ASNs) -- Tuvalu Telecommunications Corporation holds 2 (AS23917, AS133117) under an identical holder string; the third (AS142573) is registered directly to the Government of Tuvalu, not a distinct commercial telco. **The project owner's own read: Tuvalu counts as a single-telco economy** (a government allocation isn't a second market participant) -- adopted as this project's position going forward, not treated as a discrepancy to hedge on. **FSM** (6 ASNs) -- "FSM Telecommunications Corporation" holds 4 outright under an identical holder string (AS10130, AS38875, AS45193, AS139759) plus a likely-related "FSM Telecom" (AS58524); only AS142139 (Boom! Inc.) is a clearly separate operator -- effectively a telecom monopoly with one minor second entrant, not counted as strictly single-telco.
- For contrast: the largest economies (PNG 39 ASNs, Fiji 20, New Caledonia 19, Vanuatu 12) are all genuinely multi-operator markets.

**"Are they peering elsewhere?" -- checked directly via each ASN's real PeeringDB IXP memberships and facility presence in `fishbowl.json`, not assumed from the lack of a local exchange.** Answer: mostly no, with one clear, genuine exception.
- **Niue (AS55885)**: zero IXP memberships, zero facility presence anywhere. Its only real relationship is to AS55943 (ONATI, French Polynesia -- this project's own confirmed Niue<->ONATI finding). Not exchange-based peering -- reads as a direct/private transit arrangement to one specific upstream, not participation in any peering fabric.
- **Wallis and Futuna (AS45879)**: zero/zero as well. Its only neighbor is AS5511, **Opentransit Orange S.A.** -- consistent with the operator itself being a direct Orange Group subsidiary: this is intra-corporate transit to its own parent's global backbone, not peering in any conventional sense.
- **Tuvalu (AS23917/TTC)**: zero/zero. Real neighbors are AS9241 (FINTEL, Fiji -- this project's confirmed finding) and AS14593 (Starlink). The other two Tuvalu ASNs (AS133117, the second TTC allocation, and AS142573, the government one) show **zero RIS-observed neighbors at all** -- neither appears to be actively routing anything visible to RIS's vantage points.
- **FSM -- the one real exception.** AS10130 (FSM Telecommunications Corporation's primary ASN) has an actual, confirmed PeeringDB membership at **Guam IX**, plus physical facility presence at the **TATA Communications Piti Cable Landing Station** in Guam -- genuine peering infrastructure investment outside FSM's own economy, at a real regional exchange, not a private point-to-point arrangement. The rest of FSM's ASNs show no IXP/facility presence at all, only internal RIS-observed relationships to each other (AS10130<->AS38875, AS45193<->AS139759, AS58524<->AS139759) -- reading as domestic inter-ASN structure within one operator, not external peering.

**Durable takeaway, worth carrying into the report's narrative, not just its tables**: single-telco Pacific economies aren't peering anywhere in the formal, multi-member-fabric sense at all -- they sit on private/direct transit arrangements to one specific upstream carrier each (Niue->ONATI, Tuvalu->FINTEL, Wallis&Futuna->its own parent company's backbone), with FSM's solitary Guam IX membership as the one exception that actually proves the pattern: even the closest thing to "peering elsewhere" in this whole group is a single ASN at a single nearby exchange, not a real diversified peering posture. This is exactly the structural angle this project's market-concentration data should feed into the sub-optimal-routing narrative: a single-telco economy has no domestic negotiating leverage to demand better transit terms or local peering, and the data bears that out directly rather than just plausibly.

---

**[Loop tranche -- ninth hourly firing, another intra-corporate transit pattern.]** Confirmed via `CronList` this was job `33ab3487`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS38198 (Digicel Tonga)** -- a fresh GU<->TO economy pair. Sixth occurrence of the slow-scheduling pattern, resolved on a longer poll as before.

**Result: fully contiguous crossing into the target network, then a longer-than-usual silent tail -- investigated carefully rather than assumed routine.** Both probes: AS3605 -> AS3356 (Level 3/Lumen) -> AS4637 (Telstra Global) -> AS45355 (Digicel Fiji) -> AS38198. Checked the raw hop data directly: both probes actually reach a real, BGP-confirmed AS38198 address (`202.43.12.5`) one hop after the last AS45355 hop, separated by exactly one ordinary silent boundary hop -- a solid, confirmed crossing, not a gap. Only *after* that does the traceroute go fully silent trying to reach the specific queried address (`202.43.12.1`) all the way to the final hop -- read as the destination address itself not responding to probes at all (common for hardened endpoints), not a resolver problem or evidence against the adjacency, which sits before the silent stretch, not inside it. No escalation warranted -- a longer instance of an already-understood pattern, checked rather than assumed.

Upstream of the target is AS45355 (Digicel Fiji), RIS-agreeing with an *exact* match (1,321) -- checked against AS38198's full neighbor list: AS45355 is its *only* RIS-observed neighbor at all. **Worth noting in its own right**: Digicel Fiji serving as Digicel Tonga's real upstream -- both regional subsidiaries of the same corporate parent (Digicel Group), the same shape as the Wallis & Futuna->Orange S.A. relationship spotted in this session's market-structure analysis. Reads as intra-corporate regional transit rather than arm's-length peering, though the traceroute alone can't distinguish that from an ordinary transit contract between the two.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(3605, 38198)`. Verified: module imports cleanly (13 entries, up from 12); regenerated ASCII/HTML reports (renders correctly) and the geographic map (14 red `line2d` elements = 13 data lines + 1 legend swatch, matching the 13 dataclass entries). Regenerated the corridor backlog: candidate count dropped 1242 -> 1230.

---

**[User-directed firing -- "pull the next corridor and test it." A genuinely new shape of finding: the first AS3605 detour to actually cross an in-fishbowl exchange.]** Pulled the top pick: **AS3605 (Guam Cablevision) -> AS38875 (FSM Telecommunications Corporation)** -- a fresh GU<->FM economy pair. Only 1 of 3 requested probes returned.

**Result is different in kind from every other AS3605-sourced detour this session**: fully contiguous, and it actually crosses a real, in-fishbowl exchange -- AS3605 -> AS9246 (Teleguam Holdings/GTA, resolved via PeeringDB netixlan) at **MARIIX** (Mangilao, Guam -- in-fishbowl) -> AS139759. The literal target (AS38875) never itself resolved -- checked directly whether this is a different network before treating AS139759 as a match: it isn't. AS38875's only RIS-observed neighbor is AS10130, and AS139759's only RIS-observed neighbor is also AS10130 -- both are sibling ASNs of the same real operator, FSM Telecommunications Corporation (confirmed via identical holder strings, the same sibling-ASN pattern already established twice for ONATI). Even correcting for that sibling identity, RIS still doesn't confirm this specific adjacency -- neither ASN lists AS9246 or AS3605 as a neighbor at all.

**A clean, fully contiguous, real-exchange crossing that RIS simply doesn't corroborate -- exactly Validation Rule 4's shape**, and Teleguam Holdings' MARIIX membership is independently confirmed via PeeringDB, not just inferred from this traceroute. Added as a new `CandidatePeering` entry rather than `ConfirmedDetour` -- kept as a candidate on the same principle as every other entry in that module: a single clean traceroute doesn't satisfy Validation Rule 1 no matter how compelling the corroborating IXP membership evidence is.

Called `mark_corridor_tested(3605, 38875)`. Verified: module imports cleanly (3 entries, up from 2); regenerated ASCII/HTML reports (renders correctly). No map regeneration needed (`CandidatePeering` entries aren't plotted on the geographic detour map, only `ConfirmedDetour`/`ConfirmedLocalTransit` are). Regenerated the corridor backlog: candidate count dropped 1230 -> 1208 (a larger drop, since the entire GU<->FM economy pair is now covered).

---

**[User-directed firing -- "pull the next corridor and test it," landing on the exact relationship already known from the market-structure analysis.]** Pulled the top pick: **AS3605 (Guam Cablevision) -> AS45879 (Orange Wallis & Futuna)** -- a fresh GU<->WF economy pair. Seventh occurrence of the slow-scheduling pattern, resolved on a longer poll as before.

**Result: clean, RIS-confirmed, and lands on exactly the same relationship already surfaced in this session's market-concentration analysis.** Both probes: AS3605 -> AS2497 (IIJ, Japan) -> AS5511 (Opentransit Orange S.A.) -- the target itself never resolved (ordinary ICMP filtering), so RIS is checked against the last-reached ASN. RIS agrees with an *exact* match (1,665) -- identical to the count already on record from checking AS45879's own neighbor list directly during the earlier "peering elsewhere" investigation. Consistent with Wallis & Futuna's operator being a direct Orange Group subsidiary plugging into its own parent's international backbone, not an independent carrier peering arm's-length.

Added as a new `ConfirmedDetour` entry -- this project's **fifth** distinct global carrier now confirmed filling AS3605's "reach a Pacific destination via Tokyo" role (Cogent, Telstra domestic, Telstra Global, Tata, now Opentransit Orange). Called `mark_corridor_tested(3605, 45879)`. Verified: module imports cleanly (14 entries, up from 13); regenerated ASCII/HTML reports (renders correctly) and the geographic map (15 red `line2d` elements = 14 data lines + 1 legend swatch, matching the 14 dataclass entries). Regenerated the corridor backlog: candidate count dropped 1208 -> 1205.

---

**[New /loop cadence -- job replaced, then run immediately.]** The project owner ran `/loop 10m pull the next corridor and test it`. Since the standing hourly job (`33ab3487`) did the identical task, flagged the overlap directly rather than silently creating a second job -- confirmed via `AskUserQuestion`: replace it. Old job deleted, new one (`53fb30f1`, `*/10 * * * *`) created, then executed immediately per the `/loop` skill's own instructions.

**Corridor**: **AS3605 (Guam Cablevision) -> AS45891 (Solomon Telekom Co Ltd)** -- a fresh GU<->SB economy pair. Checked the holder name directly before firing, given this session's now-standard caution after the AS24013 exclusion: a real incumbent, target IP in real APNIC space -- no anomaly. Eighth occurrence of the slow-scheduling pattern, resolved on a longer poll as before.

**Result: clean and straightforward, no sibling-ASN complications needed this time.** Both probes: AS3605 -> AS2497 (IIJ, Japan) -> AS4637 (Telstra Global) -> AS139609. The literal target (AS45891) never itself resolved, but AS139609 isn't a sibling identity of the same operator the way the FSM/ONATI cases were -- it's a genuinely different, real entity: **Solomon Islands Submarine Cable Company (SISCC)**, the actual operator of the country's international submarine cable infrastructure. Checked AS45891's own RIS neighbor list directly: AS139609 is its *only* neighbor at all, an *exact* match (1,652) to what the traceroute found -- a clean, sensible, real-world relationship (a retail ISP depending on its own country's submarine cable operator for international connectivity), confirmed without any identity-substitution reasoning required.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(3605, 45891)`. Verified: module imports cleanly (15 entries, up from 14); regenerated ASCII/HTML reports (renders correctly) and the geographic map (16 red `line2d` elements = 15 data lines + 1 legend swatch, matching the 15 dataclass entries). Regenerated the corridor backlog: candidate count dropped 1205 -> 1178.

---

**[Loop tranche -- first firing under the new 10-minute cadence, a genuine dead-end with a useful lead surfaced for later.]** Confirmed via `CronList` this was job `53fb30f1`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS55722 (Cenpac Net Inc, Nauru)** -- a fresh GU<->NR economy pair.

**Result: a real dead-end, weaker than the usual "silent near destination" pattern.** Checked the raw hop data directly: both probes only ever resolve addresses inside AS3605's *own* network (`202.128.5.149`, `202.128.2.86`) before going completely silent all the way to the final hop -- unlike every prior inconclusive result this session, no intermediate carrier ever responds at all. Read as a genuine data-visibility limit for this specific source/path (heavy filtering starting essentially at the source's own edge), not evidence of anything unusual with Nauru's routing itself -- not escalated.

**Real, useful context surfaced despite the dead-end**: checked AS55722's own RIS neighbor list directly -- its *only* observed neighbor is **AS7131 (PTI Pacifica Inc., Northern Mariana Islands)**, the same ASN already confirmed this session as a real source (the AS7131->AS152735/Guam Exchange finding). AS3605 clearly isn't on Nauru's real connectivity path; AS7131 is. **Flagged for a future firing**: sourcing directly from AS7131 (which already has 3 connected probes) toward AS55722 would test an actual RIS-confirmed relationship, rather than an arbitrary pair.

Not filed in any dataclass -- a genuine negative result, matching this project's established dead-end handling. Called `mark_corridor_tested(3605, 55722)`. No report/map regeneration needed (no dataclass changed).

---

**[User-directed follow-up -- "source it from AS7131 toward AS55722."]** Immediate follow-through on the lead just flagged. Fired AS7131 (PTI Pacifica, CNMI) -> AS55722 (Cenpac Net, Nauru) directly. Only 1 of 3 probes returned, and the traceroute is physically short -- resolves cleanly to AS7131's own network, then goes completely silent from hop 5 onward, never reaching AS55722 itself. On its face this looks like another dead-end.

**But it isn't one, checked properly rather than assumed from the shape alone**: the resolved upstream this time *is* the literal traceroute source (AS7131), and RIS independently and exactly confirms AS7131 as AS55722's real neighbor -- 1,528 observations, its *only* one at all, matching precisely. Validation Rule 1 is satisfied directly here, no sibling-ASN substitution or last-resolved-ASN workaround needed -- a clean confirmation despite the short packet path. **This directly corrects the finding from two tranches ago**: PTI Pacifica (CNMI), not Guam Cablevision, is Nauru's real upstream connectivity provider -- exactly what the flagged lead predicted, now confirmed rather than just inferred from RIS data alone.

Added as a new `ConfirmedLocalTransit` entry (both MP and NR are in-scope economies). Called `mark_corridor_tested(7131, 55722)`. Verified: module imports cleanly (10 entries, up from 9); regenerated ASCII/HTML reports (renders correctly) and the geographic map (11 green `line2d` elements = 10 data lines + 1 legend swatch, matching the 10 dataclass entries). Regenerated the corridor backlog: candidate count dropped 1178 -> 1173.

---

**[Loop tranche -- a third independent corroboration of the Niue<->ONATI relationship.]** Confirmed via `CronList` this was job `53fb30f1`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS55885 (Niue)** -- a fresh GU<->NU economy pair. Slow-scheduling pattern again, resolved on a longer poll as before.

**Result: fully contiguous all the way to the literal target this time.** Both probes: AS3605 -> AS3356 (Level 3/Lumen) -> AS3257 (GTT) -> **AS9471** -> AS55885. This lands directly on the already-confirmed Niue<->ONATI relationship -- `ris_agrees: false` on the strict AS9471/AS55885 pair, same as every prior instance of this relationship, resolved via the same sibling-ASN basis (AS55943) already established for it.

Same shape as the Cook Islands and Tuvalu corroborations from two tranches ago: a fresh source path landing on an already-confirmed adjacency. **This is now the third independent-source confirmation of the Niue<->ONATI relationship specifically** (the original direct test from Niue itself, plus this new one from Guam). Added as a corroboration note to the existing entry rather than a new one. Called `mark_corridor_tested(3605, 55885)`. Verified: module imports cleanly (10 entries, no new entry added); regenerated ASCII/HTML reports (corroboration text renders correctly). No map regeneration needed. Regenerated the corridor backlog: candidate count dropped 1173 -> 1171.

---

**[Loop tranche -- a genuinely new confirmed relationship, found by retesting a different ASN in an economy that already had a dead-end.]** Confirmed via `CronList` this was job `53fb30f1`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS55943 (ONATI's other ASN, French Polynesia)**. GU<->PF had already been tested once this session (via AS9471, a genuine dead-end reaching only Hurricane Electric in Tokyo) -- but since that dead-end was never added to any dataclass, the economy pair wasn't excluded, and targeting ONATI's *other* ASN specifically was worth trying rather than assuming a repeat.

**It wasn't a repeat.** Both probes: the target itself never resolved (ordinary ICMP filtering), but the last-reached ASN is **AS3257 (GTT Communications)** -- a completely different carrier from the earlier AS9471 attempt's Hurricane Electric. RIS agrees with an *exact* match (1,657) -- checked against AS55943's full neighbor list: AS3257 is its dominant relationship (1,657 of 1,662 total observations). A real, clean, RIS-confirmed finding, distinct in both target identity and carrier from the earlier dead-end.

Added as a new `ConfirmedDetour` entry -- worth noting as a methodology point, not just a finding: **retesting a different ASN within an economy that already had an inconclusive result is genuinely worthwhile**, since an inconclusive result for one ASN says nothing about a sibling ASN's own connectivity. Called `mark_corridor_tested(3605, 55943)`. Verified: module imports cleanly (16 entries, up from 15); regenerated ASCII/HTML reports (renders correctly) and the geographic map (17 red `line2d` elements = 16 data lines + 1 legend swatch, matching the 16 dataclass entries). Regenerated the corridor backlog: candidate count dropped 1171 -> 1151 (the larger drop reflects the whole GU<->PF economy pair now being excluded, unlike the earlier dead-end which only excluded the one ASN pair).

---

**[Loop tranche -- the FSM->Kiribati Starlink chain reproduced exactly from a second, unrelated source.]** Confirmed via `CronList` this was job `53fb30f1`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS132486 (Ocean Link Ltd, Kiribati)** -- a fresh GU<->KI economy pair.

**Result: the exact same striking chain already documented for the FSM->Kiribati corridor several tranches ago, reproduced independently.** Both probes: AS3605 -> AS7578/AS137409 (GSL Networks, Australia) -> AS14593 (SpaceX Starlink) -> AS154100 (BNL Tarawa) -> target (AS132486) never resolved. RIS agrees with an *exact* match (362) -- identical to the count already on record for the existing AS154100<->AS132486 adjacency. **Two completely different, geographically distant sources (FSM and Guam) both reach Kiribati via the same Australia-then-Starlink satellite path** -- real, repeated evidence this is Kiribati's actual general-purpose ingress pattern, not an artifact specific to one source network's own routing.

Not a new entry -- added as an independent-source corroboration note to the existing `ConfirmedLocalTransit` entry. Called `mark_corridor_tested(3605, 132486)`. Verified: module imports cleanly (10 entries, no new entry added); regenerated ASCII/HTML reports (corroboration text renders correctly). No map regeneration needed. Regenerated the corridor backlog: candidate count dropped 1151 -> 1150.

---

**[Loop tranche -- a third instance of the Starlink chain, but this time a genuinely new confirmed adjacency, not a repeat.]** Confirmed via `CronList` this was job `53fb30f1`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS134783 (Amalgamated Telecom Holdings Kiribati Ltd -- ATHKL's *other* ASN, sibling of AS4865)** -- a fresh GU<->KI pair, distinct from the AS132486 target tested last firing (the KI<->KI dataclass entry doesn't exclude the whole GU<->KI economy pair, since it's recorded under KI/KI, not GU/KI -- a real, disclosed limitation of the economy-pair-level dedup, not a bug).

**Result: the identical Australia/Starlink satellite chain, a third time** -- AS3605 -> AS7578/AS137409 (GSL Networks) -> AS14593 (SpaceX Starlink) -> AS154100 (BNL Tarawa) -> target never resolved. But this time it's genuinely new, not another corroboration of the same pair: checked AS134783's own RIS neighbor list directly -- AS154100 is its dominant relationship (1,392 of ~1,806 total observations), an *exact* match. **BNL Tarawa is evidently a real, general-purpose intra-Kiribati transit provider**, not narrowly tied to one customer -- this is the second distinct Kiribati ASN now confirmed reachable through it, both via the identical satellite ingress path.

Added as a new `ConfirmedLocalTransit` entry. Called `mark_corridor_tested(3605, 134783)`. Verified: module imports cleanly (11 entries, up from 10); regenerated ASCII/HTML reports (renders correctly) and the geographic map (12 green `line2d` elements = 11 data lines + 1 legend swatch, matching the 11 dataclass entries). Regenerated the corridor backlog: candidate count dropped 1150 -> 1149.

---

**[Loop tranche -- a real signal that fits neither dataclass shape, matching the NC->GU Superloop precedent.]** Confirmed via `CronList` this was job `53fb30f1`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS140504 (Digicel Nauru Corporation)** -- a fresh GU<->NR pair.

**Result: real, but RIS disagrees, and the upstream isn't a Pacific network either.** Both probes: AS3605 -> AS3356 (Level 3/Lumen) -> AS3549 (Level 3 Parent, LLC -- the former Global Crossing backbone ASN) -> target never resolved. Checked AS140504's own RIS neighbor list directly: `{132528: 1032, 12684: 616}` -- neither is AS3549. This has the *shape* of a detour (crosses global transit) but fails Validation Rule 1 outright, so it can't be `ConfirmedDetour`; and AS3549 is an external Tier-1 carrier, not an in-scope Pacific network, so it doesn't fit `CandidatePeering` either -- the same reasoning already applied to the NC->GU Superloop case several tranches ago.

**Real color worth keeping, though**: AS140504's actual RIS-confirmed relationships are AS132528 (1,032 observations -- the same Telstra-operated "Digicel Australia" backbone ASN already confirmed as Digicel Fiji's real upstream in the NC->FJ detour, and by extension part of the same Digicel-family pattern noted for Digicel Tonga) and AS12684 (616, SES Astra -- the satellite operator already known to have zero connected Atlas probes, so untestable directly). Another real instance of Digicel's own regional subsidiaries interconnecting through shared corporate infrastructure rather than this specific traceroute's path.

Not filed in any dataclass -- a genuine, honestly-documented inconclusive result. Called `mark_corridor_tested(3605, 140504)`. No report/map regeneration needed (no dataclass changed).

---

**[Loop tranche -- another weak Nauru dead-end, with a lead connecting straight back to an already-confirmed relationship.]** Confirmed via `CronList` this was job `53fb30f1`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS141368 ("ICT", Nauru)** -- a fresh GU<->NR pair.

**Result: the same weak dead-end pattern as the earlier AS55722 attempt** -- neither probe resolves any address beyond AS3605's own network. Checked AS141368's own RIS neighbor list directly anyway: its *only* observed neighbor is **AS55722 (Cenpac Net Inc)** -- the same Nauru ASN whose real upstream (AS7131/PTI Pacifica) was directly confirmed just two tranches ago. This is a real, existing intra-Nauru relationship (AS141368<->AS55722), and by extension suggests AS141368's own international path likely also runs through PTI Pacifica -- worth a direct test in a future firing (source AS7131 toward AS141368) rather than assumed from this indirect chain.

Not filed in any dataclass. Called `mark_corridor_tested(3605, 141368)`. No report/map regeneration needed (no dataclass changed).

---

**[Loop tranche -- a genuine named-exchange crossing (BBIX Tokyo) and a real contrast in Cook Islands routing shapes.]** Confirmed via `CronList` this was job `53fb30f1`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS152093 (VakaNet Limited, Cook Islands)** -- a second, distinct Cook Islands ASN tested from Guam this session (after AS10131, reached via the in-fishbowl ONATI transit corroboration).

**Result: fully contiguous, exact RIS match, and a genuine named-exchange crossing this time.** Both probes: AS3605 -> AS9507 (NextHop Pty Ltd, Australia), resolved via PeeringDB netixlan, crossing **BBIX Tokyo** (out-of-fishbowl). RIS agrees with an *exact* match (335) -- checked against AS152093's full neighbor list: AS9507 is its *only* RIS-observed neighbor at all.

**Notable contrast with the AS10131 corridor tested from the same source**: that one reaches Cook Islands via an in-fishbowl Pacific carrier (ONATI); this one reaches a different Cook Islands operator via a conventional Australia/Tokyo exchange crossing -- two real, differently-shaped corridors within the same economy, not a uniform national pattern.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(3605, 152093)`. Verified: module imports cleanly (17 entries, up from 16); regenerated ASCII/HTML reports (renders correctly) and the geographic map (18 red `line2d` elements = 17 data lines + 1 legend swatch, matching the 17 dataclass entries). Regenerated the corridor backlog (last explicit regeneration was at 1149, before the two intervening dead-end tranches which didn't trigger one): now 1136, reflecting both those two single-pair exclusions and the whole GU<->CK economy pair newly excluded by this tranche's confirmed finding.

---

**[Loop tranche -- a second real instance of Tata Communications, closing out a run of Nauru corridors on a clean confirmation.]** Confirmed via `CronList` this was job `53fb30f1`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS152706 (Neotel, Nauru)**. Normal scheduling timing this time.

**Result: fully contiguous to the literal target, exact RIS match.** Both probes: AS3605 -> AS2497 (IIJ, Japan) -> AS6453 (Tata Communications) -> AS152706. RIS agrees exactly (292) -- checked against AS152706's full neighbor list: AS6453 is its dominant relationship. **This is the second distinct instance of Tata Communications filling AS3605's Tokyo-transit role this session** (after AS24439/Marshall Islands) -- alongside the two Cogent instances, Telstra's domestic+international pair, and Opentransit Orange, Tata is clearly a real, recurring carrier in this Guam network's actual transit mix, not a one-off.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(3605, 152706)`. Verified: module imports cleanly (18 entries, up from 17); regenerated ASCII/HTML reports (renders correctly) and the geographic map (19 red `line2d` elements = 18 data lines + 1 legend swatch, matching the 18 dataclass entries). Regenerated the corridor backlog: candidate count dropped 1136 -> 1127 (the whole GU<->NR economy pair -- a genuinely difficult one this session, three dead-ends before this confirmation -- now finally excluded).

---

**[Loop tranche -- the sharpest confirmation yet of Kiribati's real Starlink upstream, deliberately not forced into a dataclass shape it doesn't fit.]** Confirmed via `CronList` this was job `53fb30f1`'s scheduled fire. Pulled the top pick: **AS3605 (Guam Cablevision) -> AS154100 (BNL Tarawa itself, Kiribati)** -- targeting the provider ASN behind the two already-confirmed intra-Kiribati relationships directly, rather than one of its downstream customers.

**Result: the cleanest, most direct evidence yet.** Both probes resolve cleanly to **AS14593 (SpaceX Starlink) as the literal last-reached ASN** -- one hop closer than every prior instance of this chain, since this traceroute targets BNL Tarawa's own address rather than transiting through it. RIS agrees with an *exact* match (361) -- checked directly: AS14593 is BNL Tarawa's *only* RIS-observed neighbor at all.

**Deliberately not filed as a new `ConfirmedDetour` entry**, despite being a clean, RIS-confirmed finding: unlike every other detour on record, Starlink has no fixed terrestrial hub to map -- no real ground-station location is evident from a satellite traceroute, so forcing a nominal hub value the way "Tokyo" stands in for other carriers would misrepresent what's actually been confirmed (this project's map is geographic, and a satellite constellation genuinely isn't). Added instead as a sharpening note directly on the existing AS154100 entry it corroborates -- the real, durable fact (BNL Tarawa's sole international upstream is Starlink) is now confirmed as cleanly as any adjacency in this project, recorded honestly rather than shoehorned into infrastructure built for terrestrial exchanges.

Called `mark_corridor_tested(3605, 154100)`. Verified: module imports cleanly (11 entries, no new entry added); regenerated ASCII/HTML reports (renders correctly). No map regeneration needed. Regenerated the corridor backlog: candidate count dropped 1127 -> 1126. **Notable**: the next live pick is now sourced from **AS7131**, not AS3605 -- the first time in many tranches the backlog has moved to a different source ASN, since AS3605's cheap untested cross-economy targets are largely exhausted. The system is diversifying sources exactly as designed.

---

**[Loop tranche -- first firing sourced from a diversified ASN, a real signal re-hitting an already-recognized unresolved zone.]** Confirmed via `CronList` this was job `53fb30f1`'s scheduled fire. Pulled the top pick: **AS7131 (PTI Pacifica, CNMI) -> AS4638 (Telecom Fiji)** -- the backlog's first non-AS3605 source in many tranches, and a genuinely fresh MP<->FJ economy pair.

**Result: a real path, but RIS disagrees, and the gap turned out to be one already documented this session, not a new anomaly.** Both probes: AS7131 -> AS140627 (OneQode) -> AS4637 (Telstra Global) -> [gap] -> AS4638. Checked the raw hops directly before treating the gap as routine: hops 14-15 (`202.137.178.160`, `.55`) are genuinely unresolved *public* addresses -- not RFC1918, so the private-hop fix correctly doesn't touch them -- immediately followed by a run of real RFC1918 hops (correctly transparent) before the target replies. **This is the exact same `202.137.178.x` unresolved zone already flagged back in loop tranche 5**, when a different measurement (AS3605-sourced) hit the identical gap between AS45349 and AS4638's own network -- a recognized, pre-existing limitation near AS4638's boundary, not a fresh mystery. AS4638's only real RIS-confirmed neighbor remains AS45349 (already the basis of an existing `ConfirmedDetour`); AS4637 (Telstra Global) isn't in its neighbor list, and, being an external Tier-1 carrier rather than a Pacific network, doesn't fit `CandidatePeering` either -- same reasoning as the NC->GU Superloop and GU->NR/AS140504 cases.

Not filed in any dataclass. Called `mark_corridor_tested(7131, 4638)`. No report/map regeneration needed (no dataclass changed).

**[Addendum, prompted by the project owner: "OneQode has a presence in Guam, could MP->FJ be via Guam?"]** Verified directly rather than assumed. OneQode's real PeeringDB facility list (net_id 23196, 16 facilities) does include two genuine Guam entries: Tata's Piti Cable Landing Station and RTI Guam GNC. Traced the specific hop addresses from this measurement (211527961): two resolve to AS140627 -- `103.112.0.226` (generic PTR, `103-112-0-226.oneqode.net`) and `103.151.64.207`, whose PTR record is decisive: `gu-gnc-rt1-----Vlan756.hk-mgi-rt1.oneqode.net` -- a router explicitly named "gu-gnc" (Guam GNC), matching OneQode's PeeringDB-listed RTI Guam GNC facility exactly, connected via a named VLAN link to their Hong Kong router. **Confirms the lead directly**: this specific MP->FJ detour genuinely transits OneQode's real Guam infrastructure before continuing to Hong Kong and on to Telstra Global. *(Correction: the "doesn't change classification" call made here in the first draft of this addendum was overridden by the project owner -- see the governance-decision entry at the end of this file.)*

---

**[Loop tranche -- a complete, ordinary dead-end.]** Confirmed via `CronList` this was job `53fb30f1`'s scheduled fire. Pulled the top pick: **AS7131 (PTI Pacifica, CNMI) -> AS9241 (FINTEL, Fiji)** -- a fresh MP<->FJ pair (distinct target from last firing's AS4638 attempt). Only 1 of 3 probes returned.

**Result: zero hops resolved to any ASN at all.** Checked the raw hop data: the only two real hops are RFC1918 private addresses (correctly treated as transparent, no false gap manufactured), then total silence from hop 3 through the final hop -- the same "no ICMP visibility beyond the source's own edge" pattern already seen a few times this session (AS3605->AS55722, AS3605->AS141368). Not anomalous, not escalated -- a genuine, complete dead-end for this specific source/path.

Not filed in any dataclass. Called `mark_corridor_tested(7131, 9241)`. No report/map regeneration needed (no dataclass changed).

---

**[User-directed correction -- "i tested that last route from here and it is looping, maybe try a different ip address when that happens?"]** The project owner independently, personally re-tested the AS7131->AS9241 corridor from their own vantage point and found real evidence this project's "dead end / no ICMP visibility" read was incomplete: the actual route is looping, not just silent. Didn't take this on trust alone -- verified it directly against this project's own data before acting on it.

**Verified: retried the same corridor against a *different* AS9241 prefix** (`pick_target_ip` always returns the first cached prefix's address, `113.20.64.1` -- switched to `202.170.32.1`, one of AS9241's four other cached prefixes). The original address's total silence had hidden the real behavior entirely; the alternate address surfaced it immediately. **Confirmed a genuine routing loop, entirely within AS6939 (Hurricane Electric)'s own backbone**: the same resolved address (`184.104.195.46`, `184.104.192.252`, `65.19.142.246` -- all directly confirmed via RIPEstat as AS6939 space) repeats on consecutive hops across all 3 probes, RTT climbing into the 290-330ms range, before the traceroute goes dark without ever reaching AS9241 at all. A real, if unusual, finding for this project's actual thesis -- a routing loop is about as sub-optimal as routing gets, and this one was only surfaced by trying a second address after the first produced nothing informative.

**Built the project owner's suggested fix as a permanent, reusable capability, not a one-off retry.** `atlas/targets.py`: new `list_target_ips(asn)` (every cached prefix's candidate address, not just the first -- `pick_target_ip` now just returns `list_target_ips(...)[0]`, fully backward compatible) and `has_routing_loop(hops, target=None)` (detects the real loop signature: a repeated consecutive address *combined with* never reaching the actual target -- distinct from ordinary silent/filtered hops).

**Caught and fixed a real bug in the loop-detector itself, live, before trusting its output.** First version flagged *any* consecutive repeated address as a loop; immediately re-tested it against the next real measurement fired this same tranche (AS7131->AS9249, which *did* successfully reach its target despite one hop replying twice in a row -- ordinary ECMP noise) and it produced a false positive. Refined the heuristic to only call it a real loop when a repeat occurs *and* the actual target IP is never seen anywhere in the resolved hops -- re-verified against both real cases side by side (the genuine AS9241 loop still correctly flags `True`; the successful AS9249 traceroute correctly flags `False`) before considering it trustworthy. Exported both new functions from `atlas/__init__.py`.

**Then completed this tranche's actual corridor** with the improved method: **AS7131 (PTI Pacifica, CNMI) -> AS9249 (Telecom Vanuatu)** -- a fresh MP<->VU pair. Result: probe 60689 fully contiguous end-to-end -- AS7131 -> AS6939 (Hurricane Electric) -> AS4637 (Telstra Global) -> AS38442 (Vodafone Fiji) -> AS9249. RIS agrees with an *exact* match (1,346) -- this project's very first confirmed finding, now independently reinforced a **seventh** time, and the first from CNMI as a source.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(7131, 9249)`. Verified: module imports cleanly (19 entries, up from 18); regenerated ASCII/HTML reports (renders correctly) and the geographic map (20 red `line2d` elements = 19 data lines + 1 legend swatch, matching the 19 dataclass entries). Regenerated the corridor backlog: candidate count dropped 1126 -> 1113.

**Committed and pushed** (`2be8196`) the whole tranche above: the AS7131->AS9241 correction, the new `list_target_ips`/`has_routing_loop` tooling, and the AS7131->AS9249 confirmation. Also saved a durable memory (`feedback_retry_alternate_ip_on_deadend`) so future sessions retry a second address before writing off a dead-end corridor, without needing Terry to repeat the correction.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS9471 (French Polynesia).** First attempt (target `123.50.65.1`, `pick_target_ip`'s default first-prefix address) dead-ended: both probes resolved cleanly out to AS6939 (Hurricane Electric) then hit one RFC1918 hop (`172.18.0.85`) before going totally dark, target never reached. `has_routing_loop` correctly returned `False` for both probes -- no repeated address, just silence, not the AS9241 loop pattern.

**Applying the new retry policy before concluding anything**: retried with the next `list_target_ips(9471)` candidate (`123.50.66.1`). This time **both probes reached the real target** -- same path shape (AS7131 -> AS6939 -> the same RFC1918 hop -> silence for a couple of unresolved public hops -> then a direct hit on `123.50.66.1` at the final hop). Confirms the first address's total silence was address-specific ICMP filtering, not a structural dead end -- exactly the scenario this tooling was built for, and this time it wasn't a loop, just a successful second attempt.

**Triangulated the successful run against RIS** (`analyze_measurement(211541849, target_asn=9471)`): both probes resolve `AS7131 -> AS6939 -> AS9471`, `traceroute_upstream_asn=6939`, `ris_agrees=False`. Checked why directly rather than taking the disagreement at face value: `fishbowl.json` only tracks immediate neighbor relationships *among in-scope Pacific ASNs* -- AS9471's only fishbowl neighbor on record is its own sibling AS55943 (ONATI's other ASN, per the established sibling-ASN pattern), and AS6939 (Hurricane Electric) isn't a Pacific network at all, so it was never going to appear there. This is the same shape as the NC->GU Superloop precedent: a real, successful, fully-resolved traceroute with a plausible transit provider, but the observed upstream is an external, non-Pacific carrier that RIS's Pacific-scoped fishbowl has no way to corroborate -- doesn't fit `ConfirmedDetour` (no Pacific-network intermediary like AS38442 in the AS9249 case) or `CandidatePeering` (AS6939 isn't a Pacific network either).

**Not filed in any dataclass** -- documented here in prose only, per the established restraint principle. Called `mark_corridor_tested(7131, 9471)`. No report/map regeneration needed (no dataclass changed). Regenerated the corridor backlog: candidate count dropped 1113 -> 1111 (this pair plus the earlier AS9241 retry both now marked tested).

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS9751 (American Samoa).** First target address dead-ended past a private hop again (same shape as the AS9471 case just above); retried with the next `list_target_ips(9751)` candidate and both probes reached the target cleanly. Path: AS7131 -> AS6939 (Hurricane Electric) -> AS11404 (Wave Broadband) -> AS9751, contiguous on probe 60689.

**Triangulated**: `traceroute_upstream_asn=11404`, `ris_agrees=True`, count 267 -- an *exact* match against AS9751's own fishbowl neighbor list (`{174: 1055, 3356: 333, 11404: 267}`), which was already on record from the earlier GU(AS3605)->AS9751 Cogent/Tokyo `ConfirmedDetour`. This time a genuine, corroborated confirmation, not another out-of-fishbowl-carrier dead end -- the key difference from the AS9471 case right above it: AS9751's *own* RIS path data lists AS11404 directly (267 observations), where AS9471's didn't list AS6939 at all (only its sibling AS55943). Checked AS11404's holder name directly: "AS-WAVE-1 - Wave Broadband" (via RIPEstat as-overview) -- a real US Pacific Northwest ISP, not a shell.

**New external hub needed for the map.** `EXTERNAL_HUB_LATLON` only had Sydney and Tokyo; this corridor's carrier doesn't fit either. No IXP crossing was observed in this specific traceroute (`ixp_crossings` empty both probes), so picked the hub on the best available sourced evidence rather than the traceroute itself: AS9751's own `fishbowl.json` entry lists a real PeeringDB-sourced IXP membership at "DRF IX" in Honolulu -- the standard Pacific cable hub for American Samoa's international connectivity. Added `"Honolulu": (21.3069, -157.8583)` to `economy_coordinates.EXTERNAL_HUB_LATLON`. Wrote this caveat directly into the entry's note (hub chosen on sourced evidence, not directly observed in this traceroute) rather than implying it was a confirmed crossing point.

Added as a new `ConfirmedDetour` entry -- a genuinely *different* carrier reaching the same AS9751 target than the existing GU->AS entry (Wave Broadband here vs. Cogent there), confirming American Samoa's real transit mix includes more than one distinct backbone provider. Called `mark_corridor_tested(7131, 9751)`. Verified: module imports cleanly (20 entries, up from 19); regenerated ASCII/HTML reports (both render correctly, new Honolulu hub marker appears) and the geographic map (one red line per `CONFIRMED_DETOURS` entry, confirmed by reading the plotting loop directly rather than just counting SVG elements). Regenerated the corridor backlog: candidate count dropped 1111 -> 1109.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS10131 (Cook Islands).** Both probes reached the target directly on the first address, no retry needed this time. Path: AS7131 -> AS174 (Cogent) -> AS3257 (GTT) -> AS9471 -> AS10131.

**Recognized immediately as the same already-confirmed adjacency on record**, not a new finding: AS9471 -> AS10131 is `confirmed_local_transit.py`'s ONATI<->Cook-Islands entry (`provider_asn=9471, customer_asn=10131`), already independently reinforced twice before (once from ONATI's own vantage point, once from Guam/AS3605). `analyze_measurement` reported `ris_agrees=False` on the literal AS9471 number, exactly as expected -- checked `fishbowl.json` directly: AS10131's own neighbor list shows AS55943 (658, exact match) but not AS9471 itself, the same sibling-ASN situation already established for ONATI (AS9471/AS55943 share the identical RIPEstat holder name, confirmed again directly: both "ONATI-AS-AP - ONATI"). Recorded as confirmed on that same, now three-times-independently-applied sibling-ASN basis, not a fresh disagreement.

**Extended the existing entry's note rather than duplicating** (per the established convention) with a third-corroboration paragraph: a third distinct source economy (CNMI, after ONATI's own and Guam's) landing on the identical AS9471->AS10131 last leg. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (11) -- but real reinforcement. Called `mark_corridor_tested(7131, 10131)`. Regenerated ASCII/HTML reports since the note text changed (both render correctly); map unaffected (no new line, entry already plotted). Regenerated the corridor backlog: candidate count dropped 1109 -> 1107.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS17480 (New Caledonia).** First address dead-ended (both probes, no loop per `has_routing_loop`); applied the retry policy anyway before concluding anything -- the second address dead-ended too, even earlier, same shape both times (last reached via a 125.63.x.x hop, silence after). Went back and re-checked the *first* attempt's full triangulation rather than assuming both were equally inconclusive, since the raw hops looked like they went further than the second: **the first attempt had actually already reached AS17480** -- a later hop resolved cleanly to the target ASN by BGP, `contiguous_with_previous: True` the whole way. The dead-end read at a glance was wrong; only the retry (correctly) went nowhere new, and the original address's traceroute was in fact a clean success once triangulated properly. Worth noting for the retry tooling's own limits: `has_routing_loop`/raw-hop skimming alone doesn't replace running the actual triangulation before writing a result off.

**Triangulated the original (successful) attempt**: both probes fully contiguous -- AS7131 -> AS38195 (Superloop, resolved via PeeringDB netixlan) -> AS18200 (OPT NC, New Caledonia's own incumbent) -> AS17480. `ixp_crossings` confirms a real named-exchange crossing at **BBIX Tokyo** (member AS38195, `in_fishbowl: false`). Upstream of the target is AS18200, RIS-agreeing with an *exact* match (1,665). Checked further before writing this up as routine: AS18200's own full neighbor list *also* directly confirms the AS38195 hop (332 observations) -- doubly corroborated, not just the final leg.

**Explicitly contrasted with this session's NC->GU Superloop precedent**, since the same carrier (Superloop) is involved: that earlier case was a real signal RIS couldn't corroborate at all (filed nowhere); this one is the opposite -- Superloop's presence is independently confirmed on *both* sides of it here, a clean, fully-confirmed detour. Also checked AS17480's own `fishbowl.json` entry for context: it has real registered presence at both Equinix Sydney and CAN'L IX (Noumea), but this measurement's actual path uses neither -- it goes via its own incumbent and a Tokyo exchange instead.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(7131, 17480)`. Verified: module imports cleanly (21 entries, up from 20); regenerated ASCII/HTML reports (render correctly) and the geographic map (one line per entry, confirmed via the deterministic plotting-loop/count check). Regenerated the corridor backlog: candidate count dropped 1107 -> 1090.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS17828 (PNG DataCo, Papua New Guinea).** Three probes requested; one (65653) was a complete dead end from the very first hop -- checked directly before treating it as corridor-wide: the other two probes both worked cleanly, so read as a probe-specific local issue, not a property of this corridor. No retry needed.

**Lands on this project's very first-ever confirmed finding** (GU/AS3605->PG/AS17828, measurement 210901499): both working probes resolve AS7131 -> AS6939 (Hurricane Electric) -> AS17828, RIS-agreeing with an *exact* match (1,283) -- identical count to the original. This time an actual IXP crossing is directly confirmed in `ixp_crossings` for both probes (both AS6939 and AS17828 present as members at the same Equinix Sydney fabric hop), not just inferred.

**`has_routing_loop` flagged probe 60689 `True` -- checked before trusting it, per the standing rule.** The "repeat" was a near-destination address (`202.165.198.250`, inside AS17828's own announced range, not the literal queried address) replying at two consecutive hops with stable, non-climbing RTT -- the same ordinary near-destination-silence shape as many other entries this session, not the AS9241/Hurricane-Electric loop signature (RTT climbing steadily across *multiple* hops). A real, worth-noting limit of the current heuristic: it only clears a repeat when the *literal* target address appears in the hops, but a near-destination address inside the target's own range (not the literal target) can still trigger a false positive. Documented directly in the new entry's note rather than silently overridden -- no code change yet since there's no second live data point to refine the heuristic against, unlike the original false-positive fix.

Added as a new `ConfirmedDetour` entry -- second independent confirmation of AS6939<->AS17828 from a genuinely different source economy. Called `mark_corridor_tested(7131, 17828)`. Verified: module imports cleanly (22 entries, up from 21); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 1090 -> 1060.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS17893 (Palau NCC).** The single cleanest result this source has produced: all 3 probes resolved **directly** AS7131 -> AS17893, zero intermediate ASN, and unusually fast (20-30ms RTT, an order of magnitude below every Tokyo/Sydney-detour finding this session) -- a genuinely short, regional Micronesian path rather than a transpacific one.

**Triangulated: `ris_agrees: False` on both sides.** Checked each ASN's own full RIS neighbor list directly rather than taking the disagreement at face value: neither AS7131's list nor AS17893's list mentions the other at all. Not a fishbowl-scope artifact (both ends are genuinely in-fishbowl Pacific ASNs, unlike the AS9471/Hurricane-Electric case a few tranches back) -- RIS really has no visibility into this specific adjacency. `ixp_crossings` came back empty for all 3 probes, but checked further: AS7131 and AS17893 share **two** real, PeeringDB-declared IXP memberships in common (BBIX Tokyo and Guam IX) -- a plausible real venue for this exact adjacency, even though this particular traceroute's hop addresses don't land inside either registered LAN prefix directly.

**This is exactly the `CandidatePeering` shape** (clean, repeatable traceroute; RIS disagrees; both ends in-scope Pacific networks) -- added as a new entry there rather than `ConfirmedDetour`/`ConfirmedLocalTransit`, per Validation Rule 1: no single traceroute gets promoted to confirmed no matter how clean it looks, regardless of how compelling the shared-IXP-membership context is. Called `mark_corridor_tested(7131, 17893)`. Verified: module imports cleanly (4 entries, up from 3); regenerated ASCII/HTML reports (render correctly) and the geographic map (dashed amber line for the new candidate). Regenerated the corridor backlog: candidate count dropped 1060 -> 1056.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS17993 (Samoa).** Measurement stuck at `Scheduled` for the full 90s poll window with zero probe activity -- the recognized AS7131 slow-scheduling pattern, not re-investigated fresh. Resolved cleanly on a longer poll (backgrounded past the 120s tool timeout, picked up via the task notification): all 3 probes reach an AS17993-range address (`202.4.37.x`) then go dark before the literal queried address, the well-established near-destination-silence shape. `has_routing_loop` correctly returned `False` for all three -- no repeat this time, applying the lesson from the AS17828 false positive by checking directly rather than assuming either way.

**Triangulated**: all 3 probes resolve `AS7131 -> AS6939 (Hurricane Electric) -> AS17993`, upstream of target AS6939, RIS-agreeing with an *exact* match (150). Checked against AS17993's full neighbor list, already on record from the existing GU(AS3605)->WS entry (`{174: 1455, 6939: 150, 64073: 10, ...}`): a **different** carrier than that entry's dominant AS174/Cogent relationship -- the same "second distinct real carrier for the same target" shape already seen for American Samoa. `ixp_crossings` directly confirms a real Equinix Sydney crossing for all 3 probes.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(7131, 17993)`. Verified: module imports cleanly (23 entries, up from 22); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 1056 -> 1050.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS23917 (Tuvalu).** Three probes requested; one (65653) was a complete dead end from the first hop, same probe-specific-issue read as the AS17828/65653 case two tranches ago. Both working probes reach an AS23917-range address then go dark before the literal target (ordinary near-destination silence). `has_routing_loop` correctly returned `False` for all three.

**Landed on the existing FINTEL(AS9241)<->Tuvalu(AS23917) `ConfirmedLocalTransit` entry**, already reinforced once before (Guam/AS3605). RIS agrees exactly (1,009), matching both prior instances. What's genuinely new this time: the path leading *into* FINTEL is different from every prior instance -- AS7131 -> AS6939 (Hurricane Electric) -> **AS4648 (Spark NZ)** -> AS9241 -> AS23917, crossing **Equinix Los Angeles** (`ixp_crossings` confirms directly) -- neither this specific hub nor this specific intermediate carrier had appeared for this adjacency before (the Guam corroboration used Level 3/Lumen, no named exchange). Real evidence FINTEL's transit role for Tuvalu is reached via more than one route depending on the ultimate source, not just a repeat of the same path.

**Extended the existing entry's note rather than duplicating**, per the established convention. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (11). Called `mark_corridor_tested(7131, 23917)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected (no new line). Regenerated the corridor backlog: candidate count dropped 1050 -> 1048.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS24390 (University of the South Pacific, Fiji).** First time this project has targeted AS24390 directly as a destination -- previously it only ever appeared as the *source* of the FJ->VU/AS9249 detour. Both probes: AS7131 -> AS140627 (OneQode) -> AS7575 (AARNet). The literal target never resolved (ordinary near-destination ICMP filtering); `has_routing_loop` correctly returned `False` for both.

**Confirmed via the last-reached-ASN methodology**: RIS agrees with an *exact* match (337) -- the identical relationship and count already on record from the existing FJ->VU entry's own note ("AS24390's only RIS-observed neighbor at all is AS7575"). Genuinely new finding in its own right, not a duplicate of that entry: this is the reverse direction, sourced toward AS24390 rather than from it, and via a different intermediate carrier (OneQode, AS140627, already seen as a minor relationship in both AS7131's and AS17893's own fishbowl neighbor lists) with no IXP crossing this time.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(7131, 24390)`. Verified: module imports cleanly (24 entries, up from 23); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 1048 -> 1035.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS24439 (Marshall Islands NTA ISP).** Stuck at `Scheduled` for 90s with zero probe activity (recognized AS7131 pattern); a longer background poll got killed by the system's own memory pressure partway through -- not a measurement problem, just re-fetched the current state directly afterward rather than re-running a second long background wait, then topped up with one more moderate foreground poll to get all 3 probes.

**`has_routing_loop` flagged 2 of 3 probes `True` -- checked directly before trusting it, applying the exact lesson from the AS17828 case two tranches ago.** Both 'repeats' are near-destination addresses (inside Tata's own transit space, not the literal target) replying at consecutive hops with stable, non-climbing RTT -- the same ordinary noise pattern already documented as a known heuristic limit, not a real loop.

**Triangulated**: all 3 probes resolve `AS7131 -> AS174 (Cogent) -> AS6453 (Tata Communications)`, target never resolved (ordinary near-destination filtering), RIS-agreeing with an *exact* match (997) via the last-reached-ASN method. This lands on the existing GU(AS3605)->MH `ConfirmedDetour` adjacency (AS6453<->AS24439) -- a second independent confirmation from a fresh source economy, this time via Cogent directly rather than the original's AS2497/IIJ-Tokyo path. Since the transiting carrier (Tata) is an external, non-Pacific carrier, this follows the `ConfirmedDetour` convention (a new entry per source economy, like the seven AS9249 entries) rather than the `ConfirmedLocalTransit` note-extension convention (which is for in-fishbowl Pacific transit providers like ONATI/FINTEL).

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(7131, 24439)`. Verified: module imports cleanly (25 entries, up from 24); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 1035 -> 1033.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS38198 (Digicel Tonga).** Stuck at `Scheduled` again (recognized pattern); resolved on a moderate longer poll, all 3 probes returned. `has_routing_loop` flagged probe 60689 `True` -- checked directly, same known near-destination-repeat noise pattern (`202.43.12.5`, not the literal target), not a real loop.

**Lands on the existing GU->TO adjacency** (AS45355/Digicel-Fiji<->AS38198), a second independent confirmation, RIS-agreeing with an *exact* match (1,321). Genuinely new detail: probe 62689 resolves an intermediate hop to **AS132528** -- the same Telstra-operated Digicel-Australia backbone ASN already independently confirmed at Equinix Sydney in the NC->FJ/AS45355 entry -- `ixp_crossings` confirms it directly here too, a second, unrelated measurement finding the identical real infrastructure at the same fabric. All 3 probes eventually reach the same real, BGP-confirmed AS38198 address (`202.43.12.5`) already established as this corridor's routine final-hop pattern.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(7131, 38198)`. Verified: module imports cleanly (26 entries, up from 25); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 1033 -> 1029.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS38875 (FSM Telecommunications Corporation).** Unusually fast for this source (9-21ms RTT) -- a genuinely regional path, not a Tokyo/Sydney detour. Both probes cross **Guam IX** directly, and unlike every other IXP crossing this project has recorded so far, this one is **in-fishbowl** (`in_fishbowl: true`): the member ASN is AS10130, one of FSM Telecommunications Corporation's own sibling ASNs.

**Applied the established sibling-identity correction and checked it fully rather than stopping at the surface disagreement.** The literal target (AS38875) never resolved; the traceroute lands on sibling AS139759 instead. Checked both siblings' own RIS neighbor lists directly: both list AS10130 as their only neighbor (1,014 and 1,009 observations) -- so RIS *does* confirm the internal FSM sibling relationship crossed here. But checked one level further before calling this confirmed: AS10130 itself has zero RIS-observed neighbors on record, and AS7131's own list doesn't include AS10130 either -- so the actual traceroute-observed leg (AS7131 -> AS10130) remains unconfirmed by RIS from either side, exactly the same shape as the existing GU(AS3605)->FM(AS38875) MARIIX `CandidatePeering` entry, just at a different in-fishbowl exchange.

**This is the `CandidatePeering` shape**, not `ConfirmedLocalTransit` or `ConfirmedDetour`: a real in-fishbowl crossing and a real sibling-confirmed downstream relationship still don't add up to RIS confirming the specific source-to-target leg itself, per Validation Rule 1. Added as a new entry. Called `mark_corridor_tested(7131, 38875)`. Verified: module imports cleanly (5 entries, up from 4); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 1029 -> 1023.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS45879 (Orange Wallis & Futuna).** Stuck at `Scheduled` again (recognized pattern), resolved on a longer poll. `has_routing_loop` flagged probe 60689 `True` -- checked directly: a single consecutive repeat early in the Hurricane Electric backbone with only a modest RTT bump (49ms->58ms), not the near-destination-silence or steep-RTT-climb shape of a real loop -- ordinary noise, not escalated.

**Lands on the existing GU->WF adjacency** (AS5511/Opentransit-Orange<->AS45879), a second independent confirmation, RIS-agreeing with an *exact* match (1,665). A different path into Orange this time -- AS6939 (Hurricane Electric) directly, no Tokyo/IIJ hop unlike the original. **Checked whether the existing "Tokyo" hub still made sense rather than defaulting to a guess**: fetched AS5511's real PeeringDB facility list directly -- four separate Equinix Tokyo data centers, no Sydney presence at all -- so Tokyo remains the best-sourced location for this adjacency even though this specific traceroute's own path doesn't show a literal Tokyo hop. Noted this explicitly in the entry rather than silently reusing the value.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(7131, 45879)`. Verified: module imports cleanly (27 entries, up from 26); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 1023 -> 1022.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS45891 (Solomon Telekom).** A transient network read-timeout hit `wait_for_results` mid-poll (RIPE Atlas API, not a data problem) -- retried cleanly and got all 3 probes. `has_routing_loop` flagged probe 65653 `True` -- checked directly: two consecutive-address repeats, both stable RTT, the now-familiar ordinary-noise shape, not a real loop.

**Lands on the existing GU->SB adjacency** (AS139609/SISCC<->AS45891), a second independent confirmation, RIS-agreeing with an *exact* match (1,652). A different carrier and a **genuinely new named exchange**: AS7131 -> AS140627 (OneQode) -> AS139609, crossing **IX Australia Sydney (NSW-IX)** -- `ixp_crossings` confirms it directly, the first time this specific exchange (distinct from Equinix Sydney and MegaIX Sydney, both already on record) has appeared in this project.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(7131, 45891)`. Verified: module imports cleanly (28 entries, up from 27); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 1022 -> 1013.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS55885 (Niue).** `has_routing_loop` correctly returned `False` for both probes. Both resolve to AS9471 (ONATI) immediately before the target -- the well-established Niue<->ONATI sibling-ASN adjacency, already independently confirmed three times before (Niue's own vantage point, then Guam).

**Fourth independent corroboration**, extending the existing `ConfirmedLocalTransit` entry rather than duplicating: same sibling-ASN basis (AS55943, 1,662, exact match, confirmed directly against AS55885's own fishbowl neighbor list), but a genuinely different upstream carrier mix this time -- Telia (AS1299) and Tata (AS6453) both appearing for this adjacency for the first time, alongside the already-seen GTT (AS3257).

Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (11). Called `mark_corridor_tested(7131, 55885)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 1013 -> 1011. **Notable: the next live pick is now sourced from AS9249 (Vanuatu), not AS7131** -- the same diversification pattern already seen once before when AS3605's cheap untested targets ran out; AS7131's own untested cross-economy pairs appear to be thinning out similarly.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS55943 (ONATI's other ASN, French Polynesia).** `pick_next_corridor()` still returned AS7131 as source this firing (the backlog file's regenerated preview a moment earlier had shown AS9249 next -- not a contradiction, just the live picker and the last-regenerated snapshot briefly diverging by one tranche). Stuck at `Scheduled` again; resolved on a longer poll. `has_routing_loop` flagged probe 60689 `True` -- checked directly: two consecutive-address repeats early in the path, both modest and stable RTT, the now-familiar ordinary-noise shape, not a real loop.

**Lands on the existing GU->PF adjacency** (AS3257/GTT<->AS55943), a second independent confirmation, RIS-agreeing with an *exact* match (1,657). Same upstream carrier (GTT) but via Cogent (AS174) rather than the original's path. **Checked whether "Tokyo" still held before reusing it** (same discipline as the Orange/WF case): fetched GTT's real PeeringDB facility list directly -- genuine presence at both Tokyo (multiple DCs) and Sydney -- so Tokyo remains well-sourced and consistent with the original entry.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(7131, 55943)`. Verified: module imports cleanly (29 entries, up from 28); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 1011 -> 1007.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS132486 (Kiribati, Ocean Link Ltd).** One of three probes (65653) was a complete dead end from the first hop, unrelated to the corridor. `has_routing_loop` correctly returned `False` for both working probes.

**Immediately recognized the well-established Kiribati Starlink-chain pattern** (documented in the AS154100/BNL-Tarawa<->AS132486 `ConfirmedLocalTransit` entry, already reproduced twice before -- FSM and Guam): both working probes show the identical striking path -- AS7131 -> AS7578/AS137409 (GSL Networks, Australia) -> AS14593 (SpaceX Starlink) -> AS154100 (BNL Tarawa) -> target never resolved. RIS agrees with the identical exact match (362) already on record.

**A third independent reproduction, extending the existing entry's note rather than duplicating.** A third geographically distinct source (CNMI, after FSM and Guam) reaching Kiribati via the same Australia-then-Starlink satellite path -- further reinforcing this as Kiribati's real general-purpose ingress pattern. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (11). Called `mark_corridor_tested(7131, 132486)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 1007 -> 1006.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS134783 (a distinct Kiribati ASN).** Same striking Australia/Starlink chain shape at first glance -- but checked whether this landed on the already-tripled AS132486 pair or something new before writing it up either way. It's a **different, already-separately-confirmed adjacency**: AS154100 (BNL Tarawa) -> AS134783 (ATHKL's other ASN, holder-confirmed as "Amalgamated Telecom Holdings Kiribati Ltd"), already on record as its own `ConfirmedLocalTransit` entry from a prior GU-sourced measurement (211506747), RIS-agreeing with an *exact* match (1,392) -- not the 362/361 count that belongs to the AS132486 pair.

**Second independent corroboration of this specific adjacency**, extending that existing entry's note rather than duplicating: a second geographically distinct source (CNMI, after Guam) confirming AS154100<->AS134783 itself, not just the general Starlink-chain ingress pattern shared across Kiribati's downstream ASNs. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (11). Called `mark_corridor_tested(7131, 134783)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 1006 -> 1005.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS152093 (VakaNet, Cook Islands).** Only 2 of 3 probes returned on the first poll; checked `participant_count` (3, confirmed genuinely queued) and polled longer for the third rather than assuming. `has_routing_loop` flagged probe 60689 `True` -- checked directly: a single consecutive repeat with modest, stable RTT, the now-familiar ordinary-noise shape, not a real loop.

**Lands on the existing GU->CK adjacency** (AS9507/NextHop<->AS152093), a second independent confirmation, RIS-agreeing with an *exact* match (335). **All 3 probes** cross BBIX Tokyo directly this time -- `ixp_crossings` confirms it for every probe, an even stronger direct confirmation than the original's crossing.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(7131, 152093)`. Verified: module imports cleanly (30 entries, up from 29); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 1005 -> 1004.

---

**Next corridor pulled: AS7131 (PTI Pacifica, CNMI) -> AS154100 (BNL Tarawa itself, targeted directly).** Distinct from the two prior Kiribati tranches this session, which targeted downstream customers (AS132486, AS134783) -- this one aims straight at BNL Tarawa's own address, mirroring the "sharpest, most direct confirmation" measurement already on record from Guam. `has_routing_loop` flagged probe 60689 `True` -- checked directly: a modest, stable-ish RTT repeat, the now-familiar false-positive shape, not a real loop.

**2 of 3 probes resolve cleanly to AS14593 (Starlink) as the literal last-reached ASN**, identical RIS match (361) to the original direct-confirmation entry. A third distinct source (CNMI, after Guam) confirming BNL Tarawa's own Starlink upstream directly -- extended that specific entry's paragraph rather than duplicating, distinct from the separate downstream-chain corroboration paragraph added two tranches ago.

Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (11). Called `mark_corridor_tested(7131, 154100)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 1004 -> 1003.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS9471 (ONATI, French Polynesia).** First firing genuinely sourced from AS9249 -- the diversification already flagged as trending this way finally arrived. Only 1 connected probe available (`participant_count: 1`, confirmed directly rather than assumed), a real difference from AS7131's 3-probe pattern. First address dead-ended (target never resolved, upstream AS6939/Hurricane Electric, `has_routing_loop` correctly `False`).

**Applied the retry policy**: fired against the next `list_target_ips(9471)` candidate. This time the target was reached directly. Triangulated: `AS9249 -> AS38442 (Vodafone Fiji) -> AS6939 (Hurricane Electric) -> [gap] -> AS9471`, upstream of target AS6939, `ris_agrees: False`. **Recognized this as the identical shape already established for the AS7131->AS9471 tranche several firings ago**: an external, non-Pacific carrier (Hurricane Electric) sits immediately upstream of the target, and AS9471's own fishbowl neighbor list only shows its ONATI sibling (AS55943) -- RIS's Pacific-scoped fishbowl was never going to corroborate an external carrier's adjacency, this isn't a fresh disagreement to investigate further.

**Not filed in any dataclass**, per that same precedent (NC->GU Superloop shape: real signal, external carrier, doesn't fit `ConfirmedDetour` or `CandidatePeering`). Called `mark_corridor_tested(9249, 9471)` for both the dead-end and retry addresses. No report/map regeneration needed (no dataclass changed). Regenerated the corridor backlog: candidate count dropped 1003 -> 1001.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS9751 (American Samoa).** Reached directly, no retry needed. Path: AS9249 -> AS38442 (Vodafone Fiji) -> AS4637 (Telstra Global) -> AS11404 (Wave Broadband) -> AS9751.

**Lands on the existing MP(AS7131)->AS adjacency** (Wave Broadband<->AS9751), a second independent confirmation, RIS-agreeing with an *exact* match (267). **A genuine improvement on the original finding**: this traceroute directly crosses a real, named exchange -- Equinix San Jose (`ixp_crossings` confirms it) -- where the original found no crossing at all. Added a fourth external hub (`"San Jose": (37.3382, -121.8863)`) to `economy_coordinates.EXTERNAL_HUB_LATLON`, directly observed this time rather than inferred from PeeringDB facility lists like the last two new-hub cases.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(9249, 9751)`. Verified: module imports cleanly (31 entries, up from 30); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 1001 -> 999.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS10131 (Telecom Cook Islands).** Reached directly, no retry needed -- passing through `103.254.224.70`, already independently established as ONATI's own address space from the very first ONATI<->Cook-Islands measurement. `has_routing_loop` correctly returned `False`.

**Immediately recognized the well-established ONATI<->Cook-Islands sibling-ASN adjacency**, already independently confirmed three times before (ONATI's own vantage point, Guam, CNMI): `AS9249 -> AS38442 (Vodafone Fiji) -> AS4637 (Telstra Global) -> AS3257 (GTT) -> AS9471 -> AS10131`, same sibling-ASN basis (RIS confirms via AS55943).

**A fourth independent reinforcement, extending the existing entry's note rather than duplicating.** A fourth distinct source economy (Vanuatu, after ONATI's own vantage point, Guam, and CNMI). Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (11). Called `mark_corridor_tested(9249, 10131)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 999 -> 997.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS17893 (Palau NCC).** Reached directly, no retry needed. `has_routing_loop` correctly returned `False`.

**Lands on this project's very first confirmed finding** (GU->PW/AS17893, AS174/Cogent), already independently reproduced twice before -- but both prior instances were from the same source economy (Guam/AS3605). This is the **first confirmation from a genuinely different source economy**: `AS9249 -> AS38442 (Vodafone Fiji) -> AS2914 (NTT Communications) -> AS174 (Cogent Communications) -> AS17893`, fully contiguous, RIS-agreeing with the identical *exact* match (1,333). A different path into Cogent than either Guam-sourced measurement (via NTT this time, not IIJ/Tokyo), landing on the same ultimate adjacency.

Extended the existing entry's note rather than duplicating. Not a new dataclass entry -- `CONFIRMED_DETOURS` count unchanged (31). Called `mark_corridor_tested(9249, 17893)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 997 -> 995.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS17993 (Samoa).** Reached the literal target directly. Path: `AS9249 -> AS38442 (Vodafone Fiji) -> AS17993`, contiguous, with a real IXP crossing at Equinix Sydney where AS17993 itself resolves as the member (via PeeringDB netixlan) -- a physically-instantiated presence, not inferred.

**`ris_agrees: false` on both sides** -- checked each ASN's full neighbor list directly: neither AS17993's nor AS38442's list mentions the other. Not a fishbowl-scope artifact (both genuinely in-fishbowl). **Checked AS17993's holder name before writing this up**, and it sharpened the finding considerably: "Vodafone Samoa Limited" -- the same corporate brand as AS38442's "Vodafone Fiji", the same intra-corporate shape already established for Digicel Fiji<->Digicel Tonga. A particularly well-motivated candidate, not just a generic clean-traceroute-RIS-disagrees case.

**This is the `CandidatePeering` shape**, per Validation Rule 1 -- a real exchange crossing and a compelling corporate-family motivation still don't substitute for RIS confirmation. Added as a new entry. Called `mark_corridor_tested(9249, 17993)`. Verified: module imports cleanly (6 entries, up from 5); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 995 -> 988.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS23917 (Tuvalu).** `has_routing_loop` correctly returned `False`. Lands on the well-established FINTEL(AS9241)<->Tuvalu adjacency, already independently confirmed three times before (Tuvalu's own vantage point, Guam, CNMI): RIS agrees with the identical exact match (1,009).

**Fourth independent corroboration, extending the existing entry's note rather than duplicating.** A third distinct upstream path into FINTEL this time: AS9249 -> AS38442 (Vodafone Fiji) -> AS4648 (Spark NZ), crossing **MegaIX Sydney** -- neither this specific exchange nor a Sydney crossing had appeared for this adjacency before (prior instances used Level 3/Lumen with no exchange, and Equinix Los Angeles). A fourth distinct source economy (Vanuatu, after Tuvalu, Guam, CNMI).

Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (11). Called `mark_corridor_tested(9249, 23917)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 988 -> 986.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS24439 (Marshall Islands NTA).** Stuck at `Scheduled` (a new probe ID, 1008536, appeared this firing -- AS9249's own slow-scheduling behavior, the same recognized pattern already established for AS7131). Resolved on a longer poll, both probes returned. `has_routing_loop` correctly returned `False` for both.

**Third independent confirmation of the AS6453(Tata)<->AS24439 adjacency** (after the original GU entry via IIJ/Tokyo and the MP entry via Cogent): `AS9249 -> AS38442 (Vodafone Fiji) -> AS7473 (Singtel) -> AS6453`, RIS-agreeing with the identical exact match (997). Singtel is a genuinely new intermediate carrier for this adjacency. No IXP crossing this time; checked Singtel's real PeeringDB facility list before picking a hub -- genuine Tokyo presence, no Sydney -- kept `detour_hub` as Tokyo, matching the original entry rather than the second (Cogent-sourced) entry's Sydney choice.

Per the established `ConfirmedDetour` convention (new entry per source economy for external-carrier adjacencies), added as a new entry rather than extending either prior one. Called `mark_corridor_tested(9249, 24439)`. Verified: module imports cleanly (32 entries, up from 31); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 986 -> 984.

---

**Next corridor pulled (first `/loop`-driven firing): AS9249 (Telecom Vanuatu) -> AS38198 (Digicel Tonga).** Both probes reach the same real, BGP-confirmed AS38198 address (`202.43.12.5`) already established across every prior measurement of this corridor. `has_routing_loop` correctly returned `False` for both.

**Third independent confirmation of the AS45355(Digicel Fiji)<->AS38198 adjacency** (after GU via Level 3/Lumen+Telstra Global and MP via Hurricane Electric): `AS9249 -> AS38442 (Vodafone Fiji) -> AS132528 -> AS45355 -> AS38198`, RIS-agreeing with the identical exact match (1,321). **A third occurrence of AS132528 (Digicel Australia/Telstra backbone) at Equinix Sydney**, confirmed directly this time (`ixp_crossings` non-empty for both probes, unlike the MP-sourced entry where it only appeared as an intermediate hop).

Per the established convention, added as a new entry. Called `mark_corridor_tested(9249, 38198)`. Verified: module imports cleanly (33 entries, up from 32); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 984 -> 980.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS38227 (a distinct Samoa ASN).** Reached the literal target directly, both probes. `has_routing_loop` correctly returned `False`.

**A genuinely new adjacency, not seen before**: `AS9249 -> AS38442 (Vodafone Fiji) -> AS132528 (Digicel Australia/Telstra backbone, crossing Equinix Sydney -- a **fourth** occurrence of this infrastructure this session) -> AS38800 -> AS38227`. Checked both ASNs' holder names before writing this up: AS38800 is **Digicel Samoa Ltd**, AS38227 is **Computer Services Limited (CSL)**, Samoa's incumbent -- a domestic (intra-Samoa) relationship. RIS agrees with an *exact* match (990) -- AS38800 is AS38227's *only* RIS-observed neighbor at all.

**Recognized this as the `ConfirmedLocalTransit` shape**: an in-fishbowl Pacific carrier (Digicel Samoa) acting as a real transit waypoint for another Pacific carrier's network (CSL Samoa), for traffic originating from a third economy (Vanuatu) -- the same pattern already established for ONATI<->Cook-Islands and FINTEL<->Tuvalu, but at the intra-country level rather than inter-economy, a new variant worth keeping distinct.

Added as a new entry. Called `mark_corridor_tested(9249, 38227)`. Verified: module imports cleanly (12 entries, up from 11); regenerated ASCII/HTML reports (render correctly) and the geographic map (renders as a short/zero-length line since both endpoints are Samoa, consistent with the existing intra-Kiribati entries' pattern). Regenerated the corridor backlog: candidate count dropped 980 -> 979.

---

**Standing backlog-regeneration check (user-requested, independent of the per-corridor `/loop` cadence).** Ran `pacific-peering-corridor-backlog` directly. Result: `979 candidates (0 new-probe, 0 new-RIS-relationship)` -- diffed `corridor_backlog.md` directly to confirm rather than trusting the summary line alone: the only change is the `Last regenerated` timestamp, candidate count unchanged at 979. Nothing flagged as genuinely new data (no new connected Atlas probes, no new RIS-observed neighbor relationships) since the last regeneration a few minutes earlier in this same session. Nothing strange or unusual in the diff -- no escalation needed under the standing consult-the-owner order this time.

---

**`/loop` fired again (explicit user re-invocation, dynamic mode): AS9249 (Telecom Vanuatu) -> AS38800 (Digicel Samoa, targeted directly).** Both probes reached the target directly. `has_routing_loop` correctly returned `False`.

**A cleaner, more direct confirmation than last tranche's incidental discovery**: `AS9249 -> AS38442 (Vodafone Fiji) -> AS132528 -> AS38800`, upstream of the target is AS132528 itself directly -- the **fifth** occurrence of the Digicel-Australia/Telstra backbone ASN at Equinix Sydney this session, but the *first* time it's the literal immediate upstream of the target rather than an intermediate waypoint. RIS agrees with an *exact* match (1,656) -- checked directly: AS132528 is AS38800's *only* RIS-observed neighbor at all, not just dominant (corrected the note's wording after checking the raw fishbowl entry directly rather than assuming "dominant" from habit).

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(9249, 38800)`. Verified: module imports cleanly (34 entries, up from 33); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 979 -> 975.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS45879 (Orange Wallis & Futuna).** `has_routing_loop` correctly returned `False`. Lands on the well-established AS5511(Opentransit Orange)<->AS45879 adjacency, already confirmed twice before (GU, MP): `AS9249 -> AS38442 (Vodafone Fiji) -> AS4637 (Telstra Global) -> AS5511`, RIS-agreeing with the identical exact match (1,665). No IXP crossing this time; reused the already-verified Tokyo hub (checked against AS5511's real PeeringDB facility list in the MP-sourced entry) rather than re-verifying from scratch.

Per the established convention, added as a new entry (third source economy for this adjacency). Called `mark_corridor_tested(9249, 45879)`. Verified: module imports cleanly (35 entries, up from 34); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 975 -> 974.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS45891 (Solomon Telekom).** `has_routing_loop` correctly returned `False`. Lands on the well-established AS139609(SISCC)<->AS45891 adjacency, already confirmed twice before (GU, MP via NSW-IX). A notably short, direct path this time: `AS9249 -> AS38442 (Vodafone Fiji) -> AS139609`, RIS-agreeing with the identical exact match (1,652).

**Crosses MegaIX Sydney directly** -- a third distinct Sydney fabric now on record for this project (alongside Equinix Sydney and NSW-IX, both already seen), different from the MP-sourced entry's NSW-IX crossing for this same adjacency. Added as a new entry per the established convention. Called `mark_corridor_tested(9249, 45891)`. Verified: module imports cleanly (36 entries, up from 35); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 974 -> 965.

---

**`/loop` fired again (explicit user re-invocation): AS9249 (Telecom Vanuatu) -> AS55722 (Cenpac Net Inc, Nauru).** Stuck at `Scheduled` again; resolved on a longer poll. Noticed the traceroute's hops resembled AS7131's own established address space even though this measurement is sourced from AS9249, not AS7131 -- checked directly via triangulation rather than assuming, and confirmed it: `AS9249 -> AS38442 (Vodafone Fiji) -> AS6939 (Hurricane Electric) -> AS7131` (upstream of target), matching the exact adjacency already on record from the earlier user-directed AS7131->AS55722 tranche (task_plan.md, ~line 1037-1041). RIS agrees with the identical exact match (1,528).

**Second independent corroboration, extending the existing entry's note rather than duplicating.** A genuinely different source economy (Vanuatu) confirming that AS7131 (PTI Pacifica) really is a transit waypoint for a third economy's traffic reaching Nauru -- not just AS7131's own outbound relationship with its customer, the same regional-hub-carrier shape already established for ONATI, FINTEL, and Digicel Samoa. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (12). Called `mark_corridor_tested(9249, 55722)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 965 -> 964.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS55885 (Niue).** Reached an address within ONATI's own known space (`103.254.224.73`, already established from earlier tranches) before the literal target. `has_routing_loop` correctly returned `False`. Lands on the well-established Niue<->ONATI sibling-ASN adjacency.

**Extended the existing entry as a "Fifth independent corroboration" -- caught and corrected a real error before committing rather than trusting the draft.** First-draft note claimed this was a fifth distinct source economy including "American Samoa," which never actually appeared in this entry's history -- checked the entry's real prior sources directly (`grep` for every "independent corroboration" label in the file) rather than relying on memory, found the actual prior sources were only Niue's own vantage point, Guam, and CNMI. Corrected to "a fourth distinct source economy" before staging. A new upstream carrier for this adjacency either way: AS2914 (NTT Communications), not seen for this specific relationship before.

Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (12). Called `mark_corridor_tested(9249, 55885)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 964 -> 962.

---

**`/loop` fired again (explicit user re-invocation): AS9249 (Telecom Vanuatu) -> AS55943 (ONATI's other ASN, French Polynesia).** `has_routing_loop` correctly returned `False`. Lands on the well-established AS3257(GTT)<->AS55943 adjacency, already confirmed twice before (GU, MP via Cogent). Path: `AS9249 -> AS38442 (Vodafone Fiji) -> AS4637 (Telstra Global) -> AS3257`, RIS-agreeing with the identical exact match (1,657). No IXP crossing this time; reused the already-verified Tokyo hub.

Added as a new entry per the established convention (third source economy). Called `mark_corridor_tested(9249, 55943)`. Verified: module imports cleanly (37 entries, up from 36); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 962 -> 949. Notable: the next live pick includes a source other than AS7131/AS9249 for the first time in a while -- **AS9471 (ONATI, French Polynesia) -> AS4638 (Fiji)** -- source diversification continuing to spread further.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS58932 (Palau Mobile Communications Inc.).** Reached the literal target directly, both probes. `has_routing_loop` correctly returned `False`. `AS9249 -> AS38442 (Vodafone Fiji) -> AS2914 (NTT Communications) -> AS3605 (Guam Cablevision) -> AS58932`, upstream of target AS3605, RIS-agreeing with an *exact* match (664).

**Checked directly whether this landed on an already-confirmed adjacency rather than assuming a fresh finding**: yes -- AS3605<->AS58932 is already on record, originally confirmed from AS3605's own vantage point (following up on its IRR-declared AS-SET naming Palau's ASNs directly). This new measurement is a genuinely different shape though: rather than AS3605's own direct customer relationship, it shows AS3605 acting as a real transit waypoint for a third economy's (Vanuatu's) traffic -- the same regional-hub-carrier pattern already established for ONATI, FINTEL, PTI Pacifica, and Digicel Samoa.

Extended the existing entry's note (second edit attempt succeeded after the first `old_string` match failed -- diagnosed as a copy-paste mismatch in the anchor text, not a real file-state issue, fixed by anchoring on a smaller, verified-exact fragment instead of re-typing the full paragraph from memory). Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (12). Called `mark_corridor_tested(9249, 58932)`. Regenerated ASCII/HTML reports since the note text changed (render correctly, confirmed the new paragraph landed in the right entry); map unaffected. Regenerated the corridor backlog: candidate count dropped 949 -> 948.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS132486 (Kiribati, Ocean Link Ltd).** Stuck at `Scheduled` again (recognized pattern); resolved on a longer poll. `has_routing_loop` correctly returned `False`. Lands on the well-established Kiribati Starlink-chain (AS154100<->AS132486), RIS-agreeing with the identical exact match (362).

**A genuinely new intermediate carrier this time**: `AS9249 -> AS38442 (Vodafone Fiji) -> AS55850 (Mercury NZ Limited) -> AS14593 (Starlink) -> AS154100` -- checked AS55850's holder name directly rather than assuming. Neither Mercury NZ nor a named exchange had appeared for this specific chain before; crosses **MegaIX Sydney** directly (`ixp_crossings` confirms it) -- the first time this Kiribati chain has shown a real exchange crossing rather than plain global transit (GSL Networks, in every prior instance, showed none).

Fourth independent reproduction, extending the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (12). Called `mark_corridor_tested(9249, 132486)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 948 -> 947.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS133897 (Palau Equipment Co. Inc.).** Reached the literal target directly, both probes -- the identical path shape as the AS58932 corroboration two tranches ago (`AS9249 -> AS38442 -> AS2914 -> AS3605 -> target`). `has_routing_loop` correctly returned `False`.

**Lands on the existing AS3605<->AS133897 adjacency**, RIS-agreeing with the identical exact match (662). Second independent corroboration, same shape and same reasoning already applied to the AS58932 case: AS3605 confirmed once more as a genuine transit waypoint for third-economy traffic, not just its own direct customer relationship.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (12). Called `mark_corridor_tested(9249, 133897)`. Regenerated ASCII/HTML reports since the note text changed (render correctly, confirmed both the AS58932 and AS133897 paragraphs are present and distinct); map unaffected. Regenerated the corridor backlog: candidate count dropped 947 -> 946.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS134783 (ATHKL, Kiribati).** Stuck at `Scheduled` again (recognized pattern); resolved on a longer poll. `has_routing_loop` correctly returned `False`. Lands on the well-established AS154100<->AS134783 adjacency, already confirmed twice before (GU, MP), RIS-agreeing with the identical exact match (1,392).

**Genuinely new carriers this time**: `AS9249 -> AS38442 (Vodafone Fiji) -> AS4637 (Telstra Global) -> AS1221 (Telstra domestic) -> AS4826 (Vocus Connect) -> AS14593 (Starlink) -> AS154100`. Neither Telstra's domestic ASN nor Vocus Connect had appeared for this specific adjacency before -- Vocus Connect is already established elsewhere in this project as PNG DataCo's own upstream, a notable cross-reference.

Third independent corroboration, extending the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (12). Called `mark_corridor_tested(9249, 134783)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 946 -> 945.

---

**`/loop` fired again: AS9249 (Telecom Vanuatu) -> AS140504 (a distinct Nauru ASN).** First address dead-ended before reaching the literal target, resolving to AS36149 (Hawaiian Telcom Services Company) as the last-reached ASN, `ris_agrees: False`. **Checked directly whether the disagreement was ordinary or worth investigating further** rather than accepting it at face value: AS140504's own fishbowl neighbor list has exactly two real entries -- AS132528 (1,032, already well-established this session as the Digicel Australia/Telstra backbone from the Samoa and Tonga entries) and AS12684 (616) -- neither matches AS36149 at all. Applied the retry policy given the resolved carrier didn't match RIS's known relationships.

**Retry reached the target directly**, but landed on the same carrier (AS36149/Hawaiian Telcom), now with a confirmed but unresolved gap before the literal target AS140504. Still `ris_agrees: False` -- Hawaiian Telcom genuinely isn't one of AS140504's real RIS-observed neighbors. **Not filed in any dataclass**, matching the established NC->GU Superloop precedent: a real signal (a genuine, resolvable path via an identifiable external carrier), but RIS doesn't corroborate this specific adjacency, and the carrier that RIS *does* show as dominant (AS132528) never appeared in either traceroute -- worth flagging for a future direct test of AS132528's own relationship to AS140504, similar to how the AS38800 direct-target tranche sharpened the AS132528<->Digicel-Samoa relationship earlier.

Called `mark_corridor_tested(9249, 140504)` for both addresses. No report/map regeneration needed (no dataclass changed). Regenerated the corridor backlog: candidate count dropped 945 -> 944.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS141368 (Nauru).** `has_routing_loop` correctly returned `False`. **This is the exact lead flagged several tranches ago** (when a dead-end AS3605 attempt toward AS141368 surfaced its only RIS neighbor as AS55722, itself already confirmed as PTI Pacifica/AS7131's real Nauru customer -- "worth a direct test in a future firing," per the earlier note).

**The lead panned out cleanly.** Both probes: `AS9249 -> AS38442 (Vodafone Fiji) -> AS6939 (Hurricane Electric) -> AS7131 (PTI Pacifica) -> AS55722 (Cenpac Net Inc)`, upstream of target AS55722, RIS-agreeing with an *exact* match (382) -- checked directly: AS55722 is AS141368's *only* RIS-observed neighbor at all. The full chain confirmed in one traceroute: AS7131's already-confirmed upstream role for AS55722, now extended one hop further to AS55722's own domestic downstream (AS141368, holder-confirmed as "ICT"). A domestic (intra-Nauru) adjacency, the same shape as the Digicel Samoa<->CSL Samoa finding.

Added as a new `ConfirmedLocalTransit` entry, closing out a loose thread flagged earlier this session. Called `mark_corridor_tested(9249, 141368)`. Verified: module imports cleanly (13 entries, up from 12); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 944 -> 943.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS152093 (VakaNet, Cook Islands).** `has_routing_loop` correctly returned `False`. Lands on the well-established AS9507(NextHop)<->AS152093 adjacency, already confirmed twice before (GU, MP). The shortest path yet: `AS9249 -> AS38442 (Vodafone Fiji) -> AS9507`, RIS-agreeing with the identical exact match (335). Crosses Equinix Sydney directly.

Added as a new entry per the established convention (third source economy). Called `mark_corridor_tested(9249, 152093)`. Verified: module imports cleanly (38 entries, up from 37); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 943 -> 933.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS152706 (Neotel, Nauru).** Reached the literal target directly, both probes. `has_routing_loop` correctly returned `False`. Lands on the existing GU->NR adjacency (AS6453/Tata<->AS152706), a second independent confirmation, RIS-agreeing with the identical exact match (292).

**No IXP crossing this time; verified Tata's real PeeringDB facility list before reusing the Tokyo hub** rather than assuming it still held -- genuine presence at both Equinix Tokyo and Sydney, consistent with the original entry's choice.

Added as a new entry. Called `mark_corridor_tested(9249, 152706)`. Verified: module imports cleanly (39 entries, up from 38); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 933 -> 932.

---

**Next corridor pulled: AS9249 (Telecom Vanuatu) -> AS154100 (BNL Tarawa, targeted directly).** `has_routing_loop` correctly returned `False`. Both probes resolve cleanly to AS14593 (Starlink) as the literal last-reached ASN, identical RIS match (361) to the existing "sharpest, most direct" entry -- **via the same AS55850 (Mercury NZ) carrier just seen two tranches ago** for the AS132486 downstream-chain finding, now confirmed reaching BNL Tarawa's own address directly too.

Fourth independent confirmation of this specific direct relationship, extending that entry's paragraph. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(9249, 154100)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 932 -> 931.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS4638 (Telecom Fiji)** -- the first firing genuinely sourced from AS9471, per the diversification already flagged several tranches ago. All 3 probes reached the literal target directly. `has_routing_loop` correctly returned `False` for all three.

**Recognized this as the same well-known 202.137.178.x gap zone already flagged twice before this session** (loop tranche 5, and the earlier AS7131->AS4638 tranche): upstream of target is AS7474 -- checked its holder name directly, "SingTel Optus Pty Ltd" (Australia), a genuinely different carrier than either prior instance. But `ris_agrees: False` -- checked AS4638's own fishbowl neighbor list directly: its dominant/only real relationship is AS45349 (1,669, already this project's very first confirmed finding), not AS7474/Optus. Same precedent as both prior AS4638 attempts: real signal, hits the known gap, external carrier doesn't match the real RIS relationship.

Not filed in any dataclass, consistent with the established pattern. Called `mark_corridor_tested(9471, 4638)`. No report/map regeneration needed (no dataclass changed). Regenerated the corridor backlog: candidate count dropped 931 -> 930.

---

**[Significant finding -- a second, genuinely new routing loop, and a real gap in `has_routing_loop` caught live.]** Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS9241 (FINTEL, Fiji). Stuck at `Scheduled`, resolved on a longer poll. Both probes never reach the literal target: instead, from hop ~12 through hop 32 (the traceroute's full remaining length), two addresses -- `202.170.33.11` and `202.170.33.17` -- alternate back and forth, RTT oscillating in the 250-370ms range, TTL climbing the whole way.

**`has_routing_loop` returned `False` for both probes -- checked the raw hops directly anyway, per standing practice, rather than trusting a clean flag at face value on a traceroute that already looked wrong.** Resolved both bouncing addresses via RIPEstat directly: **both are `AS9241` itself** -- this is a real, live routing loop happening *inside FINTEL's own network*, between two of its own routers, not an external carrier. A different case from the original Hurricane-Electric loop (that one looped in an upstream carrier's network); this one loops at the destination's own edge.

**Diagnosed why the detector missed it**: the alternating pattern (A, B, A, B, ...) never has two *immediately consecutive* identical hops -- intervening hops often go unanswered (`None`), breaking the old consecutive-only check. Fixed `has_routing_loop` (`atlas/targets.py`) to check each resolved address against a short rolling window (last 3) instead of only the immediately-previous one -- catches 2- and 3-node alternating cycles without changing behavior for simple consecutive repeats. **Regression-tested directly against every prior recorded case before trusting the fix**: the new loop now correctly flags `True`; the original Hurricane Electric loop still flags `True`/`False`/`True` exactly as before; the successful AS9249 case and every previously-documented false-positive case (AS17828, AS38198, AS45879, AS152093) return identical results to before -- zero regressions, one real gap closed.

**Applied the retry policy anyway** (per the standing rule, and because the first address never reached the target at all): fired against `202.170.32.1`, a different AS9241 prefix. Took a completely different path this time -- via Hurricane Electric (`184.104.x.x`, `72.52.x.x`) -- and dead-ended in total silence at `65.19.142.246`, **the exact same landmark address already identified in the original AS7131->AS9241 loop discovery** several sessions ago (also AS6939/Hurricane Electric space). Two different vantage points (AS7131/CNMI, AS9471/French Polynesia), two different addresses, both surfacing real problems at FINTEL's network edge -- not a one-off artifact of a single source or address.

**Not filed in any dataclass**, matching the established precedent for the original loop finding (a real, live network anomaly documented in prose, not forced into `ConfirmedDetour`/`CandidatePeering`). Called `mark_corridor_tested(9471, 9241)` for both addresses. No report/map regeneration needed. Regenerated the corridor backlog: candidate count dropped 930 -> 929.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS9751 (American Samoa)** -- the first AS9471-sourced firing to actually reach a target. All 3 probes reached directly. Re-checked `has_routing_loop` with the just-fixed detector: correctly `False` for all three, confirming the fix doesn't over-flag a genuinely clean traceroute.

**Third confirmation for AS9751**, via the same ultimate carrier (Cogent) as the original GU entry, but a fresh vantage point (neither GU nor VU): `AS9471 -> AS174 -> AS9751`, RIS-agreeing with the identical exact match (1,055). No IXP crossing; verified Cogent's real PeeringDB facility list before keeping the Tokyo hub -- genuine presence at both Tokyo and Sydney.

Added as a new entry. Called `mark_corridor_tested(9471, 9751)`. Verified: module imports cleanly (40 entries, up from 39); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 929 -> 927.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS17480 (a fresh New Caledonia ASN).** `has_routing_loop` correctly returned `False` for all 3. Second independent confirmation of the AS18200(OPT NC)<->AS17480 adjacency (after the MP entry via Superloop/BBIX Tokyo): `AS9471 -> AS6939 (Hurricane Electric) -> AS18200 -> AS17480`, RIS-agreeing with the identical exact match (1,665).

**A genuinely different named exchange this time**: crosses Equinix Sydney directly, not BBIX Tokyo. Worth a direct callback to the original entry's own note: that measurement observed AS17480 crossing *neither* of its own registered regional presences (Equinix Sydney, CAN'L IX Noumea). This one *does* match its registered Sydney presence -- a nice confirmatory contrast showing the same target's real traffic uses genuinely different real infrastructure depending on the source.

Added as a new entry. Called `mark_corridor_tested(9471, 17480)`. Verified: module imports cleanly (41 entries, up from 40); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 927 -> 902.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS17828 (PNG DataCo).** Only 1 of 3 probes returned initially; checked `participant_count` (3, confirmed genuinely queued) and polled longer for the rest. `has_routing_loop` correctly returned `False` for all three.

**Third independent confirmation of this project's very first-ever finding** (AS6939<->AS17828, after GU and MP): all 3 probes `AS9471 -> AS6939 -> [gap] -> AS17828`, RIS-agreeing with the identical exact match (1,283). All 3 reach the same real near-destination address (`202.165.198.250`) already established from the GU entry as this corridor's routine last-hop pattern.

Added as a new entry. Called `mark_corridor_tested(9471, 17828)`. Verified: module imports cleanly (42 entries, up from 41); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 902 -> 868.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS17893 (Palau NCC).** Reached the literal target directly, all 3 probes. `has_routing_loop` correctly returned `False`. A genuinely different adjacency than the existing AS7131->AS17893 `CandidatePeering` entry (that one was a direct AS7131-AS17893 hop with RIS disagreeing): this one goes via AS6939 (Hurricane Electric), and RIS *agrees* -- exact match (106).

**The first direct traceroute confirmation of this specific adjacency**: AS6939 already appeared in AS17893's own neighbor list as quoted context inside the existing `CandidatePeering` entries (`{174: 1333, 140627: 139, 6939: 106, ...}`), but had never itself been the traceroute-confirmed upstream until now -- a real, minor relationship, not noise. No IXP crossing; checked Hurricane Electric's real PeeringDB facility list before picking Sydney -- genuine presence, consistent with the Sydney hub already used for this carrier elsewhere.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(9471, 17893)`. Verified: module imports cleanly (43 entries, up from 42); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 868 -> 860.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS17993 (Vodafone Samoa).** Only 2 of 3 probes returned initially; checked `participant_count` (3, confirmed genuinely queued) and polled longer for the third. `has_routing_loop` correctly returned `False` for all three. Second independent confirmation of the AS6939(Hurricane Electric)<->AS17993 adjacency (after MP): `AS9471 -> AS6939 -> AS17993`, RIS-agreeing with the identical exact match (150). Crosses Equinix Sydney directly, confirmed for all 3 probes this time (the original only had partial confirmation).

Added as a new entry. Called `mark_corridor_tested(9471, 17993)`. Verified: module imports cleanly (44 entries, up from 43); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 860 -> 854.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS23917 (Tuvalu).** Only 2 of 3 probes returned initially; confirmed `participant_count` (3) and polled longer. `has_routing_loop` correctly returned `False` for all three. Fifth independent corroboration of the well-established FINTEL<->Tuvalu adjacency (after Tuvalu's own vantage point, Guam, CNMI, and Vanuatu): RIS-agreeing with the identical exact match (1,009), via the same AS4648 (Spark NZ) carrier as the VU-sourced instance, but no IXP crossing this time -- a plainer path even via the same intermediate carrier.

Extended the existing entry's note rather than duplicating. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(9471, 23917)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 854 -> 852.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS24390 (USP, Fiji).** `has_routing_loop` correctly returned `False`. Second independent confirmation of the AS7575(AARNet)<->AS24390 adjacency (after the MP entry via OneQode): `AS9471 -> AS6939 (Hurricane Electric) -> AS7575`, RIS-agreeing with the identical exact match (337) -- this time via Hurricane Electric directly.

**Crosses a real named exchange this time**: Any2West, confirmed directly for all 3 probes. **Caught and fixed a real error in the first draft before committing**: initially assigned `detour_hub="Honolulu"` from memory without checking -- caught it by re-verifying Any2West's actual location (Los Angeles/Silicon Valley, already established elsewhere in this project's own `candidate_peering.py`), which is neither Honolulu nor close enough to the existing San Jose hub (~550km away) to reuse without misrepresenting the map. Added a genuine fifth external hub (`"Los Angeles": (34.0522, -118.2437)`) rather than either error.

Added as a new entry. Called `mark_corridor_tested(9471, 24390)`. Verified: module imports cleanly (45 entries, up from 44); regenerated ASCII/HTML reports (render correctly, confirms "Los Angeles" hub label) and the geographic map. Regenerated the corridor backlog: candidate count dropped 852 -> 835.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS24439 (Marshall Islands NTA).** `has_routing_loop` correctly returned `False` for all three. Fourth independent confirmation of the AS6453(Tata)<->AS24439 adjacency (after GU via IIJ/Tokyo, MP via Cogent, and VU via Singtel): `AS9471 -> AS3257 (GTT) -> AS6453`, RIS-agreeing with the identical exact match (997). GTT is a genuinely new intermediate carrier for this adjacency. No IXP crossing; reused the already-verified Tokyo hub for Tata.

Added as a new entry. Called `mark_corridor_tested(9471, 24439)`. Verified: module imports cleanly (46 entries, up from 45); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 835 -> 833.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS38198 (Digicel Tonga).** Stuck at `Scheduled` (recognized pattern); resolved on a longer poll. All 3 probes reach the same real, BGP-confirmed AS38198 address (`202.43.12.5`) already established across every prior measurement of this corridor. `has_routing_loop` correctly returned `False`.

**Fourth independent confirmation of the AS45355(Digicel Fiji)<->AS38198 adjacency** (after GU, MP, VU): `AS9471 -> AS6939 (Hurricane Electric) -> AS132528 -> AS45355 -> AS38198`, RIS-agreeing with the identical exact match (1,321). **A sixth occurrence of AS132528** (Digicel Australia/Telstra backbone) at Equinix Sydney this session, confirmed directly for all 3 probes.

Added as a new entry. Called `mark_corridor_tested(9471, 38198)`. Verified: module imports cleanly (47 entries, up from 46); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 833 -> 829.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS38875 (FSM Telecommunications Corporation).** All 3 probes returned. First save attempt wrote the raw Atlas API response instead of the parsed shape `analyze_measurement` expects (a `KeyError: 'hops'`) -- caught immediately from the traceback, fixed by re-fetching via `fetch_raw_results` + `parse_traceroute_results` and saving the dataclass shape instead. `has_routing_loop` correctly returned `False` for all three once re-checked against the corrected file.

**Lands on the same FSM sibling-substitution shape already established twice this session** (GU and MP sourced): the literal target (AS38875) never itself resolved; all 3 probes land on sibling AS139759 instead, via `AS9471 -> AS6939 (Hurricane Electric) -> AS9246 (Teleguam Holdings/GTA) -> AS139759`, contiguous throughout. `ris_agrees: False` on the corrected adjacency, matching both prior instances (neither sibling lists AS9246 as a neighbor).

**Genuinely new infrastructure this time**: `ixp_crossings` confirms AS9246 crosses at **Any2West**, not MARIIX (GU entry) or Guam IX (MP entry) -- verified directly via PeeringDB's netixlan API before trusting it: AS9246 holds a real Any2West membership (alongside SIX Seattle, MARIIX, BBIX Tokyo). Unlike the prior two in-fishbowl crossings, Any2West is out-of-fishbowl -- the first time this FSM corridor has shown a crossing outside the region's own exchanges.

Added as a new `CandidatePeering` entry (third source economy for this specific corridor shape). Called `mark_corridor_tested(9471, 38875)`. Verified: module imports cleanly (7 entries, up from 6); regenerated ASCII/HTML reports (render correctly); map unaffected (candidate_peering doesn't feed it). Regenerated the corridor backlog: candidate count dropped 829 -> 828.

---

**[Genuine promotion.] Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS45193 (a third FSM Telecommunications Corporation sibling ASN).** All 3 probes returned. `has_routing_loop` correctly returned `False` for all three.

**This traceroute resolves the literal target directly** -- the first time this project has ever reached AS45193 (or, for that matter, escaped the sibling-substitution stall this specific FSM corridor shape has shown every prior time, including the AS38875 candidate finding filed minutes earlier this same tranche). All 3 probes: `AS9471 -> AS6939 (Hurricane Electric) -> AS9246 (Teleguam Holdings/GTA) -> AS139759 -> AS45193`, fully contiguous. `ris_agrees: True`, exact match (1,681) -- RIS directly confirms the AS139759<->AS45193 internal FSM sibling relationship. Crosses **Any2West** (`ixp_crossings` confirms it, member AS9246), already independently PeeringDB-verified as a real membership when it first surfaced as a candidate finding for AS38875 just before this.

Added as a new `ConfirmedDetour` entry -- the sibling-substitution pattern that has stayed candidate-only across two prior source economies (GU, MP) finally resolved into a genuine RIS-confirmed adjacency once the literal target itself was reachable. Called `mark_corridor_tested(9471, 45193)`. Verified: module imports cleanly (48 entries, up from 47); regenerated ASCII/HTML reports and the geographic map (render correctly, confirmed the new "PF -> FM (AS45193): detours via Any2West (Los Angeles)" line). Regenerated the corridor backlog: candidate count dropped 828 -> 819.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS45879 (Orange Wallis & Futuna).** `has_routing_loop` correctly returned `False` for all three. Fourth independent confirmation of the AS5511(Opentransit Orange)<->AS45879 adjacency (after GU, MP, VU): all 3 probes `AS9471 -> AS3257 (GTT) -> AS5511`, target never resolved (ordinary ICMP filtering), RIS-agreeing with the identical exact match (1,665). GTT is a genuinely new intermediate carrier for this corridor. No IXP crossing; reused the already-verified Tokyo hub for Opentransit Orange.

Added as a new entry. Called `mark_corridor_tested(9471, 45879)`. Verified: module imports cleanly (49 entries, up from 48); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 819 -> 818.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS45891 (Solomon Telekom Co Ltd).** `has_routing_loop` correctly returned `False` for all three. Fourth independent confirmation of the AS139609(SISCC)<->AS45891 adjacency (after GU, MP, VU): all 3 probes `AS9471 -> AS6939 (Hurricane Electric) -> AS139609`, target never resolved (ordinary ICMP filtering), RIS-agreeing with the identical exact match (1,652) -- checked directly: AS139609 remains AS45891's *only* RIS-observed neighbor at all. Crosses **NSW-IX** directly, the same named exchange as the original MP-sourced entry (a second confirmation of this specific Sydney fabric, alongside the VU-sourced entry's separate MegaIX Sydney crossing).

Added as a new entry. Called `mark_corridor_tested(9471, 45891)`. Verified: module imports cleanly (50 entries, up from 49); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 818 -> 809 (AS9471's remaining cheap untested targets ran further out, following the same diversification pattern noted earlier this session; AS10131, Cook Islands, is now first in the backlog).

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS55722 (Cenpac Net Inc, Nauru).** `has_routing_loop` correctly returned `False` for all three. All 3 probes: `AS9471 -> AS6939 (Hurricane Electric) -> AS7131 (PTI Pacifica)` -- target never resolved (same short-path silence pattern as every prior instance of this corridor). RIS agrees with the identical exact match (1,528).

**Third independent corroboration** of AS7131's real transit-waypoint role for Nauru's international connectivity (after MP self-sourced, and VU as a transit waypoint), now a third distinct source economy. **Caught and fixed a counting error before committing**: first draft called this "a fourth distinct source economy" -- re-counted directly (MP, VU, PF) rather than trusting the draft, corrected to "third" before staging.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(9471, 55722)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 809 -> 808.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS132486 (Kiribati, Ocean Link Ltd).** `has_routing_loop` correctly returned `False` for all three. Fifth independent reproduction of the well-established AS154100<->AS132486 Kiribati Starlink-chain adjacency (after FSM, GU, MP, VU): all 3 probes `AS9471 -> AS6939 (Hurricane Electric) -> AS14593 (Starlink) -> AS154100`, target never resolved, RIS-agreeing with the identical exact match (362).

**A genuinely new named exchange this time**: one of 3 probes crosses **EdgeIX Auckland** directly (`ixp_crossings` confirms it, member AS14593) -- verified as a real PeeringDB-declared Starlink membership before writing it up. Only the second time this chain has shown a real exchange crossing at all (after the VU entry's MegaIX Sydney); every other instance showed plain global transit via GSL Networks with no IXP crossing.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(9471, 132486)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 808 -> 807.

---

**Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS134783 (ATHKL, Kiribati).** `has_routing_loop` correctly returned `False` for all three. Fourth independent corroboration of the AS154100<->AS134783 adjacency (after GU, MP, VU): all 3 probes `AS9471 -> AS6939 (Hurricane Electric) -> AS14593 (Starlink) -> AS154100`, target never resolved, RIS-agreeing with the identical exact match (1,392).

One of 3 probes crosses **EdgeIX Auckland** directly (`ixp_crossings` confirms it) -- the same exchange just confirmed minutes earlier for the sibling AS132486 chain, now seen on this adjacency too.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(9471, 134783)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 807 -> 806.

---

**[Significant finding -- first-ever confirmed SES Astra relationship.] Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS140504 (a distinct Nauru ASN).** The exact lead flagged in an earlier VU-sourced tranche. First address dead-ended identically: all 3 probes resolved to AS36149 (Hawaiian Telcom), `ris_agrees: False`. Applied the standing retry policy against a different cached prefix.

**The retry reached AS140504's real relationship directly**: all 3 probes `AS9471 -> AS6939 (Hurricane Electric) -> AS36149 (Hawaiian Telcom) -> [gap] -> AS12684`, RIS-agreeing with an exact match (616) -- the second, previously-untested entry in AS140504's two-relationship RIS neighbor list (`{132528: 1032, 12684: 616}`). Checked the holder identity directly: **SES ASTRA S.A.**, a major geostationary satellite operator -- the same carrier flagged but never confirmed in the earlier Cook Islands tranche (that attempt stalled at generic transit, and a direct-source test was later ruled out entirely since AS12684 has zero connected Atlas probes). **This closes that open thread from the other direction: the first traceroute-confirmed SES Astra relationship this project has recorded.**

**Caught a real query bug before trusting any hub-attribution evidence**: an initial PeeringDB facility lookup using `asn=` as the `netfac` filter silently returned unfiltered, unrelated global data for both AS12684 and AS36149 (a large list of random facilities that turned out identical between the two queries -- the tell that something was wrong). Re-queried using each network's actual `net_id` (via `/api/net?asn=`) and got correct, small, verifiable lists: AS12684 (SES Astra) has **zero** registered facilities (expected for a satellite operator with no physical colocation); AS36149 (Hawaiian Telcom) has two, both in Los Angeles (CoreSite LA1/LA2). Attributed `detour_hub="Los Angeles"` from the verified intermediate carrier rather than the unverifiable satellite operator itself, noted transparently in the entry.

Added as a new `ConfirmedDetour` entry. Called `mark_corridor_tested(9471, 140504)` for both addresses. Verified: module imports cleanly (51 entries, up from 50); regenerated ASCII/HTML reports and the geographic map (render correctly, confirmed the new "PF -> NR (AS140504): detours via AS12684 (SES ASTRA S.A.)..." line). Regenerated the corridor backlog: candidate count dropped 806 -> 803.

---

**[Third distinct routing-loop discovery this session, inside Starlink's own network -- flagged to the project owner per the standing anomaly rule.] Next corridor pulled: AS9471 (ONATI, French Polynesia) -> AS154100 (BNL Tarawa, targeted directly).** 2 of 3 probes resolved cleanly, `has_routing_loop` correctly `False`; the third (probe 52614) returned `True`.

**Checked the raw hops directly rather than trusting the flag at face value**, per standing practice: two immediately consecutive identical addresses (`206.224.66.23`, hops 18-19), well past the point (hop ~9) where AS14593 (Starlink) was already resolved and used for this same probe's RIS agreement -- so the loop doesn't affect the triangulation result for this tranche. Resolved the looping address directly via RIPEstat: it belongs to **AS14593 itself** -- a real, live routing loop inside Starlink's own network. A third distinct loop location this session (after Hurricane Electric's network and FINTEL's own edge), and the first one found inside Starlink specifically. **Surfaced clearly to the project owner in conversation, not just logged**, per the standing rule.

All 2 clean probes: `AS9471 -> AS6939 (Hurricane Electric) -> AS14593`, target never resolved, RIS-agreeing with the identical exact match (361) -- fifth independent confirmation of the direct AS154100<->AS14593 relationship (after GU, MP, VU, and this same tranche's own AS132486 downstream-chain measurement). One probe crosses EdgeIX Auckland.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(9471, 154100)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 803 -> 802.

---

**Source diversified: AS9471's cheap remaining targets are exhausted; the backlog now pulls from AS10131 (Cook Islands), as anticipated several tranches ago.** Next corridor pulled: AS10131 (Cook Islands) -> AS4638 (Telecom Fiji). Only 1 of 3 probes returned; checked `participant_count` directly (1, not 3) -- a genuine single-probe assignment this time, not the usual slow-reporting "Scheduled" pattern, so proceeded with the one result rather than polling longer for probes that were never queued. `has_routing_loop` correctly returned `False`.

**The fourth time this session hitting the exact same known `202.137.178.x` gap zone** (after loop tranche 5, the PTI Pacifica/AS7131 attempt, and the PF/AS9471 attempt): hops 15-16 land on the identical addresses (`202.137.178.160`, `.55`) already flagged as a recognized unresolved zone near AS4638's boundary. This time routed via a fourth distinct carrier chain: `AS10131 -> AS9471 (ONATI) -> AS3257 (GTT) -> AS7474 (SingTel Optus)`, target technically reached at hop 20 but with real unresolved hops in between (`contiguous: False`). `ris_agrees: False` -- checked AS4638's neighbor list directly: still exactly one real entry, AS45349 (1,669), not AS7474.

Not filed in any dataclass, consistent with the established pattern. Called `mark_corridor_tested(10131, 4638)`. No report/map regeneration needed (no dataclass changed). Regenerated the corridor backlog: candidate count dropped 802 -> 801.

---

**[User-directed edit — the project owner identified the IXP registry stat as the report's real headline.]** Per the project owner: "the ixp data is the main headline: 2/3rds of peering points in use are OUTSIDE the fish bowl." Verified the exact number before acting on the framing: of the 31 real exchanges this project's own in-scope ASNs actually declare PeeringDB membership at (not an arbitrary IXP count -- the registry is seeded only from memberships of tracked fishbowl ASNs), 21 sit outside the 20-economy study region -- **67.7%**, matching "2/3rds" exactly.

Added a computed `ReportData.ixp_registry_out_of_fishbowl_share` property (derived from the two existing int counts, never stored separately, so it can't drift out of sync) and surfaced it as an actual headline in both report renderers: a `HEADLINE:` line at the very top of the ASCII summary, and a visually distinct red-bordered banner at the top of the HTML report (reusing the existing `_CRITICAL` color token from the shared palette, matching the "sub-optimal routing" framing this project exists to document). Regenerated both reports -- render correctly, HTML parses cleanly. Not a dataclass change, so the corridor backlog and detour/transit/candidate counts are unaffected.

---

**[Third independent reproduction of the FINTEL routing loop, from a new vantage point.] Next corridor pulled: AS10131 (Cook Islands) -> AS9241 (FINTEL, Fiji).** Only 1 of 3 probes returned; checked `participant_count` directly (1, not 3) -- genuine single-probe assignment again, same as the AS4638 tranche two firings ago. `has_routing_loop` correctly returned `True`.

**Checked the raw hops directly rather than trusting the flag**: the traceroute alternates between `202.170.33.17` and `202.170.33.11` from hop 16 through hop 32 (the traceroute's full remaining length), RTT steady around 282-292ms. Resolved both addresses via RIPEstat: both are **AS9241 itself** -- the identical two addresses already identified in the original AS9471->AS9241 loop discovery earlier this session. **A third independent vantage point (Cook Islands, after MP's original discovery and PF's reproduction) now hits the exact same live loop inside FINTEL's own network edge**, reinforcing that this is a persistent, real condition, not a one-off artifact tied to any single source. Not retried with a different address this time -- the finding is already thoroughly established from two prior tranches, and a third reproduction of the identical addresses doesn't need further corroboration to be credible.

Not filed in any dataclass, matching the established precedent for this anomaly. Called `mark_corridor_tested(10131, 9241)`. No report/map regeneration needed (no dataclass changed). Regenerated the corridor backlog: candidate count dropped 801 -> 800.

---

**[Governance decision, per the project owner: "OneQode under these circumstances should 'inside' the fishbowl."]** Follows directly from the OneQode/Guam addendum above (MP->FJ/AS4638 tranche). Asked a scoping question before touching anything -- this is exactly the kind of load-bearing classification distinction the project's own IXP-registry governance rule says should never be auto-decided. Project owner confirmed the narrow scope: **only hops confirmed crossing OneQode's specific real Guam facility count as in-fishbowl; OneQode's other PoPs (Sydney, Tokyo, LA, Hong Kong, Singapore, Melbourne, Brisbane) stay out-of-fishbowl.**

Built a new hand-curated registry, `analysis/regional_carrier_facilities.py`, mirroring `ixp_lan_registry.py`'s governance style: evidence-based (a hop only matches when its PTR record or other direct evidence identifies the specific facility, never auto-applied from an ASN's registration country), and scoped to the specific confirmed facility rather than the whole carrier -- an external carrier having one real in-region PoP doesn't make its whole global footprint in-fishbowl. First (and so far only) entry: OneQode/AS140627's RTI Guam GNC facility, matched via a `gu-gnc` hostname-pattern field, with the full PTR-record evidence chain (`gu-gnc-rt1-----Vlan756.hk-mgi-rt1.oneqode.net`) documented directly in the entry. Verified the module imports cleanly (1 entry). OneQode's second known real Guam facility (Tata's Piti Cable Landing Station) is noted in the entry's evidence but not yet added as its own registry row -- no traceroute has matched a hop to it specifically yet.

**Retroactively corrects how the MP->FJ(AS4638) finding reads**: the OneQode leg of that traceroute (`AS7131 -> AS140627 (OneQode, Guam facility) -> AS4637 (Telstra Global) -> [gap] -> AS4638`) now reads as CNMI's traffic reaching real in-region infrastructure (Guam) before *then* detouring out via Telstra Global -- not a same-carrier out-of-region hop the whole way. The finding itself remains unfiled in any dataclass (RIS still disagrees on AS4637<->AS4638, so Validation Rule 1 still isn't satisfied), but the narrative shape changes: "in-region, then out" rather than "out-of-region the whole way." Worth re-checking against this registry any time a future OneQode-crossing hop turns up, and worth extending the registry itself if another external carrier's specific in-region facility ever gets the same kind of direct confirmation.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS9751 (American Samoa).** The first firing genuinely sourced from AS10131 to actually reach a target. Only 1 of 3 probes returned; checked `participant_count` directly (1, not 3) -- consistent with every other AS10131-sourced measurement this session, a genuine single-probe assignment rather than a slow-reporting pattern. `has_routing_loop` correctly returned `False`.

Fourth confirmation of the AS174(Cogent)<->AS9751 adjacency (after GU, VU, PF): `AS10131 -> AS9471 (ONATI, French Polynesia) -> AS174 -> AS9751`, fully contiguous, RIS-agreeing with the identical exact match (1,055). Notable: Cook Islands' traffic transits ONATI's own network en route to Cogent -- the same regional-hub role already well-established for ONATI elsewhere this session.

Added as a new entry. Called `mark_corridor_tested(10131, 9751)`. Verified: module imports cleanly (52 entries, up from 51); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 800 -> 798.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS17480 (a fresh New Caledonia ASN).** Only 1 of 3 probes returned; checked `participant_count` (1, not 3) -- the same genuine single-probe pattern as every other AS10131-sourced measurement this session. `has_routing_loop` correctly returned `False`.

Third independent confirmation of the AS18200(OPT NC)<->AS17480 adjacency (after MP via BBIX Tokyo and PF via Equinix Sydney): `AS10131 -> AS9471 (ONATI, French Polynesia) -> AS6939 (Hurricane Electric) -> AS18200 -> AS17480`, fully contiguous, RIS-agreeing with the identical exact match (1,665). Crosses Equinix Sydney directly -- the same exchange and the same ONATI-transit path shape already seen on the AS9751 corridor earlier this tranche cycle.

Added as a new entry. Called `mark_corridor_tested(10131, 17480)`. Verified: module imports cleanly (53 entries, up from 52); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 798 -> 779.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS17828 (PNG DataCo).** Only 1 of 3 probes returned; checked `participant_count` (1, not 3) -- the same genuine single-probe pattern as every other AS10131-sourced measurement this session. `has_routing_loop` correctly returned `False`.

Fourth independent confirmation of this project's very first-ever confirmed finding (AS6939<->AS17828), after GU, MP, and PF: `AS10131 -> AS9471 (ONATI, French Polynesia) -> AS6939 -> [gap] -> AS17828`, RIS-agreeing with the identical exact match (1,283) -- the same ONATI-transit shape already seen on both the AS9751 and AS17480 corridors this tranche cycle, reinforcing ONATI's real role as Cook Islands' de facto regional gateway to international transit.

Added as a new entry. Called `mark_corridor_tested(10131, 17828)`. Verified: module imports cleanly (54 entries, up from 53); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 779 -> 748.

---

**[User-directed fix: "the html report now needs a trim, it is blowing out with a massive unnecessary bulk."]** Diagnosed before changing anything: the notes attached to `ConfirmedDetour`/`ConfirmedLocalTransit`/`CandidatePeering` entries accumulate one paragraph per independent corroboration as a corridor gets re-tested (some now run 2,000-8,000+ characters, after five or more tranches' worth of extensions) -- 57KB of detour notes and 38KB of local-transit notes alone, all rendered as plain visible text on the page. The ASCII report was never the problem (fixed-width, scrolls naturally); the HTML page was rendering every one of these as an uncollapsed wall of text.

**Fix**: added a `_note_block` helper to `reports/html_report.py` that wraps each note in a native HTML5 `<details>`/`<summary>` element -- a short preview (first sentence, or first ~160 chars) always visible, full text collapsed by default, no JS required, one-click to expand. Applied to all three card types (detour, transit, candidate). Added minimal CSS (`cursor: pointer` on the summary, a small hover/open-state touch) reusing the existing `.note` color/sizing rules, which already apply correctly to the new `<details>` element since they're class-selector, not tag-selector, based.

**Deliberately did not touch the underlying data**: the full notes in `confirmed_detours.py`/`confirmed_local_transit.py`/`candidate_peering.py` remain exactly as extended -- they're the durable evidentiary record and git history, not something to trim or summarize away. `report.txt` also stays untouched (plain text has no collapse mechanism and wasn't the actual complaint). Regenerated the HTML report: raw byte size actually ticked up slightly (167,687 vs 154,763 -- the `<details>` markup itself adds bytes, and no text was removed), but the *rendered* page collapses from a continuous scroll of visible paragraph text down to short one-line previews per card, which is what "blowing out with bulk" actually meant. Verified the HTML still parses cleanly and the preview/expand markup renders as expected for several sample cards.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS17893 (Palau NCC).** Only 1 of 3 probes returned; checked `participant_count` (1, not 3) -- the same genuine single-probe pattern as every other AS10131-sourced measurement this session. `has_routing_loop` correctly returned `False`.

Second independent confirmation of the AS6939(Hurricane Electric)<->AS17893 adjacency (after the PF entry) -- **and genuinely stronger evidence this time**: `AS10131 -> AS9471 (ONATI) -> AS6939 -> AS17893`, fully contiguous, the literal target resolving directly (the PF entry never reached it). RIS agrees with the identical exact match (106). Crosses **BBIX Tokyo** directly (`ixp_crossings` confirms it) -- the PF entry showed no IXP crossing at all; verified AS17893's real BBIX Tokyo membership via PeeringDB before trusting it.

Added as a new entry. Called `mark_corridor_tested(10131, 17893)`. Verified: module imports cleanly (55 entries, up from 54); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 748 -> 743.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS17993 (Vodafone Samoa).** Only 1 of 3 probes returned; checked `participant_count` (1, not 3) -- the same genuine single-probe pattern as every other AS10131-sourced measurement this session. `has_routing_loop` correctly returned `False`.

Third independent confirmation of the AS6939(Hurricane Electric)<->AS17993 adjacency (after MP and PF): `AS10131 -> AS9471 (ONATI) -> AS6939 -> AS17993`, fully contiguous, RIS-agreeing with the identical exact match (150). Crosses Equinix Sydney directly -- the same exchange as both prior entries, and the same ONATI-transit shape now seen on every AS10131-sourced corridor this tranche cycle.

Added as a new entry. Called `mark_corridor_tested(10131, 17993)`. Verified: module imports cleanly (56 entries, up from 55); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 743 -> 737.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS23917 (Tuvalu Telecommunications Corporation).** Only 1 of 3 probes returned; checked `participant_count` (1, not 3) -- the same genuine single-probe pattern as every other AS10131-sourced measurement this session.

**Given AS9241/FINTEL's own live routing-loop anomaly (reproduced three times elsewhere this session), checked the raw hops directly rather than trusting the clean `has_routing_loop` flag at face value**: no repeated addresses anywhere in the path, and none of the hop addresses fall in the known `202.170.33.x` loop zone -- a genuinely clean traceroute, not a near-miss.

Sixth independent corroboration of the AS9241(FINTEL)<->AS23917(Tuvalu) adjacency (after Tuvalu's own vantage, Guam, CNMI, Vanuatu, French Polynesia): `AS10131 -> AS9471 (ONATI) -> AS6939 (Hurricane Electric) -> AS4648 (Spark NZ) -> AS9241 -> AS23917`, RIS-agreeing with the identical exact match (1,009). Crosses Equinix Los Angeles -- the same exchange as the MP entry, not the VU/PF entries' MegaIX Sydney or no-crossing paths.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(10131, 23917)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 737 -> 735.

---

**[OPEN ISSUE -- flagged by the project owner: "is there really a pathway from PF to JP directly?", investigated, confirmed real, not yet fixed pending direction.]** Checked all 3 `ConfirmedDetour` entries sourced from PF using `detour_hub="Tokyo"` (AS9751/Cogent, AS24439/GTT+Tata, AS45879/Orange). For each, checked `ixp_crossings` in the saved triangulation JSON -- **empty for all three, no measurement ever showed an actual Tokyo exchange crossing**. Went further and reverse-DNS'd the actual resolved hop addresses for real geographic evidence:

- **AS9751 (Cogent)**: hostnames resolve to `lax01`, `sfo01`, `pdx02` -- Los Angeles, San Francisco, Portland. **Entirely US West Coast, nowhere near Japan.**
- **AS24439 (Tata)**: hostnames resolve to `lvw-losangeles` then `pv4-piti` (twice) -- Los Angeles, then **Guam (Piti)**, the same cable-landing-station location already confirmed for OneQode. Not Tokyo. A second, independent confirmation of a global carrier's real physical Guam presence.
- **AS45879 (Orange)**: no PTR records on the resolved hops; RTT jumps ~99ms -> ~263ms at the last resolved hop, consistent with a long haul, but nothing confirms Tokyo specifically -- never actually verified, just inherited.

**Root cause**: `detour_hub="Tokyo"` was assigned to each of these because the carrier (Cogent/Tata/Orange) has *some* independently-verified Tokyo PeeringDB facility, established while writing a *different* source economy's entry for the same carrier, then reused here on the stated principle of "kept `detour_hub` as Tokyo, matching the original entry" -- without re-checking whether *this specific* traceroute's real hops actually went anywhere near Japan. Two of three are now demonstrably wrong; the third was never actually confirmed either way.

**Not yet corrected** -- asked the project owner how to handle it (fix these three entries' `detour_hub` to the now-confirmed real locations vs. first sweeping every other "kept hub, matching the original entry" phrase across the whole file for the same issue, since this likely isn't limited to these three) and the conversation moved on to the next `/loop` tranche before an answer came back. **Next session/tranche should either resume this directly or wait for explicit direction** -- do not silently "fix" this without confirming scope first, per the standing governance principle already applied to the OneQode/regional-carrier-facility decision.

---

**[RESOLVED -- per the project owner: "router naming is far more useful that blindly picking a FAC on peeringDB" / "so, that means we need to find a way to geolocate hops reliably."]** Direction received mid-tranche, addressed before continuing the corridor loop.

**Built `analysis/hop_geolocation.py`**: a reusable, hand-curated hostname-pattern registry (`resolve_hostname`, `geolocate_hop`), mirroring the governance style already established for `ixp_lan_registry.py` and `regional_carrier_facilities.py` -- every pattern is boundary-anchored (cuts false-positive risk from an unbounded substring match) and seeded *only* from hostnames this project has actually resolved and checked, never a generic IATA-code table applied blindly. Seeded with 6 patterns from this session's own evidence: Cogent's `lax`/`sfo`/`pdx` (IATA-code convention), Tata's `losangeles`/`piti` (spelled-out convention, a genuinely different scheme than Cogent's), and OneQode's `gu-gnc`/`hk-mgi`. Caught and fixed a real bug while building it: the first draft's `lax` pattern didn't match Tata's `lvw-losangeles` hostname (different carriers, different naming conventions for the same city) -- added a separate `losangeles` pattern rather than trying to force one regex to cover both. Verified against all 8 known IPs from this session's own investigation before trusting it -- all passed, including a correct `None` for OneQode's one unresolved generic hostname.

**Used it to actually fix the two entries with real evidence**:
- **PF->AS9751 (Cogent)**: `detour_hub` corrected from Tokyo to **Portland** (the last confirmed hop before the destination replies: `lax01` -> `sfo01` -> `pdx02`). Added "Portland" to `EXTERNAL_HUB_LATLON` (real coordinates, not previously present).
- **PF->AS24439 (Tata)**: `detour_hub` corrected from Tokyo to **Los Angeles** (`lvw-losangeles` -> `pv4-piti` x2 -- LA, then Piti/Guam). The Piti hop is itself a real, PeeringDB-confirmed Tata facility (net_id 437, matching what OneQode's own facility list separately referenced) -- added as a **second entry to `regional_carrier_facilities.py`**, verified via PeeringDB before adding. Kept the hub as Los Angeles rather than Guam since the traffic still genuinely transits external infrastructure first; the Guam leg is noted in the entry, not driving the hub choice.
- **PF->AS45879 (Orange)**: **could not be fixed with real evidence** -- the resolved Orange hops have no PTR records at all (`geolocate_hop` returns `None` for each). Rather than replace one guess (inherited Tokyo) with another, downgraded the note's confidence explicitly: "Tokyo" is kept as the least-bad available guess (still the carrier's own real, verified PeeringDB presence) but now honestly flagged as *unconfirmed by this specific traceroute*, in contrast with the sibling GU-sourced entry, which genuinely does transit a real Japanese carrier (AS2497/IIJ) and so has actual evidence behind its Tokyo claim. Explicitly left as an open item -- this entry's MP/VU siblings haven't been audited the same way yet either.

Verified: all modules import cleanly (`CONFIRMED_DETOURS` unchanged at 56 -- these were corrections, not new entries; `REGIONAL_CARRIER_FACILITIES` now 2). Regenerated ASCII/HTML reports and the geographic map -- both corrected lines render with their real locations, map plots them at Portland's and Los Angeles's actual coordinates.

---

**Resumed the interrupted corridor test: AS10131 (Cook Islands) -> AS24390 (University of the South Pacific).** Only 1 of 3 probes returned; checked `participant_count` (1, not 3) -- the same genuine single-probe pattern as every other AS10131-sourced measurement this session. `has_routing_loop` correctly returned `False`.

Third independent confirmation of the AS7575(AARNet)<->AS24390 adjacency (after MP via OneQode and PF via Hurricane Electric/Any2West): `AS10131 -> AS9471 (ONATI) -> AS6939 (Hurricane Electric) -> AS7575`, target never resolved, RIS-agreeing with the identical exact match (337). Crosses Any2West directly -- the same exchange as the PF entry, and the same ONATI-transit shape seen on every AS10131-sourced corridor this tranche cycle. (Note: this `ixp_crossings` signal is a real hop-level LAN-prefix match against Any2West's registered subnet, not a carrier-level facility guess -- unaffected by the Tokyo-hub issue just fixed.)

Added as a new entry. Called `mark_corridor_tested(10131, 24390)`. Verified: module imports cleanly (57 entries, up from 56); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 735 -> 721.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS24439 (Marshall Islands NTA).** Same target as the just-corrected Tata mislabeling. Only 1 of 3 probes returned; checked `participant_count` (1, not 3) -- the same genuine single-probe pattern as every other AS10131-sourced measurement this session. `has_routing_loop` correctly returned `False`.

Fifth confirmation of the AS6453(Tata)<->AS24439 adjacency (after GU, MP, VU, PF): `AS10131 -> AS9471 (ONATI) -> AS3257 (GTT) -> AS6453`, RIS-agreeing with the identical exact match (997). **Geolocated with the new `hop_geolocation` module from the start this time**, rather than inheriting any hub label: the resolved Tata hops are the exact same addresses as the just-corrected PF entry -- Los Angeles, then Piti, Guam. Kept `detour_hub` as Los Angeles, matching the corrected PF entry.

Added as a new entry. Called `mark_corridor_tested(10131, 24439)`. Verified: module imports cleanly (58 entries, up from 57); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 721 -> 719.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS38198 (Digicel Tonga).** Only 1 of 3 probes returned; checked `participant_count` (1, not 3) -- the same genuine single-probe pattern as every other AS10131-sourced measurement this session. `has_routing_loop` correctly returned `False`.

Fifth confirmation of the AS45355(Digicel Fiji)<->AS38198 adjacency (after GU, MP, VU, PF): `AS10131 -> AS9471 (ONATI) -> AS6939 (Hurricane Electric) -> AS132528 -> AS45355 -> AS38198`, RIS-agreeing with the identical exact match (1,321). A seventh occurrence of AS132528 at Equinix Sydney this session -- confirmed via a real hop-level LAN-prefix match, unaffected by the Tokyo-hub issue fixed earlier.

Added as a new entry. Called `mark_corridor_tested(10131, 38198)`. Verified: module imports cleanly (59 entries, up from 58); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 719 -> 715.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS38875 (FSM Telecommunications Corporation).** Only 1 of 3 probes returned; checked `participant_count` (1, not 3) -- the same genuine single-probe pattern as every other AS10131-sourced measurement this session. `has_routing_loop` correctly returned `False`.

Fourth independent source economy for the recurring FSM sibling-substitution corridor (after GU, MP, PF): `AS10131 -> AS9471 (ONATI) -> AS6939 (Hurricane Electric) -> AS9246 (Teleguam Holdings/GTA) -> AS139759`, contiguous throughout, target never resolving. `ris_agrees: false` on the corrected sibling adjacency, matching every prior instance. Crosses Any2West again -- the same exchange as the PF entry.

Added as a new `CandidatePeering` entry (not promoted, per the standing principle). Called `mark_corridor_tested(10131, 38875)`. Verified: module imports cleanly (8 entries, up from 7); regenerated ASCII/HTML reports (render correctly); map unaffected (candidate_peering doesn't feed it). Regenerated the corridor backlog: candidate count dropped 715 -> 714.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS45193 (a third FSM Telecommunications Corporation sibling ASN).** Only 1 of 3 probes returned; checked `participant_count` (1, not 3) -- the same genuine single-probe pattern as every other AS10131-sourced measurement this session. `has_routing_loop` correctly returned `False`.

Second independent confirmation of the direct AS139759<->AS45193 adjacency (after PF): `AS10131 -> AS9471 (ONATI) -> AS6939 (Hurricane Electric) -> AS9246 (Teleguam Holdings/GTA) -> AS139759 -> AS45193`, fully contiguous, the literal target resolving directly again. RIS-agreeing with the identical exact match (1,681). Crosses Any2West -- the same exchange as the PF entry.

Added as a new entry. Called `mark_corridor_tested(10131, 45193)`. Verified: module imports cleanly (60 entries, up from 59); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 714 -> 708.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS45879 (Orange Wallis & Futuna) -- the flagged Tokyo-hub-uncertainty corridor.** Only 1 of 3 probes returned; checked `participant_count` (1, not 3). `has_routing_loop` correctly returned `False`.

Fifth confirmation of the AS5511(Opentransit Orange)<->AS45879 adjacency (after GU, MP, VU, PF): `AS10131 -> AS9471 (ONATI) -> AS3257 (GTT) -> AS5511`, RIS-agreeing with the identical exact match (1,665). **Same identical Orange hop addresses as the PF entry** -- ran `hop_geolocation.geolocate_hop` on all three anyway rather than assuming the earlier result still held; still `None` for each, confirming genuinely no PTR evidence exists for this carrier chain. **Also closed out the "MP sibling not yet audited" flag from earlier**: checked measurement 211577395's own Orange-adjacent hops (`216.66.41.150`, `57.35.6.64`) -- also no PTR records. Across the whole corridor, only the GU entry has real evidence for Tokyo (a genuine IIJ/Japan hop); every other source's Tokyo attribution is the carrier's known presence, not this-traceroute-confirmed geography. Kept `detour_hub` as Tokyo on the same honestly-downgraded basis as the corrected PF entry.

Added as a new entry. Called `mark_corridor_tested(10131, 45879)`. Verified: module imports cleanly (61 entries, up from 60); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 708 -> 707.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS45891 (Solomon Telekom Co Ltd).** Only 1 of 3 probes returned; checked `participant_count` (1, not 3). `has_routing_loop` correctly returned `False`.

Fifth confirmation of the AS139609(SISCC)<->AS45891 adjacency (after GU, MP, VU, PF): `AS10131 -> AS9471 (ONATI) -> AS6939 (Hurricane Electric) -> AS139609`, target never resolved, RIS-agreeing with the identical exact match (1,652) -- AS139609 remains AS45891's only real RIS neighbor. Crosses NSW-IX directly, the same exchange as the PF entry.

Added as a new entry. Called `mark_corridor_tested(10131, 45891)`. Verified: module imports cleanly (62 entries, up from 61); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 707 -> 698 (AS10131's remaining cheap targets thinning; the backlog now shows **AS17456 (Guam)** as a new source ASN appearing next, a further diversification step).

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS55722 (Cenpac Net Inc, Nauru).** Only 1 of 3 probes returned; checked `participant_count` (1, not 3). `has_routing_loop` correctly returned `False`.

Fourth independent corroboration of AS7131's real transit-waypoint role for Nauru's international connectivity (after MP self-sourced, VU, PF): `AS10131 -> AS9471 (ONATI) -> AS6939 (Hurricane Electric) -> AS7131` -> target never resolved, RIS-agreeing with the identical exact match (1,528). A fourth distinct source economy (Cook Islands) -- notably the third time this session ONATI itself has shown up as the intermediate carrier for a Cook Islands traceroute.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(10131, 55722)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 698 -> 697. **Source has now fully diversified to AS17456 (Guam)** -- AS10131's cheap targets are exhausted.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS55885 (Niue).** Only 1 of 3 probes returned; checked `participant_count` (1, not 3). `has_routing_loop` correctly returned `False`.

**The target actually resolved directly this time, but `ris_agrees: False` -- surprising enough given how heavily-confirmed this relationship already is (five prior corroborations) that it warranted checking the raw fishbowl data directly rather than accepting the disagreement at face value.** Confirmed: this is the same established ONATI sibling-ASN substitution already handled for every prior instance of this exact corridor -- AS55885's only real RIS neighbor is AS55943 (ONATI's sibling ASN), not AS9471 directly, even though both are the same real operator. Sixth independent corroboration overall (after Niue's own vantage, GU, MP, VU, and now this), and the shortest path yet: `AS10131 -> AS9471 -> AS55885`, no intermediate carrier at all -- a fifth distinct source economy, and the fourth time this session ONATI has shown up as Cook Islands' direct upstream.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(10131, 55885)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 697 -> 695. AS10131 now fully exhausted; AS17456 (Guam) is the sole leading source.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS132486 (Kiribati, Ocean Link Ltd)** -- one last AS10131 pair the backlog still had. Only 1 of 3 probes returned; checked `participant_count` (1, not 3). `has_routing_loop` correctly returned `False`.

Sixth independent reproduction of the well-established AS154100<->AS132486 Kiribati Starlink chain: `AS10131 -> AS9471 (ONATI) -> AS6939 (Hurricane Electric) -> AS14593 (Starlink) -> AS154100`, target never resolved, identical exact RIS match (362). Crosses EdgeIX Auckland again -- the same exchange as the PF entry.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(10131, 132486)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 695 -> 694. AS17456 (Guam) is now the sole leading source.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS134783 (ATHKL, Kiribati).** Only 1 of 3 probes returned; checked `participant_count` (1, not 3). `has_routing_loop` correctly returned `False`.

Fifth independent corroboration of the AS154100<->AS134783 adjacency (after GU, MP, VU, PF): `AS10131 -> AS9471 (ONATI) -> AS6939 (Hurricane Electric) -> AS14593 (Starlink) -> AS154100`, target never resolved, identical exact RIS match (1,392). No IXP crossing this time.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(10131, 134783)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 694 -> 693. **AS17828 (Papua New Guinea, PNG DataCo) now also appearing as a new source ASN**, alongside AS17456 (Guam).

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS140504 (a distinct Nauru ASN) -- the SES Astra corridor.** Fired directly at the address already confirmed to reach SES Astra in the PF retry (`43.230.6.1`), skipping the dead-end address that triggered the retry policy there. `has_routing_loop` correctly returned `False`.

Second independent confirmation of the AS140504<->AS12684 (SES Astra) relationship: `AS10131 -> AS9471 (ONATI) -> AS6939 (Hurricane Electric) -> AS36149 (Hawaiian Telcom) -> AS12684`, **fully contiguous this time** (the PF entry had a real gap before AS12684) -- the cleanest confirmation yet. RIS agrees with the identical exact match (616).

Added as a new entry. Called `mark_corridor_tested(10131, 140504)`. Verified: module imports cleanly (63 entries, up from 62); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 693 -> 690.

---

**Next corridor pulled: AS10131 (Cook Islands) -> AS154100 (BNL Tarawa, targeted directly).** Only 1 of 3 probes returned; checked `participant_count` (1, not 3). `has_routing_loop` correctly returned `False` -- no repeat of the Starlink loop anomaly this time.

Sixth independent confirmation of the direct AS154100<->AS14593 relationship (after GU, CNMI, Vanuatu, PF, and this session's own downstream-chain measurement): `AS10131 -> AS9471 (ONATI) -> AS6939 (Hurricane Electric) -> AS14593`, target never resolved, identical exact RIS match (361).

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(10131, 154100)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 690 -> 689. **AS10131's corridors are now fully exhausted** -- the backlog has moved to AS17828 (PNG DataCo).

---

**Next corridor pulled: AS17456 (Pacific Data Systems, Guam) -> AS23917 (Tuvalu)** -- the first firing sourced from this new Guam ASN. Checked its holder identity directly before sourcing from it: "PDSGUAM-USTRANSPORT-AS-GU-AP - Pacific Data Systems." Result: complete dead-end -- only 1 of 3 requested probes connected; the single traceroute resolved just its own private gateway (`10.175.20.1`) then total silence from hop 2 onward. `has_routing_loop` correctly returned `False` (no repeated address at all, just silence).

**Applied the retry policy against a different cached prefix** rather than accepting the dead-end at face value. Identical result: same private gateway, then total silence, same shape exactly. Two different destination addresses, byte-for-byte identical dead-end pattern -- reads as this specific probe's own network filtering outbound traceroute traffic entirely, not a hidden loop at the target's end (a real loop would show *some* resolvable intermediate hop before or during the cycle; this shows none at all, on either attempt).

Not filed in any dataclass, consistent with the established treatment of genuine dead-ends. Called `mark_corridor_tested(17456, 23917)` for both addresses. No report/map regeneration needed (no dataclass changed). Regenerated the corridor backlog: candidate count dropped 689 -> 687.

---

**Next corridor pulled: AS17456 (Pacific Data Systems, Guam) -> AS55885 (Niue).** This time reached a full 20-hop traceroute (not the same probe-wide dead-end as the AS23917 attempt) -- confirms the earlier Tuvalu dead-end was corridor-specific, not a general probe-filtering issue. `has_routing_loop` correctly returned `False`.

**Fully contiguous all the way to the literal target** -- unlike most prior instances of this corridor, which stopped at AS9471 without resolving AS55885 itself: `AS17456 -> AS3605 (Guam Cablevision) -> AS2914 (NTT Communications) -> AS3257 (GTT) -> AS9471 -> AS55885`. Same established sibling-ASN basis as every prior instance (`ris_agrees: false` on the strict AS9471/AS55885 pair, resolves via AS55943). Seventh independent corroboration overall, and a second distinct Guam-based carrier now confirming this relationship (after AS3605/Guam Cablevision) -- notably transiting through AS3605 itself before reaching ONATI, Guam's own carriers routing through each other domestically before continuing internationally.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(17456, 55885)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 687 -> 685.

---

**Next corridor pulled: AS17456 (Pacific Data Systems, Guam) -> AS132486 (Kiribati, Ocean Link Ltd).** Same total dead-end shape as the earlier AS23917 attempt from this source: only the private gateway (`10.175.20.1`) resolved, then total silence. `has_routing_loop` correctly returned `False`.

**Only one known address exists for AS132486, so the standard retry-a-different-prefix policy wasn't directly applicable** -- fired a diagnostic traceroute toward AS154100 (BNL Tarawa, Starlink's own direct address) instead, to check whether the entire Kiribati/Starlink direction is unreachable from this probe or just this one target address. **Identical total dead-end shape again.** Given this same probe successfully traced a full 20 hops to Niue just one tranche earlier, this rules out a general probe-wide filtering issue -- the silence is genuinely direction-specific toward Kiribati/Starlink from this particular Guam ISP, not an artifact of one address or a broken probe.

Not filed in any dataclass -- no hop resolved to any ASN in either attempt, so there's no real signal to characterize, just informative silence. Called `mark_corridor_tested(17456, 132486)`. No report/map regeneration needed (no dataclass changed). Regenerated the corridor backlog: candidate count dropped 685 -> 684.

---

**Next corridor pulled: AS17456 (Pacific Data Systems, Guam) -> AS134783 (ATHKL, Kiribati).** Identical dead-end shape a third time: only the private gateway resolved, total silence from hop 2 onward. `has_routing_loop` correctly returned `False`.

**This is now a robust, three-times-reproduced pattern** (AS132486, the AS154100 diagnostic, and now AS134783 -- all Kiribati-direction targets, all from this same probe), while the same probe cleanly traced 20 hops toward Niue. A genuine, reproducible direction-specific silence from AS17456 toward Kiribati, not a one-off artifact.

Not filed in any dataclass. Called `mark_corridor_tested(17456, 134783)`. No report/map regeneration needed. Regenerated the corridor backlog: candidate count dropped 684 -> 683.

---

**Next corridor pulled: AS17456 (Pacific Data Systems, Guam) -> AS154100 (BNL Tarawa, targeted directly).** This exact pair was already tested two tranches ago as the diagnostic check (measurement 211778709) confirming the Kiribati-direction silence was direction-specific, not address-specific -- reused that existing result rather than firing a redundant duplicate traceroute. Called `mark_corridor_tested(17456, 154100)` directly.

Not filed in any dataclass (same total dead-end already documented). No report/map regeneration needed. Regenerated the corridor backlog: candidate count dropped 683 -> 682. **AS17456's testable corridors are now exhausted** -- AS17828 (PNG DataCo) is the sole leading source going forward.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS4638 (Telecom Fiji)** -- the first firing sourced from PNG DataCo directly. Only 1 of 3 probes returned. `has_routing_loop` correctly returned `False`.

**The fifth time this session hitting the exact same known `202.137.178.x` gap zone** (after loop tranche 5, PTI Pacifica/AS7131, PF/AS9471, and CK/AS10131): hops 10-11 land on the identical addresses (`202.137.178.160`, `.55`). This time via a fresh carrier chain: `AS17828 -> AS4826 (Vocus Connect) -> AS1221 (Telstra domestic) -> AS4637 (Telstra Global)`, target technically reached at hop 15 but with real unresolved hops in between. `ris_agrees: False` -- AS4638's only real neighbor remains AS45349.

Not filed in any dataclass, consistent with the established pattern. Called `mark_corridor_tested(17828, 4638)`. No report/map regeneration needed. Regenerated the corridor backlog: candidate count dropped 682 -> 681.

---

**[Standing 8-hourly backlog regeneration check, user-directed.]** Ran `pacific-peering-corridor-backlog` directly. Result: 681 candidates, **0 new-probe, 0 new-RIS-relationship** flags -- diffed `corridor_backlog.md` directly to confirm: the only change is the regeneration timestamp, candidate count and the full pending list are byte-identical to the state already produced by the last tranche's own implicit regeneration. Nothing strange, nothing anomalous, nothing warranting owner consultation this cycle -- a genuinely uneventful check, logged per the standing "keep track of new probes and RIS changes" order.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS9241 (FINTEL, Fiji).** Avoided the known-loop-prone `202.170.32.x` address, starting from `113.20.64.1` instead. `has_routing_loop` correctly returned `True`.

**Checked the raw hops directly**: identical alternating pattern between `202.170.33.11` and `202.170.33.17`, both already confirmed as AS9241 itself. A fourth independent vantage point (PNG, after MP's original discovery, PF's reproduction, and CK's reproduction) reproducing this same live anomaly inside FINTEL's own network edge.

Not filed in any dataclass, matching the established precedent. Called `mark_corridor_tested(17828, 9241)`. No report/map regeneration needed. Regenerated the corridor backlog: candidate count dropped 681 -> 680.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS9751 (American Samoa).** The first firing genuinely sourced from PNG DataCo to reach a target. `has_routing_loop` correctly returned `False`.

Third independent confirmation of the Wave-Broadband(AS11404)<->AS9751 adjacency (after MP and VU): `AS17828 -> AS4826 (Vocus Connect) -> AS11404`, RIS-agreeing with the identical exact match (267). Crosses Equinix San Jose directly -- the same exchange as the VU entry.

Added as a new entry. Called `mark_corridor_tested(17828, 9751)`. Verified: module imports cleanly (64 entries, up from 63); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 680 -> 678.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS17480 (a fresh New Caledonia ASN).** `has_routing_loop` correctly returned `False`.

Fourth independent confirmation of the AS18200(OPT NC)<->AS17480 adjacency (after MP, PF, CK): `AS17828 -> AS4826 (Vocus Connect) -> AS18200 -> AS17480`, fully contiguous, RIS-agreeing with the identical exact match (1,665). Crosses Equinix Sydney directly -- the same exchange as the CK and PF entries.

Added as a new entry. Called `mark_corridor_tested(17828, 17480)`. Verified: module imports cleanly (65 entries, up from 64); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 678 -> 605 (a large drop -- PNG DataCo's remaining cheap untested targets thinned significantly at once).

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS17893 (Palau NCC).** `has_routing_loop` correctly returned `False`. Lands on the project's *other* AS17893 adjacency (AS174/Cogent, not the AS6939/Hurricane Electric one PF and CK confirmed) -- a fourth independent confirmation, a third distinct source economy (after GU, GU-reproduction, VU): `AS17828 -> AS4826 (Vocus Connect) -> AS1299 (Telia) -> AS174 -> AS17893`, fully contiguous, RIS-agreeing with the identical exact match (1,333). Telia is a genuinely new intermediate carrier into Cogent for this adjacency, after IIJ and NTT.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_DETOURS` count unchanged (65). Called `mark_corridor_tested(17828, 17893)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 605 -> 603.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS17993 (Vodafone Samoa).** `has_routing_loop` correctly returned `False`. Reaches the literal target directly, fully contiguous, crossing Equinix Sydney -- but via **AS4826 (Vocus Connect)**, not the established AS6939 (Hurricane Electric) relationship. `ris_agrees: False` -- checked AS17993's neighbor list directly (`{174: 1455, 6939: 150, ...}`), no AS4826; checked AS4826's own fishbowl entry too, empty neighbor list.

**A genuinely new candidate, distinct from the existing VU-sourced AS38442 entry for this same target**: Vocus Connect is already established elsewhere this project as PNG DataCo's own real upstream carrier -- this traceroute shows it reaching a real Equinix Sydney presence for Vodafone Samoa too, a second distinct carrier now confirmed crossing at that same exchange.

Added as a new `CandidatePeering` entry. Called `mark_corridor_tested(17828, 17993)`. Verified: module imports cleanly (9 entries, up from 8); regenerated ASCII/HTML reports (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 603 -> 597.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS23917 (Tuvalu).** Given FINTEL's own loop history, checked the raw hops directly rather than trusting the clean `has_routing_loop` flag at face value: no repeated addresses, none in the known `202.170.33.x` zone -- genuinely clean.

Seventh independent corroboration of the AS9241(FINTEL)<->AS23917 adjacency (after Tuvalu's own vantage, GU, MP, VU, PF, CK): `AS17828 -> AS4826 (Vocus Connect) -> AS1299 (Telia) -> AS9241 -> AS23917`, RIS-agreeing with the identical exact match (1,009). Telia is a genuinely new intermediate carrier for this adjacency, after Level 3/Lumen, Spark NZ, and NTT.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(17828, 23917)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 597 -> 595.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS24390 (University of the South Pacific).** `has_routing_loop` correctly returned `False`.

Fourth independent confirmation of the AS7575(AARNet)<->AS24390 adjacency (after MP, PF, CK): `AS17828 -> AS4826 (Vocus Connect) -> AS7575`, target never resolved, RIS-agreeing with the identical exact match (337). No IXP crossing this time -- a direct AARNet hop, unlike the CK and PF entries' Any2West crossings.

Added as a new entry. Called `mark_corridor_tested(17828, 24390)`. Verified: module imports cleanly (66 entries, up from 65); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 595 -> 554 (a large drop -- PNG DataCo's remaining cheap untested targets thinned significantly at once).

---

**[Flagged to the project owner -- genuinely new anomaly, distinct from the established slow-scheduling pattern.] Next corridor pulled: AS17828 (PNG DataCo) -> AS24439 (Marshall Islands).** Two consecutive fired measurements both got stuck at `Scheduled` status with **zero probes ever requested or assigned** (`probes_requested: 0`, `probes_scheduled: 0`, `participant_count: 0`) -- checked directly, and this is a different failure mode than the recognized "stuck but genuinely queued" pattern seen several times earlier this session (which always showed a real non-zero `participant_count`). Verified the probe itself was healthy (probe 50365: status `Connected`, correctly attributed to AS17828) and that this wasn't a credit/quota issue (balance: 95.7M, ample). No clear root cause visible from the API's own status fields.

**Surfaced this directly to the project owner rather than retrying indefinitely or silently working around it**, per the standing anomaly-consultation rule. Asked how to proceed; owner chose to skip this corridor for now and pull a different target, rather than waiting further or pausing the loop entirely. **Not marked as tested** -- `mark_corridor_tested(17828, 24439)` was deliberately *not* called, since no real traceroute data was ever collected; this corridor remains genuinely open for a future retry once whatever caused the scheduling failure has passed.

**Manually selected the next PG candidate instead: AS17828 -> AS38198 (Digicel Tonga).** This measurement scheduled and returned normally, confirming the earlier failure was transient/isolated to that specific attempt rather than a persistent AS17828-wide issue. `has_routing_loop` correctly returned `False`.

Sixth independent confirmation of the AS45355(Digicel Fiji)<->AS38198 adjacency (after GU, MP, VU, PF, CK): `AS17828 -> AS4826 (Vocus Connect) -> AS1221 (Telstra domestic) -> AS45355`, RIS-agreeing with the identical exact match (1,321). **Notably no AS132528 this time** -- every prior confirmation crossed AS132528 at Equinix Sydney; this one reaches AS45355 via Telstra's domestic ASN directly, a genuinely different real path to the same carrier relationship.

Added as a new entry. Called `mark_corridor_tested(17828, 38198)`. Verified: module imports cleanly (67 entries, up from 66); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 554 -> 550. AS24439 (Marshall Islands) remains in the backlog, genuinely untested, for a future retry.

---

**Retried the previously-flagged corridor: AS17828 (PNG DataCo) -> AS24439 (Marshall Islands).** Fired a fresh measurement; it scheduled and returned normally this time, confirming the earlier zero-probes-scheduled anomaly was genuinely transient. `has_routing_loop` correctly returned `False`.

Sixth independent confirmation of the AS6453(Tata)<->AS24439 adjacency (after GU, MP, VU, PF, CK): `AS17828 -> AS4826 (Vocus Connect) -> AS174 (Cogent) -> AS6453`, target never resolved, RIS-agreeing with the identical exact match (997). **Geolocated with `hop_geolocation` from the start**, per the established discipline for this specific corridor: the resolved Tata hops are the exact same addresses as the already-corrected PF and CK entries -- Los Angeles, then Piti, Guam.

Added as a new entry. Called `mark_corridor_tested(17828, 24439)`. Verified: module imports cleanly (68 entries, up from 67); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 550 -> 548.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS38875 (FSM Telecommunications Corporation).** `has_routing_loop` correctly returned `False`.

Fifth independent source economy for the recurring FSM sibling-substitution corridor (after GU, MP, PF, CK): `AS17828 -> AS4826 (Vocus Connect) -> AS9246 (Teleguam Holdings/GTA) -> AS139759`, contiguous throughout, target never resolving. `ris_agrees: false` on the corrected sibling adjacency, matching every prior instance. Crosses Any2West again -- the same exchange as the PF and CK entries.

Added as a new `CandidatePeering` entry. Called `mark_corridor_tested(17828, 38875)`. Verified: module imports cleanly (10 entries, up from 9); regenerated ASCII/HTML reports (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 548 -> 547.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS45193 (a third FSM Telecommunications Corporation sibling ASN).** `has_routing_loop` correctly returned `False`.

Third independent confirmation of the direct AS139759<->AS45193 adjacency (after PF, CK): `AS17828 -> AS4826 (Vocus Connect) -> AS9246 (Teleguam Holdings/GTA) -> AS139759 -> AS45193`, fully contiguous, the literal target resolving directly again. RIS-agreeing with the identical exact match (1,681). Crosses Any2West -- the same exchange as every prior confirmation.

Added as a new entry. Called `mark_corridor_tested(17828, 45193)`. Verified: module imports cleanly (69 entries, up from 68); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 547 -> 514 (a large drop -- PNG DataCo's remaining cheap untested targets thinned significantly at once).

---

**[Significant finding -- first-ever real geographic evidence for the AS45879/Orange corridor's Tokyo attribution.] Next corridor pulled: AS17828 (PNG DataCo) -> AS45879 (Orange Wallis & Futuna).** `has_routing_loop` correctly returned `False`.

Sixth independent confirmation of the AS5511(Opentransit Orange)<->AS45879 adjacency (after GU, MP, VU, PF, CK): `AS17828 -> AS4826 (Vocus Connect) -> AS174 (Cogent) -> AS5511`, target never resolved, RIS-agreeing with the identical exact match (1,665). Cogent is a genuinely new intermediate carrier for this adjacency (after GTT).

**Reverse-DNS'd the Cogent hops directly rather than inheriting the existing entries' Tokyo label**: `sjc13.atlas.cogentco.com` -> `lax01...` -> `lax05...` -> **`orange.lax05.atlas.cogentco.com`** -- a Cogent router explicitly named for the Orange handoff, located in Los Angeles. This is the first time this whole corridor has ever had real geographic evidence for its Orange leg, rather than an inherited carrier-level guess. Filed with `detour_hub="Los Angeles"` accordingly. Added a new `sjc` pattern to `hop_geolocation.py` (San Jose) while auditing these hops.

Added as a new entry. Called `mark_corridor_tested(17828, 45879)`. Verified: module imports cleanly (70 entries, up from 69); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 514 -> 513.

---

**[A genuinely new routing-loop location -- the fourth distinct network this session.] Next corridor pulled: AS17828 (PNG DataCo) -> AS45891 (Solomon Telekom Co Ltd).** `has_routing_loop` correctly returned `True`.

**Checked the raw hops directly**: a single address (`103.142.98.131`) repeats at hop 11 and hop 14, with unanswered probes in between. Resolved it directly: it belongs to **AS139609 (SISCC) itself** -- a real, live loop at the destination's own network edge, the same general shape as the FINTEL loop but a genuinely different company's network (the fourth distinct network this session to show this pattern, after Hurricane Electric, FINTEL, and Starlink).

The loop sits after the point (hop 10, also AS139609) already used for this measurement's own RIS agreement, so it doesn't corrupt the triangulation: sixth independent confirmation of the AS139609(SISCC)<->AS45891 adjacency (after GU, MP, VU, PF, CK): `AS17828 -> AS4826 (Vocus Connect) -> AS1221 (Telstra domestic) -> AS4637 (Telstra Global) -> AS139609`, RIS-agreeing with the identical exact match (1,652).

Added as a new entry. Called `mark_corridor_tested(17828, 45891)`. Verified: module imports cleanly (71 entries, up from 70); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 513 -> 504.

---

**[Standing 8-hourly backlog regeneration check, user-directed.]** Ran `pacific-peering-corridor-backlog` directly. Result: 504 candidates, **0 new-probe, 0 new-RIS-relationship** flags -- diffed `corridor_backlog.md` directly to confirm: the only change is the regeneration timestamp, nothing else in the file differs from the state already produced by the last tranche's own implicit regeneration. Nothing strange, nothing anomalous, nothing warranting owner consultation this cycle.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS55722 (Cenpac Net Inc, Nauru).** `has_routing_loop` correctly returned `False`.

Fifth independent corroboration of AS7131's real transit-waypoint role for Nauru's international connectivity (after MP self-sourced, VU, PF, CK): `AS17828 -> AS4826 (Vocus Connect) -> AS140627 (OneQode) -> AS7131`, target never resolved, RIS-agreeing with the identical exact match (1,528). A genuinely new intermediate carrier (OneQode, after Hurricane Electric), crossing **NSW-IX Sydney** directly -- a new named exchange for this specific corridor.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(17828, 55722)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 504 -> 503. **AS17893 (Palau) now also appearing as a new source ASN** in the backlog.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS55885 (Niue).** `has_routing_loop` correctly returned `False`. Same established ONATI/AS55943 sibling-substitution pattern; target resolves directly, `ris_agrees: False` on the strict pair is expected. Eighth corroboration overall: `AS17828 -> AS4826 (Vocus Connect) -> AS174 (Cogent) -> AS3257 (GTT) -> AS9471 -> AS55885`, fully contiguous. Both Cogent and GTT appearing together sequentially is a genuinely new carrier combination for this adjacency.

**Caught and fixed a source-economy counting error before committing**: first draft wrote "sixth distinct source economy," but the "after ..." list named six prior economies (Niue, Guam, CNMI, Vanuatu, French Polynesia, Cook Islands) -- re-counted directly and corrected to "seventh" before staging.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(17828, 55885)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 503 -> 501. AS17828's remaining targets are nearly exhausted (only AS154100 left); AS17893 (Palau) is already queued as the next source.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS58932 (Palau Mobile Communications).** `has_routing_loop` correctly returned `False`. Third independent corroboration of the AS3605<->AS58932 adjacency (after the original AS3605-sourced entry and the VU-sourced corroboration): `AS17828 -> AS4826 (Vocus Connect) -> AS3605 -> AS58932`, fully contiguous, RIS-agreeing with the identical exact match (664). **Crosses Any2West directly** -- the first time this specific adjacency has shown a named exchange crossing.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(17828, 58932)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 501 -> 500. **AS17828 is now fully exhausted** -- source has moved to AS17893 (Palau NCC).

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS132486 (Kiribati, Ocean Link Ltd)** -- one last AS17828 pair the backlog still had. `has_routing_loop` correctly returned `False`.

Seventh independent reproduction of the well-established AS154100<->AS132486 Kiribati Starlink chain: `AS17828 -> AS4826 (Vocus Connect) -> AS14593 (Starlink) -> AS154100`, target never resolved, identical exact RIS match (362). No IXP crossing this time.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(17828, 132486)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 500 -> 499. AS17828 is now genuinely exhausted; AS17893 (Palau NCC) is the sole leading source.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS133897 (Palau Equipment Co. Inc.)** -- one final AS17828 pair the backlog still had. `has_routing_loop` correctly returned `False`.

Third independent corroboration of the AS3605<->AS133897 adjacency (after the original entry and VU): `AS17828 -> AS4826 (Vocus Connect) -> AS2497 (IIJ, Japan) -> AS3605 -> AS133897`, fully contiguous, RIS-agreeing with the identical exact match (662). Crosses **Equinix Singapore** directly -- a genuinely new named exchange for this adjacency, and IIJ is a new intermediate carrier too.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(17828, 133897)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 499 -> 498. AS17828 now genuinely exhausted; AS17893 (Palau NCC) is the sole leading source.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS134783 (ATHKL, Kiribati)** -- one final AS17828 pair the backlog still had. `has_routing_loop` correctly returned `False`.

Sixth independent corroboration of the AS154100<->AS134783 adjacency: `AS17828 -> AS4826 (Vocus Connect) -> AS14593 (Starlink) -> AS154100`, target never resolved, identical exact RIS match (1,392). No IXP crossing this time.

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(17828, 134783)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 498 -> 497. Now fully into AS17893 (Palau NCC).

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS140504 (Digicel Nauru Corporation)** -- fired directly at the address already confirmed to reach SES Astra territory. `has_routing_loop` correctly returned `False`.

**Reaches the literal target directly this time, but via a genuinely new path**: `AS17828 -> AS4826 (Vocus Connect) -> AS1221 (Telstra Limited, domestic ASN) -> AS140504`, fully contiguous -- the first time this project has reached AS140504 via anything other than its two already-confirmed relationships (AS132528/Digicel Australia, AS12684/SES Astra). `ris_agrees: False` -- checked AS140504's neighbor list directly (`{132528: 1032, 12684: 616}`), AS1221 doesn't appear; checked AS1221's own fishbowl entry too, empty. Notable: AS1221 and AS132528 (AS140504's real dominant neighbor) are both Telstra-operated -- a different ASN of the same corporate family reaching the target directly.

Added as a new `CandidatePeering` entry. Called `mark_corridor_tested(17828, 140504)`. Verified: module imports cleanly (11 entries, up from 10); regenerated ASCII/HTML reports (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 497 -> 494. AS17828 now fully exhausted.

---

**Next corridor pulled: AS17828 (PNG DataCo) -> AS154100 (BNL Tarawa, targeted directly)** -- one truly final AS17828 pair. `has_routing_loop` correctly returned `False`.

Seventh independent confirmation of the direct AS154100<->AS14593 relationship: `AS17828 -> AS4826 (Vocus Connect) -> AS14593`, identical exact RIS match (361).

Extended the existing entry's note. Not a new dataclass entry -- `CONFIRMED_LOCAL_TRANSIT` count unchanged (13). Called `mark_corridor_tested(17828, 154100)`. Regenerated ASCII/HTML reports since the note text changed (render correctly); map unaffected. Regenerated the corridor backlog: candidate count dropped 494 -> 493. AS17828 is now genuinely, fully exhausted; AS17893 (Palau NCC) is the sole source.

---

**Next corridor pulled: AS17893 (Palau NCC) -> AS4638 (Telecom Fiji)** -- the first firing genuinely sourced from Palau. `has_routing_loop` correctly returned `False`.

**The sixth time this session hitting the exact same known `202.137.178.x` gap zone** (after loop tranche 5, PTI Pacifica/AS7131, PF/AS9471, CK/AS10131, and PG/AS17828): hops 10-11 land in the identical zone (`202.137.178.52`, `.55`). This time via `AS17893 -> AS174 (Cogent) -> AS9241 (FINTEL)` -- FINTEL appearing directly in the chain this time, a genuinely different carrier path than any prior instance. `ris_agrees: False` -- AS4638's only real neighbor remains AS45349.

Not filed in any dataclass, consistent with the established pattern. Called `mark_corridor_tested(17893, 4638)`. No report/map regeneration needed. Regenerated the corridor backlog: candidate count dropped 493 -> 492.

---

**Next corridor pulled: AS17893 (Palau NCC) -> AS9241 (FINTEL, Fiji).** `has_routing_loop` correctly returned `True`.

**Checked the raw hops directly**: the traceroute alternates between `202.170.33.17` and `202.170.33.11` from hop 10 through hop 32, both already confirmed as AS9241 itself. A fifth independent vantage point (Palau, after MP's original discovery, PF's reproduction, CK's reproduction, and PNG's reproduction) reproducing this same live anomaly inside FINTEL's own network edge.

Not filed in any dataclass, matching the established precedent. Called `mark_corridor_tested(17893, 9241)`. No report/map regeneration needed. Regenerated the corridor backlog: candidate count dropped 492 -> 491.

---

**Next corridor pulled: AS17893 (Palau NCC) -> AS9751 (American Samoa)** -- the first firing genuinely sourced from Palau to reach a target. `has_routing_loop` correctly returned `False`.

Fifth independent confirmation of the AS174(Cogent)<->AS9751 adjacency (after GU, VU, PF, CK): `AS17893 -> AS174 -> AS9751`, RIS-agreeing with the identical exact match (1,055). **Geolocated with `hop_geolocation` from the start**: `lax01` -> `sjc13` -> `sfo01` -> `pdx01` -> `pdx02` -- the identical US West Coast chain already established for the corrected PF entry, ending at Portland.

Added as a new entry. Called `mark_corridor_tested(17893, 9751)`. Verified: module imports cleanly (72 entries, up from 71); regenerated ASCII/HTML reports (render correctly) and the geographic map. Regenerated the corridor backlog: candidate count dropped 491 -> 489.

---

**Next corridor pulled: AS17893 (Palau NCC) -> AS17480 (New Caledonia).** `has_routing_loop` correctly returned `False`.

Only one probe reported (Palau's usual low-participant-count pattern) and the traceroute went dark after hop 7 (`202.171.64.251`), never getting a reply from the destination IP itself. Per the retry-on-dead-end policy, checked whether this was hiding a real anomaly before accepting it: the dark hop is not a loop, and reverse-DNS on the last two live hops (`202.87.128.134`, `202.171.64.251` -> PTR `canl.nc`) plus a direct RIS BGP lookup showed the second-to-last hop resolves to AS18200 and the last live hop resolves directly to the target ASN, AS17480 itself -- so the adjacency is fully contiguous even though the destination address never answered.

Fifth independent confirmation of the AS18200(OPT NC)<->AS17480 adjacency (after MP, PF, CK, PG) -- and the first of the five to cross **BBIX Tokyo** instead of Equinix Sydney: `AS17893 -> AS38195 (BBIX Tokyo) -> AS18200 -> AS17480`, RIS-agreeing with the identical exact match (1,665). The Tokyo hub here is a real IXP-LAN address match confirmed via `ixp_crossings` (ix_id 126), not a carrier-facility guess -- a stronger evidentiary basis than the Cogent/Tata Tokyo mislabeling caught and corrected earlier this session.

Added as a new entry. Called `mark_corridor_tested(17893, 17480)`. Verified: module imports cleanly (73 entries, up from 72); regenerated ASCII/HTML reports and the geographic map. Regenerated the corridor backlog: candidate count dropped 489 -> 468 (0 new-probe, 0 new-RIS-relationship).

---

**Next corridor pulled: AS17893 (Palau NCC) -> AS17993 (Samoa, Vodafone Samoa Limited).** `has_routing_loop` correctly returned `False`.

Only one probe reported and again went dark before the destination IP itself replied -- the same pattern as the AS17480 tranche. RIS BGP lookup on the second-to-last hop confirmed direct AS17993 attribution, so the adjacency is contiguous. Second independent confirmation of the AS174(Cogent)<->AS17993 adjacency (after GU): `AS17893 -> AS174 -> AS17993`, RIS-agreeing with the identical exact match (1,455).

**First hop-level geolocation of this specific corridor's hub**: the Cogent hops (`ccr71.syd01.atlas.cogentco.com`, `agr51.syd01.atlas.cogentco.com`) resolved to Sydney via `hop_geolocation` -- confirming, with real PTR evidence, the "Sydney" hub the original GU entry had assigned by carrier-facility guess rather than hop evidence. Added a new `syd` pattern to `hop_geolocation.py` citing this measurement.

Added as a new entry. Called `mark_corridor_tested(17893, 17993)`. Verified: module imports cleanly (74 entries, up from 73); regenerated ASCII/HTML reports and the geographic map. Regenerated the corridor backlog: candidate count dropped 468 -> 462 (0 new-probe, 0 new-RIS-relationship).

---

**Next corridor pulled: AS17893 (Palau NCC) -> AS23917 (Tuvalu).** A long, unusual path: `AS17893 -> AS7578 (GSL/Global Secure Layer) -> AS137409 (GSL Networks) -> AS14593 (Starlink) -> AS4826 (Vocus Connect) -> AS1299 (Telia) -> AS9241 (FINTEL) -> AS23917`, fully contiguous between AS9241 and the target. `has_routing_loop` correctly returned `False`; checked manually anyway given both FINTEL's and Starlink's own loop histories this session -- no repeats anywhere, including the Starlink hops (`206.224.72.33`/`.40`, distinct from the known `206.224.66.23` loop address).

Eighth independent corroboration of the AS9241(FINTEL)<->AS23917(Tuvalu) adjacency (after Tuvalu's own vantage point, Guam, CNMI, Vanuatu, French Polynesia, Cook Islands, and PNG). RIS agrees with the identical exact match (1,009). GSL/Global Secure Layer and GSL Networks are genuinely new intermediate carriers for this adjacency; this is also the first time Starlink has shown up as a transit hop toward Tuvalu specifically (previously only on the Kiribati chains).

Extended the existing FINTEL<->Tuvalu entry's note (per the established per-source-economy convention for `ConfirmedLocalTransit`) rather than adding a new entry. Called `mark_corridor_tested(17893, 23917)`. Verified: module imports cleanly (still 13 entries, extension only); regenerated ASCII/HTML reports and the geographic map. Regenerated the corridor backlog: candidate count dropped 462 -> 460 (0 new-probe, 0 new-RIS-relationship).

---

**Next corridor pulled: AS17893 (Palau NCC) -> AS23959 (Vanuatu, Telecom Vanuatu).** A local system memory-pressure event killed the first background `wait_for_results` call mid-poll (a harness/host resource issue, not a routing anomaly) -- recovered by polling `fetch_measurement_status`/`fetch_raw_results` directly in lightweight foreground calls instead of another long-running background process.

The traceroute actually reached the destination IP itself directly (`194.114.136.1` answered at hop 14) via `AS17893 -> AS174 (Cogent) -> AS2497 (IIJ, Japan) -> [hops 9-13 dark, no replies] -> AS23959`. `has_routing_loop` correctly returned `False`. But the path is **not contiguous**: hops 9-13 never replied, so the true immediate upstream of AS23959 is unknown -- IIJ is simply the last ASN resolved before the dark stretch, not a confirmed adjacency. Checked AS23959's fishbowl-registered RIS neighbor list directly: it shows a single neighbor, AS4785 (662 observations) -- AS2497 doesn't appear at all, and RIS disagrees.

Given the gap, this doesn't meet the "clean, contiguous" bar `CandidatePeering` requires (unlike the Vodafone Fiji<->Vodafone Samoa candidate, where the final hop landed unambiguously inside the target's own registered prefix with no gap) -- just inconclusive, dark-middle evidence. Not filed in any dataclass, matching established precedent. Called `mark_corridor_tested(17893, 23959)`. No report/map regeneration needed (no dataclass changed). Regenerated the corridor backlog: candidate count dropped 460 -> 459.
