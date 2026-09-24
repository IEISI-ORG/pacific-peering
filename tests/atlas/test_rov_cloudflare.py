"""Tests for the weekly Cloudflare ROV test (atlas/rov_cloudflare.py)."""

from __future__ import annotations

from datetime import datetime, timezone

from pacific_peering.atlas import rov_cloudflare as rov

NOW = datetime(2026, 9, 30, 15, 0, tzinfo=timezone.utc)
V4_VALID, V4_INVALID = rov.ROV_TARGETS[4]["valid"][0], rov.ROV_TARGETS[4]["invalid"][0]


def _trace(probe_id, target, reached):
    hops = [{"hop": 1, "addresses": ["192.168.1.1"], "min_rtt_ms": 0.5},
            {"hop": 2, "addresses": ["203.0.113.1"], "min_rtt_ms": 5.0}]
    if reached:
        hops.append({"hop": 3, "addresses": [target], "min_rtt_ms": 20.0})
    return {"probe_id": probe_id, "target": target, "hops": hops}


def test_not_filtered_when_invalid_answers():
    v = rov.classify_probe(_trace(1, V4_VALID, True), _trace(1, V4_INVALID, True), [9471, 13335], [9471, 13335])
    assert v == {"label": "not_filtered", "drop_asn": None, "reason": None}


def test_filtered_names_the_last_asn_the_invalid_trace_reached():
    v = rov.classify_probe(
        _trace(1, V4_VALID, True), _trace(1, V4_INVALID, False), [45345, 18200, 13335], [45345, 18200]
    )
    assert v["label"] == "filtered" and v["drop_asn"] == 18200


def test_filtered_before_first_public_hop():
    v = rov.classify_probe(_trace(1, V4_VALID, True), _trace(1, V4_INVALID, False), [45345, 13335], [])
    assert v == {"label": "filtered", "drop_asn": None, "reason": "died before first public hop"}


def test_inconclusive_cases():
    valid_dark = rov.classify_probe(_trace(1, V4_VALID, False), _trace(1, V4_INVALID, False), [45345], [45345])
    assert valid_dark["label"] == "inconclusive" and "no baseline" in valid_dark["reason"]

    missing = rov.classify_probe(None, _trace(1, V4_INVALID, True), [], [45345])
    assert missing["label"] == "inconclusive"

    # A Zscaler-proxied probe tests Zscaler, not its own ISP -- even if invalid "answers".
    proxy = rov.classify_probe(_trace(1, V4_VALID, True), _trace(1, V4_INVALID, True), [53813, 13335], [53813, 13335])
    assert proxy["label"] == "inconclusive" and "proxy AS53813" in proxy["reason"]


def test_classify_measurements_maps_fallback_addresses_to_roles():
    fallback_invalid = rov.ROV_TARGETS[4]["invalid"][1]
    traces = [_trace(7, V4_VALID, True), _trace(7, fallback_invalid, False)]
    paths = {V4_VALID: [17893, 13335], fallback_invalid: [17893]}

    verdicts = rov.classify_measurements(
        traces, 4, {7: {"cc": "PW", "asn": 17893}, 8: {"cc": "PW", "asn": 17893}},
        path_of=lambda t: paths[t["target"]],
    )

    assert verdicts[7] == {"label": "filtered", "drop_asn": 17893, "reason": None}
    assert verdicts[8]["label"] == "inconclusive"  # no result at all


LISTING = {
    "NC": [{"id": 7018, "status": "Connected", "asn_v4": 45345, "asn_v6": 45345}],
    "PF": [{"id": 53098, "status": "Connected", "asn_v4": 9471, "asn_v6": 9471}],
    "MH": [{"id": 64237, "status": "Connected", "asn_v4": 14593, "asn_v6": None}],
    "WS": [{"id": 1, "status": "Abandoned", "asn_v4": 17993}],
}


def _snap(v4, v6=None):
    return rov.build_snapshot(LISTING, {4: v4, 6: v6 or {}}, {4: [1, 2]}, {}, NOW)


def _v(label, drop=None):
    return {"label": label, "drop_asn": drop, "reason": None}


def test_snapshot_counts_per_economy_and_drop_points():
    s = _snap({7018: _v("filtered", 18200), 53098: _v("not_filtered"), 64237: _v("filtered", 18200)},
              {7018: _v("not_filtered")})

    assert s["economies"]["NC"] == {"v4": {"filtered": 1}, "v6": {"not_filtered": 1}}
    assert s["drop_asns"] == {"v4:18200": 2}
    assert "1" not in s["probes"]  # abandoned probe excluded
    assert s["probes"]["64237"].get("v6") is None  # no IPv6 ASN, not in the IPv6 plan


def test_diff_reports_label_and_drop_point_changes_and_ignores_inconclusive():
    previous = _snap({7018: _v("not_filtered"), 53098: _v("filtered", 9471), 64237: _v("inconclusive")})
    current = _snap({7018: _v("filtered", 18200), 53098: _v("filtered", 55943), 64237: _v("not_filtered")})

    assert rov.diff_snapshots(previous, current) == [
        "probe 7018 (NC) v4: not_filtered -> filtered",
        "probe 53098 (PF) v4: drop point AS9471 -> AS55943",
    ]


def test_report_cells():
    report = rov.render_report(_snap({7018: _v("filtered", 18200), 53098: _v("filtered")}), [])
    assert "filtered@AS18200" in report and "filtered@local" in report
    assert "v4  AS18200: 1" in report and "v4  local: 1" in report


def test_wrong_target_rpki_state_stops_before_firing(monkeypatch, tmp_path):
    monkeypatch.setattr(rov, "HISTORY_PATH", tmp_path / "h.jsonl")
    monkeypatch.setattr(rov, "fetch_rpki_status", lambda ip: type("S", (), {"status": "valid"})())

    def _fire(*a, **k):
        raise AssertionError("must not fire when the invalid target validates as valid")

    monkeypatch.setattr(rov, "run_starlink_anchor_traces", _fire)

    assert rov.run_weekly_test(fire=True, now=NOW) is None
    assert not (tmp_path / "h.jsonl").exists()
