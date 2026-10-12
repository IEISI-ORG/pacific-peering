"""classify_corridor files a detour via a hostname-located router when no IXP is crossed.

Real shape: 221439393 (MP -> TO, reverification of #92, 2026-10-11). Saipan
probe 65653 went AS7131 -> Tata LA (121ms) -> Telstra Global -> Digicel Fiji
-> Digicel Tonga with no IXP crossing; the IXP-only rule filed #295 (local
transit, Digicel Fiji -> Digicel Tonga) and left #92 uncorroborated.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from pacific_peering.analysis import auto_classify, store
from pacific_peering.analysis.corridor_backlog import CorridorCandidate
from pacific_peering.analysis.ixp_lan_registry import IxpLanEntry

MSM = 900000002
TATA_LA = "ix-xe-2-1-4-0.tcore2.lvw-losangeles.as6453.net"
HOPS = [
    {"hop": 1, "addresses": ["192.168.1.1"], "min_rtt_ms": 1.416},
    {"hop": 4, "addresses": ["103.57.234.108"], "min_rtt_ms": 8.166},
    {"hop": 8, "addresses": ["64.86.252.73"], "min_rtt_ms": 121.458},
    {"hop": 12, "addresses": ["202.84.143.25"], "min_rtt_ms": 167.759},
    {"hop": 16, "addresses": ["202.129.231.109"], "min_rtt_ms": 206.569},
    {"hop": 18, "addresses": ["202.43.12.5"], "min_rtt_ms": 212.954},
]


def _triangulation(ixp_crossings=()):
    return {"measurement_id": MSM, "target_asn": 38198, "probes": [{
        "probe_id": 65653,
        "as_sequence": [{"asn": a, "resolution_source": "ris", "contiguous_with_previous": True}
                        for a in (7131, 6453, 4637, 45355, 38198)],
        "ixp_crossings": list(ixp_crossings), "traceroute_upstream_asn": 45355, "ris_agrees": True,
        "contiguous": True, "ris_observation_count": 1321}]}


def _candidate(reverify_finding_id=None):
    return CorridorCandidate(source_asn=7131, source_cc="MP", source_name="PTI Pacifica Inc.", target_asn=38198,
                             target_cc="TO", target_name="Digicel Tonga Ltd", rationale="test",
                             reverify_finding_id=reverify_finding_id)


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Everything classify_corridor touches, pointed at tmp_path and stubbed off the network."""
    state = {"ptr": {}, "ptr_calls": [], "registry": {}, "triangulation": _triangulation()}
    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {7131: "MP", 45355: "FJ", 38198: "TO"})
    monkeypatch.setattr(auto_classify, "load_ixp_lan_registry", lambda path: state["registry"])
    monkeypatch.setattr(auto_classify, "list_target_ips", lambda asn: ["202.43.12.1"])
    monkeypatch.setattr(auto_classify, "_fire_measurement", lambda c, ip: MSM)
    monkeypatch.setattr(auto_classify, "analyze_measurement", lambda mid, target_asn: state["triangulation"])
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_PARSED_DIR", tmp_path)
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_RAW_DIR", tmp_path / "raw")
    (tmp_path / f"{MSM}.json").write_text(json.dumps(
        [{"measurement_id": MSM, "probe_id": 65653, "target": "202.43.12.1", "hops": HOPS}]))
    monkeypatch.setattr(auto_classify, "fetch_measurement_status", lambda mid: "Stopped")
    monkeypatch.setattr(auto_classify, "mark_corridor_tested", lambda s, t: None)
    monkeypatch.setattr(auto_classify, "_write_escalations", lambda e: None)
    monkeypatch.setattr(auto_classify, "_asn_holder_name", lambda asn, cache: f"AS{asn}")
    monkeypatch.setattr(auto_classify, "_load_listing_or_empty", lambda: {})
    monkeypatch.setattr(auto_classify, "resolve_traceroute_hops", lambda hops, persist=False: [])

    def _ptr(address):
        state["ptr_calls"].append(address)
        return state["ptr"].get(address)

    monkeypatch.setattr(auto_classify, "reverse_dns", _ptr)
    db = tmp_path / "findings.db"
    monkeypatch.setattr(auto_classify._store, "connect", lambda db_path=None: _open(db))
    state["db"] = lambda: _open(db)
    return state


def _open(db):
    # tests/conftest.py replaces store.connect with a blocker before this module's fixtures
    # run, so open the tmp DB the way store.connect does instead of capturing it.
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(store._SCHEMA)
    return conn


def _rows(env, sql):
    conn = env["db"]()
    try:
        return [tuple(r) for r in conn.execute(sql).fetchall()]
    finally:
        conn.close()


def test_router_hub_files_a_detour_via_los_angeles(env):
    env["ptr"] = {"64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_detour"
    assert _rows(env, "SELECT kind, source_cc, target_asn, detour_hub, detour_ix_name FROM findings") == [
        ("confirmed_detour", "MP", 38198, "Los Angeles", f"{TATA_LA} (router in Los Angeles, no IXP crossing)")]
    (note,) = _rows(env, "SELECT note_extra FROM corroborations")[0]
    assert "hop 8 64.86.252.73" in note and "121.458ms" in note and "floor 94.63ms" in note


def test_reverification_corroborates_the_existing_detour(env):
    conn = env["db"]()
    fid = store.create_finding(conn, kind=store.KIND_CONFIRMED_DETOUR, source_cc="MP", source_asn=7131,
                               target_cc="TO", target_asn=38198, detour_hub="Sydney",
                               detour_ix_name="AS6939 + AS132528 -- international transit")
    conn.close()
    env["ptr"] = {"64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(_candidate(reverify_finding_id=fid), regenerate=False)
    assert (result.outcome, result.finding_id) == ("confirmed_detour", fid)
    assert _rows(env, "SELECT id, detour_hub FROM findings") == [(fid, "Sydney")]  # hub not overwritten
    assert _rows(env, "SELECT finding_id FROM corroborations") == [(fid,)]


def test_too_fast_hostname_escalates_and_keeps_local_transit(env):
    env["ptr"] = {"103.57.234.108": "be1.ccr41.lax01.atlas.cogentco.com", "64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_local_transit"
    assert [e.reason for e in result.escalations] == ["router hostname location physically impossible"]
    assert "hop 4 103.57.234.108" in result.escalations[0].detail


def test_unmapped_city_escalates(env):
    env["ptr"] = {"64.86.252.73": "be5991.ccr22.sfo01.atlas.cogentco.com"}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_local_transit"
    assert [e.reason for e in result.escalations] == ["router in a hub city with no coordinates"]
    assert "sfo01" in result.escalations[0].detail


def test_no_ptr_records_leaves_local_transit(env):
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert (result.outcome, result.escalations) == ("confirmed_local_transit", [])


def test_ixp_detour_takes_precedence(env):
    env["registry"] = {94: IxpLanEntry(ix_id=94, name="Equinix Sydney", city="Sydney", country="AU",
                                       in_fishbowl=False, prefixes=("45.127.172.0/22",))}
    env["triangulation"] = _triangulation([{"ix_id": 94, "name": "Equinix Sydney", "in_fishbowl": False,
                                            "hop": 6, "min_rtt_ms": 60.0}])
    env["ptr"] = {"64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_detour"
    assert _rows(env, "SELECT detour_hub, detour_ix_name FROM findings") == [("Sydney", "Equinix Sydney")]
    assert env["ptr_calls"] == []
