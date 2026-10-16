"""Tests for parking slow corridor measurements and collecting them on a later run."""

from __future__ import annotations

import threading
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

    assert [(e.candidate.target_asn, e.measurement_id) for e in ready] == [(1, 101)]
    assert persisted == {101: [{"prb_id": 1}]}
    # 102 still running and young, 104 unreachable but young: kept. 103 expired: dropped.
    assert pending_measurements.pending_pairs() == {(141695, 2), (141695, 4)}


def test_finished_but_empty_is_handed_back_for_the_zero_probe_path(store, monkeypatch):
    pending_measurements.add_pending(_candidate(), 101, "slow", created_at=_age(1))
    monkeypatch.setattr(pending_measurements, "fetch_measurement_status", lambda mid: "Failed")
    monkeypatch.setattr(pending_measurements, "fetch_raw_results", lambda mid: [])

    assert [e.measurement_id for e in pending_measurements.collect_ready()] == [101]
    assert pending_measurements.pending_pairs() == set()


def test_collect_drops_an_entry_that_has_failed_classification_too_often(store, monkeypatch):
    # Results are in, but classifying them has failed MAX_CLASSIFY_ATTEMPTS
    # times already: give up rather than retry a deterministic failure forever.
    pending_measurements.add_pending(
        _candidate(), 101, "classify error", created_at=_age(1),
        attempts=pending_measurements.MAX_CLASSIFY_ATTEMPTS,
    )
    monkeypatch.setattr(pending_measurements, "fetch_measurement_status", lambda mid: "Stopped")
    monkeypatch.setattr(pending_measurements, "fetch_raw_results", lambda mid: [{"prb_id": 1}])

    assert pending_measurements.collect_ready() == []
    assert pending_measurements.load_pending() == []


def test_attempts_default_to_zero_for_entries_saved_before_the_field(store):
    path, _ = store
    path.write_text(
        '{"pending": [{"measurement_id": 7, "created_at": "2026-10-16T15:00:00+00:00", "reason": "slow", '
        '"candidate": {"source_asn": 1, "source_cc": "FJ", "source_name": "Fiji", "target_asn": 2, '
        '"target_cc": "TO", "target_name": "Tonga", "rationale": "r"}}]}'
    )
    assert pending_measurements.load_pending()[0].attempts == 0


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


def test_classify_collected_measurement_loop_checks_the_recorded_target(store, monkeypatch, tmp_path):
    # Regression, 2026-10-07: a parked measurement skips the firing loop, which
    # left target_ip unbound and crashed the loop check (UnboundLocalError).
    class _Stop(Exception):
        pass

    seen: list[str | None] = []

    def _looping(hops, target=None):
        seen.append(target)
        raise _Stop

    (tmp_path / "219075862.json").write_text(
        '[{"measurement_id": 219075862, "probe_id": 60575, "target": "103.71.204.1", "hops": []}]'
    )
    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {})
    monkeypatch.setattr(auto_classify, "load_ixp_lan_registry", lambda path: {})
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_PARSED_DIR", tmp_path)
    monkeypatch.setattr(
        auto_classify, "analyze_measurement",
        lambda mid, asn: {"probes": [{"probe_id": 60575, "as_sequence": [{"asn": 141695}]}]},
    )
    monkeypatch.setattr(auto_classify, "looping_address", _looping)

    with pytest.raises(_Stop):
        auto_classify.classify_corridor(_candidate(), regenerate=False, measurement_id=219075862)

    assert seen == ["103.71.204.1"]


# --- a failed classification must not lose a paid measurement ---------------


def test_classify_collected_reparks_a_measurement_whose_classification_fails(store, monkeypatch):
    created = _age(2)
    pending_measurements.add_pending(_candidate(), 101, "slow", created_at=created)
    monkeypatch.setattr(pending_measurements, "fetch_measurement_status", lambda mid: "Stopped")
    monkeypatch.setattr(pending_measurements, "fetch_raw_results", lambda mid: [{"prb_id": 1}])

    def _boom(*args, **kwargs):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(auto_classify, "classify_corridor", _boom)

    assert auto_classify._classify_collected(threading.Lock()) == []

    [entry] = pending_measurements.load_pending()
    assert entry.measurement_id == 101
    assert entry.created_at == created
    assert entry.attempts == 1
    assert entry.last_attempt_at is not None


