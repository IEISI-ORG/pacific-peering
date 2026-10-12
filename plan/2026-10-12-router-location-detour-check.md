# Router-Location Detour Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify a corridor as a confirmed detour when its traceroute passes a router whose own hostname places it in an off-region hub city, and whose RTT is physically consistent with that city, even when no IXP is crossed.

**Architecture:** A new pure module `analysis/router_location.py` finds, per trace, the first hop whose PTR record matches an off-region pattern in `hop_geolocation.py`, and judges it against the fibre floor from `feasibility.py`. A report-only sweep runs it over the existing corpus first; the owner reads that report before anything is wired in (checkpoint after Task 2). Then `feasibility.check_detour_trace` learns to accept a router hop in place of an IXP hop, and `auto_classify.classify_corridor` uses the router hub when the IXP rule found no detour.

**Tech Stack:** Python 3 / `uv`, pytest, ruff, SQLite (`analysis/store.py`), RIPE Atlas parsed traces (`data/atlas/parsed/<msm>.json`).

**Spec:** No separate spec. The design comes from this session (2026-10-12) and is recorded in `task_plan.md` (2026-10-12 MP -> TO entry) and the "Design decisions" section below.

## Design decisions (read before Task 1)

1. **Location evidence comes from the router's hostname, not from latency.** Pacific paths include satellite legs (O3b MEO, GEO) whose RTT looks like an ocean crossing, so latency alone can't say *where* a path went. Latency is the **check**: a hop's cumulative RTT must be at least the fibre floor from the source economy to the hostname's city, or the hostname is wrong about where the router is. This mirrors Validation Rule 2 (`feasibility.py`) and the `hop_geolocation.py` governance ("router naming is far more reliable than picking a facility off a carrier's PeeringDB list").
2. **Only the first located off-region hop of each trace is judged.** It's deterministic and easy to explain in a finding note. A later hop is never used to rescue a too-fast first hop.
3. **No locationless detours.** A hostname city with no `EXTERNAL_HUB_LATLON` entry (today: San Francisco, Hong Kong) escalates instead of filing, the same as rule 2's unmapped-hub IXP case. The owner adds the coordinates when one comes up. This keeps the map unchanged, because `viz/geographic.py` draws every hub in that dict.
4. **The IXP rule still wins.** The router check runs only when no off-region IXP crossing produced a `detour_pick`.
5. **Existing findings are untouched.** Task 2's sweep reports which findings the rule would have classified differently. Whether to retire, hold or re-label them is the owner's decision, made after reading it.
6. **Out of scope:** a pure latency-jump detector for dark segments (the hidden-hop rule already makes those corridors inconclusive), and filing both a detour *and* a local-transit result from one measurement (see Known limitation).

