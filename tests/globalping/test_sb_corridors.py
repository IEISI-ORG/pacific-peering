"""Tests for the weekly Globalping SB corridor step (globalping/sb_corridors.py, sb_report.py)."""

from __future__ import annotations

import json
import sys

import pytest
import requests

from pacific_peering.globalping import client, sb_corridors, sb_report
from pacific_peering.globalping.sb_corridors import Planned, ProbeGroup, Target


def _probe(cc, asn, city, network, lat=0.0, lon=0.0):
    return {"location": {"country": cc, "asn": asn, "city": city, "network": network,
                         "latitude": lat, "longitude": lon}}


PROBES = [
    _probe("SB", 132468, "Honiara", "SATSOL"),
    _probe("NC", 45345, "Noumea", "Nautile"),
    _probe("NC", 45345, "Noumea", "Nautile"),
    _probe("GU", 14593, "Dededo", "Starlink"),  # external, skipped
    _probe("AU", 4826, "Sydney", "Vocus"),  # not in scope
]
SB_GROUP = ProbeGroup("SB", 132468, "SATSOL", ("Honiara",), 1)
NC_GROUP = ProbeGroup("NC", 45345, "Nautile", ("Noumea",), 2)


ASN_TO_CC = {132468: "SB", 45345: "NC", 14593: "GU", 3605: "GU"}


def test_probe_groups_merge_duplicates_and_skip_external_and_out_of_scope():
    probes = PROBES + [_probe("GU", 64512, "Hagatna", "Unregistered VPN"), {"location": {"country": "NC"}}]

    groups, skipped = sb_corridors.pacific_probe_groups(probes, ASN_TO_CC)

    assert groups == [NC_GROUP, SB_GROUP]
    assert skipped == ["GU AS14593 Starlink (Dededo) x1: does not egress locally",
                       "GU AS64512 Unregistered VPN (Hagatna) x1: ASN not in the in-scope registry"]
    assert NC_GROUP.location() == {"country": "NC", "asn": 45345, "limit": 2}


def test_plan_never_keeps_a_measurement_with_no_sources():
    huge = ProbeGroup("NC", 45345, "Nautile", ("Noumea",), 60)

    assert sb_corridors.plan_measurements([huge], [Target(45891, "SB", "2.0.0.1")]) == []


def test_plan_puts_sb_targets_first_with_inbound_sources_and_skips_own_asn():
    targets = [Target(4638, "FJ", "1.0.0.1"), Target(45891, "SB", "2.0.0.1"), Target(132468, "SB", "3.0.0.1")]

    plan = sb_corridors.plan_measurements([NC_GROUP, SB_GROUP], targets)

    assert [(p.target.asn, [g.asn for g in p.sources]) for p in plan] == [
        (45891, [132468, 45345]),  # domestic + inbound in one measurement
        (132468, [45345]),  # SATSOL doesn't trace to itself; inbound still runs
        (4638, [132468]),  # outbound only
    ]
    assert plan[0].tests == 3


def test_fire_stops_at_budget_and_at_rate_limit(monkeypatch):
    plan = [Planned(Target(a, "SB", f"10.0.0.{i}"), (SB_GROUP, NC_GROUP)) for i, a in enumerate([1, 2, 3], 1)]
    calls = []

    def create(target, locations):
        calls.append(target)
        if target == "10.0.0.2":
            raise client.RateLimited("429")
        return client.Created(f"m{len(calls)}", 3, 200)

    monkeypatch.setattr(client, "create_measurement", create)
    fired, unmeasured = sb_corridors.fire(plan, budget=100)
    assert [mid for _p, mid in fired] == ["m1"]
    assert unmeasured == ["AS2 (SB): Globalping rate limit", "AS3 (SB): Globalping rate limit"]

    calls.clear()
    fired, unmeasured = sb_corridors.fire(plan, budget=4)  # room for one 3-test measurement
    assert calls == ["10.0.0.1"]
    assert unmeasured == ["AS2 (SB): test budget used up", "AS3 (SB): test budget used up"]


