"""Regression tests for auto_classify.classify_corridor's escalation branching.

Caught 2026-09-20 via measurement 213457173 (AS7131 -> AS24439): a
transient Atlas results-fetch race (see tests/atlas/test_client.py) left
zero probe data for the measurement. The old code read that the same way
as "every probe's own path shows a known proxy/VPN ASN" and filed a
misleading "all probes proxy-corrupted" escalation whose detail string had
a giveaway empty `()` -- an empty join over a proxy-report dict that was
never populated because there were no probes to check in the first place.

These tests lock in the fix: the two cases must stay distinguishable, and
only the genuine proxy-corruption case may mark the corridor tested (a
zero-data result carries no real signal, so the corridor must retry on its
own next run rather than being permanently skipped).
"""

from __future__ import annotations

import json

from pacific_peering.analysis import auto_classify
from pacific_peering.analysis.corridor_backlog import CorridorCandidate


def _candidate() -> CorridorCandidate:
    return CorridorCandidate(
        source_asn=7131,
        source_cc="MP",
        source_name="PTI Pacifica Inc.",
        target_asn=24439,
        target_cc="MH",
        target_name="Test Target ASN",
        rationale="test fixture",
    )


def _patch_common(monkeypatch, tmp_path, triangulation, parsed_hops):
    measurement_id = 900000001
    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {})
    monkeypatch.setattr(auto_classify, "load_ixp_lan_registry", lambda path: {})
    monkeypatch.setattr(auto_classify, "list_target_ips", lambda asn: ["203.0.113.1"])
    monkeypatch.setattr(
        auto_classify, "_fire_measurement", lambda candidate, ip: measurement_id
    )
    monkeypatch.setattr(
        auto_classify, "analyze_measurement", lambda mid, target_asn: triangulation
    )
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_PARSED_DIR", tmp_path)
    (tmp_path / f"{measurement_id}.json").write_text(_json_dumps(parsed_hops))

    marked: list[tuple[int, int]] = []
    monkeypatch.setattr(
        auto_classify, "mark_corridor_tested", lambda source_asn, target_asn: marked.append(
            (source_asn, target_asn)
        )
    )
    written: list[list] = []
    monkeypatch.setattr(
        auto_classify, "_write_escalations", lambda escalations: written.append(escalations)
    )
    return marked, written


def _json_dumps(obj) -> str:
    return json.dumps(obj)


def test_zero_probes_escalates_without_marking_tested(monkeypatch, tmp_path):
    """No probe data at all must not be read as 'all probes proxy-corrupted'."""
    triangulation = {"measurement_id": 900000001, "target_asn": 24439, "probes": []}
    marked, written = _patch_common(monkeypatch, tmp_path, triangulation, parsed_hops=[])

    result = auto_classify.classify_corridor(_candidate())

    assert result.outcome == "escalated"
    assert len(result.escalations) == 1
    assert result.escalations[0].reason == "no probe data returned"
    assert marked == [], "a zero-data result must not permanently mark the corridor tested"
    assert written == [result.escalations]


def test_all_probes_proxy_corrupted_still_marks_tested(monkeypatch, tmp_path):
    """The genuine proxy-corruption case is unaffected by the zero-data fix."""
    triangulation = {
        "measurement_id": 900000001,
        "target_asn": 24439,
        "probes": [
            {
                "probe_id": 65653,
                "as_sequence": [
                    {"asn": 53813, "resolution_source": "whois", "contiguous_with_previous": True}
                ],
                "ixp_crossings": [],
                "traceroute_upstream_asn": 53813,
                "ris_agrees": False,
                "contiguous": True,
                "ris_observation_count": 0,
            }
        ],
    }
    parsed_hops = [{"probe_id": 65653, "hops": []}]
    marked, written = _patch_common(monkeypatch, tmp_path, triangulation, parsed_hops)

    result = auto_classify.classify_corridor(_candidate())

    assert result.outcome == "escalated"
    assert len(result.escalations) == 1
    assert result.escalations[0].reason == "all probes proxy-corrupted"
    assert "probe 65653 via Zscaler" in result.escalations[0].detail
    assert marked == [(7131, 24439)]
    assert written == [result.escalations]