**Measured scale (2026-10-12, one-off sweep in the session scratchpad):** 1,612 unique public hop addresses in 906 parsed measurements; 1,052 have PTR records and 242 match a curated pattern (Sydney 102, Los Angeles 67, San Jose 33, Portland 19, San Francisco 8, Tokyo 5, Guam 8). Among filed findings, traces with a located off-region router and **no** off-region IXP back 64 detours, **11 `confirmed_local_transit`** (#177, #184, #186, #187, #203, #233, #239, #249, #287, #293, #295) and **6 `candidate_peering`** (#2, #15, #16, #18, #229, #230).

## Global Constraints

- Run everything through `uv run` (`uv run pytest`, `uv run ruff check`).
- No network in tests: inject the PTR resolver, and patch every `auto_classify` call that would reach RIPEstat, bgp.tools or Atlas.
- No Atlas credits are spent by any task.
- Tasks 1–2 change no stored findings, and neither does Task 2's sweep.
- **Cron runs from this working tree on `main`.** A pushed Task 4 changes the 01:00 nightly batch immediately. Don't start Task 3 until the owner has read Task 2's report and said to proceed.
- Commits: Conventional Commits, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; commit and push after each task (owner's standing preference).
- Match the surrounding code: module docstrings that give the owner's reasoning and dated evidence (measurement IDs), `logger = logging.getLogger(__name__)`, type hints, frozen dataclasses.

## Review Focus

1. **A hostname that lies about its city** (carrier reused a name after moving the router): when the hop answers faster than the fibre floor, expect an escalation and no detour. Pinned in Task 1 (`test_hostname_too_fast_for_its_city`) and Task 4 (`test_too_fast_hostname_escalates_and_keeps_local_transit`).
2. **A city with no hub coordinates** (Cogent `sfo01`, 216155108): expect an escalation naming the hostname, and no detour filed. Pinned in Task 1 (`test_unmapped_city_has_no_floor`) and Task 4 (`test_unmapped_city_escalates`).
3. **A measurement where one probe goes via LA and another goes direct**: the detour claim should rest only on the probe that passed the router, so the direct probe can't make the feasibility check read "impossible" or "mixed". Pinned in Task 3 (`test_claim_rests_on_router_hub_probes_only`).
4. **A trace that crosses an off-region IXP and also passes a located router**: expect the existing IXP name and hub to be kept, and no PTR lookups at all. Pinned in Task 4 (`test_ixp_detour_takes_precedence`).
5. **No PTR record / DNS failure at 01:00**: expect the corridor to classify exactly as it does today. Pinned in Task 1 (`test_reverse_dns_returns_none_on_lookup_failure`) and Task 4 (`test_no_ptr_records_leaves_local_transit`).

## Known limitation (owner decision, not in this plan)

`classify_corridor` returns one outcome per measurement. After Task 4, re-testing a corridor like MP -> TO corroborates the detour (#92), and the local-transit edge it also shows (#295, Digicel Fiji -> Digicel Tonga) is no longer corroborated. #295 will then age out of date and keep being re-queued, the same staleness #92 has today. Fixing that means filing more than one outcome per measurement, which is a separate change.

## File Structure

- Create `src/pacific_peering/analysis/router_location.py`: `RouterHub`, `reverse_dns`, `find_router_hub`. Pure apart from the PTR lookup, which is injected.
- Create `tests/analysis/test_router_location.py`.
- Create `src/pacific_peering/analysis/router_detour_sweep.py`: report-only corpus sweep, writes `outputs/reports/router_detour_sweep.txt`.
- Create `tests/analysis/test_router_detour_sweep.py`.
- Modify `pyproject.toml` `[project.scripts]`: add `pacific-peering-router-detour-sweep`.
- Modify `src/pacific_peering/analysis/feasibility.py` (`check_detour_trace`, ~line 139): optional `router_hub_hop`.
- Modify `tests/analysis/test_feasibility_detour.py`.
- Modify `src/pacific_peering/analysis/auto_classify.py`: module docstring rule 2; `_detour_feasibility` (~line 376); the router check after the per-probe loop (~line 700); `_corroborate` (~line 755).
- Create `tests/analysis/test_router_detour.py`.
- Modify `CHANGELOG.md`, `task_plan.md`.

---

### Task 1: `router_location` module

**Files:**
- Create: `src/pacific_peering/analysis/router_location.py`
- Test: `tests/analysis/test_router_location.py`

**Interfaces:**
- Consumes: `hop_geolocation.resolve_hostname(hostname) -> HopLocation | None` (`.city`, `.economy_cc`); `feasibility.great_circle_km`, `feasibility.min_feasible_rtt_ms`; `economy_coordinates.ECONOMY_LATLON`, `ECONOMY_SPREAD_KM`, `EXTERNAL_HUB_LATLON`.
- Produces:
  - `HUB_OK = "ok"`, `HUB_TOO_FAST = "too_fast"`, `HUB_UNMAPPED = "unmapped"`
  - `RouterHub(probe_id: int, hop: int, address: str, hostname: str, city: str, min_rtt_ms: float, floor_ms: float | None, verdict: str)` with `.note() -> str`
  - `reverse_dns(address: str) -> str | None` (LRU-cached)
  - `find_router_hub(trace: dict, source_cc: str, resolver: Callable[[str], str | None] = reverse_dns) -> RouterHub | None`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for router_location: an off-region router placed by its hostname, checked against the fibre floor.

Fixtures are cut down from real parsed Atlas traces (measurement IDs in each
test). Per the project owner (2026-10-12): 221439393 (MP -> TO) left the
region via Tata Los Angeles with no IXP crossing, and the IXP-only detour
rule missed it.
"""

from __future__ import annotations

import socket

import pytest

from pacific_peering.analysis import router_location as rl

TATA_LA = "ix-xe-2-1-4-0.tcore2.lvw-losangeles.as6453.net"

# 221439393 probe 65653 (Saipan): AS7131 -> Tata LA -> Telstra Global -> Digicel Fiji -> Digicel Tonga.
MP_TO_TRACE = {
    "probe_id": 65653,
    "target": "202.43.12.1",
    "hops": [
        {"hop": 1, "addresses": ["192.168.1.1"], "min_rtt_ms": 1.416},
        {"hop": 4, "addresses": ["103.57.234.108"], "min_rtt_ms": 8.166},
        {"hop": 8, "addresses": ["64.86.252.73"], "min_rtt_ms": 121.458},
        {"hop": 12, "addresses": ["202.84.143.25"], "min_rtt_ms": 167.759},
        {"hop": 18, "addresses": ["202.43.12.5"], "min_rtt_ms": 212.954},
    ],
}


def _resolver(table: dict[str, str]):
    calls: list[str] = []

    def resolve(address: str) -> str | None:
        calls.append(address)
        return table.get(address)

    resolve.calls = calls
    return resolve


def test_tata_los_angeles_on_mp_to_to_is_a_hub():
    hub = rl.find_router_hub(MP_TO_TRACE, "MP", _resolver({"64.86.252.73": TATA_LA}))
    assert hub is not None
    assert (hub.probe_id, hub.hop, hub.address, hub.city) == (65653, 8, "64.86.252.73", "Los Angeles")
    assert hub.floor_ms == 94.63  # Saipan -> LA, less MP's 150km spread, fibre at 2/3 c
    assert hub.verdict == rl.HUB_OK
    assert "121.458ms" in hub.note() and "floor 94.63ms" in hub.note()


def test_hostname_too_fast_for_its_city():
    # A "lax" name on the 8.166ms PTI hop can't be in Los Angeles.
    hub = rl.find_router_hub(
        MP_TO_TRACE, "MP", _resolver({"103.57.234.108": "be1.ccr41.lax01.atlas.cogentco.com"})
    )
    assert (hub.hop, hub.city, hub.verdict) == (4, "Los Angeles", rl.HUB_TOO_FAST)


def test_only_the_first_located_hop_is_judged():
    # Too-fast hop 4 is not rescued by the genuine LA hop 8.
    hub = rl.find_router_hub(
        MP_TO_TRACE, "MP",
        _resolver({"103.57.234.108": "be1.ccr41.lax01.atlas.cogentco.com", "64.86.252.73": TATA_LA}),
    )
    assert (hub.hop, hub.verdict) == (4, rl.HUB_TOO_FAST)


def test_unmapped_city_has_no_floor():
    # 216155108 probe 7455 (VU): Cogent San Francisco at 140.259ms. No EXTERNAL_HUB_LATLON entry.
    trace = {"probe_id": 7455, "hops": [{"hop": 6, "addresses": ["154.54.168.254"], "min_rtt_ms": 140.259}]}
    hub = rl.find_router_hub(trace, "VU", _resolver({"154.54.168.254": "be5991.ccr22.sfo01.atlas.cogentco.com"}))
    assert (hub.city, hub.floor_ms, hub.verdict) == ("San Francisco", None, rl.HUB_UNMAPPED)
    assert "no hub coordinates" in hub.note()


def test_in_region_hostname_is_skipped():
    # 219060211: OneQode's router name carries a Guam token; Guam is in scope, so not a hub.
    trace = {"probe_id": 6923, "hops": [{"hop": 2, "addresses": ["103.151.64.7"], "min_rtt_ms": 70.4}]}
    resolve = _resolver({"103.151.64.7": "gu-gnc-rt1-----Vlan780.au-gssyd-rt1.oneqode.net"})
    assert rl.find_router_hub(trace, "GU", resolve) is None


def test_private_ecmp_and_rttless_hops_are_never_looked_up():
    trace = {"probe_id": 1, "hops": [
        {"hop": 1, "addresses": ["10.35.115.2"], "min_rtt_ms": 3.9},
        {"hop": 2, "addresses": ["64.86.252.73", "64.86.252.74"], "min_rtt_ms": 121.0},
        {"hop": 3, "addresses": ["64.86.252.73"], "min_rtt_ms": None},
    ]}
    resolve = _resolver({"64.86.252.73": TATA_LA, "10.35.115.2": TATA_LA})
    assert rl.find_router_hub(trace, "MP", resolve) is None
    assert resolve.calls == []


def test_no_ptr_record_means_no_hub():
    assert rl.find_router_hub(MP_TO_TRACE, "MP", _resolver({})) is None


def test_source_without_coordinates_means_no_hub():
    assert rl.find_router_hub(MP_TO_TRACE, "XX", _resolver({"64.86.252.73": TATA_LA})) is None


def test_reverse_dns_returns_none_on_lookup_failure(monkeypatch):
    def _fail(address):
        raise socket.herror(1, "Unknown host")

    rl.reverse_dns.cache_clear()
    monkeypatch.setattr(rl.socket, "gethostbyaddr", _fail)
    assert rl.reverse_dns("192.0.2.1") is None
    rl.reverse_dns.cache_clear()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/analysis/test_router_location.py -q`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'pacific_peering.analysis.router_location'`.

- [ ] **Step 3: Write the module**

```python
"""Locate a traceroute's first off-region router from its own hostname, checked against physics.

Per the project owner (2026-10-12): a corridor can leave the region without
crossing any IXP. 221439393 (MP -> TO, reverification of #92) went Saipan ->
Tata `tcore2.lvw-losangeles.as6453.net` 121ms -> Telstra Global -> Digicel
Fiji -> Digicel Tonga over private interconnects. The IXP-based detour rule
never fired, and the run filed #295 (local transit) instead.

The location comes from the router's PTR record via `hop_geolocation`'s
curated pattern table, never from RTT alone: Pacific paths include satellite
legs whose latency looks like an ocean crossing. RTT is the check, not the
evidence. The hop's cumulative RTT must be at least the fibre floor from the
source economy to the named city (`feasibility.min_feasible_rtt_ms`, with the
source economy's spread taken off so it stays a lower bound), or the hostname
can't be telling the truth about where the router is.

Only the first located off-region hop of a trace is judged, so a later hop
never rescues a too-fast one. ECMP hops (more than one address) are skipped:
their `min_rtt_ms` may belong to a different router. A city with no
`EXTERNAL_HUB_LATLON` entry has no floor and is reported as unmapped, for a
human to add, never filed as a locationless detour.
"""

from __future__ import annotations

import functools
import ipaddress
import logging
import socket
from collections.abc import Callable
from dataclasses import dataclass

from pacific_peering.analysis.feasibility import great_circle_km, min_feasible_rtt_ms
from pacific_peering.analysis.hop_geolocation import resolve_hostname
from pacific_peering.discovery.economy_coordinates import ECONOMY_LATLON, ECONOMY_SPREAD_KM, EXTERNAL_HUB_LATLON

logger = logging.getLogger(__name__)

HUB_OK = "ok"
HUB_TOO_FAST = "too_fast"  # answered faster than fibre allows from the source to that city
HUB_UNMAPPED = "unmapped"  # city has no EXTERNAL_HUB_LATLON entry, so no floor

PtrResolver = Callable[[str], "str | None"]


@dataclass(frozen=True)
class RouterHub:
    """The first hop of one probe's trace that its hostname places outside the region."""

    probe_id: int
    hop: int
    address: str
    hostname: str
    city: str
    min_rtt_ms: float
    floor_ms: float | None  # None when `city` has no EXTERNAL_HUB_LATLON entry
    verdict: str  # HUB_OK | HUB_TOO_FAST | HUB_UNMAPPED

    def note(self) -> str:
        floor = "no hub coordinates" if self.floor_ms is None else f"floor {self.floor_ms}ms"
        return (
            f"router hub: hop {self.hop} {self.address} {self.hostname} -> {self.city}, "
            f"{self.min_rtt_ms}ms ({floor}, {self.verdict})"
        )


@functools.lru_cache(maxsize=4096)
def reverse_dns(address: str) -> str | None:
    """PTR lookup; None on any failure. Cached: a nightly batch meets the same backbone routers again and again."""
    try:
        return socket.gethostbyaddr(address)[0]
    except OSError:
        return None


def _is_global(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False


def find_router_hub(trace: dict, source_cc: str, resolver: PtrResolver = reverse_dns) -> RouterHub | None:
    """The first hop of `trace` whose hostname places it outside the region, judged against the fibre floor.

    `trace` is one entry of `data/atlas/parsed/<msm>.json`. Returns None when the
    source economy has no coordinates, or no single-address public hop with an
    RTT has a hostname matching an off-region pattern (`economy_cc` None).
    """
    if source_cc not in ECONOMY_LATLON:
        return None
    for h in trace.get("hops", []):
        addresses = h.get("addresses", [])
        rtt = h.get("min_rtt_ms")
        if len(addresses) != 1 or rtt is None or not _is_global(addresses[0]):
            continue
        address = addresses[0]
        hostname = resolver(address)
        location = resolve_hostname(hostname) if hostname else None
        if location is None or location.economy_cc is not None:
            continue
        floor_ms: float | None = None
        verdict = HUB_UNMAPPED
        if location.city in EXTERNAL_HUB_LATLON:
            km = max(
                0.0,
                great_circle_km(*ECONOMY_LATLON[source_cc], *EXTERNAL_HUB_LATLON[location.city])
                - ECONOMY_SPREAD_KM.get(source_cc, 0.0),
            )
            floor_ms = round(min_feasible_rtt_ms(km), 2)
            verdict = HUB_OK if rtt >= floor_ms else HUB_TOO_FAST
        return RouterHub(trace["probe_id"], h["hop"], address, hostname, location.city, rtt, floor_ms, verdict)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/analysis/test_router_location.py -q && uv run ruff check src/pacific_peering/analysis/router_location.py tests/analysis/test_router_location.py`
Expected: `9 passed`; `All checks passed!`. If `test_tata_los_angeles_on_mp_to_to_is_a_hub` reports a floor other than 94.63, stop and compare with `uv run python -c "from pacific_peering.analysis.feasibility import *; from pacific_peering.discovery.economy_coordinates import *; print(round(min_feasible_rtt_ms(great_circle_km(*ECONOMY_LATLON['MP'], *EXTERNAL_HUB_LATLON['Los Angeles']) - ECONOMY_SPREAD_KM['MP']), 2))"`. Don't edit the expected value to match without finding out why.

- [ ] **Step 5: Full suite, commit, push**

```bash
uv run pytest -q
git add src/pacific_peering/analysis/router_location.py tests/analysis/test_router_location.py
git commit -m "feat(analysis): locate off-region routers by hostname, checked against the fibre floor

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 2: Report-only corpus sweep (owner checkpoint follows)

**Files:**
- Create: `src/pacific_peering/analysis/router_detour_sweep.py`
- Modify: `pyproject.toml` (`[project.scripts]`, next to `pacific-peering-feasibility-sweep`)
- Test: `tests/analysis/test_router_detour_sweep.py`

**Interfaces:**
- Consumes: `router_location.find_router_hub`, `RouterHub`, `reverse_dns`; `store.connect`; `ixp_lan_registry.load_ixp_lan_registry` (entries have `.prefixes: tuple[str, ...]`, `.in_fishbowl: bool | str`).
- Produces: `off_region_ixp_networks(registry) -> list[ipaddress._BaseNetwork]`, `sweep(conn, parsed_dir, networks, resolver) -> list[dict]`, `render(rows: list[dict]) -> str`, `main() -> None`; console script `pacific-peering-router-detour-sweep`.

- [ ] **Step 1: Write the failing test**

```python
"""router_detour_sweep: report-only, lists findings the router-location rule would reclassify."""

from __future__ import annotations

import json

from pacific_peering.analysis import router_detour_sweep as sweep_mod
from pacific_peering.analysis import store

TATA_LA = "ix-xe-2-1-4-0.tcore2.lvw-losangeles.as6453.net"


def _trace(probe_id, hops):
    return {"measurement_id": 221439393, "probe_id": probe_id, "target": "202.43.12.1",
            "hops": [{"hop": h, "addresses": [a], "min_rtt_ms": r} for h, a, r in hops]}


def test_sweep_lists_local_transit_backed_by_an_la_router(tmp_path):
    conn = store.connect(tmp_path / "f.db")
    fid = store.create_finding(conn, kind=store.KIND_CONFIRMED_LOCAL_TRANSIT, source_cc="FJ", source_asn=45355,
                               target_cc="TO", target_asn=38198)
    store.add_corroboration(conn, finding_id=fid, measurement_id=221439393, vantage_point_cc="MP")
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    (parsed / "221439393.json").write_text(json.dumps([
        _trace(65653, [(8, "64.86.252.73", 121.458), (18, "202.43.12.5", 212.954)]),
    ]))

    rows = sweep_mod.sweep(conn, parsed, [], {"64.86.252.73": TATA_LA}.get)

    assert len(rows) == 1
    row = rows[0]
    assert (row["finding_id"], row["kind"], row["measurement_id"], row["probe_id"]) == (
        fid, "confirmed_local_transit", 221439393, 65653)
    assert row["city"] == "Los Angeles" and row["verdict"] == "ok"
    text = sweep_mod.render(rows)
    assert f"#{fid}" in text and "lvw-losangeles" in text


def test_sweep_skips_traces_that_cross_an_off_region_ixp(tmp_path):
    import ipaddress

    conn = store.connect(tmp_path / "f.db")
    fid = store.create_finding(conn, kind=store.KIND_CONFIRMED_LOCAL_TRANSIT, source_cc="FJ", source_asn=45355,
                               target_cc="TO", target_asn=38198)
    store.add_corroboration(conn, finding_id=fid, measurement_id=221439393, vantage_point_cc="MP")
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    (parsed / "221439393.json").write_text(json.dumps([
        _trace(65653, [(6, "45.127.172.46", 60.0), (8, "64.86.252.73", 121.458)]),
    ]))

    rows = sweep_mod.sweep(conn, parsed, [ipaddress.ip_network("45.127.172.0/22")], {"64.86.252.73": TATA_LA}.get)

    assert rows == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/analysis/test_router_detour_sweep.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'pacific_peering.analysis.router_detour_sweep'`.

- [ ] **Step 3: Write the sweep**

```python
"""Report-only sweep: which existing findings would the router-location detour rule have read differently?

Per the project owner's precedent for Validation Rule 2 (2026-09-29, see
`feasibility_sweep.py`): run a new classification rule over the corpus once and
read the results before wiring it into nightly classification. Changes nothing
in the findings store; writes `outputs/reports/router_detour_sweep.txt`.

For every corroboration with a measurement, each parsed trace that does not
already cross an off-region IXP is checked with `router_location.find_router_hub`,
using the corroboration's `vantage_point_cc` as the source economy (a label --
`auto_classify._original_vantage` exists because labels have been wrong). PTR
lookups are live and cached for the run.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import sqlite3
from collections import Counter
from pathlib import Path

from pacific_peering.analysis import store as _store
from pacific_peering.analysis.feasibility import DEFAULT_ATLAS_PARSED_DIR
from pacific_peering.analysis.ixp_lan_registry import load_ixp_lan_registry
from pacific_peering.analysis.router_location import PtrResolver, find_router_hub, reverse_dns

logger = logging.getLogger(__name__)

REPORT_PATH = Path("outputs/reports/router_detour_sweep.txt")


def off_region_ixp_networks(registry: dict) -> list:
    """LAN prefixes of every exchange classified out-of-fishbowl (in_fishbowl is False, never "TBA")."""
    return [ipaddress.ip_network(p) for e in registry.values() if e.in_fishbowl is False for p in e.prefixes]


def _crosses(trace: dict, networks: list) -> bool:
    for h in trace.get("hops", []):
        for a in h.get("addresses", []):
            try:
                ip = ipaddress.ip_address(a)
            except ValueError:
                continue
            if any(ip.version == n.version and ip in n for n in networks):
                return True
    return False


def sweep(conn: sqlite3.Connection, parsed_dir: Path, networks: list, resolver: PtrResolver) -> list[dict]:
    rows = conn.execute(
        "SELECT f.id, f.kind, c.measurement_id, c.vantage_point_cc FROM corroborations c "
        "JOIN findings f ON f.id = c.finding_id WHERE c.measurement_id IS NOT NULL ORDER BY f.id, c.measurement_id"
    ).fetchall()
    out: list[dict] = []
    seen: set[tuple[int, int, int]] = set()
    for finding_id, kind, measurement_id, source_cc in rows:
        path = parsed_dir / f"{measurement_id}.json"
        if not path.exists():
            continue
        for trace in json.loads(path.read_text()):
            key = (finding_id, measurement_id, trace["probe_id"])
            if key in seen or _crosses(trace, networks):
                continue
            seen.add(key)
            hub = find_router_hub(trace, source_cc, resolver)
            if hub is None:
                continue
            out.append({
                "finding_id": finding_id, "kind": kind, "measurement_id": measurement_id,
                "probe_id": trace["probe_id"], "source_cc": source_cc, "city": hub.city,
                "verdict": hub.verdict, "note": hub.note(),
            })
    return out


def render(rows: list[dict]) -> str:
    by_kind = Counter(r["kind"] for r in {r["finding_id"]: r for r in rows}.values())
    lines = [
        "Router-location detour sweep (report-only; nothing in findings.db changed)",
        "",
        "Findings with at least one trace through a hostname-located off-region router and no off-region IXP:",
        *(f"  {kind}: {n}" for kind, n in sorted(by_kind.items())),
        "",
    ]
    for r in rows:
        if r["kind"] == _store.KIND_CONFIRMED_DETOUR:
            continue
        lines.append(f"#{r['finding_id']} {r['kind']} msm {r['measurement_id']} probe {r['probe_id']} "
                     f"(from {r['source_cc']}): {r['note']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    conn = _store.connect()
    try:
        rows = sweep(conn, DEFAULT_ATLAS_PARSED_DIR, off_region_ixp_networks(load_ixp_lan_registry()), reverse_dns)
    finally:
        conn.close()
    REPORT_PATH.write_text(render(rows))
    logger.info("Wrote %s (%d trace rows)", REPORT_PATH, len(rows))


if __name__ == "__main__":
    main()
```

Add to `pyproject.toml` under `[project.scripts]`, directly below `pacific-peering-feasibility-sweep`:

```toml
pacific-peering-router-detour-sweep = "pacific_peering.analysis.router_detour_sweep:main"
```

- [ ] **Step 4: Run tests, then the sweep for real**

Run: `uv run pytest tests/analysis/test_router_detour_sweep.py -q && uv run ruff check src/pacific_peering/analysis/router_detour_sweep.py`
Expected: `2 passed`; `All checks passed!`

Run: `uv sync -q && uv run pacific-peering-router-detour-sweep && head -12 outputs/reports/router_detour_sweep.txt`
Expected: about the 2026-10-12 one-off numbers, with `candidate_peering` around 6, `confirmed_detour` around 64 and `confirmed_local_transit` around 11. They can differ a little, because this sweep uses vantage labels and the fibre-floor verdict, which the one-off didn't. #295 must appear with `lvw-losangeles`. A different order of magnitude means something is wrong: stop and investigate.

- [ ] **Step 5: Commit, push, and STOP for the owner**

```bash
uv run pytest -q
git add src/pacific_peering/analysis/router_detour_sweep.py tests/analysis/test_router_detour_sweep.py pyproject.toml uv.lock outputs/reports/router_detour_sweep.txt
git commit -m "feat(analysis): report-only sweep for the router-location detour rule

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

**Checkpoint:** give the owner the report's summary, every `too_fast` and `unmapped` row, and the non-detour findings listed. Wait for an explicit go-ahead before Task 3. The owner may decide to add hub coordinates (San Francisco), to change the rule, or to stop here.

---

### Task 3: Feasibility check accepts a router hop as the hub hop

**Files:**
- Modify: `src/pacific_peering/analysis/feasibility.py` (`check_detour_trace`, ~lines 139–199)
- Test: `tests/analysis/test_feasibility_detour.py` (append)

**Interfaces:**
- Consumes: nothing new.
- Produces: `check_detour_trace(..., source_spread_km=0.0, target_spread_km=0.0, router_hub_hop: int | None = None) -> dict`. When `router_hub_hop` is given it replaces the IXP-derived hub hop, so `claim_probes` treats that probe as having crossed the hub.

- [ ] **Step 1: Write the failing tests (append to `tests/analysis/test_feasibility_detour.py`)**

```python
SAIPAN, LOS_ANGELES, NUKUALOFA = (15.1780, 145.7500), (34.0522, -118.2437), (-21.1789, -175.1982)


def _router_trace(probe_id, hops, target="202.43.12.1"):
    return {"probe_id": probe_id, "target": target,
            "hops": [{"hop": h, "min_rtt_ms": rtt, "addresses": [a]} for h, rtt, a in hops]}


def test_router_hub_hop_stands_in_for_an_ixp_hop():
    # 221439393 probe 65653: Tata Los Angeles router at hop 8, no IXP anywhere on the path.
    trace = _router_trace(65653, [(8, 121.458, "64.86.252.73"), (18, 212.954, "202.43.12.5")])
    c = fz.check_detour_trace(trace, [], SAIPAN, LOS_ANGELES, "Los Angeles", NUKUALOFA, {}, 150.0, 650.0,
                              router_hub_hop=8)
    assert c["hub"]["hop"] == 8 and c["hub"]["verdict"] == fz.VERDICT_OK
    assert c["target_via_hub"]["verdict"] == fz.VERDICT_NO_HOP  # 202.43.12.1 never answered


def test_too_fast_router_hub_hop_is_impossible():
    trace = _router_trace(65653, [(4, 8.166, "103.57.234.108")])
    c = fz.check_detour_trace(trace, [], SAIPAN, LOS_ANGELES, "Los Angeles", NUKUALOFA, {}, 150.0, 650.0,
                              router_hub_hop=4)
    assert c["hub"]["verdict"] == fz.VERDICT_IMPOSSIBLE


def test_claim_rests_on_router_hub_probes_only():
    # A country-sourced measurement: one probe via LA, one straight to the target at 40ms.
    via_la = fz.check_detour_trace(
        _router_trace(1, [(8, 121.458, "64.86.252.73")]), [], SAIPAN, LOS_ANGELES, "Los Angeles",
        NUKUALOFA, {}, 150.0, 650.0, router_hub_hop=8)
    direct = fz.check_detour_trace(
        _router_trace(2, [(5, 40.0, "202.43.12.1")]), [], SAIPAN, LOS_ANGELES, "Los Angeles",
        NUKUALOFA, {}, 150.0, 650.0)
    assert [c["probe_id"] for c in fz.claim_probes([via_la, direct])] == [1]
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/analysis/test_feasibility_detour.py -q`
Expected: 3 FAIL with `TypeError: check_detour_trace() got an unexpected keyword argument 'router_hub_hop'`. The existing tests still pass.

- [ ] **Step 3: Implement**

In `check_detour_trace`, add the parameter after `target_spread_km: float = 0.0,`:

```python
    router_hub_hop: int | None = None,
```

Replace the `hub_hop = next(...)` assignment with:

```python
    hub_hop = router_hub_hop if router_hub_hop is not None else next(
        (h.hop for h in resolved_hops
         if h.ixp_context is not None and ix_city.get(h.ixp_context.get("ix_id")) == hub_city),
        None,
    )
```

Append this paragraph to the docstring, before the `resolved_hops` sentence:

```
    `router_hub_hop` is a hop already placed in `hub_city` by its own hostname
    (`router_location`, 2026-10-12): it stands in for the IXP-LAN hop on a
    detour that crossed no exchange, and gets the same hub floor.
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/analysis/test_feasibility_detour.py -q && uv run ruff check src/pacific_peering/analysis/feasibility.py`
Expected: all pass; `All checks passed!`

- [ ] **Step 5: Commit, push**

```bash
uv run pytest -q
git add src/pacific_peering/analysis/feasibility.py tests/analysis/test_feasibility_detour.py
git commit -m "feat(feasibility): accept a hostname-located router hop as the detour hub hop

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```


#### Task 3, part B: cap each reverse-DNS lookup at 2 seconds (owner, 2026-10-12 checkpoint)

Added at the post-Task-2 checkpoint. `socket.gethostbyaddr` has no timeout, and
an address with no reverse zone holds it for the resolver's whole retry cycle:
the Task 2 sweep spent about 13 minutes on ~800 serial lookups (0.26 s with a
cache). Task 4 puts these lookups inside the nightly 2-hour batch, so the cap
lands first. A lookup that doesn't answer within the cap counts as no PTR.

**Files:**
- Modify: `src/pacific_peering/analysis/router_location.py` (`reverse_dns`, imports, one constant)
- Test: `tests/analysis/test_router_location.py` (append)

**Interfaces:**
- Produces: `PTR_TIMEOUT_S: float = 2.0` (module constant, read at call time); `reverse_dns(address) -> str | None` keeps its signature and `lru_cache`.

- [ ] **Step B1: Write the failing tests (append to `tests/analysis/test_router_location.py`; add `import threading` and `import time` to its imports)**

```python
def test_reverse_dns_returns_the_ptr_name(monkeypatch):
    rl.reverse_dns.cache_clear()
    monkeypatch.setattr(rl.socket, "gethostbyaddr", lambda address: (TATA_LA, [], [address]))
    try:
        assert rl.reverse_dns("64.86.252.73") == TATA_LA
    finally:
        rl.reverse_dns.cache_clear()


def test_reverse_dns_gives_up_after_the_cap(monkeypatch):
    release = threading.Event()

    def _hang(address):
        release.wait(5)
        return ("late.example.net", [], [address])

    rl.reverse_dns.cache_clear()
    monkeypatch.setattr(rl, "PTR_TIMEOUT_S", 0.05)
    monkeypatch.setattr(rl.socket, "gethostbyaddr", _hang)
    start = time.monotonic()
    try:
        assert rl.reverse_dns("192.0.2.2") is None
        assert time.monotonic() - start < 1.0
    finally:
        release.set()
        rl.reverse_dns.cache_clear()
```

- [ ] **Step B2: Run to verify the cap test fails**

Run: `uv run pytest tests/analysis/test_router_location.py -q`
Expected: `test_reverse_dns_gives_up_after_the_cap` FAILS (`AttributeError: ... has no attribute 'PTR_TIMEOUT_S'`); the other tests pass.

- [ ] **Step B3: Implement**

Add `import threading` to `router_location.py`'s standard-library imports. Add this constant after the `PtrResolver` alias:

```python
PTR_TIMEOUT_S = 2.0
"""Longest one PTR lookup may take before it counts as no PTR (2026-10-12: an
uncapped serial sweep of ~800 hops took ~13 minutes, mostly addresses with no
reverse zone running out the resolver's retries)."""
```

Replace `reverse_dns` with:

```python
@functools.lru_cache(maxsize=4096)
def reverse_dns(address: str) -> str | None:
    """PTR lookup capped at `PTR_TIMEOUT_S`; None on failure or timeout.

    Cached: a nightly batch meets the same backbone routers again and again.
    `gethostbyaddr` has no timeout of its own, so it runs on a daemon thread
    that is abandoned (never joined again) once the cap passes; a daemon
    thread can't hold the batch open at exit, and a pool would queue new
    lookups behind hung ones.
    """
    found: list[str] = []

    def _lookup() -> None:
        try:
            found.append(socket.gethostbyaddr(address)[0])
        except OSError:
            pass

    worker = threading.Thread(target=_lookup, name=f"ptr-{address}", daemon=True)
    worker.start()
    worker.join(PTR_TIMEOUT_S)
    return found[0] if found else None
```

- [ ] **Step B4: Run tests**

Run: `uv run pytest tests/analysis/test_router_location.py -q && uv run ruff check src/pacific_peering/analysis/router_location.py tests/analysis/test_router_location.py`
Expected: `11 passed`; `All checks passed!`

- [ ] **Step B5: Commit**

```bash
uv run pytest -q
git add src/pacific_peering/analysis/router_location.py tests/analysis/test_router_location.py
git commit -m "fix(analysis): cap each reverse-DNS lookup at 2 seconds

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Wire the router hub into `classify_corridor`

**Files:**
- Modify: `src/pacific_peering/analysis/auto_classify.py`
- Test: `tests/analysis/test_router_detour.py`
- Modify: `CHANGELOG.md`, `task_plan.md`

**Interfaces:**
- Consumes: `router_location.find_router_hub`, `reverse_dns`, `RouterHub`, `HUB_OK`, `HUB_TOO_FAST`; `check_detour_trace(..., router_hub_hop=)` from Task 3.
- Produces: `_detour_feasibility(candidate, measurement_id, clean_probe_ids, hub_city, ix_city, router_hub_hops: dict[int, int] | None = None)`; `_corroborate(conn, finding_id, probes, notes: dict[int, str] | None = None)`; escalation reasons `"router hostname location physically impossible"` and `"router in a hub city with no coordinates"`.

- [ ] **Step 1: Write the failing tests**

The fixture below was run against the pre-change code on 2026-10-12 and returned `confirmed_local_transit` with no escalations, so `test_router_hub_files_a_detour_via_los_angeles` fails for the right reason.

```python
"""classify_corridor files a detour via a hostname-located router when no IXP is crossed.

Real shape: 221439393 (MP -> TO, reverification of #92, 2026-10-11). Saipan
probe 65653 went AS7131 -> Tata LA (121ms) -> Telstra Global -> Digicel Fiji
-> Digicel Tonga with no IXP crossing; the IXP-only rule filed #295 (local
transit, Digicel Fiji -> Digicel Tonga) and left #92 uncorroborated.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from pacific_peering.analysis import auto_classify, store
from pacific_peering.analysis.corridor_backlog import CorridorCandidate
from pacific_peering.analysis.ixp_lan_registry import IxpLanEntry

MSM = 900000002
TATA_LA = "ix-xe-2-1-4-0.tcore2.lvw-losangeles.as6453.net"
HOPS = [
    {"hop": 1, "addresses": ["192.168.1.1"], "min_rtt_ms": 1.416},
    {"hop": 4, "addresses": ["103.57.234.108"], "min_rtt_ms": 8.166},
    {"hop": 8, "addresses": ["64.86.252.73"], "min_rtt_ms": 121.458},
    {"hop": 12, "addresses": ["202.84.143.25"], "min_rtt_ms": 167.759},
    {"hop": 16, "addresses": ["202.129.231.109"], "min_rtt_ms": 206.569},
    {"hop": 18, "addresses": ["202.43.12.5"], "min_rtt_ms": 212.954},
]


def _triangulation(ixp_crossings=()):
    return {"measurement_id": MSM, "target_asn": 38198, "probes": [{
        "probe_id": 65653,
        "as_sequence": [{"asn": a, "resolution_source": "ris", "contiguous_with_previous": True}
                        for a in (7131, 6453, 4637, 45355, 38198)],
        "ixp_crossings": list(ixp_crossings), "traceroute_upstream_asn": 45355, "ris_agrees": True,
        "contiguous": True, "ris_observation_count": 1321}]}


def _candidate(reverify_finding_id=None):
    return CorridorCandidate(source_asn=7131, source_cc="MP", source_name="PTI Pacifica Inc.", target_asn=38198,
                             target_cc="TO", target_name="Digicel Tonga Ltd", rationale="test",
                             reverify_finding_id=reverify_finding_id)


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Everything classify_corridor touches, pointed at tmp_path and stubbed off the network."""
    state = {"ptr": {}, "ptr_calls": [], "registry": {}, "triangulation": _triangulation()}
    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {7131: "MP", 45355: "FJ", 38198: "TO"})
    monkeypatch.setattr(auto_classify, "load_ixp_lan_registry", lambda path: state["registry"])
    monkeypatch.setattr(auto_classify, "list_target_ips", lambda asn: ["202.43.12.1"])
    monkeypatch.setattr(auto_classify, "_fire_measurement", lambda c, ip: MSM)
    monkeypatch.setattr(auto_classify, "analyze_measurement", lambda mid, target_asn: state["triangulation"])
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_PARSED_DIR", tmp_path)
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_RAW_DIR", tmp_path / "raw")
    (tmp_path / f"{MSM}.json").write_text(json.dumps(
        [{"measurement_id": MSM, "probe_id": 65653, "target": "202.43.12.1", "hops": HOPS}]))
    monkeypatch.setattr(auto_classify, "fetch_measurement_status", lambda mid: "Stopped")
    monkeypatch.setattr(auto_classify, "mark_corridor_tested", lambda s, t: None)
    monkeypatch.setattr(auto_classify, "_write_escalations", lambda e: None)
    monkeypatch.setattr(auto_classify, "_asn_holder_name", lambda asn, cache: f"AS{asn}")
    monkeypatch.setattr(auto_classify, "_load_listing_or_empty", lambda: {})
    monkeypatch.setattr(auto_classify, "resolve_traceroute_hops", lambda hops, persist=False: [])

    def _ptr(address):
        state["ptr_calls"].append(address)
        return state["ptr"].get(address)

    monkeypatch.setattr(auto_classify, "reverse_dns", _ptr)
    db = tmp_path / "findings.db"
    monkeypatch.setattr(auto_classify._store, "connect", lambda db_path=None: _open(db))
    state["db"] = lambda: _open(db)
    return state


def _open(db):
    # tests/conftest.py replaces store.connect with a blocker before this module's fixtures
    # run, so open the tmp DB the way store.connect does instead of capturing it.
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(store._SCHEMA)
    return conn


def _rows(env, sql):
    conn = env["db"]()
    try:
        return [tuple(r) for r in conn.execute(sql).fetchall()]
    finally:
        conn.close()


def test_router_hub_files_a_detour_via_los_angeles(env):
    env["ptr"] = {"64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_detour"
    assert _rows(env, "SELECT kind, source_cc, target_asn, detour_hub, detour_ix_name FROM findings") == [
        ("confirmed_detour", "MP", 38198, "Los Angeles", f"{TATA_LA} (router in Los Angeles, no IXP crossing)")]
    (note,) = _rows(env, "SELECT note_extra FROM corroborations")[0]
    assert "hop 8 64.86.252.73" in note and "121.458ms" in note and "floor 94.63ms" in note


def test_reverification_corroborates_the_existing_detour(env):
    conn = env["db"]()
    fid = store.create_finding(conn, kind=store.KIND_CONFIRMED_DETOUR, source_cc="MP", source_asn=7131,
                               target_cc="TO", target_asn=38198, detour_hub="Sydney",
                               detour_ix_name="AS6939 + AS132528 -- international transit")
    conn.close()
    env["ptr"] = {"64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(_candidate(reverify_finding_id=fid), regenerate=False)
    assert (result.outcome, result.finding_id) == ("confirmed_detour", fid)
    assert _rows(env, "SELECT id, detour_hub FROM findings") == [(fid, "Sydney")]  # hub not overwritten
    assert _rows(env, "SELECT finding_id FROM corroborations") == [(fid,)]


def test_too_fast_hostname_escalates_and_keeps_local_transit(env):
    env["ptr"] = {"103.57.234.108": "be1.ccr41.lax01.atlas.cogentco.com", "64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_local_transit"
    assert [e.reason for e in result.escalations] == ["router hostname location physically impossible"]
    assert "hop 4 103.57.234.108" in result.escalations[0].detail


def test_unmapped_city_escalates(env):
    env["ptr"] = {"64.86.252.73": "be5991.ccr22.sfo01.atlas.cogentco.com"}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_local_transit"
    assert [e.reason for e in result.escalations] == ["router in a hub city with no coordinates"]
    assert "sfo01" in result.escalations[0].detail


def test_no_ptr_records_leaves_local_transit(env):
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert (result.outcome, result.escalations) == ("confirmed_local_transit", [])


def test_ixp_detour_takes_precedence(env):
    env["registry"] = {94: IxpLanEntry(ix_id=94, name="Equinix Sydney", city="Sydney", country="AU",
                                       in_fishbowl=False, prefixes=("45.127.172.0/22",))}
    env["triangulation"] = _triangulation([{"ix_id": 94, "name": "Equinix Sydney", "in_fishbowl": False,
                                            "hop": 6, "min_rtt_ms": 60.0}])
    env["ptr"] = {"64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_detour"
    assert _rows(env, "SELECT detour_hub, detour_ix_name FROM findings") == [("Sydney", "Equinix Sydney")]
    assert env["ptr_calls"] == []
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/analysis/test_router_detour.py -q`
Expected: the `env` fixture errors with `AttributeError: <module 'pacific_peering.analysis.auto_classify'> does not have the attribute 'reverse_dns'`, so all six tests ERROR. That's the missing import. If `IxpLanEntry(...)` raises a `TypeError` instead, check its field list at `ixp_lan_registry.py:47` and fix the test, not the dataclass.

- [ ] **Step 3: Implement in `auto_classify.py`**

3a. Imports, next to the other `pacific_peering.analysis` imports:

```python
from pacific_peering.analysis.router_location import HUB_OK, HUB_TOO_FAST, RouterHub, find_router_hub, reverse_dns
```

3b. Module docstring, rule 2: append after "`"TBA"` exchanges and unmapped hubs escalate instead of guessing.":

```
   No IXP crossing, but a router whose own hostname places it in an
   off-region hub city (`router_location.find_router_hub`, added 2026-10-12
   after 221439393 left MP for Tonga via Tata Los Angeles over private
   interconnects) is a Confirmed Detour too, provided the hop's RTT clears
   the fibre floor from the source to that city. A hostname that answers too
   fast for its city, or names a city with no hub coordinates, escalates.
```

3c. `_detour_feasibility`: add the parameter `router_hub_hops: dict[int, int] | None = None` after `ix_city`, and pass it per trace in the `check_detour_trace(...)` call:

```python
                ECONOMY_SPREAD_KM.get(candidate.source_cc, 0.0), ECONOMY_SPREAD_KM.get(candidate.target_cc, 0.0),
                router_hub_hop=(router_hub_hops or {}).get(t["probe_id"]),
```

3d. In `classify_corridor`, directly after the `for probe in clean_probes:` loop ends (just before `if tba_ixp_hit and detour_pick is None:`):

```python
    # Rule 2, no IXP crossed: a router placed off-region by its own hostname.
    router_hubs: dict[int, RouterHub] = {}
    if detour_pick is None:
        for probe in clean_probes:
            trace = {"probe_id": probe["probe_id"], "hops": hops_by_probe.get(probe["probe_id"], [])}
            hub = find_router_hub(trace, candidate.source_cc, resolver=reverse_dns)
            if hub is not None:
                router_hubs[probe["probe_id"]] = hub
        ok = [h for h in router_hubs.values() if h.verdict == HUB_OK]
        if ok:
            detour_pick = (None, f"{ok[0].hostname} (router in {ok[0].city}, no IXP crossing)", ok[0].city)
        for hub in router_hubs.values():
            if hub.verdict == HUB_OK:
                continue
            escalations.append(_Escalation(
                candidate=candidate,
                measurement_id=measurement_id,
                reason=(
                    "router hostname location physically impossible" if hub.verdict == HUB_TOO_FAST
                    else "router in a hub city with no coordinates"
                ),
                detail=f"probe {hub.probe_id}: {hub.note()}",
            ))
```

`detour_pick[0]` (the IXP crossing dict) is never read. `_finalize` unpacks it as `_`, and everything else uses `detour_pick[2]`, so `None` there is safe. Check with `grep -n "detour_pick\[" src/pacific_peering/analysis/auto_classify.py`: only `[2]` should appear.

3e. Pass the router hops into the feasibility call (the `if detour_pick is not None:` block):

```python
        feasibility = _detour_feasibility(
            candidate, measurement_id, {p["probe_id"] for p in clean_probes}, detour_pick[2],
            {ix_id: e.city for ix_id, e in ixp_registry.items()},
            {pid: h.hop for pid, h in router_hubs.items() if h.verdict == HUB_OK},
        )
```

3f. `_corroborate`: add `notes: dict[int, str] | None = None` to its signature, and pass `note_extra=(notes or {}).get(probe["probe_id"]),` to `_store.add_corroboration`. In `_finalize`'s detour branch, change `_corroborate(conn, finding_id, clean_probes)` to:

```python
                _corroborate(conn, finding_id, clean_probes, {pid: h.note() for pid, h in router_hubs.items()})
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/analysis/test_router_detour.py -q && uv run pytest -q && uv run ruff check src tests`
Expected: `6 passed`; the full suite passes (259 after Task 1, plus 2 + 3 + 2 + 6 = 272); `All checks passed!`

- [ ] **Step 5: Docs**

Append to `CHANGELOG.md`:

```
- Detours with no IXP crossing (2026-10-12, owner): `classify_corridor` now
  files a confirmed detour when a probe passes a router whose hostname places
  it in an off-region hub city (`analysis/router_location.py`, via
  `hop_geolocation`'s curated patterns) and whose RTT clears the fibre floor
  from the source to that city. Prompted by 221439393 (MP -> TO via Tata Los
  Angeles), which the IXP-only rule filed as local transit (#295). Too-fast
  hostnames and cities with no hub coordinates escalate. The IXP rule still
  takes precedence; existing findings are untouched (see
  `outputs/reports/router_detour_sweep.txt`).
```

Add a dated entry to `task_plan.md` that records what was implemented, the sweep numbers and the owner's checkpoint decision, plus the Known limitation above (local-transit edges stop being corroborated on corridors that now classify as detours).

- [ ] **Step 6: Commit, push**

```bash
git add src/pacific_peering/analysis/auto_classify.py tests/analysis/test_router_detour.py CHANGELOG.md task_plan.md
git commit -m "feat(analysis): file detours via hostname-located off-region routers when no IXP is crossed

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

Then confirm the next nightly run: `grep -E "router hub|router in a hub city|physically impossible|confirmed_detour" logs/cron.log | tail`.
