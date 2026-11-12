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


# Probe 1018023 (SPC Tonga, AS38198) drops ICMP traceroute past hop 1 but
# passes UDP (measurements 218132808 vs 218166491, 2026-10-02). Atlas sets
# protocol per measurement, so only an all-overridden probe list switches.
def test_create_traceroute_uses_udp_for_an_overridden_probe(monkeypatch):
    posted = _capture_post(monkeypatch)
    monkeypatch.setattr(client, "PROBE_PROTOCOL_OVERRIDES", {1018023: "UDP"})

    client.create_traceroute_measurement("probes", "1018023", "1.1.1.1", "d", 1, api_key="k")

    assert posted[0]["definitions"][0]["protocol"] == "UDP"


def test_create_traceroute_keeps_icmp_when_probes_are_mixed(monkeypatch):
    posted = _capture_post(monkeypatch)
    monkeypatch.setattr(client, "PROBE_PROTOCOL_OVERRIDES", {1018023: "UDP"})

    client.create_traceroute_measurement("probes", "1018023,11691", "1.1.1.1", "d", 2, api_key="k")
    client.create_traceroute_measurement("country", "TO", "1.1.1.1", "d", 2, api_key="k")

    assert [p["definitions"][0]["protocol"] for p in posted] == ["ICMP", "ICMP"]


# --- Transient-failure retries on Atlas GETs (2026-11-12) ---
# The weekly ROV re-run created 236756255, then its first status poll hit a
# 30 s ReadTimeout (Atlas was answering in ~22 s) and the whole run died.
# Status and results GETs are idempotent, so transient failures are retried.


class _JsonResponse:
    def __init__(self, payload, status_code=200):
        self._payload, self.status_code = payload, status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)

    def json(self):
        return self._payload


def _scripted_get(monkeypatch, outcomes):
    """Patch requests.get to raise or return each outcome in turn; returns the call log."""
    calls = []
    outcomes = iter(outcomes)

    def _get(url, timeout=None, **kwargs):
        calls.append(url)
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(client.requests, "get", _get)
    monkeypatch.setattr(client.time, "sleep", lambda seconds: None)
    return calls


def test_status_poll_retries_a_read_timeout(monkeypatch):
    calls = _scripted_get(monkeypatch, [
        requests.exceptions.ReadTimeout("Read timed out. (read timeout=30.0)"),
        _JsonResponse({"status": {"name": "Ongoing"}}),
    ])

    assert client.fetch_measurement_status(236756255) == "Ongoing"
    assert len(calls) == 2


def test_status_poll_raises_once_retries_are_exhausted(monkeypatch):
    calls = _scripted_get(monkeypatch, [requests.exceptions.ReadTimeout("timed out")] * 3)

    try:
        client.fetch_measurement_status(236756255)
    except requests.exceptions.ReadTimeout:
        pass
    else:
        raise AssertionError("expected ReadTimeout after the last retry")
    assert len(calls) == 3  # first try + 2 retries


def test_results_fetch_retries_a_server_error(monkeypatch):
    calls = _scripted_get(monkeypatch, [
        _JsonResponse({}, status_code=502),
        _JsonResponse([{"prb_id": 7018}]),
    ])

    assert client.fetch_raw_results(236756255) == [{"prb_id": 7018}]
    assert len(calls) == 2


def test_a_client_error_is_not_retried(monkeypatch):
    calls = _scripted_get(monkeypatch, [_JsonResponse({}, status_code=404)])

    try:
        client.fetch_measurement_status(1)
    except requests.HTTPError:
        pass
    else:
        raise AssertionError("expected the 404 to raise")
    assert len(calls) == 1


# --- The probe's own source address is kept (2026-11-13) ---
# Niue probe 64391 sits on public addresses, so its own gateway is the first
# resolved ASN on every path; `src_addr` lets rule 0 see past it.

RAW_64391 = {
    "msm_id": 236238083, "prb_id": 64391, "dst_addr": "1.1.1.1",
    "src_addr": "49.156.50.5", "from": "14.1.76.105",
    "result": [{"hop": 1, "result": [{"from": "49.156.50.254", "rtt": 0.4}]}],
}


def test_parse_keeps_the_probes_own_source_address():
    (result,) = client.parse_traceroute_results([RAW_64391])
    assert result.source_address == "49.156.50.5"  # src_addr, not `from` (the control-plane address)


def test_parsed_cache_records_the_source_address(monkeypatch, tmp_path):
    import json

    from pacific_peering.atlas import smoketest

    monkeypatch.setattr(smoketest, "DEFAULT_RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(smoketest, "DEFAULT_PARSED_DIR", tmp_path / "parsed")
    smoketest.persist_results(236238083, [RAW_64391])

    (parsed,) = json.loads((tmp_path / "parsed" / "236238083.json").read_text())
    assert parsed["source_address"] == "49.156.50.5"
