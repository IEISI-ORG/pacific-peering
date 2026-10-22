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
- [x] **No-data retests need 3 attempts (owner, 2026-10-21).** A retest that
  ends in "no probe data returned" is recorded as `no_data`. Only every third
  one since the finding's last real attempt or corroboration moves it down
  the queue (`NO_DATA_ATTEMPTS_REQUIRED`).
- [ ] **Rotation, remaining (watch):**
  - `_pop_reverify_candidate` drops a staged finding that can't be rebuilt
    (no connected probe in its vantage economy) without recording an attempt,
    so it would be re-staged every week, taking a ration slot each time
    (no credits spent). It affects no findings today (0 of 257, checked
    2026-10-21); it starts to matter only if an economy loses its last probe.
    Fix if that happens: stamp `no_vantage`.
  - Rare: a retest parked Saturday and collected Monday is still in Sunday's
    queue, so it can be re-fired right after being stamped.
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

- [x] **Router hubs in more than one city: escalate (owner, 2026-10-21).** When
  `HUB_OK` routers span several cities, the run escalates "router hubs in several
  cities" with every probe's router and files no router-based detour, whatever
  the probe order. The city filter in the feasibility call stays as a second guard.
- [x] **Network guard needs a single BGP owner (owner, 2026-10-21).** A located
  router whose hop resolves to no ASN, or to more than one, becomes `HUB_NO_OWNER`
  and escalates ("router address has no single BGP owner") instead of filing.
  It affects none of today's 18 located routers.
- [ ] **IP-resolution cache keeps RIPEstat failures (separate change, not approved yet).**
  A failed lookup is cached as a permanent "no owner" (77 public-address
  negatives as of 2026-10-21). Now that the guard escalates no-owner routers,
  a bad RIPEstat night turns such routers into permanent escalations instead
  of silent passes. Fix: retry failures instead of caching them, and keep
  genuine "unannounced" answers. This touches every hop resolution.

## Owner decision (2026-10-22, ixp-country-jedi review)

- [ ] **Corroboration chain text #87 and #89** (finding 58, GU -> WS,
  measurement 212240634) still carries the stale-`late`-reply artefact: #87
  shows a false `AS3605 -> AS3356 -> AS3605` loop and #89 omits AS3356. The
  finding's conclusion is unchanged (its detour description already names
  AS3356). Correct the text in `findings.db` or leave it as recorded? See
  `docs/traceroute_late_edst_and_guessed_probe_locations.md`.

## Parked by the owner (2026-10-22)

- [ ] **Anchor stitching** (ixp-country-jedi's `viaanchor`: direct min RTT
  A->B vs A->anchor + anchor->B, to estimate what a regional hub would save).
  Start once there are more Pacific anchors (TFL's Fiji anchor is the first in
  progress).
- [ ] **Weighting findings by users.** Needs research first: what a weight
  should mean and which measure is reliable for the Pacific. The owner does not
  trust ad-sampled eyeball estimates (APNIC's per-ASN user shares come from
  Google ad placements) to weight Pacific use fairly.

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
