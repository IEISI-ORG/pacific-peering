"""The weekly reverification ration must rotate through every finding.

Caught 2026-10-19: `select_reverification_batch` ranked findings by their
latest corroboration only, so a retest that filed no corroboration
(inconclusive, dark trace, a different kind) left the finding where it
was, at the head of the ranking. #26, #33, #69, #76, #91, #121 and #144
were each retested 5 times between 09-20 and 10-11 while most findings
never reached the queue. Each scheduled retest now also records an
attempt (`store.reverification_attempts`), and the ranking uses
max(last verified, last attempted). The attempt is bookkeeping for the
queue only: `_last_verified`, reports and the export are unchanged.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pacific_peering.analysis import auto_classify, pending_measurements
from pacific_peering.analysis import store as _store
from pacific_peering.analysis.corridor_backlog import CorridorCandidate
from pacific_peering.analysis.store import connect as _real_connect  # bound before conftest patches it
from pacific_peering.atlas.client import MeasurementPending


def _open(db_path: Path) -> sqlite3.Connection:
    """store.connect without the conftest guard (it blocks the real DB path only by patching)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_store._SCHEMA)
    return conn


def _finding(conn: sqlite3.Connection, created_at: str, target_asn: int) -> int:
    finding_id = _store.create_finding(
        conn, kind=_store.KIND_CANDIDATE_PEERING, source_cc="FJ", source_asn=4648,
        target_cc="FJ", target_asn=target_asn, created_at=created_at,
    )
    _store.add_corroboration(
        conn, finding_id=finding_id, measurement_id=100 + finding_id, vantage_point_cc="FJ",
        created_at=created_at,
    )
    return finding_id


def _candidate(finding_id: int | None) -> CorridorCandidate:
    return CorridorCandidate(
        141695, "FJ", "Fiji", 132248, "FJ", "Fiji", "test fixture", reverify_finding_id=finding_id,
    )


