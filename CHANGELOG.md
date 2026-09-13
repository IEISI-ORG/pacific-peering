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
