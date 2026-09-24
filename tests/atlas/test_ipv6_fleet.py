"""Tests for the weekly IPv6 fleet check (atlas/ipv6_fleet.py)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from pacific_peering.atlas import ipv6_fleet

NOW = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)

LISTING = {
    "NC": [
        {"id": 7018, "status": "Connected", "asn_v4": 45345, "asn_v6": 45345,
         "ipv6_tags": ["system-ipv6-capable", "system-ipv6-works"]},
        {"id": 63050, "status": "Connected", "asn_v4": 45345, "asn_v6": 45345,
         "ipv6_tags": ["system-ipv6-capable", "system-ipv6-doesnt-work"]},
        {"id": 99, "status": "Abandoned", "asn_v4": 45345, "asn_v6": 45345, "ipv6_tags": []},
    ],
    "KI": [{"id": 1008229, "status": "Connected", "asn_v4": 14593, "asn_v6": 14593,
            "ipv6_tags": ["system-ipv6-capable"]}],
    "MH": [{"id": 64237, "status": "Connected", "asn_v4": 14593, "asn_v6": None, "ipv6_tags": []}],
}


def _trace(probe_id, target, reached):
    hops = [{"hop": 1, "addresses": ["fe80::1"], "min_rtt_ms": 0.5}]
    if reached:
        hops.append({"hop": 2, "addresses": [target], "min_rtt_ms": 40.0})
    return {"probe_id": probe_id, "target": target, "hops": hops}


def test_ipv6_probes_are_connected_with_an_ipv6_asn_only():
    assert sorted(ipv6_fleet.ipv6_probes(LISTING)) == [7018, 63050, 1008229]


def test_economy_counts():
    counts = ipv6_fleet.economy_counts(LISTING)

    assert counts["NC"] == {"connected": 2, "ipv6_asn": 2, "ipv6_works_tag": 1}
    assert counts["MH"] == {"connected": 1, "ipv6_asn": 0, "ipv6_works_tag": 0}


def test_measured_access_reached_no_reach_and_no_result():
    traces = [
        _trace(7018, "2606:4700:4700::1111", reached=False),
        _trace(7018, "2001:4860:4860::8888", reached=True),  # one anchor is enough
        _trace(63050, "2606:4700:4700::1111", reached=False),
    ]

    access = ipv6_fleet.measured_access(traces, [7018, 63050, 1008229])

    assert access == {7018: "reached", 63050: "no_reach", 1008229: "no_result"}


def _snapshot(access):
    return ipv6_fleet.build_snapshot(LISTING, access, [1], NOW)


def test_diff_first_snapshot():
    assert ipv6_fleet.diff_snapshots(None, _snapshot({})) == ["First snapshot -- nothing to compare against."]


def test_diff_reports_access_change_new_probe_and_tag_flip():
    previous = _snapshot({7018: "no_reach", 63050: "no_reach"})
    del previous["probes"]["1008229"]
    current = _snapshot({7018: "reached", 63050: "no_reach", 1008229: "no_result"})
    current["probes"]["63050"]["ipv6_tags"] = ["system-ipv6-capable", "system-ipv6-works"]

    changes = ipv6_fleet.diff_snapshots(previous, current)

    assert "probe 1008229 (KI) gained an IPv6 ASN (AS14593)" in changes
    assert "probe 7018 (NC) measured access no_reach -> reached" in changes
    assert "probe 63050 (NC) Atlas tag system-ipv6-works added" in changes
    assert "probe 63050 (NC) Atlas tag system-ipv6-doesnt-work removed" in changes
    assert len(changes) == 4


def test_diff_ignores_not_measured_weeks():
    previous = _snapshot({7018: "reached"})
    current = _snapshot({})  # e.g. Atlas refused every anchor this week

    assert not any("measured access" in c for c in ipv6_fleet.diff_snapshots(previous, current))


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(ipv6_fleet, "HISTORY_PATH", tmp_path / "history.jsonl")
    monkeypatch.setattr(ipv6_fleet, "REPORT_PATH", tmp_path / "ipv6_fleet.txt")
    monkeypatch.setattr(ipv6_fleet, "load_probe_listing", lambda: LISTING)
    monkeypatch.setattr(ipv6_fleet, "load_last_snapshot", lambda: None)


def test_dry_run_fires_nothing_and_writes_nothing(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)

    def _fire(*args, **kwargs):
        raise AssertionError("dry run must not create measurements")

    monkeypatch.setattr(ipv6_fleet, "run_starlink_anchor_traces", _fire)

    snapshot = ipv6_fleet.run_weekly_check(fire=False, now=NOW)

    assert all(p["access"] == "not_measured" for p in snapshot["probes"].values())
    assert not (tmp_path / "history.jsonl").exists()
    assert not (tmp_path / "ipv6_fleet.txt").exists()


def test_fire_traces_ipv6_probes_with_af6_and_appends_history(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    fired = []

    def _run(probe_ids, anchors, af, label):
        fired.append((probe_ids, af, label))
        return [501, 502]

    monkeypatch.setattr(ipv6_fleet, "run_starlink_anchor_traces", _run)
    monkeypatch.setattr(
        ipv6_fleet, "refetch_parsed",
        lambda mids: [_trace(7018, "2606:4700:4700::1111", reached=True)],
    )

    ipv6_fleet.run_weekly_check(fire=True, now=NOW)

    assert fired == [([7018, 63050, 1008229], 6, "ipv6-fleet-anchor")]
    lines = (tmp_path / "history.jsonl").read_text().splitlines()
    assert len(lines) == 1
    recorded = json.loads(lines[0])
    assert recorded["date"] == "2026-09-30"
    assert recorded["measurement_ids"] == [501, 502]
    assert {pid: p["access"] for pid, p in recorded["probes"].items()} == {
        "7018": "reached", "63050": "no_result", "1008229": "no_result"
    }
    assert "IPv6 fleet check -- 2026-09-30" in (tmp_path / "ipv6_fleet.txt").read_text()


def test_per_anchor_results_keys_by_service_and_keeps_the_dark_hop():
    # Real 2026-09-24 PF shape: Cloudflare reached, Google dark at fc00:1::1.
    cloudflare = {
        "probe_id": 53098, "target": "2606:4700:4700::1111",
        "hops": [{"hop": 1, "addresses": ["2402:8200::1"], "min_rtt_ms": 0.9},
                 {"hop": 5, "addresses": ["2606:4700:4700::1111"], "min_rtt_ms": 1.544}],
    }
    google_fallback = {
        "probe_id": 53098, "target": "2001:4860:4860::8844",  # a fallback week
        "hops": [{"hop": 4, "addresses": ["fc00:1::1"], "min_rtt_ms": 3.956},
                 {"hop": 255, "addresses": [], "min_rtt_ms": None}],
    }

    results = ipv6_fleet.per_anchor_results([cloudflare, google_fallback])[53098]

    assert results["cloudflare"] == {
        "target": "2606:4700:4700::1111", "reached": True, "rtt_ms": 1.544, "last_address": "2606:4700:4700::1111"
    }
    assert results["google"]["reached"] is False
    assert results["google"]["last_address"] == "fc00:1::1"
    assert results["google"]["rtt_ms"] is None


def test_report_shows_per_anchor_cells():
    anchors = {7018: {"cloudflare": {"target": "x", "reached": True, "rtt_ms": 0.55, "last_address": "x"},
                      "google": {"target": "y", "reached": False, "rtt_ms": None, "last_address": "fc00:1::1"}}}
    snapshot = ipv6_fleet.build_snapshot(LISTING, {7018: "reached"}, [1], NOW, anchors)

    report = ipv6_fleet.render_report(snapshot, [])

    line = next(line for line in report.splitlines() if "  7018  " in line)
    assert "cloudflare ok 0.6ms" in line
    assert "google dark@fc00:1::1" in line
    no_result_line = next(line for line in report.splitlines() if "1008229" in line)
    assert "cloudflare -" in no_result_line and "google -" in no_result_line


def test_diff_reports_per_service_reach_change_and_tolerates_old_snapshots():
    def _a(reached):
        return {"target": "t", "reached": reached, "rtt_ms": None, "last_address": None}

    previous = ipv6_fleet.build_snapshot(
        LISTING, {7018: "reached"}, [1], NOW, {7018: {"cloudflare": _a(True), "google": _a(True)}}
    )
    current = ipv6_fleet.build_snapshot(
        LISTING, {7018: "reached"}, [2], NOW, {7018: {"cloudflare": _a(True), "google": _a(False)}}
    )
    assert ipv6_fleet.diff_snapshots(previous, current) == ["probe 7018 (NC) no longer reaches the google anchor"]

    old_style = json.loads(json.dumps(previous))
    for p in old_style["probes"].values():
        del p["anchors"]  # pre-per-anchor snapshot shape
    assert ipv6_fleet.diff_snapshots(old_style, current) == []
