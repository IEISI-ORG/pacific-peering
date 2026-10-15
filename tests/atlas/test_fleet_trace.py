"""Tests for queued fleet traceroutes (atlas/fleet_trace.py)."""

from __future__ import annotations

from datetime import datetime, timezone

import requests

from pacific_peering.atlas import fleet_trace

NOW = datetime(2026, 10, 16, 15, 0, tzinfo=timezone.utc)

LISTING = {
    "FJ": [{"id": 60575, "status": "Connected", "asn_v4": 141695},
           {"id": 64, "status": "Abandoned", "asn_v4": None}],
    "TV": [{"id": 7588, "status": "Connected", "asn_v4": 23917}],
    "GU": [{"id": 23039, "status": "Connected", "asn_v4": 17456}],
}

TRACES = [
    {"probe_id": 60575, "target": "103.99.43.254",
     "hops": [{"hop": 1, "addresses": ["192.168.3.37"], "min_rtt_ms": 0.8},
              {"hop": 9, "addresses": ["103.99.43.254"], "min_rtt_ms": 80.1}]},
    {"probe_id": 7588, "target": "103.99.43.254",
     "hops": [{"hop": 1, "addresses": ["202.2.120.34"], "min_rtt_ms": 0.4},
              {"hop": 2, "addresses": [], "min_rtt_ms": None}]},
]


def test_enqueue_is_idempotent_per_target(tmp_path):
    path = tmp_path / "queue.json"
    fleet_trace.enqueue("103.99.43.254", 136921, "FNU retest", path)
    queue = fleet_trace.enqueue("103.99.43.254", 136921, "again", path)

    assert [e["reason"] for e in queue] == ["FNU retest"]


def test_connected_probes_skip_other_statuses():
    assert fleet_trace.connected_probes(LISTING) == {
        60575: ("FJ", 141695), 7588: ("TV", 23917), 23039: ("GU", 17456)}


def test_section_reports_reached_dark_and_missing():
    entry = {"target_ip": "103.99.43.254", "target_asn": 136921, "reason": "FNU retest"}
    section = fleet_trace.render_section(entry, 1, fleet_trace.connected_probes(LISTING), TRACES, NOW)

    assert "3 probes, 2 reported, 1 reached the target" in section
    assert "reached 80.1 ms (hop 9)" in section
    assert "dark after 202.2.120.34 (0.4 ms, hop 1)" in section
    assert "23039  AS17456    no result" in section


def test_run_queued_drains_fired_targets_and_keeps_refused_ones(tmp_path, monkeypatch):
    queue_path, report_path = tmp_path / "queue.json", tmp_path / "fleet_traces.txt"
    fleet_trace.enqueue("103.99.43.254", 136921, "FNU retest", queue_path)
    fleet_trace.enqueue("144.120.146.2", 24390, "USP retest", queue_path)
    monkeypatch.setattr(fleet_trace, "load_probe_listing", lambda: LISTING)
    monkeypatch.setattr(fleet_trace, "refetch_parsed", lambda ids: TRACES)

    def fake_fire(source_type, probe_value, target_ip, description, probe_count):
        assert source_type == "probes" and probe_value == "7588,23039,60575" and probe_count == 3
        assert len(description) < 255
        if target_ip == "144.120.146.2":
            raise requests.HTTPError("refused")
        return 42

    monkeypatch.setattr(fleet_trace, "_fire_and_persist", fake_fire)

    assert fleet_trace.run_queued(queue_path, report_path, NOW) == [42]
    assert [e["target_ip"] for e in fleet_trace.load_queue(queue_path)] == ["144.120.146.2"]
    assert report_path.read_text().startswith("== 103.99.43.254 (AS136921) -- 2026-10-16, measurement 42")


def test_run_queued_with_empty_queue_fires_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(fleet_trace, "_fire_and_persist", lambda *a: (_ for _ in ()).throw(AssertionError))
    assert fleet_trace.run_queued(tmp_path / "queue.json", tmp_path / "r.txt", NOW) == []
