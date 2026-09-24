"""Regression tests for atlas.client.wait_for_results's terminal-status race.

Atlas's own status and results endpoints aren't atomically consistent: a
measurement can read as terminal (e.g. "Stopped") moments before its results
are actually indexed. Caught 2026-09-20 via measurement 213457173 -- the
first fetch right after reaching terminal status came back empty even though
the measurement had a real probe result, and that empty list got cached and
misclassified downstream (see tests/analysis/test_auto_classify.py). This
file locks in the retry behavior added to fix it.
"""

from __future__ import annotations

import requests

from pacific_peering.atlas import client


def test_retries_on_empty_result_after_terminal_status(monkeypatch):
    """First fetch after terminal status is empty; a later retry has real data."""
    monkeypatch.setattr(client, "fetch_measurement_status", lambda mid, timeout=30.0: "Stopped")
    fetches = iter([[], [], [{"prb_id": 65653}]])
    monkeypatch.setattr(client, "fetch_raw_results", lambda mid, timeout=30.0: next(fetches))
    monkeypatch.setattr(client.time, "sleep", lambda seconds: None)

    result = client.wait_for_results(
        213457173, empty_result_retries=3, empty_result_retry_delay=0.0
    )

    assert result == [{"prb_id": 65653}]


def test_gives_up_after_exhausting_retries_on_genuinely_empty_result(monkeypatch):
    """A 'Stopped' measurement that's genuinely still empty after every retry
    stays empty, not an error -- and stops retrying at the configured limit."""
    monkeypatch.setattr(client, "fetch_measurement_status", lambda mid, timeout=30.0: "Stopped")
    call_count = 0

    def _fetch(mid, timeout=30.0):
        nonlocal call_count
        call_count += 1
        return []

    monkeypatch.setattr(client, "fetch_raw_results", _fetch)
    monkeypatch.setattr(client.time, "sleep", lambda seconds: None)

    result = client.wait_for_results(
        123456, empty_result_retries=2, empty_result_retry_delay=0.0
    )

    assert result == []
    assert call_count == 3  # first fetch + 2 retries, never a 4th


def test_no_suitable_probes_skips_retry_entirely(monkeypatch):
    """'No suitable probes' is a durable fact, not a fetch race -- no retry."""
    monkeypatch.setattr(
        client, "fetch_measurement_status", lambda mid, timeout=30.0: "No suitable probes"
    )
    call_count = 0

    def _fetch(mid, timeout=30.0):
        nonlocal call_count
        call_count += 1
        return []

    monkeypatch.setattr(client, "fetch_raw_results", _fetch)

    def _no_sleep_allowed(seconds):
        raise AssertionError("should not sleep when skipping the empty-result retry loop")

    monkeypatch.setattr(client.time, "sleep", _no_sleep_allowed)

    result = client.wait_for_results(999, empty_result_retries=3, empty_result_retry_delay=5.0)

    assert result == []
    assert call_count == 1


def test_transient_fetch_error_during_retry_is_tolerated(monkeypatch):
    """A single flaky fetch (timeout/5xx) during the retry window shouldn't
    abort the retries whose whole purpose is tolerating Atlas flakiness."""
    monkeypatch.setattr(client, "fetch_measurement_status", lambda mid, timeout=30.0: "Stopped")
    responses = iter(
        [[], requests.exceptions.ConnectionError("boom"), [{"prb_id": 7}]]
    )

    def _fetch(mid, timeout=30.0):
        outcome = next(responses)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(client, "fetch_raw_results", _fetch)
    monkeypatch.setattr(client.time, "sleep", lambda seconds: None)

    result = client.wait_for_results(
        42, empty_result_retries=3, empty_result_retry_delay=0.0
    )

    assert result == [{"prb_id": 7}]


def test_no_retry_needed_when_first_fetch_already_has_data(monkeypatch):
    """The common case: results are already there on the first fetch -- no extra calls."""
    monkeypatch.setattr(client, "fetch_measurement_status", lambda mid, timeout=30.0: "Stopped")
    call_count = 0

    def _fetch(mid, timeout=30.0):
        nonlocal call_count
        call_count += 1
        return [{"prb_id": 1}]

    monkeypatch.setattr(client, "fetch_raw_results", _fetch)
    monkeypatch.setattr(client.time, "sleep", lambda seconds: None)

    result = client.wait_for_results(1, empty_result_retries=3, empty_result_retry_delay=0.0)

    assert result == [{"prb_id": 1}]
    assert call_count == 1


class _FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"measurements": [214999999]}


def _capture_post(monkeypatch):
    posted = []

    def _post(url, json, headers, timeout):
        posted.append(json)
        return _FakeResponse()

    monkeypatch.setattr(client.requests, "post", _post)
    return posted


def test_create_traceroute_defaults_to_ipv4(monkeypatch):
    posted = _capture_post(monkeypatch)

    client.create_traceroute_measurement("probes", "1008228", "1.1.1.1", "d", 1, api_key="k")

    assert posted[0]["definitions"][0]["af"] == 4


def test_create_traceroute_passes_af_6_through(monkeypatch):
    posted = _capture_post(monkeypatch)

    client.create_traceroute_measurement(
        "probes", "1008228", "2606:4700:4700::1111", "d", 1, api_key="k", af=6
    )

    assert posted[0]["definitions"][0]["af"] == 6
    assert posted[0]["definitions"][0]["target"] == "2606:4700:4700::1111"


def test_create_traceroute_rejects_unknown_af_before_posting(monkeypatch):
    posted = _capture_post(monkeypatch)

    try:
        client.create_traceroute_measurement("probes", "1", "1.1.1.1", "d", 1, api_key="k", af=5)
    except ValueError:
        pass
    else:
        raise AssertionError("af=5 must be rejected")
    assert posted == []


def test_create_traceroute_rejects_overlong_description_before_posting(monkeypatch):
    posted = _capture_post(monkeypatch)

    try:
        client.create_traceroute_measurement("probes", "1", "1.1.1.1", "x" * 255, 1, api_key="k")
    except ValueError:
        pass
    else:
        raise AssertionError("a 255-char description must be rejected")
    assert posted == []


def test_create_ping_measurement_payload(monkeypatch):
    posted = _capture_post(monkeypatch)
    specs = [{"type": "country", "value": "AU", "requested": 3}, {"type": "country", "value": "NZ", "requested": 2}]

    client.create_ping_measurement(specs, "103.101.192.1", "d", api_key="k")

    definition = posted[0]["definitions"][0]
    assert (definition["type"], definition["packets"], definition["af"]) == ("ping", 3, 4)
    assert posted[0]["probes"] == specs


def test_create_ping_measurement_shares_the_description_check(monkeypatch):
    posted = _capture_post(monkeypatch)
    try:
        client.create_ping_measurement([], "1.1.1.1", "a -> b", api_key="k")
    except ValueError:
        pass
    else:
        raise AssertionError("'>' must be rejected")
    assert posted == []


def test_stop_measurement_deletes_and_never_raises(monkeypatch):
    calls = []

    class _Ok:
        def raise_for_status(self):
            pass

    def _delete(url, headers, timeout):
        calls.append(url)
        return _Ok()

    monkeypatch.setattr(client.requests, "delete", _delete)
    assert client.stop_measurement(215118287, api_key="k") is True
    assert calls[0].endswith("/measurements/215118287/")

    def _boom(url, headers, timeout):
        raise client.requests.ConnectionError("down")

    monkeypatch.setattr(client.requests, "delete", _boom)
    assert client.stop_measurement(1, api_key="k") is False