def test_fire_respects_rate_limit_remaining_header(monkeypatch):
    plan = [Planned(Target(a, "SB", f"10.0.0.{a}"), (SB_GROUP,)) for a in (1, 2)]
    monkeypatch.setattr(client, "create_measurement", lambda target, locations: client.Created("m", 1, 0))

    fired, unmeasured = sb_corridors.fire(plan, budget=240)

    assert len(fired) == 1
    assert unmeasured == ["AS2 (SB): Globalping rate limit"]


def test_fire_skips_an_oversized_measurement_but_runs_smaller_ones_after_it(monkeypatch):
    big = Planned(Target(1, "SB", "10.0.0.1"), (ProbeGroup("NC", 45345, "Nautile", ("Noumea",), 11),))
    small = Planned(Target(2, "FJ", "10.0.0.2"), (SB_GROUP,))
    monkeypatch.setattr(client, "create_measurement", lambda target, locations: client.Created("m", 1, 200))

    fired, unmeasured = sb_corridors.fire([big, small], budget=5)

    assert [p.target.asn for p, _mid in fired] == [2]
    assert unmeasured == ["AS1 (SB): test budget used up"]


def test_fire_stops_on_network_error(monkeypatch):
    plan = [Planned(Target(a, "SB", f"10.0.0.{a}"), (SB_GROUP,)) for a in (1, 2)]

    def down(target, locations):
        raise requests.ConnectionError("no route")

    monkeypatch.setattr(client, "create_measurement", down)
    fired, unmeasured = sb_corridors.fire(plan, budget=240)

    assert fired == []
    assert unmeasured == ["AS1 (SB): network error (ConnectionError)", "AS2 (SB): network error (ConnectionError)"]