def test_zero_probes_does_not_retry_against_alternate_target_ip(monkeypatch, tmp_path):
    """Zero probes is a source-side failure -- a second target IP can't fix
    it, and firing one anyway both doubles Atlas spend and (as happened for
    real on 2026-09-20) can silently overwrite a first attempt's genuine
    dark-but-real data with a second, information-free empty measurement."""
    measurement_id = 900000001
    triangulation = {"measurement_id": measurement_id, "target_asn": 24439, "probes": []}
    fire_calls: list[str] = []

    def _fire(candidate, ip):
        fire_calls.append(ip)
        return measurement_id

    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {})
    monkeypatch.setattr(auto_classify, "load_ixp_lan_registry", lambda path: {})
    monkeypatch.setattr(
        auto_classify, "list_target_ips", lambda asn: ["203.0.113.1", "203.0.113.2"]
    )
    monkeypatch.setattr(auto_classify, "_fire_measurement", _fire)
    monkeypatch.setattr(
        auto_classify, "analyze_measurement", lambda mid, target_asn: triangulation
    )
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_PARSED_DIR", tmp_path)
    (tmp_path / f"{measurement_id}.json").write_text(_json_dumps([]))
    monkeypatch.setattr(auto_classify, "mark_corridor_tested", lambda *a: None)
    monkeypatch.setattr(auto_classify, "_write_escalations", lambda escalations: None)

    result = auto_classify.classify_corridor(_candidate())

    assert fire_calls == ["203.0.113.1"], "must not fire a second measurement on zero probes"
    assert result.outcome == "escalated"
    assert result.escalations[0].reason == "no probe data returned"


def test_pick_next_for_batch_skips_excluded_pairs(monkeypatch):
    """A pair already tried this run (zero probe data, still not marked
    tested) must not be re-picked -- otherwise a persistently-broken
    corridor consumes the whole run_batch time budget re-firing itself
    instead of other workers/corridors making progress (caught in code
    review before this shipped, 2026-09-20)."""
    stuck = CorridorCandidate(
        source_asn=7131, source_cc="MP", source_name="PTI Pacifica Inc.",
        target_asn=24439, target_cc="MH", target_name="Test Target ASN",
        rationale="stuck",
    )
    other = CorridorCandidate(
        source_asn=45345, source_cc="NC", source_name="Test Source ASN",
        target_asn=17480, target_cc="NC", target_name="Test Target 2",
        rationale="other",
    )
    monkeypatch.setattr(
        auto_classify, "enumerate_candidate_corridors", lambda: [stuck, other]
    )

    picked = auto_classify._pick_next_for_batch(
        exclude_source_asns=set(), exclude_pairs=frozenset({(7131, 24439)})
    )

    assert picked is other


def test_fire_measurement_forwards_target_ip_to_run_smoketest(monkeypatch):
    """Caught 2026-09-21: this used to accept target_ip and silently drop it,
    so the alternate-cached-prefix retry never actually retried a different
    address (see tests/atlas/test_smoketest.py for the other end of this)."""
    captured = {}

    def _run_smoketest(target_asn, target_cc, probe_count, source_cc, target_ip):
        captured["target_ip"] = target_ip
        return 900000002

    monkeypatch.setattr(auto_classify, "run_smoketest", _run_smoketest)

    measurement_id = auto_classify._fire_measurement(_candidate(), "203.78.152.1")

    assert measurement_id == 900000002
    assert captured["target_ip"] == "203.78.152.1"


def _probe(probe_id, first_asn):
    return {
        "probe_id": probe_id,
        "as_sequence": [{"asn": first_asn, "resolution_source": "bgp", "contiguous_with_previous": True}],
        "ixp_crossings": [],
        "traceroute_upstream_asn": first_asn,
        "ris_agrees": False,
        "contiguous": True,
        "ris_observation_count": 0,
    }


def test_starlink_first_hop_probe_is_dropped_like_a_proxy(monkeypatch, tmp_path):
    """FM 62046 failing over to its Starlink uplink (or GU 65337 via country
    sourcing) must not be read as the source economy's own routing."""
    triangulation = {"measurement_id": 900000001, "target_asn": 24439, "probes": [_probe(62046, 14593)]}
    marked, written = _patch_common(monkeypatch, tmp_path, triangulation, [{"probe_id": 62046, "hops": []}])

    result = auto_classify.classify_corridor(_candidate())

    assert result.outcome == "escalated"
    assert "probe 62046 via Starlink" in result.escalations[0].detail


def test_starlink_is_not_a_proxy_for_the_rov_and_ipv6_checks():
    assert 14593 in auto_classify.NON_LOCAL_FIRST_HOP_ASNS
    assert 14593 not in auto_classify.KNOWN_PROXY_ASNS
    assert set(auto_classify.KNOWN_PROXY_ASNS) <= set(auto_classify.NON_LOCAL_FIRST_HOP_ASNS)
