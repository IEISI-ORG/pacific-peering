# TODO

Open items from the 2026-10-12 router-location detour work
(`plan/2026-10-12-router-location-detour-check.md`; full narrative in
`task_plan.md`, 2026-10-12 entries). The rule has been live since the
2026-10-13 01:00 batch. That batch had no corridors queued (0 tested), so it
hasn't met real data yet.

## P0: owner decision

- [ ] **What reverification does to the 17 swept findings.** Re-testing a
  local-transit or candidate-peering finding whose probe still passes a
  hostname-located router now corroborates or creates a *detour*. The original
  finding is then never refreshed: it stays oldest-verified and is re-queued
  weekly, each time costing Atlas credits. Example: #233 would start a TV
  detour (HE Sydney, 57.6 ms vs a 35.7 ms floor). Choose one:
  1. Accept it: new detour findings may appear.
  2. Hold the 17 out of the reverify queue until each is decided.
  3. Prioritise multi-outcome filing (see P1).

  The 17: candidate_peering #2, #15, #16, #18, #229, #230; local_transit #177,
  #184, #186, #187, #203, #233, #239, #249, #287, #293, #295.
- [ ] **What to do with each of the 17**: retire, hold or relabel. They are
  listed in `outputs/reports/router_detour_sweep.txt`.

## P1: next small change (needs owner approval: changes what gets filed)

- [ ] **City filter.** In `auto_classify.classify_corridor`, pass only OK router
  hubs in the chosen city to `_detour_feasibility`:
  `h.verdict == HUB_OK and h.city == detour_pick[2]`. Add a two-probe,
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
  so #295-style findings stop ageing out.
- [ ] **Tests to add with the above.** A multi-probe measurement;
  `classify_corridor` demoting a router pick on an impossible feasibility
  verdict; a too_fast corroboration note.

## P2: watch / later

- [ ] **First real nightly run with corridors queued.** Compare the
  `Batch done ... in Ns` line in `logs/cron.log` with earlier nights:
  2026-10-12 was 66 corridors in 2991 s, and 2026-10-09 was 35 in 6920 s.
  Expected PTR cost per measurement is a median of 10 lookups (p99 37), each
  at most 2 s. Also check `escalations.md` for "router hostname location
  physically impossible" and "router in a hub city with no coordinates".
- [ ] **San Francisco hub coordinates.** Not added, so Cogent `sfo01` routers
  escalate. If added: the viz map draws every hub, and
  `test_unmapped_city_has_no_floor` must change.
- [ ] **Sydney floors are weak** (15-35 ms from NC/PG/FJ/TO/TV), so location
  there rests on pattern curation. A possible tightening is to subtract the
  probe's first public-hop RTT before comparing.
  Also anchor new `hop_geolocation` patterns to carrier domains where
  possible.
- [ ] **Corroboration rows count every clean probe**, including probes whose
  own router hub was rejected (the IXP path does the same).
- [ ] **A router-hub pick suppresses that night's TBA-exchange escalation**
  (the IXP pick does the same).
- [ ] **Minor code hygiene:**
  - `router_location.py`: unused logger. `reverse_dns`'s `_lookup` catches
    only `OSError`; anything else leaves a traceback in `cron.log` and
    returns None.
  - `router_detour_sweep.py`: serial and silent; `render()` hides
    too_fast/unmapped rows on detour findings; strict `ip_network`;
    cwd-relative report path; untested branches.
