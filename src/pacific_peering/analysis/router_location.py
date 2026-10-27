"""Locate a traceroute's first off-region router from its own hostname, checked against physics.

Per the project owner (2026-10-12): a corridor can leave the region without
crossing any IXP. 221439393 (MP -> TO, reverification of #92) went Saipan ->
Tata `tcore2.lvw-losangeles.as6453.net` 121ms -> Telstra Global -> Digicel
Fiji -> Digicel Tonga over private interconnects. The IXP-based detour rule
never fired, and the run filed #295 (local transit) instead.

The location comes from the router's PTR record via `hop_geolocation`'s
curated pattern table, never from RTT alone: Pacific paths include satellite
legs whose latency looks like an ocean crossing. RTT is the check, not the
evidence. The hop's cumulative RTT must be at least the fibre floor from the
source economy to the named city (`feasibility.min_feasible_rtt_ms`, with the
source economy's spread taken off so it stays a lower bound), or the hostname
can't be telling the truth about where the router is.

Only the first located off-region hop of a trace is judged, so a later hop
never rescues a too-fast one. ECMP hops (more than one address) are skipped:
their `min_rtt_ms` may belong to a different router. A city with no
`EXTERNAL_HUB_LATLON` entry has no floor and is reported as unmapped, for a
human to add, never filed as a locationless detour.
"""

from __future__ import annotations

import functools
import ipaddress
import logging
import socket
import threading
from collections.abc import Callable
from dataclasses import dataclass

from pacific_peering.analysis.feasibility import great_circle_km, min_feasible_rtt_ms
from pacific_peering.analysis.hop_geolocation import resolve_hostname
from pacific_peering.discovery.economy_coordinates import ECONOMY_LATLON, ECONOMY_SPREAD_KM, EXTERNAL_HUB_LATLON

logger = logging.getLogger(__name__)

HUB_OK = "ok"
HUB_TOO_FAST = "too_fast"  # answered faster than fibre allows from the source to that city
HUB_UNMAPPED = "unmapped"  # city has no EXTERNAL_HUB_LATLON entry, so no floor
HUB_IN_REGION = "in_region"  # placed off-region by its hostname, but BGP puts the address in a fishbowl ASN
HUB_NO_OWNER = "no_owner"  # BGP gives the address no single origin ASN, so the guard above can't clear it

PtrResolver = Callable[[str], "str | None"]

PTR_TIMEOUT_S = 2.0
"""Longest one PTR lookup may take before it counts as no PTR (2026-10-12: an
uncapped serial sweep of ~800 hops took ~13 minutes, mostly addresses with no
reverse zone running out the resolver's retries)."""


@dataclass(frozen=True)
class RouterHub:
    """The first hop of one probe's trace that its hostname places outside the region."""

    probe_id: int
    hop: int
    address: str
    hostname: str
    city: str
    min_rtt_ms: float
    floor_ms: float | None  # None when `city` has no EXTERNAL_HUB_LATLON entry
    verdict: str  # HUB_OK | HUB_TOO_FAST | HUB_UNMAPPED; auto_classify may set HUB_IN_REGION | HUB_NO_OWNER

    def note(self) -> str:
        floor = "no hub coordinates" if self.floor_ms is None else f"floor {self.floor_ms}ms"
        return (
            f"router hub: hop {self.hop} {self.address} {self.hostname} -> {self.city}, "
            f"{self.min_rtt_ms}ms ({floor}, {self.verdict})"
        )


@functools.lru_cache(maxsize=4096)
def reverse_dns(address: str) -> str | None:
    """PTR lookup capped at `PTR_TIMEOUT_S`; None on failure or timeout.

    Cached: a nightly batch meets the same backbone routers again and again.
    `gethostbyaddr` has no timeout of its own, so it runs on a daemon thread
    that is abandoned (never joined again) once the cap passes; a daemon
    thread can't hold the batch open at exit, and a pool would queue new
    lookups behind hung ones.
    """
    found: list[str] = []

    def _lookup() -> None:
        try:
            found.append(socket.gethostbyaddr(address)[0])
        except OSError:
            pass

    worker = threading.Thread(target=_lookup, name=f"ptr-{address}", daemon=True)
    worker.start()
    worker.join(PTR_TIMEOUT_S)
    return found[0] if found else None


def _is_global(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False


def find_router_hub(trace: dict, source_cc: str, resolver: PtrResolver = reverse_dns) -> RouterHub | None:
    """The first hop of `trace` whose hostname places it outside the region, judged against the fibre floor.

    `trace` is one entry of `data/atlas/parsed/<msm>.json`. Returns None when the
    source economy has no coordinates, or no single-address public hop with an
    RTT has a hostname matching an off-region pattern (`economy_cc` None).
    """
    if source_cc not in ECONOMY_LATLON:
        return None
    for h in trace.get("hops", []):
        addresses = h.get("addresses", [])
        rtt = h.get("min_rtt_ms")
        if len(addresses) != 1 or rtt is None or not _is_global(addresses[0]):
            continue
        address = addresses[0]
        hostname = resolver(address)
        if not hostname:
            continue
        location = resolve_hostname(hostname)
        if location is None or location.economy_cc is not None:
            continue
        floor_ms: float | None = None
        verdict = HUB_UNMAPPED
        if location.city in EXTERNAL_HUB_LATLON:
            km = max(
                0.0,
                great_circle_km(*ECONOMY_LATLON[source_cc], *EXTERNAL_HUB_LATLON[location.city])
                - ECONOMY_SPREAD_KM.get(source_cc, 0.0),
            )
            floor_ms = round(min_feasible_rtt_ms(km), 2)
            verdict = HUB_OK if rtt >= floor_ms else HUB_TOO_FAST
        return RouterHub(trace["probe_id"], h["hop"], address, hostname, location.city, rtt, floor_ms, verdict)
    return None
