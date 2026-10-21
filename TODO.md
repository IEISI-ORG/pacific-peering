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

- [ ] **Fix the reverify rotation (`last_attempted`).** Not built.
  `select_reverification_batch` ranks by the latest corroboration, so a retest
  that files nothing (inconclusive, dark, or a different kind) leaves the
  finding at the head of the queue. It is still happening: the 10-18 nightly
  re-staged #26, #29, #33 and #69, all last verified 2026-09-16. Each repeat
  costs Atlas credits, and most findings never reach the queue, so the
  "full rotation roughly every 4 weeks" in `CLAUDE.md` isn't true yet.
  Proposed fix: record `last_attempted` per finding and rank by
  `max(last_verified, last_attempted)`, built test-first.
- [ ] **The 17 swept findings: probably resolved by the fix above.** The worry
  was that a retest which now files a detour never refreshes the original
  finding, so it is re-queued weekly. With `last_attempted`, any retest moves it
  down the queue, so options 2 and 3 below become unnecessary. Real data so far
  is mild: the 10-18 nightly retested #177, #233 and #239, and all three
  corroborated as local transit with RIS agreeing, with no new detours.
  #233 was retested from NU, not TV, so the predicted TV detour didn't occur.
  Recommendation: option 1 (accept), together with the rotation fix.
  1. Accept it: new detour findings may appear.
  2. Hold the 17 out of the reverify queue until each is decided.
  3. Prioritise multi-outcome filing (see P1).

  The 17: candidate_peering #2, #15, #16, #18, #229, #230; local_transit #177,
  #184, #186, #187, #203, #233, #239, #249, #287, #293, #295. Per-finding
  retire/hold/relabel can wait unless one actually starts filing detours. The
  list is in `outputs/reports/router_detour_sweep.txt`.

## P1: next small change (needs owner approval: changes what gets filed)

- [ ] **City filter.** Still not built (2026-10-21): `auto_classify.py` passes
  every `HUB_OK` router hub to `_detour_feasibility`, whatever its city. Pass
  only `h.verdict == HUB_OK and h.city == detour_pick[2]`, and add a two-probe,
  two-city test. This closes a narrow wrong-filing case: an offshore target
  plus a slow probe via Sydney turns IMPOSSIBLE into MIXED, so a detour is
  filed, with an escalation.
- [ ] **Network guard against misnamed or spoofed PTRs.** If a located router's
  address belongs to a fishbowl ASN (`asn_to_cc`), escalate instead of
  filing. `resolve_traceroute_hops` already gives per-hop ASNs, so this costs
  no extra network calls. FCrDNS was considered and rejected: it adds nightly
  DNS work and drops real routers.
- [ ] **Multi-outcome filing** (the Known limitation). When the detour is
  router-based, also corroborate the local-transit edge the same trace shows,
  so #295-style findings stop ageing out. Less urgent once the rotation fix
  lands.
- [ ] **Tests to add with the above.** A multi-probe measurement;
  `classify_corridor` demoting a router pick on an impossible feasibility
  verdict; a too_fast corroboration note.

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
