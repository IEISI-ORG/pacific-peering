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
- [ ] Phase 1b: RIPE Atlas measurement code — create/manage traceroute measurements between relevant probes/anchors for in-scope AS pairs; store raw + parsed results.
- [ ] Phase 1c: Scheduling/automation — recurring job (7-day or monthly) that re-runs discovery + RIS pull + Atlas measurements, versions each run's output directory, is safe to re-run/resume.
- [ ] Phase 1d: Sub-optimal routing analysis — triangulate source/destination pairs to flag transpacific paths that detour outside the region (e.g., via US/AU) when a more direct path should exist.
- [ ] Phase 1e: Visualization — pathway maps (geographic + AS-graph) highlighting missing/indirect routes.
- [ ] Phase 1f: Reporting — generate ASCII report and HTML report from the same underlying analysis output, per run.

### P2 — Polish and dissemination (can wait)
- [ ] Phase 2a: Presentation skeleton — slide/outline template for NOGs and conferences, pulling from the latest report.
- [ ] Phase 2b: Documentation pass — docstrings/module docs for all code, comprehensive README fleshed out beyond skeleton.
- [ ] Phase 2c: Changelog discipline — keep `CHANGELOG.md` narrating the project's journey as phases land (ongoing, not a single task).

## Key Questions
1. ~~RIS data source~~ — resolved: RIPEstat API.
2. ~~Atlas credit budget~~ — resolved: ~100M credits available on the account behind `secrets.yaml`'s API key. Still open: which probes/anchors exist in-region vs need requesting — revisit at Phase 1b.
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

Next: Phase 1b — RIPE Atlas measurement code (traceroutes between in-scope AS pairs), using the `secrets.yaml` API key (~100M credits available).
