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
- [ ] Phase 1c: Scheduling/automation — recurring job (7-day or monthly) that re-runs discovery + RIS pull + Atlas measurements, versions each run's output directory, is safe to re-run/resume.
- [ ] Phase 1d: Sub-optimal routing analysis — triangulate source/destination pairs to flag transpacific paths that detour outside the region (e.g., via US/AU) when a more direct path should exist. **Settled premise, per the project owner: peering that lands outside the study area — AU, NZ, or the US — is not optimal, by definition.** That is not a hypothesis this project tests; it's a given. What's still open is establishing the specific instances and degree, which is what Phase 1b's Atlas traceroutes are for (see Fish Bowl Limitations). Candidate instances already surfaced from Phase 1a's `fishbowl.json`, awaiting Atlas corroboration on the specifics:
  - **Australia as the de facto peering hub — ✅ ground-truthed by Atlas (Phase 1b).** Equinix Sydney + MegaIX Sydney together account for the single largest IXP cluster in the whole dataset (9 + 6 = 15 memberships), reaching more distinct in-scope economies (Cook Islands, Fiji, French Polynesia, New Caledonia, PNG, Samoa, Tonga) than any actual in-region IXP. Phase 1b's first live traceroute (Guam -> PNG, measurement 210901499) confirmed this directly: all 3 probes' paths hit `45.127.172.31` — the exact IP recorded for AS17828's Equinix Sydney port — before reaching PNG DataCo's own network. Still to do: repeat across more AS pairs/economies to establish how widespread this is, not just that it happens at least once.
  - **AS24013 (Solomon Islands) — anycast/hosting location vs. real network location, compounded by a confirmed PeeringDB gap.** PeeringDB shows 7 IXP memberships, all in Germany (DE-CIX/LOCIX Frankfurt, Düsseldorf, Hamburg, Munich) plus one in Sydney, none in the Pacific. Per the project owner: this is a known pattern where anycast/hosting presence (e.g. a CDN or DNS anycast node advertised from Frankfurt) gets recorded as "the network's" IXP membership, when it has nothing to do with where that network's actual Solomon Islands traffic transits — a caution about *attributing* the finding correctly, not about the AU/NZ/US-is-suboptimal premise. **Compounding factor, confirmed by the project owner: the Solomon Islands has a real, working local IXP that PeeringDB doesn't list at all** — so "AS24013 shows zero in-region IXP presence" was never a clean read of reality; it's an artifact of PeeringDB's incompleteness on top of the anycast/hosting issue. Needs an Atlas traceroute check (per the Validation Rules above) to sort out what's actually happening, and the unlisted Solomons IXP needs to go in this project's own supplementary IXP list.
  - **Engineering follow-through from the Validation Rules above**: (a) build the actual ASN-to-ASN adjacency maps from Phase 1a's RIS neighbor data and Phase 1b's Atlas results, keeping only edges both sources agree on; (b) add a latency/hop-count feasibility check before accepting any such edge; (c) run inbound traceroutes (external vantage points -> each in-scope ASN), not just the outbound direction done so far; (d) use ASN-to-ASN traceroutes to hunt for peering relationships absent from both RIS and PeeringDB, and to spot-check existing PeeringDB IXP claims against real hop evidence; (e) start a supplementary list of known-but-PeeringDB-unlisted regional IXPs, seeded with the Solomon Islands one.
- [ ] Phase 1e: Visualization — pathway maps (geographic + AS-graph) highlighting missing/indirect routes.
- [ ] Phase 1f: Reporting — generate ASCII report and HTML report from the same underlying analysis output, per run.

### P2 — Polish and dissemination (can wait)
- [ ] Phase 2a: Presentation skeleton — slide/outline template for NOGs and conferences, pulling from the latest report.
- [ ] Phase 2b: Documentation pass — docstrings/module docs for all code, comprehensive README fleshed out beyond skeleton.
- [ ] Phase 2c: Changelog discipline — keep `CHANGELOG.md` narrating the project's journey as phases land (ongoing, not a single task).

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

## Working Agreements (apply for the rest of this project, including inside the `/loop`)
- **Commit and push after each major change** — not just when explicitly asked in the moment. A "major change" is a completed unit of work (a new module, a real finding, a plan/methodology update worth preserving), not every intermediate edit within one.
- **Never leak credentials or private data.** Never read `secrets.yaml`'s value into a response, never print/log the Atlas API key, never let it end up in a commit — verify `git status`/`git diff` before every commit if there's any chance a secret-bearing file changed.

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
