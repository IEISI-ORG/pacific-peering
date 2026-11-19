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

from pacific_peering.analysis import auto_classify, store, traceroute_topology
from pacific_peering.analysis.corridor_backlog import CorridorCandidate
from pacific_peering.analysis.ip_resolution_cache import IpResolutionCache
from pacific_peering.analysis.ixp_lan_registry import IxpLanEntry
from pacific_peering.analysis.traceroute_topology import HopResolution
from pacific_peering.discovery.economy_coordinates import EXTERNAL_HUB_LATLON

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
    # resolved: BGP owner per hop number, as resolve_traceroute_hops gives it. The located
    # routers default to their real carriers (hop 8 Tata AS6453; hops 3 and 5 Cogent AS174).
    state = {"ptr": {}, "ptr_calls": [], "registry": {}, "triangulation": _triangulation(), "parsed_dir": tmp_path,
             "resolved": {8: (6453,), 5: (174,), 3: (174,)}}
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
    # Per-hop ASNs for the hops in state["resolved"] ({hop: (asn, ...)}); an empty tuple for the rest.
    monkeypatch.setattr(auto_classify, "resolve_traceroute_hops", lambda hops, persist=False: [
        HopResolution(hop=h["hop"], addresses=tuple(h.get("addresses", [])), asns=state["resolved"].get(h["hop"], ()),
                      resolution_source="bgp" if h["hop"] in state["resolved"] else None)
        for h in hops])

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


def _existing_detour(env, hub):
    conn = env["db"]()
    fid = store.create_finding(conn, kind=store.KIND_CONFIRMED_DETOUR, source_cc="MP", source_asn=7131,
                               target_cc="TO", target_asn=38198, detour_hub=hub,
                               detour_ix_name="AS6939 + AS132528 -- international transit")
    conn.close()
    return fid


