"""Tests for parking slow corridor measurements and collecting them on a later run."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import requests

from pacific_peering.analysis import auto_classify, pending_measurements
from pacific_peering.analysis.corridor_backlog import CorridorCandidate
from pacific_peering.atlas import client
from pacific_peering.atlas.client import MeasurementPending


def _candidate(target_asn: int = 132248) -> CorridorCandidate:
    return CorridorCandidate(141695, "FJ", "Fiji", target_asn, "FJ", "Fiji", "domestic pair")


# --- wait_for_results(defer_if_unfinished=True) -----------------------------


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(client.time, "sleep", lambda s: None)


def test_status_check_error_defers(monkeypatch, no_sleep):
    def _boom(mid):
        raise requests.ReadTimeout("read timed out")

    monkeypatch.setattr(client, "fetch_measurement_status", _boom)
    with pytest.raises(MeasurementPending) as exc:
        client.wait_for_results(42, defer_if_unfinished=True)
    assert exc.value.measurement_id == 42


def test_unfinished_and_empty_at_deadline_defers(monkeypatch, no_sleep):
    monkeypatch.setattr(client, "fetch_measurement_status", lambda mid: "Ongoing")
    monkeypatch.setattr(client, "fetch_raw_results", lambda mid: [])
    with pytest.raises(MeasurementPending):
        client.wait_for_results(42, max_wait=0, defer_if_unfinished=True)


def test_unfinished_with_results_returns_them(monkeypatch, no_sleep):
    # The normal case: one-off measurements read "Ongoing" long after the probe reported.
    monkeypatch.setattr(client, "fetch_measurement_status", lambda mid: "Ongoing")
    monkeypatch.setattr(client, "fetch_raw_results", lambda mid: [{"prb_id": 1}])
    assert client.wait_for_results(42, max_wait=0, defer_if_unfinished=True) == [{"prb_id": 1}]


def test_without_the_flag_empty_is_still_returned(monkeypatch, no_sleep):
    monkeypatch.setattr(client, "fetch_measurement_status", lambda mid: "Ongoing")
    monkeypatch.setattr(client, "fetch_raw_results", lambda mid: [])
    assert client.wait_for_results(42, max_wait=0) == []


# --- the pending store -------------------------------------------------------


@pytest.fixture
def store(tmp_path, monkeypatch):
    path = tmp_path / "pending.json"
    monkeypatch.setattr(pending_measurements, "DEFAULT_PENDING_PATH", path)
    persisted: dict[int, list] = {}
    monkeypatch.setattr(pending_measurements, "persist_results", lambda mid, raw: persisted.__setitem__(mid, raw))
    return path, persisted


def _age(hours: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def test_collect_returns_ready_keeps_young_drops_expired(store, monkeypatch):
    path, persisted = store
    pending_measurements.add_pending(_candidate(1), 101, "slow", created_at=_age(1))
    pending_measurements.add_pending(_candidate(2), 102, "slow", created_at=_age(1))
    pending_measurements.add_pending(_candidate(3), 103, "slow", created_at=_age(25))
    pending_measurements.add_pending(_candidate(4), 104, "slow", created_at=_age(2))
    assert pending_measurements.pending_pairs() == {(141695, 1), (141695, 2), (141695, 3), (141695, 4)}

    results = {101: [{"prb_id": 1}], 102: [], 103: []}
    statuses = {101: "Stopped", 102: "Ongoing", 103: "Ongoing"}

    def _status(mid):
        if mid == 104:
            raise requests.ConnectionError("down")
        return statuses[mid]

    monkeypatch.setattr(pending_measurements, "fetch_measurement_status", _status)
    monkeypatch.setattr(pending_measurements, "fetch_raw_results", lambda mid: results[mid])

    ready = pending_measurements.collect_ready()

    assert [(c.target_asn, mid) for c, mid in ready] == [(1, 101)]
    assert persisted == {101: [{"prb_id": 1}]}
    # 102 still running and young, 104 unreachable but young: kept. 103 expired: dropped.
    assert pending_measurements.pending_pairs() == {(141695, 2), (141695, 4)}


def test_finished_but_empty_is_handed_back_for_the_zero_probe_path(store, monkeypatch):
    pending_measurements.add_pending(_candidate(), 101, "slow", created_at=_age(1))
    monkeypatch.setattr(pending_measurements, "fetch_measurement_status", lambda mid: "Failed")
    monkeypatch.setattr(pending_measurements, "fetch_raw_results", lambda mid: [])

    assert [mid for _, mid in pending_measurements.collect_ready()] == [101]
    assert pending_measurements.pending_pairs() == set()


def test_candidate_round_trips_with_reverify_id(store):
    cand = CorridorCandidate(1, "FJ", "Fiji", 2, "TO", "Tonga", "reverify", reverify_finding_id=77)
    pending_measurements.add_pending(cand, 5, "slow")
    assert pending_measurements.load_pending()[0].candidate == cand


# --- classify_corridor parks instead of failing ------------------------------


def test_classify_corridor_parks_a_slow_measurement(store, monkeypatch):
    marked = []
    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {})
    monkeypatch.setattr(auto_classify, "load_ixp_lan_registry", lambda path: {})
    monkeypatch.setattr(auto_classify, "list_target_ips", lambda asn: ["103.71.204.1"])
    monkeypatch.setattr(auto_classify, "mark_corridor_tested", lambda *a: marked.append(a))

    def _fire(candidate, ip):
        raise MeasurementPending(219075862, "status check failed")

    monkeypatch.setattr(auto_classify, "_fire_measurement", _fire)

    result = auto_classify.classify_corridor(_candidate(), regenerate=False)

    assert result.outcome == "pending"
    assert marked == []
    assert [p.measurement_id for p in pending_measurements.load_pending()] == [219075862]
