"""Regression tests for corridor source-probe pinning and per-probe vantage ASNs.

Caught 2026-09-30 (overnight review of measurement 216991839): the corridor
AS17456 (GU) -> AS9246 (GU) was fired as `country=GU`, which Atlas filled
with probes on AS7131, AS3605 and Starlink -- none on AS17456, despite
AS17456's own probe 23039 being Connected. Every corroboration was still
stored with `vantage_point_asn=17456`, and the candidate-peering branch
filed one finding (AS7131 -> AS9246) and hung *every* probe's corroboration
on it, including probe 64953's AS3605 -> MARIIX -> AS9246 chain, which
belongs to the existing AS3605 -> AS9246 finding.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from pacific_peering.analysis import auto_classify
from pacific_peering.analysis import store as _store
from pacific_peering.analysis.corridor_backlog import CorridorCandidate

_LISTING = {
    "GU": [
        {"id": 23039, "status": "Connected", "asn_v4": 17456},
        {"id": 22813, "status": "Abandoned", "asn_v4": 17456},
        {"id": 60689, "status": "Connected", "asn_v4": 7131},
        {"id": 64953, "status": "Connected", "asn_v4": 3605},
        {"id": 65337, "status": "Connected", "asn_v4": 14593},
    ],
    "MP": [{"id": 7777, "status": "Connected", "asn_v4": 7131}],
}


def _candidate(source_asn: int = 17456, source_cc: str = "GU") -> CorridorCandidate:
    return CorridorCandidate(
        source_asn=source_asn,
        source_cc=source_cc,
        source_name="Guam",
        target_asn=9246,
        target_cc="GU",
        target_name="Guam",
        rationale="test fixture",
    )


def test_source_probe_ids_pins_to_connected_probes_on_the_source_asn_in_the_source_economy():
    assert auto_classify._source_probe_ids(_candidate(), listing=_LISTING) == [23039]
    # AS7131 probes exist in both GU and MP: only the source economy's count.
    assert auto_classify._source_probe_ids(_candidate(7131, "MP"), listing=_LISTING) == [7777]
    assert auto_classify._source_probe_ids(_candidate(9999, "GU"), listing=_LISTING) == []


def test_source_probe_ids_applies_probe_asn_overrides():
    """FM 62046's Atlas asn_v4 is Starlink, but it measures via AS139759."""
    listing = {"FM": [{"id": 62046, "status": "Connected", "asn_v4": 14593}]}
    assert auto_classify._source_probe_ids(_candidate(139759, "FM"), listing=listing) == [62046]


def test_fire_measurement_sources_from_pinned_probes(monkeypatch):
    calls = {}
    monkeypatch.setattr(auto_classify, "load_probe_listing", lambda: _LISTING)

    def _probe_sourced(probe_ids, target_asn, target_ip, purpose, defer_if_unfinished=False):
        calls["probes"] = (probe_ids, target_asn, target_ip, purpose)
        return 900000010

    def _country(**kwargs):
        raise AssertionError("must not fall back to country sourcing when a source probe exists")

    monkeypatch.setattr(auto_classify, "run_probe_sourced_traceroute", _probe_sourced)
    monkeypatch.setattr(auto_classify, "run_smoketest", _country)

    assert auto_classify._fire_measurement(_candidate(), "114.142.192.1") == 900000010
    assert calls["probes"] == ([23039], 9246, "114.142.192.1", "corridor")


def test_fire_measurement_falls_back_to_country_without_a_source_probe(monkeypatch):
    calls = {}
    monkeypatch.setattr(auto_classify, "load_probe_listing", lambda: _LISTING)

    def _run_smoketest(target_asn, target_cc, probe_count, source_cc, target_ip, defer_if_unfinished=False):
        calls["country"] = source_cc
        return 900000011

    monkeypatch.setattr(auto_classify, "run_smoketest", _run_smoketest)

    assert auto_classify._fire_measurement(_candidate(9999, "GU"), "114.142.192.1") == 900000011
    assert calls["country"] == "GU"


