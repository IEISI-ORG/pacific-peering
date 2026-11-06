"""Rate-capped bulk PTR lookups against lab's local unbound, with a 30-day cache.

2026-11-06 (sysadm hand-off): the first convergence runs sent ~4,600
in-addr.arpa lookups in three minutes through glibc to Pi-hole on ::1, from
16 unthrottled `gethostbyaddr` workers plus a retry pass. Pi-hole limits each
client to 1000 queries/min, and every process on lab shares the ::1 identity,
so it REFUSED all of lab's DNS (github.com, api.anthropic.com, cloudflared,
the heartbeat) for ~4 minutes. Those REFUSED answers came back as "no PTR"
and split routers between runs, the 967-vs-1003 drift first put down to load.

So bulk lookups here:
- go straight to unbound at 127.0.0.1:5335, never through /etc/resolv.conf,
  keeping the batch off lab's shared Pi-hole (whose limit stays as it is);
- pass through one `RateLimiter` at `MAX_LOOKUPS_PER_S`, both passes combined;
- keep failures apart from "no PTR": NXDOMAIN or no answer is a definitive
  no-PTR and is cached like a name; REFUSED, SERVFAIL and timeouts raise
  `PtrLookupFailed`, are never cached, are retried once, and are reported.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import dns.exception
import dns.resolver

logger = logging.getLogger(__name__)

UNBOUND_ADDRESS = "127.0.0.1"
UNBOUND_PORT = 5335
MAX_LOOKUPS_PER_S = 10.0  # sysadm's cap, 2026-11-06: ~600/min, well under Pi-hole's 1000/min even if misrouted
LOOKUP_TIMEOUT_S = 2.0
LOOKUP_LIFETIME_S = 3.0
WORKERS = 4  # the limiter sets the pace; workers only keep slow answers from stalling it
CACHE_MAX_AGE_DAYS = 30


class PtrLookupFailed(Exception):
    """The lookup got no usable answer (REFUSED, SERVFAIL, timeout): try again later, not "no PTR"."""


class RateLimiter:
    """At most `rate_per_s` acquires per second across all threads (evenly spaced slots)."""

    def __init__(self, rate_per_s: float, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self._interval = 1.0 / rate_per_s
        self._clock = clock
        self._sleep = sleep
        self._next = 0.0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = self._clock()
            slot = max(now, self._next)
            self._next = slot + self._interval
        if slot > now:
            self._sleep(slot - now)


def make_unbound_resolver() -> dns.resolver.Resolver:
    """A dnspython resolver that asks only lab's unbound, ignoring /etc/resolv.conf."""
    r = dns.resolver.Resolver(configure=False)
    r.nameservers = [UNBOUND_ADDRESS]
    r.port = UNBOUND_PORT
    r.timeout = LOOKUP_TIMEOUT_S
    r.lifetime = LOOKUP_LIFETIME_S
    return r


def unbound_lookup(resolver: dns.resolver.Resolver | None = None) -> Callable[[str], str | None]:
    """A PTR lookup: the name, None for NXDOMAIN/no answer, `PtrLookupFailed` otherwise."""
    res = resolver if resolver is not None else make_unbound_resolver()

    def lookup(address: str) -> str | None:
        try:
            answer = res.resolve_address(address)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return None
        except dns.exception.DNSException as e:  # NoNameservers (REFUSED/SERVFAIL), Timeout, ...
            raise PtrLookupFailed(f"{address}: {type(e).__name__}") from e
        for rr in answer:
            return rr.target.to_text().rstrip(".")
        return None

    return lookup


def resolve_ptrs(
    addresses: Iterable[str],
    lookup: Callable[[str], str | None],
    cache: dict[str, dict],
    today: str,
    limiter: RateLimiter | None = None,
    workers: int = WORKERS,
) -> tuple[dict[str, str | None], set[str]]:
    """PTR names for `addresses`, and the set whose lookups failed this run.

    Cache entries (`{"name": str | None, "checked": iso_date}`, None = no PTR)
    younger than `CACHE_MAX_AGE_DAYS` are used as they are. Due addresses are
    looked up through `limiter`; failures are retried once through the same
    limiter, then keep any older cached name and are returned in the failed
    set. `cache` is updated in place, with names and no-PTR answers only.
    """
    limiter = limiter if limiter is not None else RateLimiter(MAX_LOOKUPS_PER_S)
    cutoff = (datetime.fromisoformat(today) - timedelta(days=CACHE_MAX_AGE_DAYS)).date().isoformat()
    addresses = list(addresses)
    names: dict[str, str | None] = {}
    due = []
    for a in addresses:
        entry = cache.get(a)
        if entry is not None and entry["checked"] >= cutoff:
            names[a] = entry["name"]
        else:
            due.append(a)

    def one(address: str) -> tuple[str, str | None, bool]:
        limiter.acquire()
        try:
            return address, lookup(address), True
        except PtrLookupFailed:
            return address, None, False

    failed: set[str] = set()
    batch = due
    for attempt in (1, 2):
        if not batch:
            break
        failed = set()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for address, name, ok in pool.map(one, batch):
                if ok:
                    names[address] = name
                    cache[address] = {"name": name, "checked": today}
                else:
                    failed.add(address)
        if failed:
            logger.info("PTR pass %d: %d of %d lookups failed", attempt, len(failed), len(batch))
        batch = sorted(failed)
    for address in failed:
        names[address] = (cache.get(address) or {}).get("name")
    return names, failed
