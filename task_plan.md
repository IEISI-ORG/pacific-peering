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
  - **AS24013 (Solomon Islands) — anycast/hosting location vs. real network location**: PeeringDB shows 7 IXP memberships, all in Germany (DE-CIX/LOCIX Frankfurt, Düsseldorf, Hamburg, Munich) plus one in Sydney, none in the Pacific. Per the project owner: this is a known pattern where anycast/hosting presence (e.g. a CDN or DNS anycast node advertised from Frankfurt) gets recorded as "the network's" IXP membership, when it has nothing to do with where that network's actual Solomon Islands traffic transits. This is a caution about *attributing* the finding correctly (don't claim AS24013's user traffic transits Germany), not a caution about the AU/NZ/US-is-suboptimal premise itself — needs an Atlas traceroute check to establish what's actually happening before it goes in any report.
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

## Errors Encountered
(none yet)

## Secrets
- `secrets.yaml` (repo root) holds the RIPE Atlas API key; account has ~100M measurement credits. Added to `.gitignore` (`secrets.yaml` + `*.secret.yaml`), confirmed untracked. Never commit it or echo its contents. Phase 1b's Atlas client should load it directly (e.g. `yaml.safe_load`) rather than requiring an env-var re-encoding.

## Status
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

Observed oddity (not yet root-caused, not blocking): the first `pacific-peering-atlas-smoketest` run after the key correction failed with a bare 400 (no useful body captured), but a near-identical request seconds later via the raw client succeeded outright — possibly a brief propagation delay right after the key was updated. Not investigated further now; if it recurs under Phase 1c's recurring scheduled runs, that phase should add basic retry-on-failure, but one transient failure isn't enough signal to build that yet.

Next: Phase 1c — scheduling/automation (recurring discovery + RIS + Atlas runs), or extend Phase 1b's one-ASN-pair proof into a real AS-pair measurement campaign across the registry.
