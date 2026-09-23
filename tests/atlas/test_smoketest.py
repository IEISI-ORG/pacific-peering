"""Regression test for run_smoketest silently dropping a given target_ip.

Caught 2026-09-21: `auto_classify._fire_measurement` accepted a `target_ip`
argument (the whole point of the "retry against an alternate cached prefix
on a dead end" mechanism added 2026-09-19) but never passed it to
`run_smoketest`, which always re-derived the target ASN's *first* cached
prefix via `pick_target_ip` regardless. Every "retry against an alternate
prefix" actually re-tested the identical first address.
"""

from __future__ import annotations

from pacific_peering.atlas import smoketest


def test_run_smoketest_uses_the_given_target_ip_without_repicking(monkeypatch):
    monkeypatch.setattr(smoketest, "pick_best_covered_economy", lambda exclude_cc: "GU")
    monkeypatch.setattr(
        smoketest, "ECONOMIES_BY_CC", {"GU": type("E", (), {"name": "Guam"})()}
    )

    def _pick_target_ip(asn):
        raise AssertionError("must not re-derive the first cached prefix when target_ip is given")

    monkeypatch.setattr(smoketest, "pick_target_ip", _pick_target_ip)

    calls = []

    def _fire_and_persist(source_type, source_value, target_ip, description, probe_count):
        calls.append(target_ip)
        return 42

    monkeypatch.setattr(smoketest, "_fire_and_persist", _fire_and_persist)

    measurement_id = smoketest.run_smoketest(
        target_asn=7131, target_cc="MP", source_cc="GU", target_ip="203.78.152.1"
    )

    assert measurement_id == 42
    assert calls == ["203.78.152.1"]


def test_run_smoketest_falls_back_to_pick_target_ip_when_none_given(monkeypatch):
    monkeypatch.setattr(smoketest, "pick_best_covered_economy", lambda exclude_cc: "GU")
    monkeypatch.setattr(
        smoketest, "ECONOMIES_BY_CC", {"GU": type("E", (), {"name": "Guam"})()}
    )
    monkeypatch.setattr(smoketest, "pick_target_ip", lambda asn: "103.202.149.1")

    calls = []

    def _fire_and_persist(source_type, source_value, target_ip, description, probe_count):
        calls.append(target_ip)
        return 43

    monkeypatch.setattr(smoketest, "_fire_and_persist", _fire_and_persist)

    smoketest.run_smoketest(target_asn=7131, target_cc="MP", source_cc="GU")

    assert calls == ["103.202.149.1"]


def test_run_probe_sourced_traceroute_sources_by_explicit_probe_ids(monkeypatch):
    monkeypatch.setattr(smoketest, "pick_target_ip", lambda asn: "202.1.22.1")

    calls = []

    def _fire_and_persist(source_type, source_value, target_ip, description, probe_count):
        calls.append((source_type, source_value, target_ip, probe_count))
        return 99

    monkeypatch.setattr(smoketest, "_fire_and_persist", _fire_and_persist)

    measurement_id = smoketest.run_probe_sourced_traceroute(
        probe_ids=[1008228, 1008229], target_asn=154100
    )

    assert measurement_id == 99
    assert calls == [("probes", "1008228,1008229", "202.1.22.1", 2)]


def test_run_probe_sourced_traceroute_uses_given_target_ip_without_repicking(monkeypatch):
    def _pick_target_ip(asn):
        raise AssertionError("must not re-derive the target when target_ip is given")

    monkeypatch.setattr(smoketest, "pick_target_ip", _pick_target_ip)

    calls = []

    def _fire_and_persist(source_type, source_value, target_ip, description, probe_count):
        calls.append((source_type, source_value, target_ip, probe_count))
        return 100

    monkeypatch.setattr(smoketest, "_fire_and_persist", _fire_and_persist)

    smoketest.run_probe_sourced_traceroute(
        probe_ids=[64237], target_asn=24439, target_ip="203.215.52.1"
    )

    assert calls == [("probes", "64237", "203.215.52.1", 1)]