def _attempts(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    return [
        (r["finding_id"], r["outcome"])
        for r in conn.execute("SELECT finding_id, outcome FROM reverification_attempts ORDER BY id")
    ]


# --- selection ----------------------------------------------------------------


def test_retest_without_corroboration_moves_the_finding_behind_untouched_older_ones(monkeypatch, tmp_path):
    db_path = tmp_path / "findings.db"
    conn = _open(db_path)
    oldest = _finding(conn, "2026-09-01T00:00:00+00:00", 1)
    middle = _finding(conn, "2026-09-05T00:00:00+00:00", 2)
    _finding(conn, "2026-09-10T00:00:00+00:00", 3)
    monkeypatch.setattr(_store, "connect", lambda: _open(db_path))

    assert auto_classify.select_reverification_batch(fraction=1 / 3) == [oldest]

    _store.record_reverification_attempt(
        conn, finding_id=oldest, outcome="inconclusive", attempted_at="2026-10-01T00:00:00+00:00"
    )

    assert auto_classify.select_reverification_batch(fraction=1 / 3) == [middle]
    # An attempt is not a verification: the finding's evidence timestamp is untouched.
    finding = next(f for f in _store.all_findings(conn) if f.id == oldest)
    assert auto_classify._last_verified(conn, finding) == "2026-09-01T00:00:00+00:00"


def test_corroborated_finding_ranks_by_its_corroboration_as_before(monkeypatch, tmp_path):
    db_path = tmp_path / "findings.db"
    conn = _open(db_path)
    oldest = _finding(conn, "2026-09-01T00:00:00+00:00", 1)
    middle = _finding(conn, "2026-09-05T00:00:00+00:00", 2)
    monkeypatch.setattr(_store, "connect", lambda: _open(db_path))

    _store.add_corroboration(
        conn, finding_id=oldest, measurement_id=555, vantage_point_cc="FJ",
        created_at="2026-10-01T00:00:00+00:00",
    )

    assert auto_classify.select_reverification_batch(fraction=0.5) == [middle]
    # A corroboration newer than the last attempt wins too (max of the two).
    _store.record_reverification_attempt(
        conn, finding_id=oldest, outcome="inconclusive", attempted_at="2026-09-20T00:00:00+00:00"
    )
    assert auto_classify.select_reverification_batch(fraction=0.5) == [middle]


def test_a_finding_that_errored_before_any_measurement_is_not_stamped(monkeypatch, tmp_path):
    db_path = tmp_path / "findings.db"
    conn = _open(db_path)
    finding_id = _finding(conn, "2026-09-01T00:00:00+00:00", 1)
    monkeypatch.setattr(_store, "connect", lambda: _open(db_path))

    auto_classify._note_reverification_attempt(_candidate(finding_id), "pending", threading.Lock())
    auto_classify._note_reverification_attempt(_candidate(None), "inconclusive", threading.Lock())

    assert _attempts(conn) == []


# --- migration ----------------------------------------------------------------


def test_connect_adds_the_attempts_table_to_an_old_db_and_keeps_its_rows(tmp_path):
    db_path = tmp_path / "findings.db"
    conn = _open(db_path)
    finding_id = _finding(conn, "2026-09-01T00:00:00+00:00", 1)
    # A database from before the table existed.
    conn.executescript("DROP TABLE reverification_attempts;")
    conn.close()

    for _ in range(2):  # applying the schema twice must be a no-op the second time
        conn = _real_connect(db_path)
        assert conn.execute("SELECT COUNT(*) FROM findings").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM corroborations").fetchone()[0] == 1
        assert _store.last_reverification_attempt(conn, finding_id) is None
        conn.close()

    conn = _real_connect(db_path)
    _store.record_reverification_attempt(conn, finding_id=finding_id, outcome="inconclusive")
    conn.close()
    conn = _real_connect(db_path)
    assert _store.last_reverification_attempt(conn, finding_id) is not None
    assert conn.execute("SELECT COUNT(*) FROM findings").fetchone()[0] == 1


# --- the parked-measurement path stamps exactly once -------------------------


def test_parked_reverification_is_stamped_once_when_collected(monkeypatch, tmp_path):
    db_path = tmp_path / "findings.db"
    conn = _open(db_path)
    finding_id = _finding(conn, "2026-09-01T00:00:00+00:00", 1)
    monkeypatch.setattr(_store, "connect", lambda: _open(db_path))
    monkeypatch.setattr(pending_measurements, "DEFAULT_PENDING_PATH", tmp_path / "pending.json")
    monkeypatch.setattr(pending_measurements, "persist_results", lambda mid, raw: None)
    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {})
    monkeypatch.setattr(auto_classify, "load_ixp_lan_registry", lambda path: {})
    monkeypatch.setattr(auto_classify, "list_target_ips", lambda asn: ["103.71.204.1"])

    def _fire(candidate, ip):
        raise MeasurementPending(219075862, "status check failed")

    monkeypatch.setattr(auto_classify, "_fire_measurement", _fire)
    candidate = _candidate(finding_id)
    lock = threading.Lock()

    # Night 1: fired, parked. No attempt yet -- its fate isn't known.
    result = auto_classify.classify_corridor(candidate, lock=lock, regenerate=False)
    auto_classify._note_reverification_attempt(candidate, result.outcome, lock)
    assert result.outcome == "pending"
    assert _attempts(conn) == []

    # Night 2: collected and classified (no corroboration filed).
    monkeypatch.setattr(pending_measurements, "fetch_measurement_status", lambda mid: "Stopped")
    monkeypatch.setattr(pending_measurements, "fetch_raw_results", lambda mid: [{"prb_id": 1}])
    monkeypatch.setattr(
        auto_classify, "classify_corridor",
        lambda cand, lock, regenerate, measurement_id: auto_classify.ClassifyResult(cand, "inconclusive"),
    )
    assert [r.outcome for r in auto_classify._classify_collected(lock)] == ["inconclusive"]
    assert _attempts(conn) == [(finding_id, "inconclusive")]

    # Nothing left to collect: no second stamp.
    assert auto_classify._classify_collected(lock) == []
    assert _attempts(conn) == [(finding_id, "inconclusive")]