def _probe(probe_id: int, first_asn: int, crosses: str | None = None) -> dict:
    return {
        "probe_id": probe_id,
        "as_sequence": [
            {"asn": first_asn, "resolution_source": "bgp", "contiguous_with_previous": True},
            {"asn": 9246, "resolution_source": "bgp", "contiguous_with_previous": True},
        ],
        "ixp_crossings": (
            [{"in_fishbowl": True, "name": crosses, "min_rtt_ms": 1.0, "ix_id": 1}] if crosses else []
        ),
        "traceroute_upstream_asn": first_asn,
        "ris_agrees": False,
        "contiguous": True,
        "ris_observation_count": 0,
    }


def _open(db_path: Path) -> sqlite3.Connection:
    """store.connect without the conftest guard (it blocks the real DB path only by patching)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_store._SCHEMA)
    return conn


def _run(monkeypatch, tmp_path, probes: list[dict]) -> auto_classify.ClassifyResult:
    measurement_id = 900000012
    db_path = tmp_path / "findings.db"
    monkeypatch.setattr(_store, "connect", lambda: _open(db_path))
    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {7131: "MP", 3605: "GU"})
    monkeypatch.setattr(auto_classify, "load_ixp_lan_registry", lambda path: {})
    monkeypatch.setattr(auto_classify, "list_target_ips", lambda asn: ["114.142.192.1"])
    monkeypatch.setattr(auto_classify, "_fire_measurement", lambda candidate, ip: measurement_id)
    monkeypatch.setattr(
        auto_classify,
        "analyze_measurement",
        lambda mid, target_asn: {"measurement_id": mid, "target_asn": target_asn, "probes": probes},
    )
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_PARSED_DIR", tmp_path)
    (tmp_path / f"{measurement_id}.json").write_text(
        json.dumps([{"probe_id": p["probe_id"], "hops": []} for p in probes])
    )
    monkeypatch.setattr(auto_classify, "load_probe_listing", lambda: _LISTING)
    monkeypatch.setattr(auto_classify, "fetch_asn_names", lambda asns: {})
    monkeypatch.setattr(auto_classify, "mark_corridor_tested", lambda *a: None)
    monkeypatch.setattr(auto_classify, "_write_escalations", lambda escalations: None)
    return auto_classify.classify_corridor(_candidate(), regenerate=False)


def _corroborations(tmp_path) -> dict[tuple[int, int], list[_store.Corroboration]]:
    conn = _open(tmp_path / "findings.db")
    try:
        return {(f.source_asn, f.target_asn): _store.get_corroborations(conn, f.id) for f in _store.all_findings(conn)}
    finally:
        conn.close()


def test_candidate_peering_files_each_upstream_on_its_own_finding(monkeypatch, tmp_path):
    result = _run(monkeypatch, tmp_path, [_probe(60689, 7131), _probe(64953, 3605, crosses="MARIIX")])

    assert result.outcome == "candidate_peering"
    by_pair = _corroborations(tmp_path)
    assert set(by_pair) == {(7131, 9246), (3605, 9246)}
    assert [c.chain for c in by_pair[(7131, 9246)]] == ["AS7131 -> AS9246"]
    assert [c.chain for c in by_pair[(3605, 9246)]] == ["AS3605 -> AS9246"]
    assert by_pair[(3605, 9246)][0].crosses_ixp == "MARIIX"


def test_corroboration_records_the_probe_asn_not_the_candidate_label(monkeypatch, tmp_path):
    _run(monkeypatch, tmp_path, [_probe(60689, 7131), _probe(64953, 3605)])

    by_pair = _corroborations(tmp_path)
    assert by_pair[(7131, 9246)][0].vantage_point_asn == 7131
    assert by_pair[(3605, 9246)][0].vantage_point_asn == 3605


def test_probe_agreement_counts_each_upstream_against_all_clean_probes(monkeypatch, tmp_path):
    _run(monkeypatch, tmp_path, [_probe(60689, 7131), _probe(7777, 7131), _probe(64953, 3605)])

    conn = _open(tmp_path / "findings.db")
    try:
        agreement = {f.source_asn: f.probe_agreement for f in _store.all_findings(conn)}
    finally:
        conn.close()
    assert agreement == {7131: "2/3 probes", 3605: "1/3 probes"}


# Caught 2026-10-02 (findings #270, #271; measurements 217929784, 217930561):
# NC probe 61210's traces died at hop 5 inside its own AS141197, never
# reaching the target ASN, and RIS "disagreeing" with AS141197 as the target's
# neighbour got them filed as candidate peering. No hop in the target means no
# observed adjacency to call peering (module docstring rule 4 vs rule 5).
def _dead_end_probe(probe_id: int, own_asn: int) -> dict:
    return {
        "probe_id": probe_id,
        "as_sequence": [{"asn": own_asn, "resolution_source": "bgp", "contiguous_with_previous": True}],
        "ixp_crossings": [],
        "traceroute_upstream_asn": own_asn,
        "ris_agrees": False,
        "contiguous": True,
        "ris_observation_count": None,
    }


def test_dead_end_trace_is_inconclusive_not_candidate_peering(monkeypatch, tmp_path):
    result = _run(monkeypatch, tmp_path, [_dead_end_probe(61210, 141197)])

    assert result.outcome == "inconclusive"
    assert _corroborations(tmp_path) == {}


def test_dead_end_probe_is_left_off_a_real_candidate_peering_finding(monkeypatch, tmp_path):
    result = _run(monkeypatch, tmp_path, [_probe(60689, 7131), _dead_end_probe(61210, 141197)])

    assert result.outcome == "candidate_peering"
    assert set(_corroborations(tmp_path)) == {(7131, 9246)}


# The alternate-IP retry used to fire only when no probe resolved any ASN at
# all, so a dead end inside the probe's own AS (findings #270/#271) never got
# its second address -- against the retry-on-dead-end rule. These pin which
# results are decisive (no retry) and which are dead ends (retry once).
def _run_two_ips(monkeypatch, tmp_path, probes_by_ip: dict[str, list[dict]]):
    ips = list(probes_by_ip)
    ids = {ip: 900000020 + i for i, ip in enumerate(ips)}
    fired: list[str] = []

    def _fire(candidate, ip):
        fired.append(ip)
        return ids[ip]

    by_id = {ids[ip]: probes for ip, probes in probes_by_ip.items()}
    db_path = tmp_path / "findings.db"
    monkeypatch.setattr(_store, "connect", lambda: _open(db_path))
    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {7131: "MP", 3605: "GU"})
    monkeypatch.setattr(auto_classify, "load_ixp_lan_registry", lambda path: {})
    monkeypatch.setattr(auto_classify, "list_target_ips", lambda asn: ips)
    monkeypatch.setattr(auto_classify, "_fire_measurement", _fire)
    monkeypatch.setattr(
        auto_classify,
        "analyze_measurement",
        lambda mid, target_asn: {"measurement_id": mid, "target_asn": target_asn, "probes": by_id[mid]},
    )
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_PARSED_DIR", tmp_path)
    for mid, probes in by_id.items():
        (tmp_path / f"{mid}.json").write_text(json.dumps([{"probe_id": p["probe_id"], "hops": []} for p in probes]))
    monkeypatch.setattr(auto_classify, "load_probe_listing", lambda: _LISTING)
    monkeypatch.setattr(auto_classify, "fetch_asn_names", lambda asns: {})
    monkeypatch.setattr(auto_classify, "mark_corridor_tested", lambda *a: None)
    monkeypatch.setattr(auto_classify, "_write_escalations", lambda escalations: None)
    return auto_classify.classify_corridor(_candidate(), regenerate=False), fired


def test_dead_end_retries_the_alternate_ip_and_classifies_that_result(monkeypatch, tmp_path):
    result, fired = _run_two_ips(
        monkeypatch, tmp_path,
        {"203.0.113.1": [_dead_end_probe(61210, 141197)], "203.0.113.2": [_probe(60689, 7131)]},
    )

    assert fired == ["203.0.113.1", "203.0.113.2"]
    assert result.outcome == "candidate_peering"
    assert set(_corroborations(tmp_path)) == {(7131, 9246)}


def test_dead_end_on_both_ips_is_inconclusive(monkeypatch, tmp_path):
    result, fired = _run_two_ips(
        monkeypatch, tmp_path,
        {"203.0.113.1": [_dead_end_probe(61210, 141197)], "203.0.113.2": [_dead_end_probe(61210, 141197)]},
    )

    assert fired == ["203.0.113.1", "203.0.113.2"]
    assert result.outcome == "inconclusive"


def test_ris_corroborated_short_trace_is_decisive_and_not_retried(monkeypatch, tmp_path):
    local_transit = {**_dead_end_probe(60689, 7131), "ris_agrees": True, "ris_observation_count": 50}
    result, fired = _run_two_ips(
        monkeypatch, tmp_path, {"203.0.113.1": [local_transit], "203.0.113.2": [_probe(60689, 7131)]}
    )

    assert fired == ["203.0.113.1"]
    assert result.outcome == "confirmed_local_transit"


def test_proxy_egress_is_not_retried_against_another_ip(monkeypatch, tmp_path):
    """A second target address can't fix a source probe stuck behind Zscaler."""
    result, fired = _run_two_ips(
        monkeypatch, tmp_path,
        {"203.0.113.1": [_dead_end_probe(60575, 53813)], "203.0.113.2": [_probe(60689, 7131)]},
    )

    assert fired == ["203.0.113.1"]
    assert result.escalations[0].reason == "all probes proxy-corrupted"


