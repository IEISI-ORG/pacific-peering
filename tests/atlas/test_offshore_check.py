"""Tests for the offshore-hosting check (atlas/offshore_check.py)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from pacific_peering.atlas import offshore_check as oc

NOW = datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc)
SYDNEY = (-33.79, 151.13)  # AU probe 31347, northern Sydney
PERTH = (-31.99, 115.78)


def test_physical_minimum_sydney_to_port_vila():
    assert 24 < oc.physical_min_rtt_ms(SYDNEY, "VU") < 26


TOKYO = (35.69, 139.69)
LA = (34.05, -118.26)


def test_one_probe_beating_physics_is_only_unconfirmed():
    # Real 2026-09-24 numbers: 103.101.192.1 answered a Sydney probe in 0.825ms.
    judged = oc.judge_address([{"prb_id": 31347, "min": 0.825}], "VU", {31347: SYDNEY}, {31347: 137576})
    assert judged["verdict"] == "unconfirmed"
    assert abs(judged["violations"][0]["rtt_ms"] - 0.825) < 0.01


def test_two_networks_beating_physics_is_offshore():
    # AS23959's 194.127.166.1: Tokyo probes on AS3258 and AS4713, 11.2/13.2ms vs ~67ms minimum.
    judged = oc.judge_address(
        [{"prb_id": 1014094, "min": 11.19}, {"prb_id": 1007464, "min": 13.16}],
        "VU", {1014094: TOKYO, 1007464: TOKYO}, {1014094: 3258, 1007464: 4713},
    )
    assert judged["verdict"] == "offshore"


def test_two_probes_on_the_same_network_stay_unconfirmed():
    judged = oc.judge_address(
        [{"prb_id": 1, "min": 1.0}, {"prb_id": 2, "min": 2.0}], "VU", {1: SYDNEY, 2: SYDNEY}, {1: 4764, 2: 4764}
    )
    assert judged["verdict"] == "unconfirmed"


def test_mislocated_single_probe_case_is_unconfirmed():
    # AS58932's flag: probe 1000112 registered in LA but on AS3258 xTom Japan, 48.7ms to Palau.
    judged = oc.judge_address(
        [{"prb_id": 1000112, "min": 48.72}, {"prb_id": 1016950, "min": 48.4}],
        "PW", {1000112: LA, 1016950: TOKYO}, {1000112: 3258, 1016950: 401615},
    )
    assert judged["verdict"] == "unconfirmed"  # only the LA-registered probe beats physics


def test_probes_with_unknown_asn_count_as_separate_networks():
    judged = oc.judge_address(
        [{"prb_id": 1, "min": 1.0}, {"prb_id": 2, "min": 2.0}], "VU", {1: SYDNEY, 2: SYDNEY}, {}
    )
    assert judged["verdict"] == "offshore"


def test_genuinely_local_address_is_consistent():
    # ~45ms from Sydney to Port Vila is plausible for a real VU host.
    judged = oc.judge_address(
        [{"prb_id": 1, "min": 45.0}, {"prb_id": 2, "min": 95.0}], "VU", {1: SYDNEY, 2: PERTH}
    )
    assert judged == {"verdict": "consistent", "answered": 2, "violations": [],
                      "nearest": {"probe": 1, "cc": None, "rtt_ms": 45.0}}


def test_no_reply_and_unknown_probe_location():
    assert oc.judge_address([{"prb_id": 1, "min": -1}], "VU", {1: SYDNEY})["verdict"] == "no_response"
    # A reply from a probe with no known location can't beat physics.
    assert oc.judge_address([{"prb_id": 9, "min": 0.5}], "VU", {})["verdict"] == "consistent"


def test_asn_verdict_precedence():
    assert oc.asn_verdict({"a": {"verdict": "consistent"}, "b": {"verdict": "offshore"}}) == "offshore"
    assert oc.asn_verdict({"a": {"verdict": "no_response"}, "b": {"verdict": "consistent"}}) == "consistent"
    assert oc.asn_verdict({"a": {"verdict": "not_measured"}}) == "not_measured"
    assert oc.asn_verdict({"a": {"verdict": "unconfirmed"}, "b": {"verdict": "consistent"}}) == "unconfirmed"
    assert oc.asn_verdict({"a": {"verdict": "unconfirmed"}, "b": {"verdict": "offshore"}}) == "offshore"


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


def test_incomplete_full_run_is_retried_for_its_unmeasured_asns_only():
    # 2026-09-24: Atlas refused ~160 pings; such a run must not block retries for a month.
    # 2026-11-26 (owner: "build the retry mode"): retry only what it missed, not the whole sweep.
    assert oc.plan_run(REGISTRY, [_run("full", 1, measured=[1], unmeasured=[2, 3])], NOW) == ("retry", [2, 3])


def test_retries_continue_nightly_until_every_asn_is_measured():
    history = [_run("full", 2, measured=[1], unmeasured=[2, 3]), _run("retry", 1, measured=[2], unmeasured=[3])]
    assert oc.plan_run(REGISTRY, history, NOW) == ("retry", [3])
    assert oc.plan_run(REGISTRY, history + [_run("retry", 0, measured=[3])], NOW) == ("skip", [])


def test_retry_skips_untestable_and_includes_newly_added_asns():
    history = [_run("full", 1, measured=[1], unmeasured=[3], untestable=[2])]
    assert oc.plan_run({**REGISTRY, 4: "WS"}, history, NOW) == ("retry", [3, 4])


def test_retry_only_counts_runs_since_the_latest_full():
    # 3 measured last month does not cover this month's incomplete full.
    history = [_run("full", 40, measured=[1, 2, 3]), _run("full", 1, measured=[1, 2], unmeasured=[3])]
    assert oc.plan_run(REGISTRY, history, NOW) == ("retry", [3])


def test_incomplete_full_run_a_month_old_starts_a_new_full():
    history = [_run("full", 30, measured=[1], unmeasured=[2, 3]), _run("retry", 29, measured=[2, 3])]
    assert oc.plan_run(REGISTRY, history, NOW) == ("full", [1, 2, 3])


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


def _timeout_then(outcomes, calls):
    """A create_ping_measurement stand-in that raises or returns each outcome in turn."""
    outcomes = iter(outcomes)

    def _create(specs, target, description):
        calls.append(description)
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return _create


def test_create_timeout_adopts_the_measurement_atlas_made(monkeypatch):
    # 2026-11-26 02:32: the POST for 103.166.70.9 timed out (30 s read) and the
    # ReadTimeout killed the whole run, yet Atlas had created 244221908.
    calls, lookups = [], []
    monkeypatch.setattr(oc, "create_ping_measurement",
                        _timeout_then([requests.exceptions.ReadTimeout("timed out")], calls))
    monkeypatch.setattr(oc, "find_measurement_by_description",
                        lambda d, started_since: lookups.append(d) or 244221908)
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)

    assert oc._create_with_retry(139263, "PF", "103.166.70.9") == 244221908
    assert len(calls) == 1  # no second POST, so no duplicate ping
    assert lookups == ["pacific-peering offshore-check AS139263 PF to 103.166.70.9"]


def test_create_timeout_retries_when_atlas_made_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr(oc, "create_ping_measurement",
                        _timeout_then([requests.exceptions.ConnectionError("reset"), 43], calls))
    monkeypatch.setattr(oc, "find_measurement_by_description", lambda d, started_since: None)
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)

    assert oc._create_with_retry(9249, "VU", "202.80.35.1") == 43
    assert len(calls) == 2


def test_create_timeout_gives_up_if_the_lookup_fails_too(monkeypatch):
    calls = []
    monkeypatch.setattr(oc, "create_ping_measurement",
                        _timeout_then([requests.exceptions.ReadTimeout("timed out"), 43], calls))

    def _lookup(d, started_since):
        raise requests.exceptions.ReadTimeout("timed out")

    monkeypatch.setattr(oc, "find_measurement_by_description", _lookup)
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)

    # Unknown whether Atlas made it: skip the address rather than risk a duplicate.
    assert oc._create_with_retry(9249, "VU", "202.80.35.1") is None
    assert len(calls) == 1


def test_create_timeouts_stop_after_the_retry_limit(monkeypatch):
    calls = []
    monkeypatch.setattr(oc, "create_ping_measurement",
                        _timeout_then([requests.exceptions.ReadTimeout("timed out")] * 10, calls))
    monkeypatch.setattr(oc, "find_measurement_by_description", lambda d, started_since: None)
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)

    assert oc._create_with_retry(9249, "VU", "202.80.35.1") is None
    assert len(calls) == oc.CREATE_TIMEOUT_RETRIES + 1


def _server_error(status):
    response = requests.Response()
    response.status_code = status
    response._content = b"<html>502 Bad Gateway</html>"
    return requests.HTTPError(response=response)


def test_lookup_waits_then_searches_from_before_the_post(monkeypatch):
    events = []
    monkeypatch.setattr(oc.time, "time", lambda: 1795624366.4)
    monkeypatch.setattr(oc, "create_ping_measurement",
                        _timeout_then([requests.exceptions.ReadTimeout("timed out")], []))
    monkeypatch.setattr(oc.time, "sleep", lambda s: events.append(("sleep", s)))
    monkeypatch.setattr(oc, "find_measurement_by_description",
                        lambda d, started_since: events.append(("lookup", started_since)) or 244221908)

    oc._create_with_retry(139263, "PF", "103.166.70.9")

    assert events == [("sleep", oc.CREATE_LOOKUP_WAIT_S), ("lookup", 1795624366 - oc.CREATE_LOOKUP_SKEW_S)]


def test_server_error_on_create_is_looked_up_like_a_timeout(monkeypatch):
    # A 502/504 from Atlas's front end can hide a measurement the backend made.
    calls = []
    monkeypatch.setattr(oc, "create_ping_measurement", _timeout_then([_server_error(502)], calls))
    monkeypatch.setattr(oc, "find_measurement_by_description", lambda d, started_since: 244221908)
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)

    assert oc._create_with_retry(139263, "PF", "103.166.70.9") == 244221908
    assert len(calls) == 1


def test_unreadable_reply_to_a_create_is_looked_up(monkeypatch):
    # A broken body or an unexpected 2xx shape: Atlas may well have made it.
    for error in (requests.exceptions.ChunkedEncodingError("broken"), KeyError("measurements")):
        calls = []
        monkeypatch.setattr(oc, "create_ping_measurement", _timeout_then([error], calls))
        monkeypatch.setattr(oc, "find_measurement_by_description", lambda d, started_since: 244221908)
        monkeypatch.setattr(oc.time, "sleep", lambda s: None)

        assert oc._create_with_retry(139263, "PF", "103.166.70.9") == 244221908
        assert len(calls) == 1


def test_resend_after_a_timeout_still_honours_the_concurrency_cap(monkeypatch):
    calls = []
    monkeypatch.setattr(oc, "create_ping_measurement", _timeout_then([
        requests.exceptions.ReadTimeout("timed out"),
        _refusal('{"detail":"You are not permitted to run more than 100 concurrent measurements."}'),
        44,
    ], calls))
    monkeypatch.setattr(oc, "find_measurement_by_description", lambda d, started_since: None)
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)

    assert oc._create_with_retry(9249, "VU", "202.80.35.1") == 44
    assert len(calls) == 3


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


def test_duplicate_addresses_within_an_asn_are_pinged_once(monkeypatch, tmp_path):
    monkeypatch.setattr(oc, "REGISTRY_PATH", tmp_path / "reg.json")
    (tmp_path / "reg.json").write_text('{"VU": {"asns": [9249]}}')
    monkeypatch.setattr(oc, "load_history", lambda: [])
    # Covering /22 and a /24 inside it both give 202.80.34.1 (seen for AS9249).
    monkeypatch.setattr(oc, "list_target_ips", lambda asn, include_excluded=False: ["202.80.34.1", "202.80.34.1", "202.80.35.1"])
    seen = {}

    def _measure(targets):
        seen["targets"] = targets
        raise SystemExit  # stop after planning; nothing is fired

    monkeypatch.setattr(oc, "_measure", _measure)
    try:
        oc.run_check(fire=True, now=NOW)
    except SystemExit:
        pass
    assert [a for _, _, a in seen["targets"]] == ["202.80.34.1", "202.80.35.1"]


def test_nearest_vantage_records_fastest_probe_country():
    judged = oc.judge_address(
        [{"prb_id": 1, "min": 45.0}, {"prb_id": 7, "min": 12.5}], "VU", {1: SYDNEY, 7: SYDNEY},
        {1: 100, 7: 200}, {1: "AU", 7: "SG"},
    )
    assert judged["nearest"] == {"probe": 7, "cc": "SG", "rtt_ms": 12.5}


def test_new_screen_flags_skip_seen_and_acknowledged():
    history = [{"screen_flags": ["151398"]}]
    assert oc._new_screen_flags(history, ["151398", "45495", "56017"]) == ["56017"]


def test_hub_probes_include_sg_hk_gb():
    assert {s["value"] for s in oc.HUB_PROBE_SPECS} >= {"AU", "NZ", "US", "JP", "SG", "HK", "GB"}


def test_status_poll_failure_keeps_waiting_instead_of_ending_the_run(monkeypatch):
    # fetch_measurement_status already retries twice; on 2026-11-23 one
    # measurement timed out twice in a row, one short of raising.
    polls = iter([requests.exceptions.ReadTimeout("timed out"), "Stopped"])

    def _status(mid):
        outcome = next(polls)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(oc, "fetch_measurement_status", _status)
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)

    oc._wait_until_done([244221908], max_wait_s=3600)  # returns, no exception


def test_results_fetch_failure_leaves_only_that_address_unmeasured(monkeypatch, tmp_path):
    counter = iter(range(1000, 2000))
    monkeypatch.setattr(oc, "DEFAULT_RAW_DIR", tmp_path)
    monkeypatch.setattr(oc, "_create_with_retry", lambda asn, cc, a: next(counter))
    monkeypatch.setattr(oc, "_wait_until_done", lambda ids: None)
    monkeypatch.setattr(oc, "wait_for_headroom", lambda n: True)

    def _fetch(mid):
        if mid == 1001:
            raise requests.exceptions.ReadTimeout("timed out")
        return [{"prb_id": 1, "min": 50.0}]

    monkeypatch.setattr(oc, "fetch_raw_results", _fetch)

    ids, raw = oc._measure([(1, "VU", "a"), (2, "VU", "b"), (3, "VU", "c")])

    assert set(raw) == {"a", "c"}
    assert ids == {"a": 1000, "b": 1001, "c": 1002}  # the id is kept, so the run can be re-judged


def test_probe_info_keeps_trying_through_a_longer_outage(monkeypatch):
    # After a whole sweep's pings, a probes-endpoint outage must not end the run.
    attempts, sleeps = [], []

    def _fetch(ids, fields):
        attempts.append(ids)
        if len(attempts) < oc.PROBE_INFO_ATTEMPTS:
            raise requests.exceptions.ReadTimeout("timed out")
        return [{"id": 7, "geometry": {"coordinates": [151.13, -33.79]}, "asn_v4": 4826, "country_code": "AU"}]

    monkeypatch.setattr(oc, "fetch_probes", _fetch)
    monkeypatch.setattr(oc.time, "sleep", sleeps.append)

    locations, _, _ = oc._probe_info({7})
    assert locations == {7: (-33.79, 151.13)}
    assert sleeps == [oc.PROBE_INFO_RETRY_WAIT_S] * (oc.PROBE_INFO_ATTEMPTS - 1)


def test_probe_info_raises_rather_than_judging_without_locations(monkeypatch):
    # Missing locations would skip the physics check and read offshore as consistent.
    def _fetch(ids, fields):
        raise requests.exceptions.ReadTimeout("timed out")

    monkeypatch.setattr(oc, "fetch_probes", _fetch)
    monkeypatch.setattr(oc.time, "sleep", lambda s: None)

    try:
        oc._probe_info({7})
    except requests.exceptions.ReadTimeout:
        pass
    else:
        raise AssertionError("expected the last ReadTimeout to propagate")


def test_probe_info_reads_locations_asns_and_countries(monkeypatch):
    monkeypatch.setattr(oc, "fetch_probes", lambda ids, fields: [
        {"id": 7, "geometry": {"coordinates": [151.13, -33.79]}, "asn_v4": 4826, "country_code": "AU"},
        {"id": 8, "geometry": None, "asn_v4": None, "country_code": None},
    ])

    locations, asns, countries = oc._probe_info({7, 8})
    assert locations == {7: (-33.79, 151.13)}
    assert asns == {7: 4826, 8: None} and countries == {7: "AU", 8: None}
