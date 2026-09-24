"""Tests for the offshore-hosting check (atlas/offshore_check.py)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pacific_peering.atlas import offshore_check as oc

NOW = datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc)
SYDNEY = (-33.79, 151.13)  # AU probe 31347, northern Sydney
PERTH = (-31.99, 115.78)


def test_physical_minimum_sydney_to_port_vila():
    assert 24 < oc.physical_min_rtt_ms(SYDNEY, "VU") < 26


def test_sydney_hosted_address_beats_physics():
    # Real 2026-09-24 numbers: 103.101.192.1 answered a Sydney probe in 0.825ms.
    judged = oc.judge_address([{"prb_id": 31347, "min": 0.825}], "VU", {31347: SYDNEY})
    assert judged["verdict"] == "offshore"
    assert abs(judged["violations"][0]["rtt_ms"] - 0.825) < 0.01


def test_genuinely_local_address_is_consistent():
    # ~45ms from Sydney to Port Vila is plausible for a real VU host.
    judged = oc.judge_address(
        [{"prb_id": 1, "min": 45.0}, {"prb_id": 2, "min": 95.0}], "VU", {1: SYDNEY, 2: PERTH}
    )
    assert judged == {"verdict": "consistent", "answered": 2, "violations": []}


def test_no_reply_and_unknown_probe_location():
    assert oc.judge_address([{"prb_id": 1, "min": -1}], "VU", {1: SYDNEY})["verdict"] == "no_response"
    # A reply from a probe with no known location can't beat physics.
    assert oc.judge_address([{"prb_id": 9, "min": 0.5}], "VU", {})["verdict"] == "consistent"


def test_asn_verdict_precedence():
    assert oc.asn_verdict({"a": {"verdict": "consistent"}, "b": {"verdict": "offshore"}}) == "offshore"
    assert oc.asn_verdict({"a": {"verdict": "no_response"}, "b": {"verdict": "consistent"}}) == "consistent"
    assert oc.asn_verdict({"a": {"verdict": "not_measured"}}) == "not_measured"


REGISTRY = {1: "VU", 2: "FJ", 3: "WS"}


def _run(mode, days_ago, asns):
    return {"run_at": (NOW - timedelta(days=days_ago)).isoformat(), "mode": mode, "asns": [str(a) for a in asns], "results": {}}


def test_schedule_full_when_never_run_or_month_old():
    assert oc.plan_run(REGISTRY, [], NOW) == ("full", [1, 2, 3])
    assert oc.plan_run(REGISTRY, [_run("full", 30, [1, 2, 3])], NOW) == ("full", [1, 2, 3])


def test_schedule_new_asns_only_between_full_runs():
    history = [_run("full", 10, [1, 2]), _run("new", 3, [])]
    assert oc.plan_run(REGISTRY, history, NOW) == ("new", [3])
    assert oc.plan_run(REGISTRY, history + [_run("new", 1, [3])], NOW) == ("skip", [])


def test_only_new_offshore_flags_escalate(tmp_path, monkeypatch):
    monkeypatch.setattr(oc, "ESCALATIONS_PATH", tmp_path / "escalations.md")
    offshore_addr = {"verdict": "offshore", "measurement_id": 7,
                     "violations": [{"probe": 31347, "rtt_ms": 0.83, "physical_min_ms": 24.7}]}
    per_asn = {"136996": {"cc": "VU", "verdict": "offshore", "addresses": {"103.101.192.1": offshore_addr}},
               "9249": {"cc": "VU", "verdict": "consistent", "addresses": {}}}
    history = [{"results": {"555": {"verdict": "offshore"}}}]

    new = oc._new_offshore(history + [{"results": {"136996": {"verdict": "consistent"}}}], per_asn)
    assert new == ["136996"]
    assert oc._new_offshore([{"results": {"136996": {"verdict": "offshore"}}}], per_asn) == []

    oc._escalate(new, per_asn, NOW)
    text = (tmp_path / "escalations.md").read_text()
    assert "## AS136996 (VU) -- possible offshore-hosted address space" in text
    assert "0.83ms < 24.7ms minimum (measurement 7)" in text