def test_parked_reverification_that_is_given_up_on_is_stamped_as_lost(monkeypatch, tmp_path):
    db_path = tmp_path / "findings.db"
    conn = _open(db_path)
    finding_id = _finding(conn, "2026-09-01T00:00:00+00:00", 1)
    monkeypatch.setattr(_store, "connect", lambda: _open(db_path))
    monkeypatch.setattr(pending_measurements, "DEFAULT_PENDING_PATH", tmp_path / "pending.json")
    monkeypatch.setattr(pending_measurements, "fetch_measurement_status", lambda mid: "Ongoing")
    monkeypatch.setattr(pending_measurements, "fetch_raw_results", lambda mid: [])
    pending_measurements.add_pending(
        _candidate(finding_id), 219075862, "slow",
        created_at=datetime.now(timezone.utc) - timedelta(hours=30),
    )

    assert auto_classify._classify_collected(threading.Lock()) == []
    assert pending_measurements.load_pending() == []
    assert _attempts(conn) == [(finding_id, "lost")]


# --- "no probe data returned" needs 3 attempts (owner, 2026-10-21) -----------------------------


def _no_data(conn, finding_id, day):
    _store.record_reverification_attempt(
        conn, finding_id=finding_id, outcome=auto_classify.ATTEMPT_NO_DATA,
        attempted_at=f"2026-10-{day:02d}T00:00:00+00:00",
    )


def test_no_data_retest_keeps_its_turn_until_the_third(monkeypatch, tmp_path):
    # Zero probes reporting is usually a transient Atlas results-fetch race, not
    # a look at the path, so one or two of them don't send the finding back.
    db_path = tmp_path / "findings.db"
    conn = _open(db_path)
    oldest = _finding(conn, "2026-09-01T00:00:00+00:00", 1)
    middle = _finding(conn, "2026-09-05T00:00:00+00:00", 2)
    monkeypatch.setattr(_store, "connect", lambda: _open(db_path))

    _no_data(conn, oldest, 1)
    _no_data(conn, oldest, 8)
    assert auto_classify.select_reverification_batch(fraction=0.5) == [oldest]
    _no_data(conn, oldest, 15)
    assert auto_classify.select_reverification_batch(fraction=0.5) == [middle]


def test_no_data_count_restarts_after_a_real_attempt(monkeypatch, tmp_path):
    db_path = tmp_path / "findings.db"
    conn = _open(db_path)
    oldest = _finding(conn, "2026-09-01T00:00:00+00:00", 1)
    middle = _finding(conn, "2026-10-05T00:00:00+00:00", 2)
    monkeypatch.setattr(_store, "connect", lambda: _open(db_path))

    _no_data(conn, oldest, 1)
    _no_data(conn, oldest, 2)
    _store.record_reverification_attempt(
        conn, finding_id=oldest, outcome="inconclusive", attempted_at="2026-10-03T00:00:00+00:00"
    )
    # The real attempt ranks it at 10-03, still ahead of middle (10-05), and the
    # two earlier no-data attempts don't carry over: two more don't move it, a third does.
    assert auto_classify.select_reverification_batch(fraction=0.5) == [oldest]
    _no_data(conn, oldest, 10)
    _no_data(conn, oldest, 11)
    assert auto_classify.select_reverification_batch(fraction=0.5) == [oldest]
    _no_data(conn, oldest, 12)
    assert auto_classify.select_reverification_batch(fraction=0.5) == [middle]


def test_zero_probe_escalation_is_recorded_as_no_data():
    no_data = auto_classify.ClassifyResult(
        _candidate(1), "escalated", None,
        [auto_classify._Escalation(_candidate(1), 9, "no probe data returned", "x")],
    )
    dark = auto_classify.ClassifyResult(_candidate(1), "inconclusive", None, [])
    assert auto_classify._attempt_outcome(no_data) == auto_classify.ATTEMPT_NO_DATA
    assert auto_classify._attempt_outcome(dark) == "inconclusive"