# Per the project owner (2026-10-09): a lack of real hop data is just
# inconclusive every time. Findings #286/#288/#291/#294 (NR probe 1018134,
# 2026-10-08) were filed as candidate peering for OneQode -> FJ/SB targets
# though dark hops or a return-TTL jump sat between OneQode's Sydney router
# and the target.
def test_dark_hops_before_the_target_are_inconclusive_not_candidate_peering(monkeypatch, tmp_path):
    probe = _probe(1018134, 140627)
    probe["as_sequence"][1]["contiguous_with_previous"] = False
    probe["contiguous"] = False

    result = _run(monkeypatch, tmp_path, [probe])

    assert result.outcome == "inconclusive"
    assert _corroborations(tmp_path) == {}


def test_return_ttl_jump_before_the_target_is_inconclusive(monkeypatch, tmp_path):
    from pacific_peering.analysis.traceroute_topology import HopResolution

    raw = [{
        "prb_id": 1018134,
        "dst_addr": "114.142.192.1",
        "result": [
            {"hop": 5, "result": [{"from": "103.151.64.7", "ttl": 60, "rtt": 106.4}]},
            {"hop": 6, "result": [{"from": "114.142.192.1", "ttl": 244, "rtt": 235.9}]},
        ],
    }]
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "900000012.json").write_text(json.dumps(raw))
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(
        auto_classify,
        "resolve_traceroute_hops",
        lambda hops, persist=True: [
            HopResolution(hop=5, addresses=("103.151.64.7",), asns=(140627,), resolution_source="bgp"),
            HopResolution(hop=6, addresses=("114.142.192.1",), asns=(9246,), resolution_source="bgp"),
        ],
    )

    result = _run(monkeypatch, tmp_path, [_probe(1018134, 140627)])

    assert result.outcome == "inconclusive"
    assert _corroborations(tmp_path) == {}