def test_classify_collected_does_not_repark_once_writing_has_started(store, monkeypatch):
    # Same duplicate-corroboration risk as a fresh fire: the wrapper must
    # tell `_classify_collected` that the failure came after writing began.
    pending_measurements.add_pending(_candidate(), 101, "slow", created_at=_age(2))
    monkeypatch.setattr(pending_measurements, "fetch_measurement_status", lambda mid: "Stopped")
    monkeypatch.setattr(pending_measurements, "fetch_raw_results", lambda mid: [{"prb_id": 1}])

    def _fails_mid_write(candidate, lock, regenerate, measurement_id, progress):
        progress.writing = True
        raise RuntimeError("mark_corridor_tested failed after corroborating")

    monkeypatch.setattr(auto_classify, "_classify_corridor", _fails_mid_write)

    assert auto_classify._classify_collected(threading.Lock()) == []
    assert pending_measurements.load_pending() == []


def _no_fetch(mid):
    raise AssertionError("a re-parked entry's results are already cached; don't fetch them again")


def test_collect_waits_before_retrying_a_recent_classification_failure(store, monkeypatch):
    # Batches collect at start and end; without a gap, one bad night would
    # spend every attempt.
    pending_measurements.add_pending(
        _candidate(), 101, "classify error", created_at=_age(3), attempts=1, last_attempt_at=_age(1)
    )
    monkeypatch.setattr(pending_measurements, "fetch_measurement_status", _no_fetch)
    monkeypatch.setattr(pending_measurements, "fetch_raw_results", _no_fetch)

    assert pending_measurements.collect_ready() == []
    assert [e.measurement_id for e in pending_measurements.load_pending()] == [101]


def test_collect_retries_a_reparked_entry_from_cache_even_past_max_age(store, monkeypatch):
    pending_measurements.add_pending(
        _candidate(), 101, "classify error", created_at=_age(48), attempts=1, last_attempt_at=_age(13)
    )
    monkeypatch.setattr(pending_measurements, "fetch_measurement_status", _no_fetch)
    monkeypatch.setattr(pending_measurements, "fetch_raw_results", _no_fetch)

    assert [e.measurement_id for e in pending_measurements.collect_ready()] == [101]
    assert pending_measurements.load_pending() == []


def _fresh_fire_setup(monkeypatch, tmp_path, measurement_id: int) -> None:
    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {})
    monkeypatch.setattr(auto_classify, "load_ixp_lan_registry", lambda path: {})
    monkeypatch.setattr(auto_classify, "list_target_ips", lambda asn: ["103.3.168.1"])
    monkeypatch.setattr(auto_classify, "_fire_measurement", lambda candidate, ip: measurement_id)
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_PARSED_DIR", tmp_path)
    (tmp_path / f"{measurement_id}.json").write_text("[]")


def test_classify_corridor_parks_a_fresh_measurement_when_analysis_fails(store, monkeypatch, tmp_path):
    _fresh_fire_setup(monkeypatch, tmp_path, 555)

    def _boom(mid, asn):
        raise RuntimeError("stale bgp.tools cache, download failed")

    monkeypatch.setattr(auto_classify, "analyze_measurement", _boom)

    with pytest.raises(RuntimeError):
        auto_classify.classify_corridor(_candidate(), regenerate=False)

    [entry] = pending_measurements.load_pending()
    assert entry.measurement_id == 555
    assert entry.attempts == 1
    assert entry.last_attempt_at is not None


def test_classify_corridor_does_not_park_once_writing_has_started(store, monkeypatch, tmp_path):
    # Corroborations aren't deduplicated, so re-classifying a measurement
    # whose write phase had begun could file it twice: don't park it.
    _fresh_fire_setup(monkeypatch, tmp_path, 556)
    monkeypatch.setattr(auto_classify, "analyze_measurement", lambda mid, asn: {"probes": []})

    def _boom(*args, **kwargs):
        raise RuntimeError("failed mid-write")

    monkeypatch.setattr(auto_classify, "_escalate_and_return", _boom)

    with pytest.raises(RuntimeError):
        auto_classify.classify_corridor(_candidate(), regenerate=False)

    assert pending_measurements.load_pending() == []
