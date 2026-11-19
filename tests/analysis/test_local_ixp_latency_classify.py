"""The local-IXP latency check as wired into `classify_corridor`, and its escalation text.

Code review of fbbb5e8 (2026-11-19): the only classify-level test with an
in-fishbowl crossing used a 1ms crossing, so the flag path and the detail
string were never exercised end to end. Fixture: 235633070, probe 7018
(NC AS45345 -> FJ AS4638), TFL AS45349's Fiji-IXP port .30 at 39.157ms after
FINTEL's 16.007ms cable hop; excess 22.5ms against a 14.0ms allowance.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from pacific_peering.analysis import auto_classify
from pacific_peering.analysis import store as _store
from pacific_peering.analysis.corridor_backlog import CorridorCandidate
from pacific_peering.analysis.ixp_lan_registry import IxpLanEntry

_MEASUREMENT_ID = 900000077
_FIJI_IXP = IxpLanEntry(
    ix_id=3085, name="Fiji-IXP", city="Suva", country="FJ", in_fishbowl=True, prefixes=("103.147.194.0/24",),
)
_HOPS_7018 = [
    {"hop": n, "addresses": [] if rtt is None else ["192.0.2.1"], "min_rtt_ms": rtt}
    for n, rtt in [(1, 0.432), (2, 0.436), (3, 1.414), (4, None), (5, None), (6, None),
                   (7, 16.007), (8, 39.157), (9, 38.52), (10, None), (11, 39.12)]
]


def _candidate() -> CorridorCandidate:
    return CorridorCandidate(
        source_asn=45345, source_cc="NC", source_name="OPT-NC",
        target_asn=4638, target_cc="FJ", target_name="TFL", rationale="test fixture",
    )


def _probe() -> dict:
    return {
        "probe_id": 7018,
        "as_sequence": [
            {"asn": 45345, "resolution_source": "bgp", "contiguous_with_previous": True},
            {"asn": 4638, "resolution_source": "bgp", "contiguous_with_previous": True},
        ],
        "ixp_crossings": [
            {"hop": 8, "member_asns": [45349], "min_rtt_ms": 39.157, "ix_id": 3085, "name": "Fiji-IXP",
             "in_fishbowl": True},
        ],
        "traceroute_upstream_asn": 45345,
        "ris_agrees": True,
        "contiguous": True,
        "ris_observation_count": 1,
    }


def _open(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_store._SCHEMA)
    return conn


def _latency_details(monkeypatch, tmp_path, parsed_hops: list[dict]) -> list[str]:
    db_path = tmp_path / "findings.db"
    monkeypatch.setattr(_store, "connect", lambda: _open(db_path))
    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {45345: "NC", 4638: "FJ", 45349: "FJ"})
    monkeypatch.setattr(auto_classify, "load_ixp_lan_registry", lambda path: {3085: _FIJI_IXP})
    monkeypatch.setattr(auto_classify, "list_target_ips", lambda asn: ["202.62.0.1"])
    monkeypatch.setattr(auto_classify, "_fire_measurement", lambda candidate, ip: _MEASUREMENT_ID)
    monkeypatch.setattr(
        auto_classify, "analyze_measurement",
        lambda mid, target_asn: {"measurement_id": mid, "target_asn": target_asn, "probes": [_probe()]},
    )
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_PARSED_DIR", tmp_path)
    (tmp_path / f"{_MEASUREMENT_ID}.json").write_text(json.dumps([{"probe_id": 7018, "hops": parsed_hops}]))
    monkeypatch.setattr(
        auto_classify, "load_probe_listing",
        lambda: {"NC": [{"id": 7018, "status": "Connected", "asn_v4": 45345}]},
    )
    monkeypatch.setattr(auto_classify, "fetch_asn_names", lambda asns: {})
    monkeypatch.setattr(auto_classify, "mark_corridor_tested", lambda *a: None)
    monkeypatch.setattr(auto_classify, "_write_escalations", lambda escalations: None)
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    return [e.detail for e in result.escalations if e.reason == "local IXP crossing with implausibly high latency"]


def test_the_tfl_crossing_escalates_with_its_allowance(monkeypatch, tmp_path):
    details = _latency_details(monkeypatch, tmp_path, _HOPS_7018)
    assert len(details) == 1
    assert "22.5ms more than the hop before it" in details[0]
    assert "above the 14.0ms allowed" in details[0]


def test_an_uncomputable_excess_does_not_claim_to_be_above_the_allowance(monkeypatch, tmp_path):
    # The probe's parsed hops are missing, so the excess can't be computed: the crossing still
    # escalates, but its own 39.157ms reply is not "above" anything it was compared with.
    details = _latency_details(monkeypatch, tmp_path, [])
    assert len(details) == 1
    assert "excess could not be computed" in details[0]
    assert "above the" not in details[0]
    assert "the allowance would be 30.0ms" in details[0]
