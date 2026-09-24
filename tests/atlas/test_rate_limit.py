"""Tests for the Atlas account-level pre-flight check (atlas/rate_limit.py)."""

from __future__ import annotations

from pacific_peering.atlas import rate_limit as rl


def _counter(values):
    it = iter(values)
    return lambda: next(it)


def test_room_available_returns_immediately():
    sleeps = []
    assert rl.wait_for_headroom(20, counter=_counter([40]), sleep=sleeps.append) is True
    assert sleeps == []


def test_waits_until_the_batch_fits_under_cap_minus_margin():
    # Limit is 100 - 5 = 95: 90 + 20 doesn't fit, 70 + 20 does.
    sleeps = []
    assert rl.wait_for_headroom(20, poll_s=60, counter=_counter([103, 90, 70]), sleep=sleeps.append) is True
    assert sleeps == [60, 60]


def test_gives_up_after_max_wait_and_lets_the_caller_fire():
    sleeps = []
    ok = rl.wait_for_headroom(1, max_wait_s=120, poll_s=60, counter=_counter([99] * 10), sleep=sleeps.append)
    assert ok is False
    assert sleeps == [60, 60]


def test_fails_open_when_the_count_cant_be_read():
    assert rl.wait_for_headroom(50, counter=_counter([None]), sleep=lambda s: None) is True


def test_count_in_flight_uses_one_status_in_query(monkeypatch):
    seen = {}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"count": 17}

    def _get(url, params, headers, timeout):
        seen.update(url=url, params=params)
        return _Resp()

    monkeypatch.setattr(rl.requests, "get", _get)

    assert rl.count_in_flight(api_key="k") == 17
    assert seen["params"]["status__in"] == "0,1,2"
    assert seen["url"].endswith("/measurements/my/")


def test_count_in_flight_returns_none_on_network_error(monkeypatch):
    def _get(*a, **k):
        raise rl.requests.ConnectionError("down")

    monkeypatch.setattr(rl.requests, "get", _get)
    assert rl.count_in_flight(api_key="k") is None
