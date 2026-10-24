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

- [x] **Corroboration chain text #87 and #89 corrected (owner, 2026-10-22).**
  Finding 58, GU -> WS, measurement 212240634: both now read
  `AS3605 -> AS3356 -> AS174 -> AS17993` (was a false AS3605 loop in #87, and
  AS3356 missing in #89), with the old chain and cause in `note_extra`. See
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

## Bounce follow-ups (mail sweep 2026-10-23)

Every `mailer-daemon@googlemail.com` notice from the last 30 days (28 notices,
13 addresses, all in the tcsweetser mailbox, none in the other four), plus
three bounces sent by recipients' own servers. Subjects below are the
original messages. One item per operator whose contact never got the mail.
Addresses are in the private contact notes, not here.

- [ ] **MTC, AS9839 (MP): nobody got "Request: hosting a RIPE Atlas probe on
  MTC (AS9839)" (10-21).** The named contact failed 5.1.1. The second
  address has been delayed since 10-22 because its domain's MX lookup returns
  SERVFAIL (still SERVFAIL 10-23 via 8.8.8.8). Gmail gives up around
  10-24 22:44Z. The other MTC domain's mail runs on mx.ite.net, so try IT&E
  (AS7131) or an MTC role mailbox. Low priority: AS9839's only RIS neighbour
  is AS7131, which already hosts Saipan's probe.
- [ ] **bmobile Solomon Islands, AS132462 (SB): "Request: hosting a RIPE
  Atlas probe on bmobile Solomon Islands (AS132462)" never arrived.** Two
  SB addresses on 10-08 (domain SERVFAIL, still so 10-23), then a resend to
  the PNG domain on 10-13 (MX timed out for 3 days, failed 10-16). There is no
  email route. Try LinkedIn, Lia (RIPE NCC) or PacNOG. The Netcraft/SISCC lead
  doesn't cover this ASN.
- [ ] **Vodafone Kiribati, AS4865/AS134783 (KI): the named contact on
  "Request: hosting a RIPE Atlas probe on Vodafone Kiribati (AS4865,
  AS134783)" (10-08) doesn't exist (5.1.1).** The IT helpdesk copy was
  delivered, but there has been no reply in 15 days, and round 2 didn't nudge
  KI. Nudge the helpdesk and find a named engineer.
- [ ] **Ocean Link, AS132486 (KI): one of the two addresses on "Request:
  hosting a RIPE Atlas probe on Ocean Link (AS132486)" (10-08) doesn't
  exist (554).** The other was delivered, with no reply since. Nudge it and
  look for a second contact.
- [ ] **Vodafone Fiji (FJ): "Fiji-IXP port addresses in PeeringDB don't match
  traceroutes" and its reply (10-17) both bounced at the PeeringDB peering
  POC (554 5.4.14 mail loop).** No other Vodafone Fiji address is in Sent,
  so Vodafone Fiji hasn't seen the question. (The NOC on that message is
  TFL's, not Vodafone's.) Find a working Vodafone Fiji NOC address, resend,
  and ask them to fix the PeeringDB POC.
- [ ] **FINTEL (FJ): the named contact on "Re: Fiji-IXP port addresses in
  PeeringDB don't match traceroutes" (10-17) is still undelivered.** FINTEL's
  MX times out, and the final failure is due around 10-24 11:00Z. The FINTEL
  NOC named Taniela Sikivou and Meiva Tinivai on 10-19, but nobody has sent
  them the port-address question. Send it to both, and leave the dead address
  off replies.
- [ ] **TAF / Fiji-IXP: the 2020 PeeringDB tech contact Cc'd on "Fiji-IXP:
  offer of help with PeeringDB, a RIPE Atlas probe and operations" (10-16)
  is gone (550 5.4.1).** The official contact copy was delivered, with no
  TAF reply in 7 days. Nudge it, or ask Ravneel (USP) who at TAF runs the
  exchange now.
- [ ] **Digicel Vanuatu, AS132429 (VU): "Request: hosting a RIPE Atlas probe
  on Digicel Vanuatu (AS132429)" (10-21) was rejected by the RDAP group,
  which only accepts internal senders (5.7.133).** The route is Mark Duffell
  (Digicel-wide note sent 10-22), and he hasn't replied yet. Chase him if
  nothing arrives.
- [ ] **Blue Sky, AS23657 (AS): the RDAP admin Cc on "Re: [pacnog] Re: We
  need more RIPE ATLAS PROBES across the Pacific" (10-21, the follow-up to
  Alo Anesi) was blocked (5.7.1).** Alo's own copy was delivered, but he
  hasn't replied. If he stays quiet, use the PacNOG thread or his office phone.
- [x] **Vodafone Cook Islands: both bounces on "RIPE Atlas probe 22761
  (Telecom Aitutaki) offline since 1 October" (10-08).** No action: Andreas
  Pareanga replied 10-09 and the probe is back.
- [x] **Interchange VU: one role mailbox bounced twice on "Request: hosting a
  RIPE Atlas probe on Interchange / Prima DC (AS45495, AS132254)" (10-21).**
  No action: the other addresses were delivered and Simon Fletcher (Prima DC)
  replied the same day.

Not project bounces: a personal newsletter reply (10-08) and an ASX forward
(Digital Directors mailbox).

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
