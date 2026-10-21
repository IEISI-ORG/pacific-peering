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

- [ ] **Fix the reverify rotation (`last_attempted`).** Approved 2026-10-21;
  in progress on a separate branch, built test-first.
  `select_reverification_batch` ranks by the latest corroboration, so a retest
  that files nothing (inconclusive, dark, or a different kind) leaves the
  finding at the head of the queue. It is still happening: the 10-18 nightly
  re-staged #26, #29, #33 and #69, all last verified 2026-09-16. Each repeat
  costs Atlas credits, and most findings never reach the queue, so the
  "full rotation roughly every 4 weeks" in `CLAUDE.md` isn't true yet.
  Proposed fix: record `last_attempted` per finding and rank by
  `max(last_verified, last_attempted)`, built test-first.
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
