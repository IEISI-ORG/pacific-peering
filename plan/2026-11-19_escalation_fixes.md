# Escalation fixes from the 2026-11-19 reviews: plan

Status: **done 2026-11-19** (owner: "go P1 and P2, F1 option 2"): P1 `52c627a`, P2 `e968614` and `c5153c9`, F1 with the guard `343ac2c`. The F1 guard is per override (`needs_ris_for_adjacency`), not global; see task_plan.md.

This plan covers only the obvious fixes: clear, low-risk and backed by evidence. Anything that changes a filed finding or needs a judgement call is listed under "Rulings owed" and is not planned here.

Sources:
- The code review of `fbbb5e8` (local-IXP latency, option B) and `8d66f1b` (laxc/tyo patterns), 2026-11-19. The code-reviewer subagent's report is in the session transcript; its scripts `sim.py` and `fsm.py` are in the session scratchpad.
- `temp/escalation_reviews_2026-11-19/review_{ixp_latency,routing_loops,hub_mismatch,remaining}.md` (untracked).
- `temp/as23657_routing_2026-11-19/report.md` (untracked).
- `task_plan.md` 2026-11-19 entries.

Already done today, so not in this plan: F2 (`0c38ccf`), the laxc/tyo patterns (`8d66f1b`), the #321/#109/#66/#65 relabels, the AS23657 pin and retry list (`6ef8ec3`, `3f13175`), the #67/#237/#311 IX names (`1b25568`) and 28 escalation resolutions (`03f87f9`, `bf58391`, `429a54b`).

## P1. Local-IXP latency check: give leg_out only to ports confirmed remote

**Problem (code review, MEDIUM).** `_local_ixp_check` (`src/pacific_peering/analysis/auto_classify.py:347-349`) grants leg_out from the member ASN's home economy alone.

- FSMTC (AS10130, registered FM) has its Guam IX port on a router in Guam. Its cached crossings show an excess of −5.4 to 2.9 ms (228276710, 228277589, 234924588, 234926289), yet every FSMTC port gets 24.6 ms of leg_out.
- A 20-30 ms backhaul behind that port would now clear without a flag.
- The headroom is larger elsewhere: GU→MH gives 44.7 ms, and a PG member at Fiji-IXP would get 52.6 ms. 52.6 ms is enough to hide a trip via Sydney, which is the case this check exists to catch.
- Only two ports have evidence of a remote router: PNCC AS17893's Guam IX .18 (Koror; anchoring mesh 86005050) and CenPac AS55722's Guam IX .24 (Nauru; 54.5 ms with the CenPac core 0.005-0.03 ms behind it).

**Change.**

1. Add a hand-verified table in `auto_classify.py`, next to `LOCAL_IXP_CABLE_STRETCH`:
   ```python
   # Exchange ports whose router sits in another economy (owner-confirmed evidence only).
   # Key (PeeringDB ix_id, member ASN) -> economy of the router behind the port.
   REMOTE_IXP_PORTS: dict[tuple[int, int], str] = {
       (4494, 17893): "PW",  # PNCC Guam IX .18 -> Koror (anchoring mesh 86005050)
       (4494, 55722): "NR",  # CenPac Guam IX .24 -> Nauru (234928910, core 0.005-0.03ms behind)
   }
   ```
   The key uses (ix_id, ASN), not (ix_id, IP), because crossing dicts carry `ix_id` and `member_asns` but no address (`traceroute_topology.py:452-460`). Adding the address would touch every triangulation file for no gain while each member has one port per exchange.
2. leg_out comes only from that table. For each member ASN on the hop, take the remote economy from `REMOTE_IXP_PORTS[(ix_id, asn)]`. If any member is missing from the table, leg_out is 0. Otherwise leg_out = min over members of `stretch × floor(ixp_cc → remote_cc)`.
   - This also fixes code-review item 2: today the result depends on which ASN number sorts lowest. `[3605, 10130]` flags but `[10130, 3605]` clears.
   - Use `crossing.get("member_asns") or []` so a `None` value is safe.
   - `asn_to_cc` is no longer needed by `_local_ixp_check`. Drop the parameter and its loader call only if nothing else uses it.
3. Update the docstring and the `fbbb5e8` comment block to say that leg_out applies to confirmed remote ports only.

**Tests first** (`tests/analysis/test_local_ixp_latency.py`):

- New, should fail before the change:
  - FSMTC local port: GU probe, hops (1, 0.5), (2, 30.0), (3, 30.1), crossing hop 2, member 10130, `ix_id` 4494, economies GU/GU. It must flag, with leg_out 0 and allowance 10.0.
  - Member order: `[3605, 10130]` and `[10130, 3605]` give the same result (flag). `[6939, 10130]` flags.
  - A remote and an unlisted member on one hop (`[17893, 10130]`): leg_out 0.
