"""Probe watch: metadata diffs and egress regression checks (atlas/probe_watch.py)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from pacific_peering.atlas import probe_watch as pw

NOW = datetime(2026, 9, 29, 15, tzinfo=timezone.utc)


def _listing(spc_asn=141695, spc_status="Connected"):
    return {
        "FJ": [{"id": 60575, "asn_v4": spc_asn, "asn_v6": None, "status": spc_status}],
        "TO": [{"id": 11691, "asn_v4": 24390, "asn_v6": None, "status": "Connected"},
               {"id": 64, "asn_v4": None, "asn_v6": None, "status": "Abandoned"}],
    }


def _setup(monkeypatch, tmp_path, listing, egress_by_probe):
    for name in ("SNAPSHOT_PATH", "HISTORY_PATH", "REPORT_PATH", "ESCALATIONS_PATH"):
        monkeypatch.setattr(pw, name, tmp_path / name.lower())
    monkeypatch.setattr(pw, "load_probe_listing", lambda: listing)
    fired: list[list[int]] = []

    def _trace(probe_ids):
        fired.append(probe_ids)
        return [999], {str(p): egress_by_probe.get(p) for p in probe_ids}

    monkeypatch.setattr(pw, "trace_egress", _trace)
    return fired


def test_state_skips_dead_probes_and_diff_reports_field_changes():
    before = pw.probe_state(_listing())
    assert set(before) == {"60575", "11691"}
    after = pw.probe_state(_listing(spc_asn=4648))
    changes = pw.diff_states(before, after)
    assert changes == [{"probe": 60575, "field": "asn_v4", "old": 141695, "new": 4648}]
    assert pw.metadata_changed_probes(changes) == {60575}


def test_status_only_change_is_not_a_metadata_change():
    before, after = pw.probe_state(_listing()), pw.probe_state(_listing(spc_status="Disconnected"))
    changes = pw.diff_states(before, after)
    assert [c["field"] for c in changes] == ["status"]
    assert pw.metadata_changed_probes(changes) == set()


def test_first_run_is_a_baseline_and_fires_nothing_off_the_weekly_run(monkeypatch, tmp_path):
    fired = _setup(monkeypatch, tmp_path, _listing(), {})
    result = pw.run_watch(fire=True, now=NOW)
    assert fired == [] and result["changes"] == []
    assert json.loads(pw.SNAPSHOT_PATH.read_text())["probes"]["60575"]["asn_v4"] == 141695
    assert not pw.ESCALATIONS_PATH.exists()


def test_asn_change_triggers_trace_and_escalation(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, _listing(), {})
    pw.run_watch(fire=True, now=NOW)
    fired = _setup(monkeypatch, tmp_path, _listing(spc_asn=4648), {60575: 4648})
    result = pw.run_watch(fire=True, now=NOW)
    assert fired == [[60575]] and result["escalations"] == 1
    text = pw.ESCALATIONS_PATH.read_text()
    assert "Probe 60575" in text and "asn_v4 141695 -> 4648" in text and "egress trace: AS4648" in text


def test_weekly_egress_escalates_only_when_first_hop_changes(monkeypatch, tmp_path):
    fired = _setup(monkeypatch, tmp_path, _listing(), {60575: 53813})
    pw.run_watch(fire=True, weekly=True, now=NOW)  # baseline egress: Zscaler
    assert fired == [[60575]] and not pw.ESCALATIONS_PATH.exists()
    _setup(monkeypatch, tmp_path, _listing(), {60575: 53813})
    pw.run_watch(fire=True, weekly=True, now=NOW)  # unchanged: quiet
    assert not pw.ESCALATIONS_PATH.exists()
    _setup(monkeypatch, tmp_path, _listing(), {60575: 4648})
    pw.run_watch(fire=True, weekly=True, now=NOW)  # off the VPN, metadata unchanged
    text = pw.ESCALATIONS_PATH.read_text()
    assert "egress changed" in text and "AS53813 (Zscaler) -- non-local egress -> AS4648" in text


def test_dry_run_writes_nothing(monkeypatch, tmp_path):
    fired = _setup(monkeypatch, tmp_path, _listing(), {})
    pw.run_watch(fire=False, weekly=True, now=NOW)
    assert fired == [] and not pw.SNAPSHOT_PATH.exists()


def test_first_weekly_check_escalates_if_watched_probe_is_already_off_the_proxy(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, _listing(), {60575: 4648})
    pw.run_watch(fire=True, weekly=True, now=NOW)
    assert "no earlier check (watched as proxy-egressing) -> AS4648" in pw.ESCALATIONS_PATH.read_text()


def test_change_while_disconnected_stays_pending_until_traced(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, _listing(), {})
    pw.run_watch(fire=True, now=NOW)
    fired = _setup(monkeypatch, tmp_path, _listing(spc_asn=4648, spc_status="Disconnected"), {60575: 4648})
    result = pw.run_watch(fire=True, now=NOW)
    assert fired == [] and result["pending"] == [60575]
    assert "not traced yet" in pw.ESCALATIONS_PATH.read_text()
    fired = _setup(monkeypatch, tmp_path, _listing(spc_asn=4648), {60575: 4648})  # reconnects: status-only
    result = pw.run_watch(fire=True, now=NOW)
    assert fired == [[60575]] and result["pending"] == []
    assert "deferred regression trace" in pw.ESCALATIONS_PATH.read_text()


def test_ipv6_only_change_is_reported_not_traced_or_escalated(monkeypatch, tmp_path):
    listing = _listing()
    _setup(monkeypatch, tmp_path, listing, {})
    pw.run_watch(fire=True, now=NOW)
    listing["TO"][0]["asn_v6"] = 24390
    fired = _setup(monkeypatch, tmp_path, listing, {})
    result = pw.run_watch(fire=True, now=NOW)
    assert fired == [] and [c["field"] for c in result["changes"]] == ["asn_v6"]
    assert not pw.ESCALATIONS_PATH.exists()


def test_unresolved_weekly_trace_neither_escalates_nor_overwrites_history(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, _listing(), {60575: 53813})
    pw.run_watch(fire=True, weekly=True, now=NOW)
    _setup(monkeypatch, tmp_path, _listing(), {60575: None})
    pw.run_watch(fire=True, weekly=True, now=NOW)
    _setup(monkeypatch, tmp_path, _listing(), {60575: 53813})
    pw.run_watch(fire=True, weekly=True, now=NOW)
    assert not pw.ESCALATIONS_PATH.exists()
    assert pw.last_egress() == {"60575": 53813}


def test_new_probe_escalated_only_if_it_egresses_non_locally(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, _listing(), {})
    pw.run_watch(fire=True, now=NOW)
    listing = _listing()
    listing["TO"].append({"id": 70000, "asn_v4": 38198, "asn_v6": None, "status": "Connected"})
    listing["TO"].append({"id": 70001, "asn_v4": 38198, "asn_v6": None, "status": "Connected"})
    fired = _setup(monkeypatch, tmp_path, listing, {70000: 38198, 70001: 53813})
    pw.run_watch(fire=True, now=NOW)
    text = pw.ESCALATIONS_PATH.read_text()
    assert fired == [[70000, 70001]]
    assert "Probe 70001" in text and "Probe 70000" not in text


def test_trace_failure_keeps_changes_pending(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, _listing(), {})
    pw.run_watch(fire=True, now=NOW)
    _setup(monkeypatch, tmp_path, _listing(spc_asn=4648), {})

    def _boom(probe_ids):
        raise OSError("atlas down")

    monkeypatch.setattr(pw, "trace_egress", _boom)
    assert pw.run_watch(fire=True, now=NOW)["pending"] == [60575]


# BOLO (owner, 2026-10-02): TCC's two 2019 hardware probes (AS38201, Tonga)
# may still be cabled but unpowered. A revived probe that egresses locally
# used to be traced and then said nothing -- these must always raise a flag.
def _tcc_listing(status_51448="Abandoned"):
    listing = _listing()
    listing["TO"].append({"id": 51448, "asn_v4": 38201, "asn_v6": None, "status": status_51448})
    return listing


def test_bolo_probe_back_online_is_escalated_even_with_local_egress(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, _tcc_listing(), {})
    pw.run_watch(fire=True, now=NOW)
    fired = _setup(monkeypatch, tmp_path, _tcc_listing("Connected"), {51448: 38201})
    pw.run_watch(fire=True, now=NOW)
    text = pw.ESCALATIONS_PATH.read_text()
    assert fired == [[51448]]
    assert "## Probe 51448 (TO, AS38201) -- BOLO probe back online" in text
    assert "AS38201" in text.split("BOLO probe back online")[1]


def test_bolo_probe_back_but_disconnected_is_escalated_before_any_trace(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, _tcc_listing(), {})
    pw.run_watch(fire=True, now=NOW)
    fired = _setup(monkeypatch, tmp_path, _tcc_listing("Disconnected"), {})
    pw.run_watch(fire=True, now=NOW)
    text = pw.ESCALATIONS_PATH.read_text()
    assert fired == []
    assert "BOLO probe back online" in text and "not traced yet" in text


def test_trace_egress_fires_protocol_overridden_probes_separately(monkeypatch):
    """One mixed measurement would force ICMP on probe 1018023, which is dark over ICMP."""
    monkeypatch.setattr(pw, "PROBE_PROTOCOL_OVERRIDES", {1018023: "UDP"})
    calls: list[list[int]] = []

    def _anchor_traces(probe_ids, anchors, af, label):
        calls.append(probe_ids)
        return [len(calls)]

    monkeypatch.setattr(pw, "run_starlink_anchor_traces", _anchor_traces)
    monkeypatch.setattr(pw, "refetch_parsed", lambda mids: [])

    measurement_ids, _ = pw.trace_egress([11691, 1018023, 60575])

    assert sorted(calls) == [[11691, 60575], [1018023]]
    assert measurement_ids == [1, 2]
