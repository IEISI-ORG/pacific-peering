"""A reverified finding whose target is an external carrier's in-region facility
must re-trace the address it traced, not look the target up by ASN.

Caught 2026-11-02: the nightly batch's scheduled retest of #272 (GU AS9246
GTA -> AS140627 OneQode, a confirmed detour via BBIX Tokyo) failed with
`FileNotFoundError: No cached RIS data for AS140627`. #272's target is
OneQode's RTI Guam GNC facility (`regional_carrier_facilities.py`), not an
in-scope ASN: AS140627 is AU-registered, outside `asn_registry.json`, so the
fishbowl never caches its prefixes. An ASN-level pick would be wrong even
with a cache, because most OneQode space is in Sydney, Tokyo or LA. The
retest now re-traces 103.151.64.31, the address measurement 218411496 hit.
An in-scope target with no cache still fails loudly: that is a pipeline
fault, not a facility finding.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from pacific_peering.analysis import auto_classify
from pacific_peering.analysis import store as _store
from pacific_peering.analysis.corridor_backlog import CorridorCandidate

_MEASUREMENT = 218411496
_FACILITY_IP = "103.151.64.31"


def _db(tmp_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(tmp_path / "findings.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_store._SCHEMA)
    return conn


def _finding(conn: sqlite3.Connection, target_asn: int) -> int:
    finding_id = _store.create_finding(
        conn, kind=_store.KIND_CONFIRMED_DETOUR, source_cc="GU", source_asn=9246,
        target_cc="GU", target_asn=target_asn, created_at="2026-10-02T22:28:45+00:00",
    )
    _store.add_corroboration(
        conn, finding_id=finding_id, measurement_id=_MEASUREMENT, vantage_point_cc="GU",
        vantage_point_asn=9246, created_at="2026-10-02T22:28:45+00:00",
    )
    return finding_id


@pytest.fixture
def _parsed(monkeypatch, tmp_path):
    """The stored measurement, as parsed: two probes, both traced to the facility."""
    (tmp_path / f"{_MEASUREMENT}.json").write_text(json.dumps([
        {"measurement_id": _MEASUREMENT, "probe_id": 23039, "target": _FACILITY_IP, "hops": []},
        {"measurement_id": _MEASUREMENT, "probe_id": 7385, "target": _FACILITY_IP, "hops": []},
    ]))
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_PARSED_DIR", tmp_path)
    monkeypatch.setattr(auto_classify, "load_probe_listing", lambda: {})
    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {9246: "GU", 7131: "GU"})


def test_facility_target_reverify_pins_the_traced_address(_parsed, tmp_path):
    conn = _db(tmp_path)
    finding_id = _finding(conn, target_asn=140627)  # OneQode: not in the registry

    candidate = auto_classify._candidate_from_finding(conn, finding_id)

    assert candidate is not None
    assert candidate.target_asn == 140627
    assert candidate.target_ip == _FACILITY_IP


def test_in_scope_target_reverify_keeps_asn_level_selection(_parsed, tmp_path):
    conn = _db(tmp_path)
    finding_id = _finding(conn, target_asn=7131)  # in the registry

    candidate = auto_classify._candidate_from_finding(conn, finding_id)

    assert candidate is not None
    assert candidate.target_ip is None


def test_facility_target_with_no_stored_measurement_is_left_unpinned(_parsed, tmp_path):
    """No parsed file to read the address from: fall through to the loud
    ASN-level failure rather than guess an address."""
    conn = _db(tmp_path)
    finding_id = _finding(conn, target_asn=140627)
    (tmp_path / f"{_MEASUREMENT}.json").unlink()

    candidate = auto_classify._candidate_from_finding(conn, finding_id)

    assert candidate is not None
    assert candidate.target_ip is None


def test_pinned_candidate_fires_at_its_address_without_an_ris_lookup(monkeypatch, tmp_path):
    fired: list[str] = []

    def _no_ris(asn):
        raise FileNotFoundError(f"No cached RIS data for AS{asn}")

    def _fire(candidate, ip):
        fired.append(ip)
        return 900000002

    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {})
    monkeypatch.setattr(auto_classify, "load_ixp_lan_registry", lambda path: {})
    monkeypatch.setattr(auto_classify, "list_target_ips", _no_ris)
    monkeypatch.setattr(auto_classify, "_fire_measurement", _fire)
    monkeypatch.setattr(
        auto_classify, "analyze_measurement",
        lambda mid, target_asn: {"measurement_id": mid, "target_asn": target_asn, "probes": []},
    )
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_PARSED_DIR", tmp_path)
    (tmp_path / "900000002.json").write_text("[]")
    monkeypatch.setattr(auto_classify, "fetch_measurement_status", lambda mid: "Stopped")
    monkeypatch.setattr(auto_classify, "mark_corridor_tested", lambda *a: None)
    monkeypatch.setattr(auto_classify, "_write_escalations", lambda escalations: None)
    candidate = CorridorCandidate(
        9246, "GU", "Guam", 140627, "GU", "Guam", "test fixture",
        reverify_finding_id=272, target_ip=_FACILITY_IP,
    )

    auto_classify.classify_corridor(candidate, regenerate=False)

    assert fired == [_FACILITY_IP]


def test_parked_entries_written_before_the_field_existed_still_load():
    entry = {
        "source_asn": 9246, "source_cc": "GU", "source_name": "Guam", "target_asn": 7131,
        "target_cc": "GU", "target_name": "Guam", "rationale": "old entry",
        "is_new_probe": False, "is_new_ris_relationship": False, "reverify_finding_id": None,
    }
    assert CorridorCandidate(**entry).target_ip is None