- Existing tests that must still pass: `_GU_TO_PNCC_PORT`, `_GUAM_IX_REMOTE_PORT`, `_PW_TO_CENPAC_PORT` and `_FM_TO_PNCC_PORT` clear; `_NC_TO_TFL_PORT` flags at 22.5 ms against 14.0 ms. `_crossing()` has to gain an `ix_id` (default 4494 for the Guam fixtures, the Fiji-IXP id for the FJ ones).

**Verify.**

- Re-run the reviewer's `sim.py` over the 114 cached in-fishbowl crossings with RTTs. It must give the same 6 flags (NC → Fiji-IXP → AS45349 on 228735988 and 235633070). The 12 resolved Guam IX entries must still clear. Any new flag gets a name and a look before commit, not a silent pass.
- `uv run pytest -q`, `ruff check .`, `mypy src/`.

## P2. Minor items from the same review (same commit or the next one)

1. **Escalation text when excess is None** (`auto_classify.py:968-976`). Today it can read "at 19.05ms, above the 29.4ms allowed". When `excess_ms is None`, write "excess could not be computed (exchange hop not in the parsed trace); the allowance would be X ms".
   - Test: a unit test on the detail string. It may be easier to move the f-string into a small `_local_ixp_detail(crossing)` helper and test that helper.
2. **One "hop before" list, not two** (`:293` and `:346`). Have one helper return `(excess, before_rtt)` so leg_in and excess always measure from the same hop. This is a pure refactor; the existing tests cover it.
3. **Classify-level test** (code-review item 4). Feed the frozen 235633070 / probe 7018 crossing through `_classify_corridor`, in the style of `test_auto_classify_source_pinning.py`. Assert one "local IXP crossing with implausibly high latency" escalation whose detail contains "14.0ms allowed". Add one unit test with `ixp_cc=None` and a remote member, expecting an allowance of 10.0.
4. **Stale test comment** (`tests/analysis/test_hop_geolocation.py:144`). It says "All nine tyo1 names in the PTR cache"; the cache now has 10. Add `port-channel10.core3.tyo1.he.net` to `HE_TOKYO` and change "nine" to "ten (2026-11-19)". It already resolves to Tokyo, so this is a test-data change only.

**Verify:** `uv run pytest -q`, `ruff check .`, `mypy src/`. No data files change and no findings move.

## Order and commits

1. P1 (test-first), with its sim re-run in the commit body.
2. P2.1-P2.3 (test-first for 1 and 3).
3. P2.4.

Each gets its own Conventional Commit, with no attribution trailer, then a push. Add CHANGELOG lines and a `task_plan.md` entry. No Atlas credits and no findings.db changes.

## Not planned: rulings owed

These change filed findings or the method, so they need the owner first:

- **F1** (Superloop 103.200.13.0/24 → AS38195 override). The rehearsal shows 211259107 would file a new NC → GU AS3605 detour, with RIS disagreeing on the AS38195 → AS3605 step. The options are (1) apply as is, (2) apply with a guard that a step made contiguous only by the override must still pass RIS agreement before it files (recommended), or (3) leave it. The patch is at `temp/escalation_reviews_2026-11-19/f1_superloop_override.patch`.
- **#55**: should 229249274's dark hop at the tyo1 position count as no data, so that Tokyo passes on 4 runs?
- **#303**: count only runs to an answering address, or count reaching AS3605 (the sole RIS upstream)? Should dead-end traces still corroborate local-transit edges #280 and #325?
- **#287**: a per-finding pin to 202.4.47.1. This needs a new mechanism, because the AS23657 pin sends its reruns to 38.134.236.1.
- **#66**: should the dark-probe run 233087028 count as no data?
- **#20/#115**: the forward path has been local since 10-28.
- **#159-#161**: filed via LA; the routers now show Tokyo, matching their JPNAP Tokyo crossings.
- **#314**: now Tokyo, then Level3 HongKong3. Also: quarantine AS132462 and hold #15/#314 until APNIC replies?
- **Any2West hub city**: crossings are dropped silently today (62 hops, 16 findings).
- **First crossing vs last city**: about 21 findings, likely including #47.
- **Pinning the traced address** in reverification generally.
- **NOC-150312**: add 113.197.15.213/.194 to known_anomalies? Recommend no until AARNet or USP reply.
- Also owed:
  - #328: hold or drop.
  - #51: rows 918 and 1343, with the 113-row decision.
  - AS152706: close now or wait for APNIC.
  - #54's retest source.
  - The PacNOG deck note on probe 23039's uplink change behind the Guam ROV figure.
  - Whether to add the Bemobile weekday windows to the APNIC thread.
  - F3 (private hops before the target, 7 findings).