def test_wait_for_all_returns_partial_results_at_the_deadline(monkeypatch):
    clock = iter(range(0, 10_000, 5))
    monkeypatch.setattr(client.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(client.time, "sleep", lambda s: None)
    polls = {"a": [{"status": "finished"}], "b": [{"status": "in-progress"}] * 100}

    def fetch(mid):
        if mid == "c":
            raise requests.ConnectionError("down")
        return polls[mid].pop(0)

    monkeypatch.setattr(client, "fetch_measurement", fetch)
    done = client.wait_for_all(["a", "b", "c"], timeout_s=60)

    assert done == {"a": {"status": "finished"}, "b": {"status": "in-progress"}}  # c never fetched


def test_to_parsed_hops_numbers_hops_and_keeps_dark_ones():
    hops = [{"resolvedAddress": "10.172.0.1", "timings": [{"rtt": 0.47}, {"rtt": 0.459}]},
            {"resolvedAddress": None, "timings": []},
            {"resolvedAddress": "218.100.52.11", "timings": [{"rtt": 47.9}, {"rtt": None}]}]

    assert sb_corridors.to_parsed_hops(hops) == [
        {"hop": 1, "addresses": ["10.172.0.1"], "min_rtt_ms": 0.459},
        {"hop": 2, "addresses": [], "min_rtt_ms": None},
        {"hop": 3, "addresses": ["218.100.52.11"], "min_rtt_ms": 47.9},
    ]


def test_fibre_floor_is_zero_in_economy_and_positive_abroad():
    honiara = {"country": "SB", "latitude": -9.43, "longitude": 159.95}
    assert sb_corridors.fibre_floor_ms(honiara, "SB") == 0.0
    assert sb_corridors.fibre_floor_ms(honiara, "GU") > 20


def _result(country, asn, city, lat, lon, hops):
    return {"probe": {"country": country, "asn": asn, "city": city, "latitude": lat, "longitude": lon},
            "result": {"status": "finished", "hops": hops}}


@pytest.fixture
def no_resolution(monkeypatch):
    monkeypatch.setattr(sb_corridors, "resolve_traceroute_hops", lambda hops: [])
    monkeypatch.setattr(sb_corridors, "extract_as_sequence", lambda resolved: [])


def test_analyse_flags_a_trace_faster_than_fibre(no_resolution):
    # "Honiara" probe reaching Guam in 5 ms: the probe or the target is mislabelled.
    result = _result("SB", 132468, "Honiara", -9.43, 159.95,
                     [{"resolvedAddress": "10.0.0.1", "timings": [{"rtt": 0.5}]},
                      {"resolvedAddress": "202.128.0.1", "timings": [{"rtt": 5.0}]}])

    trace = sb_corridors.analyse_result(Target(3605, "GU", "202.128.0.1"), result)

    assert trace["reached"] and trace["rtt_ms"] == 5.0
    assert trace["below_floor"]


def test_analyse_reports_last_answering_hop_when_dark(no_resolution):
    result = _result("NC", 45345, "Noumea", -22.27, 166.45,
                     [{"resolvedAddress": "203.0.113.9", "timings": [{"rtt": 30.2}]},
                      {"resolvedAddress": None, "timings": []}])

    trace = sb_corridors.analyse_result(Target(45891, "SB", "2.0.0.1"), result)

    assert not trace["reached"] and not trace["below_floor"]
    assert (trace["last_address"], trace["last_rtt_ms"]) == ("203.0.113.9", 30.2)


def test_analyse_survives_null_hops_and_a_reached_hop_without_rtt(no_resolution):
    offline = {"probe": {"country": "NC", "asn": 45345, "latitude": -22.27, "longitude": 166.45},
               "result": {"status": "offline", "hops": None}}
    no_rtt = _result("SB", 132468, "Honiara", -9.43, 159.95,
                     [{"resolvedAddress": "2.0.0.1", "timings": None}])

    dark = sb_corridors.analyse_result(Target(45891, "SB", "2.0.0.1"), offline)
    reached = sb_corridors.analyse_result(Target(45891, "SB", "2.0.0.1"), no_rtt)

    assert (dark["status"], dark["reached"], dark["src_city"]) == ("offline", False, "?")
    assert reached["reached"] and reached["rtt_ms"] is None and not reached["below_floor"]
    report = sb_report.render_report(_snapshot([dark, reached]), [], {})
    assert "probe result offline" in report and "reached (no RTT)" in report


def test_collect_notes_uncollected_and_unparseable_results(monkeypatch, tmp_path, no_resolution):
    planned = Planned(Target(45891, "SB", "2.0.0.1"), (SB_GROUP,))
    monkeypatch.setattr(client, "wait_for_all", lambda ids: {"m1": {"results": [{"probe": {}}]}})

    traces, notes = sb_corridors.collect([(planned, "m1"), (planned, "m2")], raw_dir=tmp_path)

    assert traces == []
    assert notes[0].startswith("AS45891 (SB): one result unparseable (m1: KeyError")
    assert notes[1] == "AS45891 (SB): results not collected (m2)"
    assert (tmp_path / "m1.json").exists()


def test_empty_runs_are_never_the_diff_baseline(tmp_path):
    path = tmp_path / "history.jsonl"
    full = _snapshot([_trace("SB", 132468, "SB", 45891, True, [132468, 45891])])
    path.write_text(json.dumps(full) + "\n" + json.dumps(_snapshot([])) + "\n")

    assert sb_report.load_last_snapshot(path) == full


def test_diff_ignores_unfinished_results_and_duplicate_probe_counts():
    reached = _trace("NC", 45345, "SB", 45891, True, [45345, 45891])
    before = _snapshot([reached, reached], groups=("NC AS45345 Nautile (Noumea) x2",))
    after = _snapshot([reached, _trace("NC", 45345, "SB", 45891, False, [], status="offline")],
                      groups=("NC AS45345 Nautile (Noumea) x1",))

    assert sb_report.diff_snapshots(before, after) == [
        "probe group changed: NC AS45345 Nautile (Noumea) x2 => NC AS45345 Nautile (Noumea) x1"]


def _trace(src_cc, src_asn, target_cc, target_asn, reached, as_path, **extra):
    base = {"src_cc": src_cc, "src_asn": src_asn, "src_city": "City", "target_cc": target_cc,
            "target_asn": target_asn, "target_ip": "192.0.2.1", "reached": reached,
            "rtt_ms": 12.0 if reached else None, "last_address": None if reached else "192.0.2.254",
            "last_rtt_ms": None if reached else 40.0, "as_path": as_path, "ixps": [],
            "floor_ms": 0.0, "below_floor": False}
    return base | extra


def _snapshot(traces, groups=("SB AS132468 SATSOL (Honiara) x1",)):
    return {"date": "2026-11-25", "probe_groups": list(groups), "skipped_probes": [], "measurement_ids": ["m1"],
            "tests": len(traces), "unmeasured": [], "traces": traces}


def test_diff_reports_path_and_probe_group_changes():
    before = _snapshot([_trace("SB", 132468, "SB", 45891, True, [132468, 139609, 45891])])
    after = _snapshot([_trace("SB", 132468, "SB", 45891, False, [132468, 139609])],
                      groups=("SB AS132468 SATSOL (Honiara) x1", "SB AS45891 Our Telekom (Honiara) x1"))

    changes = sb_report.diff_snapshots(before, after)

    assert changes == [
        "probe group new: SB AS45891 Our Telekom (Honiara) x1",
        "AS132468 City (SB) -> AS45891: reached [AS132468 AS139609 AS45891] => not reached [AS132468 AS139609]",
    ]
    assert sb_report.diff_snapshots(None, after) == ["first run"]


def test_report_sections_and_out_of_region_ixp():
    ixp = {"hop": 4, "name": "IX Australia NSW", "in_fishbowl": False, "rtt_ms": 38.3}
    snapshot = _snapshot([
        _trace("SB", 132468, "SB", 45891, True, [132468, 139609, 45891], ixps=[ixp]),
        _trace("NC", 45345, "SB", 45891, False, [45345]),
        _trace("SB", 132468, "FJ", 4638, True, [132468, 4638]),
    ])

    report = sb_report.render_report(snapshot, ["first run"], {132468: "SB", 139609: "SB", 45891: "SB",
                                                               45345: "NC", 4638: "FJ"})

    assert "Domestic (SB -> SB): 1 traces" in report
    assert "Inbound (other Pacific -> SB): 1 traces" in report
    assert "Outbound (SB -> other Pacific economies): 1 traces" in report
    assert "AS132468(SB) AS139609(SB) AS45891(SB) | IX IX Australia NSW (out of region) 38.3 ms" in report
    assert "dark after 192.0.2.254 (40.0 ms)" in report
    assert "Faster than fibre allows" in report and "  (none)" in report


def test_report_tags_satellite_operators_on_the_path():
    # Shape of the 2026-11-23 SB -> NU AS10025 trace: Sydney via Lumen and OneQode, then Kacific GEO to Niue.
    niue = _trace("SB", 132468, "NU", 10025, True, [3356, 7594, 135409, 10025])
    cable = _trace("SB", 132468, "FJ", 4638, True, [132468, 4638])

    report = sb_report.render_report(_snapshot([niue, cable]), [], {132468: "SB", 10025: "NU", 4638: "FJ"})

    assert "AS3356 AS7594 AS135409 AS10025(NU) | satellite Kacific Broadband Satellites (GEO)" in report
    assert report.count("| satellite ") == 1
    assert "geostationary operator" in report


@pytest.fixture
def run_calls(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(sb_corridors, "run", lambda fire_measurements, budget: calls.append((fire_measurements, budget)))
    return calls


def test_help_exits_without_running(monkeypatch, run_calls):
    monkeypatch.setattr(sys, "argv", ["pacific-peering-globalping-sb", "--help"])
    with pytest.raises(SystemExit) as exc:
        sb_corridors.main()
    assert exc.value.code == 0
    assert run_calls == []


def test_default_is_a_dry_run_and_fire_fires(monkeypatch, run_calls):
    monkeypatch.setattr(sys, "argv", ["pacific-peering-globalping-sb"])
    sb_corridors.main()
    monkeypatch.setattr(sys, "argv", ["pacific-peering-globalping-sb", "--fire", "--budget", "100"])
    sb_corridors.main()
    assert run_calls == [(False, 240), (True, 100)]


def test_unknown_flag_errors_without_running(monkeypatch, run_calls):
    monkeypatch.setattr(sys, "argv", ["pacific-peering-globalping-sb", "--fier"])
    with pytest.raises(SystemExit) as exc:
        sb_corridors.main()
    assert exc.value.code == 2
    assert run_calls == []
