"""A retest must not rebuild a finding as a trace from a network to itself.

Caught 2026-11-02: #182 (PF AS9471 ONATI -> NU AS55885, local transit) and
#179 (FJ AS9241 FINTEL -> TV AS23917) were corroborated from the *target's*
own probe tracing outward, so `_candidate_from_finding` rebuilt them as
55885 -> 55885 and 23917 -> 23917. Each two-week retest spent Atlas credits
on a self-trace (2026-10-28: #179 two dark measurements; #182 a loop inside
Niue's own network). Owner, 2026-11-02: source the retest from the
finding's own upstream; if that network has no connected probe, skip it and
record the attempt.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from pacific_peering.analysis import auto_classify
from pacific_peering.analysis import store as _store


def _db(tmp_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(tmp_path / "findings.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_store._SCHEMA)
    return conn


def _finding(conn, source_cc, source_asn, target_cc, target_asn, vantage_cc, vantage_asn) -> int:
    finding_id = _store.create_finding(
        conn, kind=_store.KIND_CONFIRMED_LOCAL_TRANSIT, source_cc=source_cc, source_asn=source_asn,
        target_cc=target_cc, target_asn=target_asn, created_at="2026-09-16T10:53:55+00:00",
    )
    _store.add_corroboration(
        conn, finding_id=finding_id, measurement_id=211091699, vantage_point_cc=vantage_cc,
        vantage_point_asn=vantage_asn, created_at="2026-09-16T10:53:55+00:00",
    )
    return finding_id


_LISTING = {
    "PF": [{"id": 30712, "status": "Connected", "asn_v4": 9471}],
    "FJ": [{"id": 21075, "status": "Abandoned", "asn_v4": 9241}],
    "NU": [{"id": 64391, "status": "Connected", "asn_v4": 55885}],
    "TV": [{"id": 7588, "status": "Connected", "asn_v4": 23917}],
    "GU": [{"id": 23039, "status": "Connected", "asn_v4": 9246}],
}


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_PARSED_DIR", tmp_path)  # no parsed file: vantage kept
    monkeypatch.setattr(auto_classify, "load_probe_listing", lambda: _LISTING)
    monkeypatch.setattr(auto_classify, "_load_listing_or_empty", lambda: _LISTING)
    monkeypatch.setattr(
        auto_classify, "_load_asn_to_cc",
        lambda path=None: {9471: "PF", 9241: "FJ", 55885: "NU", 23917: "TV", 9246: "GU", 7131: "GU"},
    )


def test_self_corridor_is_retested_from_the_findings_upstream(tmp_path):
    conn = _db(tmp_path)
    finding_id = _finding(conn, "PF", 9471, "NU", 55885, vantage_cc="NU", vantage_asn=55885)  # #182

    candidate = auto_classify._candidate_from_finding(conn, finding_id)

    assert candidate is not None
    assert (candidate.source_cc, candidate.source_asn) == ("PF", 9471)
    assert (candidate.target_cc, candidate.target_asn) == ("NU", 55885)
    assert candidate.reverify_finding_id == finding_id


def test_self_corridor_whose_upstream_has_no_probe_is_skipped_and_recorded(tmp_path):
    conn = _db(tmp_path)
    finding_id = _finding(conn, "FJ", 9241, "TV", 23917, vantage_cc="TV", vantage_asn=23917)  # #179

    assert auto_classify._candidate_from_finding(conn, finding_id) is None
    rows = conn.execute(
        "SELECT outcome FROM reverification_attempts WHERE finding_id = ?", (finding_id,)
    ).fetchall()
    assert [r[0] for r in rows] == [auto_classify.ATTEMPT_NO_VANTAGE]


def test_an_ordinary_finding_keeps_its_corroboration_vantage(tmp_path):
    conn = _db(tmp_path)
    finding_id = _finding(conn, "GU", 9246, "GU", 7131, vantage_cc="GU", vantage_asn=9246)

    candidate = auto_classify._candidate_from_finding(conn, finding_id)

    assert candidate is not None
    assert candidate.source_asn == 9246
    assert conn.execute("SELECT COUNT(*) FROM reverification_attempts").fetchone()[0] == 0
