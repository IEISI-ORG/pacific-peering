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


def _run(mode, days_ago, measured=(), unmeasured=(), untestable=()):
    results = {str(a): {"verdict": "consistent"} for a in measured}
    results.update({str(a): {"verdict": "not_measured"} for a in unmeasured})
    return {"run_at": (NOW - timedelta(days=days_ago)).isoformat(), "mode": mode, "results": results,
            "untestable": list(untestable), "complete": not unmeasured}


def test_schedule_full_when_never_run_or_month_old():
    assert oc.plan_run(REGISTRY, [], NOW) == ("full", [1, 2, 3])
    assert oc.plan_run(REGISTRY, [_run("full", 30, measured=[1, 2, 3])], NOW) == ("full", [1, 2, 3])


def test_schedule_new_asns_only_between_full_runs():
    history = [_run("full", 10, measured=[1], untestable=[2])]
    assert oc.plan_run(REGISTRY, history, NOW) == ("new", [3])
    assert oc.plan_run(REGISTRY, history + [_run("new", 1, measured=[3])], NOW) == ("skip", [])


def test_incomplete_full_run_does_not_count():
    # 2026-09-24: Atlas refused ~160 pings; such a run must not block retries for a month.
    assert oc.plan_run(REGISTRY, [_run("full", 1, measured=[1], unmeasured=[2, 3])], NOW) == ("full", [1, 2, 3])


def test_unmeasured_asns_are_retried_between_full_runs():
    history = [_run("full", 10, measured=[1, 2, 3]), _run("new", 2, unmeasured=[3])]
    assert oc.plan_run(REGISTRY, history, NOW)[0] == "skip"  # 3 was measured in the full run
    history = [_run("full", 10, measured=[1, 2]), _run("new", 2, unmeasured=[3])]
    assert oc.plan_run(REGISTRY, history, NOW) == ("new", [3])


def _refusal(text):
    import requests

    response = requests.Response()
    response.status_code = 400
    response._content = text.encode()
    return requests.HTTPError(response=response)


def test_concurrency_cap_is_retried_then_succeeds(monkeypatch):
    calls = []

    def _create(specs, target, description):
        calls.append(target)
        if len(calls) == 1:
            raise _refusal('{"detail":"You are not permitted to run more than 100 concurrent measurements."}')
        return 42

    monkeypatch.setattr(oc, "create_ping_measurement", _create)
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)

    assert oc._create_with_retry(9249, "VU", "202.80.35.1") == 42
    assert len(calls) == 2


def test_other_refusals_are_not_retried(monkeypatch):
    calls = []

    def _create(specs, target, description):
        calls.append(target)
        raise _refusal('{"detail":"Text contains disallowed characters"}')

    monkeypatch.setattr(oc, "create_ping_measurement", _create)
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)

    assert oc._create_with_retry(9249, "VU", "202.80.35.1") is None
    assert len(calls) == 1


def test_batches_do_not_overlap(monkeypatch, tmp_path):
    events = []
    counter = iter(range(1000, 2000))
    monkeypatch.setattr(oc, "BATCH_SIZE", 2)
    monkeypatch.setattr(oc, "DEFAULT_RAW_DIR", tmp_path)
    monkeypatch.setattr(oc, "_create_with_retry", lambda asn, cc, a: (events.append(("create", a)), next(counter))[1])
    monkeypatch.setattr(oc, "_wait_until_done", lambda ids: events.append(("wait", tuple(ids))))
    monkeypatch.setattr(oc, "fetch_raw_results", lambda mid: [{"prb_id": 1, "min": 50.0}])
    monkeypatch.setattr(oc, "wait_for_headroom", lambda n: events.append(("preflight", n)) or True)

    ids, raw = oc._measure([(1, "VU", "a"), (2, "VU", "b"), (3, "VU", "c")])

    assert [e[0] for e in events] == ["preflight", "create", "create", "wait", "preflight", "create", "wait"]
    assert [e[1] for e in events if e[0] == "preflight"] == [2, 1]  # asks for room for each batch
    assert set(raw) == {"a", "b", "c"}


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