def test_reverification_through_the_filed_hub_corroborates_the_existing_detour(env):
    fid = _existing_detour(env, "Los Angeles")
    env["ptr"] = {"64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(_candidate(reverify_finding_id=fid), regenerate=False)
    assert (result.outcome, result.finding_id) == ("confirmed_detour", fid)
    assert _rows(env, "SELECT finding_id FROM corroborations") == [(fid,)]


def test_detour_whose_last_hub_is_the_filed_one_corroborates(env):
    """Owner's rule (#33/#58): the hub is the last city outside the region. Tata LA at hop 8
    is where the path leaves; hop 12 is named Sydney, so a Sydney-filed detour is corroborated
    (46 of 118 first-city mismatches on 2026-11-16 were this case)."""
    fid = _existing_detour(env, "Sydney")
    env["ptr"] = {"64.86.252.73": TATA_LA, "202.84.143.25": "xe-0-0-2.pe1.bkvl.nsw.aarnet.net.au"}
    env["resolved"][12] = (4637,)
    result = auto_classify.classify_corridor(_candidate(reverify_finding_id=fid), regenerate=False)
    assert (result.outcome, result.finding_id) == ("confirmed_detour", fid)
    assert _rows(env, "SELECT finding_id FROM corroborations") == [(fid,)]


@pytest.mark.parametrize("reverify", [True, False], ids=["reverification", "new_corridor_run"])
def test_detour_through_another_hub_escalates_instead_of_corroborating(env, reverify):
    """Owner, 2026-11-16 (#51): a run leaving via a different city than the filed hub is
    escalated for a human relabel (as #77/#84 were on 2026-11-06), never added as evidence.
    #51 is filed as Sydney; 231073937 (Portland) and 238217235 (Los Angeles) corroborated it."""
    fid = _existing_detour(env, "Sydney")
    env["ptr"] = {"64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(
        _candidate(reverify_finding_id=fid if reverify else None), regenerate=False)
    assert result.outcome == "escalated"
    assert _rows(env, "SELECT id, detour_hub FROM findings") == [(fid, "Sydney")]
    assert _rows(env, "SELECT finding_id FROM corroborations") == []
    (escalation,) = [e for e in result.escalations if e.reason == "detour hub differs from the filed finding"]
    assert f"#{fid}" in escalation.detail and "Sydney" in escalation.detail and "Los Angeles" in escalation.detail
    assert TATA_LA in escalation.detail


# 238217235 (MP probe 65653 -> PG AS17828 103.20.76.1, 2026-11-15), the real trace: it leaves
# via HE Los Angeles at 237.9ms and goes dark inside AS6939; nothing in PNG answers.
DEAD_END_MSM = 238217235
DEAD_END_HOPS = [
    {"hop": 1, "addresses": ["192.168.1.1"], "min_rtt_ms": 1.123},
    {"hop": 2, "addresses": ["10.170.7.1"], "min_rtt_ms": 77.473},
    {"hop": 3, "addresses": ["103.57.234.255"], "min_rtt_ms": 5.192},
    {"hop": 4, "addresses": ["103.57.233.1"], "min_rtt_ms": 8.139},
    {"hop": 5, "addresses": [], "min_rtt_ms": None},
    {"hop": 6, "addresses": ["10.25.37.22"], "min_rtt_ms": 8.054},
    {"hop": 7, "addresses": ["8.3.127.1"], "min_rtt_ms": 8.421},
    {"hop": 8, "addresses": [], "min_rtt_ms": None},
    {"hop": 9, "addresses": ["64.71.131.185"], "min_rtt_ms": 9.558},
    {"hop": 10, "addresses": [], "min_rtt_ms": None},
    {"hop": 11, "addresses": [], "min_rtt_ms": None},
    {"hop": 12, "addresses": [], "min_rtt_ms": None},
    {"hop": 13, "addresses": ["184.104.189.163"], "min_rtt_ms": 237.879},
    {"hop": 14, "addresses": [], "min_rtt_ms": None},
    {"hop": 15, "addresses": [], "min_rtt_ms": None},
    {"hop": 16, "addresses": ["184.104.194.234"], "min_rtt_ms": 246.216},
    {"hop": 17, "addresses": [], "min_rtt_ms": None},
    {"hop": 255, "addresses": [], "min_rtt_ms": None},
]


def test_router_hub_on_a_trace_that_never_reaches_the_target_is_inconclusive(env, monkeypatch):
    """Owner, 2026-11-16: a trace that leaves via an off-region router but goes dark before
    the target AS is inconclusive (no hop data), not detour evidence."""
    monkeypatch.setattr(auto_classify, "_fire_measurement", lambda c, ip: DEAD_END_MSM)
    (env["parsed_dir"] / f"{DEAD_END_MSM}.json").write_text(json.dumps(
        [{"measurement_id": DEAD_END_MSM, "probe_id": 65653, "target": "103.20.76.1", "hops": DEAD_END_HOPS}]))
    env["triangulation"] = {"measurement_id": DEAD_END_MSM, "target_asn": 17828, "probes": [{
        "probe_id": 65653,
        "as_sequence": [{"asn": 7131, "resolution_source": "ris", "contiguous_with_previous": True},
                        {"asn": 6939, "resolution_source": "ris", "contiguous_with_previous": True}],
        "ixp_crossings": [], "traceroute_upstream_asn": 6939, "ris_agrees": True,
        "contiguous": False, "ris_observation_count": 1293}]}
    env["resolved"] = {13: (6939,), 16: (6939,)}
    env["ptr"] = {"184.104.189.163": "be48.core3.lax1.he.net"}
    candidate = CorridorCandidate(source_asn=7131, source_cc="MP", source_name="PTI Pacifica Inc.",
                                  target_asn=17828, target_cc="PG", target_name="DataCo", rationale="test")
    result = auto_classify.classify_corridor(candidate, regenerate=False)
    assert result.outcome == "inconclusive"
    assert _rows(env, "SELECT id FROM findings") == []
    assert _rows(env, "SELECT id FROM corroborations") == []


def test_too_fast_hostname_escalates_and_keeps_local_transit(env):
    env["ptr"] = {"103.57.234.108": "be1.ccr41.lax01.atlas.cogentco.com", "64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_local_transit"
    assert [e.reason for e in result.escalations] == ["router hostname location physically impossible"]
    assert "hop 4 103.57.234.108" in result.escalations[0].detail


def test_unmapped_city_escalates(env, monkeypatch):
    # Hong Kong has coordinates since 2026-11-17; drop them to exercise the unmapped path.
    monkeypatch.delitem(EXTERNAL_HUB_LATLON, "Hong Kong")
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
    # Since the several-cities rule (below) this escalates before feasibility runs;
    # the city filter in the feasibility call stays as a second guard.
    _two_probe_measurement(env, LA_FAST_TARGET, SYD_SLOW)
    env["ptr"] = {"64.86.252.73": TATA_LA, "154.54.89.1": COGENT_SYD}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_local_transit"
    assert [e.reason for e in result.escalations] == ["router hubs in several cities"]
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


def test_hub_mismatch_still_corroborates_the_existing_local_transit_edge(env):
    # The edge is its own evidence on the trace; only the detour's hub is in question.
    detour = _existing_detour(env, "Sydney")
    conn = env["db"]()
    lt = store.create_finding(conn, kind=store.KIND_CONFIRMED_LOCAL_TRANSIT, source_cc="FJ", source_asn=45355,
                              target_cc="TO", target_asn=38198)
    conn.close()
    env["ptr"] = {"64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(_candidate(reverify_finding_id=detour), regenerate=False)
    assert result.outcome == "escalated"
    assert _rows(env, "SELECT finding_id FROM corroborations") == [(lt,)]


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


# --- 2026-10-21 owner decision: routers in several cities escalate ------------------------------

LA_ONLY = [{"hop": 1, "addresses": ["192.168.1.1"], "min_rtt_ms": 1.4},
           {"hop": 8, "addresses": ["64.86.252.73"], "min_rtt_ms": 121.5}]
SYD_ONLY = [{"hop": 1, "addresses": ["192.168.1.1"], "min_rtt_ms": 1.4},
            {"hop": 5, "addresses": ["154.54.89.1"], "min_rtt_ms": 110.0}]


@pytest.mark.parametrize("order", ["la_first", "syd_first"])
def test_router_hubs_in_several_cities_escalate_instead_of_filing(env, order):
    # Which city got filed used to depend on probe order (code review of 0e6370a).
    hops_a, hops_b = (LA_ONLY, SYD_ONLY) if order == "la_first" else (SYD_ONLY, LA_ONLY)
    _two_probe_measurement(env, hops_a, hops_b)
    env["ptr"] = {"64.86.252.73": TATA_LA, "154.54.89.1": COGENT_SYD}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_local_transit"
    assert [e.reason for e in result.escalations] == ["router hubs in several cities"]
    detail = result.escalations[0].detail
    assert "Los Angeles" in detail and "Sydney" in detail
    assert "hop 8 64.86.252.73" in detail and "hop 5 154.54.89.1" in detail
    assert _rows(env, "SELECT kind FROM findings") == [("confirmed_local_transit",)]


def test_routers_in_one_city_still_file_the_detour(env):
    _two_probe_measurement(env, LA_ONLY, LA_ONLY)
    env["ptr"] = {"64.86.252.73": TATA_LA}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert (result.outcome, result.escalations) == ("confirmed_detour", [])


# --- 2026-10-21 owner decision (Q2): a located router needs a single BGP owner -----------------


@pytest.mark.parametrize("asns", [(), (6453, 3356)], ids=["no_owner", "two_origins"])
def test_router_with_no_single_bgp_owner_escalates_instead_of_filing(env, asns):
    # No data is inconclusive: the network guard can't clear an address BGP doesn't
    # pin to one network (RIPEstat failure, unannounced space, multiple origins).
    env["ptr"] = {"64.86.252.73": TATA_LA}
    env["resolved"] = {8: asns}
    result = auto_classify.classify_corridor(_candidate(), regenerate=False)
    assert result.outcome == "confirmed_local_transit"
    assert [e.reason for e in result.escalations] == ["router address has no single BGP owner"]
    assert "hop 8 64.86.252.73" in result.escalations[0].detail
    assert _rows(env, "SELECT kind FROM findings") == [("confirmed_local_transit",)]


# --- 2026-11-19 owner ruling (F1): Superloop's unannounced Los Angeles router --------------------

# 240073513 (NC AS45345 -> FM AS45193, 2026-11-18), probe 7018, hops 4-8 as cached in
# data/atlas/parsed. Hop 7 is Superloop's border router at 624 S Grand Ave, Los Angeles, in
# 103.200.13.0/24, which no RIS peer sees; hop 8 is the Any2West LAN in the same building.
SUPERLOOP_MSM = 240073513
SUPERLOOP_LAX = "HundredGigE0-0-1-2.921.bdr01-ipt-624sgran-lax.us.as38195.net"
SUPERLOOP_HOPS = [
    {"hop": 4, "addresses": ["125.63.12.157"], "min_rtt_ms": 24.916},
    {"hop": 5, "addresses": ["125.63.12.157"], "min_rtt_ms": 24.96},
    {"hop": 6, "addresses": ["103.200.13.67"], "min_rtt_ms": 192.596},
    {"hop": 7, "addresses": ["103.200.13.168"], "min_rtt_ms": 190.441},
    {"hop": 8, "addresses": ["206.72.210.133"], "min_rtt_ms": 236.402},
]
SUPERLOOP_PTR = {
    "125.63.12.157": "Bundle-Ether42.2001.bdr03-ipt-4edenpar-syd.au.as38195.net",
    "103.200.13.67": "Bundle-Ether42.221.bdr03-ipt-47bourke-syd.au.as38195.net",
    "103.200.13.168": SUPERLOOP_LAX,
    "206.72.210.133": "teleguam-holdings.as9246.any2ix.coresite.com",
}
SUPERLOOP_BGP = {"125.63.12.157": [38195]}  # 103.200.13.0/24 is unannounced; 206.72.210.133 is IXP LAN
ANY2WEST = IxpLanEntry(ix_id=142, name="Any2West", city="Los Angeles and Silicon Valley", country="US",
                       in_fishbowl=False, prefixes=("206.72.210.0/23",))


def test_superloop_la_router_files_the_detour_via_los_angeles(env, monkeypatch, tmp_path):
    """Owner, 2026-11-19 (F1): with 103.200.13.0/24 -> AS38195 as a prefix override, the LA
    router has a single owner, so 240073513 reads Los Angeles (#110's hub) instead of
    escalating "router address has no single BGP owner" on every NC run through Superloop."""
    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {
        45345: "NC", 18200: "NC", 9246: "GU", 139759: "FM", 45193: "FM"})
    monkeypatch.setattr(auto_classify, "_fire_measurement", lambda c, ip: SUPERLOOP_MSM)
    (env["parsed_dir"] / f"{SUPERLOOP_MSM}.json").write_text(json.dumps([{
        "measurement_id": SUPERLOOP_MSM, "probe_id": 7018, "target": "103.39.252.1", "hops": SUPERLOOP_HOPS}]))
    env["registry"] = {142: ANY2WEST}
    env["triangulation"] = {"measurement_id": SUPERLOOP_MSM, "target_asn": 45193, "probes": [{
        "probe_id": 7018,
        "as_sequence": [{"asn": a, "resolution_source": "bgp", "contiguous_with_previous": True}
                        for a in (45345, 18200, 38195, 9246, 139759, 45193)],
        "ixp_crossings": [{"hop": 8, "member_asns": [9246], "min_rtt_ms": 236.402, "ix_id": 142,
                           "name": "Any2West", "in_fishbowl": False}],
        "traceroute_upstream_asn": 139759, "ris_agrees": True, "contiguous": True,
        "ris_observation_count": 1659}]}
    env["ptr"] = SUPERLOOP_PTR
    # The real resolver (so the prefix override is what gives hop 7 its owner), BGP frozen.
    cache = IpResolutionCache(path=tmp_path / "cache.json", entries={})
    monkeypatch.setattr(traceroute_topology.IpResolutionCache, "load", lambda path: cache)
    monkeypatch.setattr(traceroute_topology, "resolve_ip_to_asns", lambda ip: SUPERLOOP_BGP.get(ip, []))
    monkeypatch.setattr(traceroute_topology, "resolve_ip_via_netixlan",
                        lambda ip: 9246 if ip == "206.72.210.133" else None)
    monkeypatch.setattr(auto_classify, "resolve_traceroute_hops", lambda hops, persist=False: (
        traceroute_topology.resolve_traceroute_hops(hops, ixp_registry_path=tmp_path / "none.json", persist=False)))
    candidate = CorridorCandidate(source_asn=45345, source_cc="NC", source_name="New Caledonia", target_asn=45193,
                                  target_cc="FM", target_name="FSM Telecom", rationale="test")

    result = auto_classify.classify_corridor(candidate, regenerate=False)

    assert "router address has no single BGP owner" not in [e.reason for e in result.escalations]
    assert result.outcome == "confirmed_detour"
    assert _rows(env, "SELECT kind, detour_hub, detour_ix_name FROM findings WHERE kind = 'confirmed_detour'") == [
        ("confirmed_detour", "Los Angeles", f"{SUPERLOOP_LAX} (router in Los Angeles, no IXP crossing)")]


# --- F1 option 2 (owner, 2026-11-19): the override never files an adjacency RIS hasn't seen --------
# 211259107 (NC AS45345 -> GU AS3605, September), probe 7018, as cached in data/atlas/parsed:
# Superloop Sydney -> the unannounced LA routers -> Any2West LAN (AS3605's port) -> Guam. RIS has
# never seen AS38195 next to AS3605, and the September decision (task_plan.md, "deliberately NOT
# forced into a dataclass") kept this run out of the findings. With the override alone, the LA
# router gets an owner and the run would file NC -> AS3605 via Los Angeles; without PTRs it would
# file a candidate peering AS38195 -> AS3605. The guard keeps it inconclusive.
NC_GU_MSM = 211259107
NC_GU_HOPS = [
    {"hop": 1, "addresses": ["103.2.186.221"], "min_rtt_ms": 0.567},
    {"hop": 2, "addresses": ["202.87.128.198"], "min_rtt_ms": 0.493},
    {"hop": 3, "addresses": ["202.87.128.197"], "min_rtt_ms": 1.255},
    {"hop": 4, "addresses": ["125.63.12.157"], "min_rtt_ms": 23.841},
    {"hop": 5, "addresses": ["125.63.12.157"], "min_rtt_ms": 25.43},
    {"hop": 6, "addresses": ["103.200.13.67"], "min_rtt_ms": 172.165},
    {"hop": 7, "addresses": ["103.200.13.168"], "min_rtt_ms": 169.448},
    {"hop": 8, "addresses": ["206.72.210.236"], "min_rtt_ms": 190.584},
    {"hop": 9, "addresses": ["198.81.233.24"], "min_rtt_ms": 278.919},
    {"hop": 10, "addresses": ["202.128.5.115"], "min_rtt_ms": 300.172},
    {"hop": 11, "addresses": ["198.81.233.92"], "min_rtt_ms": 278.783},
    {"hop": 12, "addresses": ["202.128.28.33"], "min_rtt_ms": 303.115},
    {"hop": 13, "addresses": ["182.173.224.1"], "min_rtt_ms": 278.637},
]
NC_GU_BGP = {"103.2.186.221": [45345], "202.87.128.198": [18200], "202.87.128.197": [18200],
             "125.63.12.157": [38195], "198.81.233.24": [3605], "202.128.5.115": [3605],
             "198.81.233.92": [3605], "202.128.28.33": [3605], "182.173.224.1": [3605]}


def _run_nc_gu(env, monkeypatch, tmp_path, ptr, neighbours_of_3605):
    """classify_corridor over 211259107 probe 7018 with the real resolver and triangulation."""
    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {
        45345: "NC", 18200: "NC", 3605: "GU", 9246: "GU"})
    monkeypatch.setattr(auto_classify, "_fire_measurement", lambda c, ip: NC_GU_MSM)
    (env["parsed_dir"] / f"{NC_GU_MSM}.json").write_text(json.dumps([{
        "measurement_id": NC_GU_MSM, "probe_id": 7018, "target": "182.173.224.1", "hops": NC_GU_HOPS}]))
    env["ptr"] = ptr
    cache = IpResolutionCache(path=tmp_path / "cache.json", entries={})
    monkeypatch.setattr(traceroute_topology.IpResolutionCache, "load", lambda path: cache)
    monkeypatch.setattr(traceroute_topology, "resolve_ip_to_asns", lambda ip: NC_GU_BGP.get(ip, []))
    monkeypatch.setattr(traceroute_topology, "resolve_ip_via_netixlan",
                        lambda ip: 3605 if ip == "206.72.210.236" else None)
    real_resolve = traceroute_topology.resolve_traceroute_hops

    def _resolve(hops, persist=False, **kwargs):
        return real_resolve(hops, ixp_registry_path=tmp_path / "none.json", persist=False)

    monkeypatch.setattr(traceroute_topology, "resolve_traceroute_hops", _resolve)
    monkeypatch.setattr(auto_classify, "resolve_traceroute_hops", _resolve)
    fishbowl = tmp_path / "fishbowl.json"
    fishbowl.write_text(json.dumps({"3605": {"neighbors": {str(a): 10 for a in neighbours_of_3605}}}))
    monkeypatch.setattr(auto_classify, "analyze_measurement", lambda mid, asn: traceroute_topology.analyze_measurement(
        mid, asn, atlas_parsed_dir=env["parsed_dir"], fishbowl_path=fishbowl, output_dir=tmp_path / "tri"))
    candidate = CorridorCandidate(source_asn=45345, source_cc="NC", source_name="Nautile", target_asn=3605,
                                  target_cc="GU", target_name="GTA", rationale="test")
    return auto_classify.classify_corridor(candidate, regenerate=False)


_NC_GU_PTR = {"125.63.12.157": SUPERLOOP_PTR["125.63.12.157"], "103.200.13.67": SUPERLOOP_PTR["103.200.13.67"],
              "103.200.13.168": SUPERLOOP_LAX}


def test_override_bridged_step_ris_has_not_seen_files_no_detour(env, monkeypatch, tmp_path):
    result = _run_nc_gu(env, monkeypatch, tmp_path, _NC_GU_PTR, neighbours_of_3605=[9246])
    assert result.outcome == "inconclusive"
    assert _rows(env, "SELECT kind FROM findings") == []


def test_override_bridged_step_ris_has_not_seen_files_no_candidate_peering(env, monkeypatch, tmp_path):
    result = _run_nc_gu(env, monkeypatch, tmp_path, {}, neighbours_of_3605=[9246])
    assert result.outcome == "inconclusive"
    assert _rows(env, "SELECT kind FROM findings") == []


def test_override_bridged_step_ris_agrees_with_still_files(env, monkeypatch, tmp_path):
    # Control: the guard is about RIS agreement, not about overrides as such.
    result = _run_nc_gu(env, monkeypatch, tmp_path, _NC_GU_PTR, neighbours_of_3605=[38195])
    assert result.outcome == "confirmed_detour"
    assert _rows(env, "SELECT kind, detour_hub FROM findings") == [("confirmed_detour", "Los Angeles")]
