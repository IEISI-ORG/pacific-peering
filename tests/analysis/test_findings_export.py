"""findings_export.jsonl carries findings, not recheck bookkeeping.

`aspa_checked_at` only records when an ASPA lookup last ran -- a query, not
a change to the finding -- so exporting it made every weekly recheck commit
a diff even when nothing was promoted.
"""

import sqlite3
from pathlib import Path

from pacific_peering.analysis import store


def _db_with_checked_candidate(tmp_path: Path):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(store._SCHEMA)
    fid = store.create_finding(
        conn, kind=store.KIND_CANDIDATE_PEERING, source_cc="FJ", source_asn=4648,
        target_cc="TO", target_asn=24390,
    )
    store.mark_aspa_checked(conn, fid, confirmed=False, checked_at="2026-10-11T15:00:00+00:00")
    return conn, fid


def test_unpromoted_recheck_does_not_change_the_export(tmp_path: Path) -> None:
    conn, fid = _db_with_checked_candidate(tmp_path)
    out = tmp_path / "findings_export.jsonl"
    store.export_jsonl(conn, out)
    before = out.read_text()

    store.mark_aspa_checked(conn, fid, confirmed=False, checked_at="2026-10-18T15:00:00+00:00")
    store.export_jsonl(conn, out)

    assert out.read_text() == before
    assert "aspa_checked_at" not in before


def test_promotion_still_reaches_the_export(tmp_path: Path) -> None:
    conn, fid = _db_with_checked_candidate(tmp_path)
    out = tmp_path / "findings_export.jsonl"

    store.mark_aspa_checked(conn, fid, confirmed=True, checked_at="2026-10-18T15:00:00+00:00")
    store.export_jsonl(conn, out)

    assert '"kind": "confirmed_local_transit"' in out.read_text()
    assert '"aspa_confirmed": true' in out.read_text()
