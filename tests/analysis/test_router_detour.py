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
from pacific_peering.analysis.traceroute_topology import HopResolution

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
    state = {"ptr": {}, "ptr_calls": [], "registry": {}, "triangulation": _triangulation(), "parsed_dir": tmp_path,
             "resolved": {}}
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
    # Per-hop ASNs for the hops a test names in state["resolved"] ({hop: (asn, ...)}); none otherwise.
    monkeypatch.setattr(auto_classify, "resolve_traceroute_hops", lambda hops, persist=False: [
        HopResolution(hop=h["hop"], addresses=tuple(h.get("addresses", [])), asns=state["resolved"][h["hop"]],
                      resolution_source="bgp")
        for h in hops if h["hop"] in state["resolved"]])

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
    env["ptr"] = {"64.86.252.73": "hk-mgi-rt1.oneqode.net"}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_local_transit"
    assert [e.reason for e in result.escalations] == ["router in a hub city with no coordinates"]
    assert "hk-mgi" in result.escalations[0].detail


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


# --- 2026-10-21 follow-ups (TODO.md P1): multi-probe measurements ---------------------------------

TARGET = "202.43.12.5"
COGENT_SYD = "be4026.ccr21.syd01.atlas.cogentco.com"
COGENT_LAX = "be1.ccr41.lax01.atlas.cogentco.com"


def _probe(probe_id):
    return {**_triangulation()["probes"][0], "probe_id": probe_id}


def _two_probe_measurement(env, hops_a, hops_b):
    """Probe 65653 (hops_a) and probe 50000 (hops_b), both reaching the target via AS45355."""
    env["triangulation"] = {"measurement_id": MSM, "target_asn": 38198, "probes": [_probe(65653), _probe(50000)]}
    (env["parsed_dir"] / f"{MSM}.json").write_text(json.dumps([
        {"measurement_id": MSM, "probe_id": 65653, "target": TARGET, "hops": hops_a},
        {"measurement_id": MSM, "probe_id": 50000, "target": TARGET, "hops": hops_b},
    ]))


# Floors from MP: Los Angeles hub 94.63ms, LA-routed target 118.97ms; Sydney hub 54.9ms.
LA_FAST_TARGET = [  # Tata LA is plausible, but the target answers too fast to be behind it (offshore)
    {"hop": 1, "addresses": ["192.168.1.1"], "min_rtt_ms": 1.4},
    {"hop": 8, "addresses": ["64.86.252.73"], "min_rtt_ms": 121.5},
    {"hop": 12, "addresses": [TARGET], "min_rtt_ms": 80.0},
]
SYD_SLOW = [  # a Sydney router, slow enough to also clear the LA floors
    {"hop": 1, "addresses": ["192.168.1.1"], "min_rtt_ms": 1.4},
    {"hop": 5, "addresses": ["154.54.89.1"], "min_rtt_ms": 110.0},
    {"hop": 14, "addresses": [TARGET], "min_rtt_ms": 250.0},
]


def test_router_in_another_city_is_not_the_detour_hub(env):
    # Probe 50000's Sydney router used to stand in as the LA hub hop, so its slow trace
    # "passed" the LA floors and turned an impossible claim into a filed, mixed one.
    _two_probe_measurement(env, LA_FAST_TARGET, SYD_SLOW)
    env["ptr"] = {"64.86.252.73": TATA_LA, "154.54.89.1": COGENT_SYD}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_local_transit"
    assert "detour via Los Angeles physically impossible (Validation Rule 2)" in [e.reason for e in result.escalations]
    assert _rows(env, "SELECT kind FROM findings") == [("confirmed_local_transit",)]


def test_impossible_feasibility_demotes_a_router_pick(env):
    _two_probe_measurement(env, LA_FAST_TARGET, LA_FAST_TARGET)
    env["ptr"] = {"64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_local_transit"
    (esc,) = [e for e in result.escalations if "Validation Rule 2" in e.reason]
    assert esc.reason == "detour via Los Angeles physically impossible (Validation Rule 2)"
    assert "probe 65653 target_via_hub hop 12 80.0ms" in esc.detail


def test_too_fast_probe_note_lands_on_the_detour_corroboration(env):
    too_fast = [{"hop": 1, "addresses": ["192.168.1.1"], "min_rtt_ms": 1.4},
                {"hop": 3, "addresses": ["154.54.1.9"], "min_rtt_ms": 20.0}]
    _two_probe_measurement(env, HOPS, too_fast)
    env["ptr"] = {"64.86.252.73": TATA_LA, "154.54.1.9": COGENT_LAX}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_detour"
    assert [e.reason for e in result.escalations] == ["router hostname location physically impossible"]
    notes = [n for (n,) in _rows(env, "SELECT note_extra FROM corroborations")]
    assert len(notes) == 2
    assert any("hop 3 154.54.1.9" in n and "too_fast" in n for n in notes)
    assert any("hop 8 64.86.252.73" in n and "(floor 94.63ms, ok)" in n for n in notes)


def test_router_in_a_fishbowl_network_escalates_instead_of_filing(env):
    # Hostname says Tata LA, but BGP says the address is Digicel Fiji's (in the fishbowl):
    # a misnamed or spoofed PTR, never evidence of a detour on its own.
    env["ptr"] = {"64.86.252.73": TATA_LA}
    env["resolved"] = {8: (45355,)}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_local_transit"
    assert [e.reason for e in result.escalations] == ["router hostname off-region but address in a fishbowl network"]
    assert "AS45355" in result.escalations[0].detail and "hop 8 64.86.252.73" in result.escalations[0].detail


def test_router_detour_also_corroborates_the_existing_local_transit_edge(env):
    # 221439393 (MP -> TO): the detour (#92) and the Digicel Fiji -> Digicel Tonga edge (#295)
    # are both on the same trace; only the detour used to be corroborated.
    conn = env["db"]()
    lt = store.create_finding(conn, kind=store.KIND_CONFIRMED_LOCAL_TRANSIT, source_cc="FJ", source_asn=45355,
                              target_cc="TO", target_asn=38198)
    conn.close()
    env["ptr"] = {"64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_detour"
    assert sorted(_rows(env, "SELECT finding_id FROM corroborations")) == sorted([(result.finding_id,), (lt,)])


def test_router_detour_never_creates_a_local_transit_finding(env):
    env["ptr"] = {"64.86.252.73": TATA_LA}
    auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert _rows(env, "SELECT kind FROM findings") == [("confirmed_detour",)]


def test_ixp_detour_leaves_the_local_transit_edge_alone(env):
    conn = env["db"]()
    store.create_finding(conn, kind=store.KIND_CONFIRMED_LOCAL_TRANSIT, source_cc="FJ", source_asn=45355,
                         target_cc="TO", target_asn=38198)
    conn.close()
    env["registry"] = {94: IxpLanEntry(ix_id=94, name="Equinix Sydney", city="Sydney", country="AU",
                                       in_fishbowl=False, prefixes=("45.127.172.0/22",))}
    env["triangulation"] = _triangulation([{"ix_id": 94, "name": "Equinix Sydney", "in_fishbowl": False,
                                            "hop": 6, "min_rtt_ms": 60.0}])
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_detour"
    assert _rows(env, "SELECT finding_id FROM corroborations") == [(result.finding_id,)]
