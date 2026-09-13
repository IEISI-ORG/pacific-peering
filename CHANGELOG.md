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
