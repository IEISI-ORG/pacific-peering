# TODO

Open items from the 2026-10-12 router-location detour work
(`plan/2026-10-12-router-location-detour-check.md`; full narrative in
`task_plan.md`, 2026-10-12 entries), plus the reverify-rotation gap found
2026-10-12 (`task_plan.md`, "the weekly reverify rotation doesn't rotate").

**Triaged 2026-10-21.** The router rule has now met real data: the 10-18
nightly (cron line `2026-10-19 01:51`) tested 67 corridors in 2984 s against
66 in 2991 s on 2026-10-12, so the PTR lookups add no visible cost. It raised
one escalation (San Francisco unmapped, now fixed) and no "physically
impossible" escalations.

## P0: owner decision

- [x] **Reverify rotation fixed (2026-10-21, `8594ec7`, merged `77c4ba2`).** New
  `reverification_attempts` table (added by `CREATE TABLE IF NOT EXISTS`, so it
  needs no migration step). `select_reverification_batch` ranks by
  `max(last_verified, last attempt)`. A retest is stamped once its fate is
  known: classified (any outcome), failed after writing began, or a parked
  measurement collected or given up on ("lost"). Not exported, so a rebuild
  from the JSONL falls back to last-verified. 6 tests in `test_reverify_rotation.py`.
- [ ] **Rotation follow-ups (owner decision):**
  - A retest ending in "no probe data returned" (usually a transient Atlas
    fetch race) now counts as an attempt and goes to the back. Exclude that
    reason in `_note_reverification_attempt` if it should keep its turn.
  - Pre-existing: `_pop_reverify_candidate` drops a staged finding whose vantage
    economy has no connected probe without stamping it, so it takes a ration
    slot every week (no credits spent). Could stamp "no_vantage".
  - Pre-existing, rare: a retest parked Saturday and collected Monday is still
    in Sunday's queue, so it can be re-fired right after being stamped.
- [x] **The 17 swept findings: option 1, accept (owner, 2026-10-21).** New detour
  findings may appear when one is retested. The rotation fix above keeps any
  retest from leaving a finding stuck at the head of the queue, and
  multi-outcome filing (done, below) keeps local-transit edges like #295
  refreshed. No per-finding retire/hold/relabel unless one actually starts
  filing detours. The list is in `outputs/reports/router_detour_sweep.txt`.

## P1: done 2026-10-21 (owner approved)

All four are in `auto_classify.py`, with 7 new tests in `test_router_detour.py`; 358 pass.

- [x] **City filter.** Only `HUB_OK` routers with `h.city == detour_pick[2]` stand in
  for the hub hop. Test: `test_router_in_another_city_is_not_the_detour_hub`
  (LA claim with an offshore-fast target plus a slow Sydney probe: was filed
  mixed, now escalated impossible).
- [x] **Network guard.** An OK router whose address BGP gives to a fishbowl ASN
  becomes `HUB_IN_REGION` and escalates ("router hostname off-region but address
  in a fishbowl network"), never a detour. Uses `resolve_traceroute_hops` only.
- [x] **Multi-outcome filing.** A router-located detour also corroborates an
  existing local-transit finding for the same upstream -> target edge. It never
  creates one, and IXP detours are unchanged.
- [x] **Tests:** multi-probe measurement; impossible feasibility demoting a router
  pick; too_fast note on the detour corroboration; the guard; multi-outcome
  (corroborates, never creates, IXP path untouched).

## P1 review follow-ups (owner decision; code review of `0e6370a`, 2026-10-21)

- [ ] **Router hubs in more than one city.** `detour_pick` takes its city from the
  first `HUB_OK` probe, and the city filter now leaves other cities' routers
  out of the feasibility check altogether. So one measurement can file an LA
  detour or a Sydney one depending on probe order, and the other city's router
  is recorded nowhere. Option: escalate "router hubs in several cities" naming
  every city and hop, or check each city separately and file only the claims
  that aren't impossible.
- [ ] **Network guard passes when the hub address has no single ASN.** It
  fires only if `asns` contains a fishbowl ASN. With no ASN (RIPEstat failure,
  unannounced space) or more than one origin, the router stays `HUB_OK` and
  the detour is filed. Option: treat no-ASN as unverified and escalate.
  Related, pre-existing: `ip_resolution_cache` stores a RIPEstat failure as a
  permanent negative (118 such entries), so one bad night disables the guard
  for that address.

## P2: watch / later

- [ ] **Sydney floors are weak** (15-35 ms from NC/PG/FJ/TO/TV), so location
  there rests on pattern curation. A possible tightening is to subtract the
  probe's first public-hop RTT before comparing.
  Also anchor new `hop_geolocation` patterns to carrier domains where
  possible.
- [ ] **Corroboration rows count every clean probe**, including probes whose
  own router hub was rejected (the IXP path does the same).
- [ ] **A router-hub pick suppresses that night's TBA-exchange escalation**
  (the IXP pick does the same).
- [ ] **Tests open the real findings DB at import.** `corridor_backlog.py:60-62`
  loads the legacy tuples via `store.connect()` at import, before
  `conftest._block_real_db` patches it. Any schema change therefore reaches
  `data/analysis/findings.db` on the first test run (seen 2026-10-21: the empty
  `reverification_attempts` table appeared during pytest after the merge).
  It only reads, plus `CREATE ... IF NOT EXISTS`, but it isn't isolated.
- [ ] **Router-detour review, low items:** only the first local-transit edge is
  refreshed when probes have different fishbowl upstreams; the edge
  corroboration filters on upstream only, as the existing branch does;
  `router_detour_sweep.py` doesn't apply the network guard, so it reports
  "ok" for routers the nightly run escalates; the `RouterHub.verdict` comment
  doesn't list `HUB_IN_REGION`.
- [ ] **Minor code hygiene** (still present 2026-10-21):
  - `router_location.py`: logger defined but never used. `reverse_dns`'s
    `_lookup` catches only `OSError`; anything else leaves a traceback in
    `cron.log` and returns None.
  - `router_detour_sweep.py`: serial and silent; `render()` hides
    too_fast/unmapped rows on detour findings; strict `ip_network`;
    cwd-relative report path; untested branches.

## Done

- [x] **First real nightly run with corridors queued** (2026-10-19 cron line;
  checked 2026-10-21). 67 corridors in 2984 s, the same pace as before the
  rule. One escalation, "router in a hub city with no coordinates" (Cogent
  `sfo01`, 224427229). No "physically impossible" escalations.
- [x] **San Francisco hub coordinates** (2026-10-21, owner).
  `EXTERNAL_HUB_LATLON["San Francisco"]` was added, the unmapped-city tests now
  use OneQode Hong Kong, and `test_san_francisco_is_mapped` freezes the
  224427229 hop.
