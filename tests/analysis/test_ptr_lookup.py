"""ptr_lookup: rate-capped bulk PTR lookups that keep failures apart from "no PTR".

2026-11-06 (sysadm hand-off): 16 unthrottled gethostbyaddr workers sent
~4,600 lookups through lab's Pi-hole on ::1 in three minutes, tripped its
1000/min per-client limit, and Pi-hole REFUSED every query from lab for
~4 minutes. REFUSED came back as "no PTR" and split routers.
"""

from __future__ import annotations

import threading
import time

import dns.exception
import dns.resolver
import pytest

from pacific_peering.analysis import ptr_lookup as pl

TODAY = "2026-11-06"


class _FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, s):
        self.now += s


class _CountingLimiter:
    def __init__(self):
        self.calls = 0

    def acquire(self):
        self.calls += 1


def _fail(address):
    raise pl.PtrLookupFailed(address)


# --- RateLimiter ---------------------------------------------------------------

def test_rate_limiter_spaces_acquires_at_the_cap():
    clock = _FakeClock()
    limiter = pl.RateLimiter(10.0, clock=clock.monotonic, sleep=clock.sleep)
    for _ in range(21):
        limiter.acquire()
    assert clock.now == pytest.approx(2.0)  # 21 lookups at 10/s: the 21st starts at t=2.0s


def test_rate_limiter_holds_across_threads():
    limiter = pl.RateLimiter(50.0)
    start = time.monotonic()
    threads = [threading.Thread(target=lambda: [limiter.acquire() for _ in range(5)]) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert time.monotonic() - start >= 19 / 50.0 - 0.01  # 20 acquires, 19 gaps of 20ms


# --- resolve_ptrs --------------------------------------------------------------

def test_every_lookup_including_retries_goes_through_the_one_limiter():
    limiter = _CountingLimiter()
    pl.resolve_ptrs(["9.9.9.1", "9.9.9.2"], _fail, {}, today=TODAY, limiter=limiter)
    assert limiter.calls == 4  # two addresses, first pass + one retry each


def test_nxdomain_is_cached_as_no_ptr_and_not_asked_again():
    cache: dict = {}
    names, failed = pl.resolve_ptrs(["9.9.9.1"], lambda a: None, cache, today=TODAY, limiter=_CountingLimiter())
    assert names == {"9.9.9.1": None} and failed == set()
    assert cache["9.9.9.1"] == {"name": None, "checked": TODAY}
    calls = []
    pl.resolve_ptrs(["9.9.9.1"], lambda a: calls.append(a), cache, today="2026-11-20", limiter=_CountingLimiter())
    assert calls == []


def test_a_failed_lookup_is_never_cached_and_is_reported():
    cache: dict = {}
    names, failed = pl.resolve_ptrs(["9.9.9.1"], _fail, cache, today=TODAY, limiter=_CountingLimiter())
    assert names == {"9.9.9.1": None} and failed == {"9.9.9.1"}
    assert cache == {}


def test_a_failed_lookup_keeps_the_previously_cached_name():
    cache = {"9.9.9.1": {"name": "be1.core1.hub.example.net", "checked": "2026-09-01"}}  # stale, so due
    names, failed = pl.resolve_ptrs(["9.9.9.1"], _fail, cache, today=TODAY, limiter=_CountingLimiter())
    assert names == {"9.9.9.1": "be1.core1.hub.example.net"} and failed == {"9.9.9.1"}
    assert cache["9.9.9.1"]["checked"] == "2026-09-01"


def test_a_failure_is_retried_once_in_the_same_run():
    answers = iter([pl.PtrLookupFailed("9.9.9.1"), "be1.core1.hub.example.net"])

    def flaky(address):
        a = next(answers)
        if isinstance(a, Exception):
            raise a
        return a

    names, failed = pl.resolve_ptrs(["9.9.9.1"], flaky, {}, today=TODAY, limiter=_CountingLimiter())
    assert names == {"9.9.9.1": "be1.core1.hub.example.net"} and failed == set()


def test_fresh_cache_entries_are_not_looked_up():
    cache = {"9.9.9.1": {"name": "be1.core1.hub.example.net", "checked": "2026-11-01"}}
    limiter = _CountingLimiter()
    names, _ = pl.resolve_ptrs(["9.9.9.1"], _fail, cache, today=TODAY, limiter=limiter)
    assert names == {"9.9.9.1": "be1.core1.hub.example.net"} and limiter.calls == 0


# --- unbound resolver: REFUSED/SERVFAIL/timeout are failures, NXDOMAIN is "no PTR" ---

class _StubResolver:
    def __init__(self, outcome):
        self.outcome = outcome

    def resolve_address(self, address, **kw):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return [type("Rr", (), {"target": type("N", (), {"to_text": lambda s: self.outcome})()})()]


def test_unbound_lookup_returns_the_name():
    lookup = pl.unbound_lookup(_StubResolver("be2378.ccr51.pdx02.atlas.cogentco.com."))
    assert lookup("154.54.164.22") == "be2378.ccr51.pdx02.atlas.cogentco.com"


@pytest.mark.parametrize("exc", [dns.resolver.NXDOMAIN(), dns.resolver.NoAnswer()])
def test_unbound_nxdomain_and_no_answer_mean_no_ptr(exc):
    assert pl.unbound_lookup(_StubResolver(exc))("9.9.9.1") is None


@pytest.mark.parametrize("exc", [dns.resolver.NoNameservers(), dns.resolver.LifetimeTimeout(timeout=3.0, errors=[]),
                                 dns.exception.Timeout()])
def test_unbound_refused_servfail_and_timeout_are_failures(exc):
    with pytest.raises(pl.PtrLookupFailed):
        pl.unbound_lookup(_StubResolver(exc))("9.9.9.1")


def test_default_resolver_targets_local_unbound_not_resolv_conf():
    r = pl.make_unbound_resolver()
    assert r.nameservers == ["127.0.0.1"] and r.port == 5335
