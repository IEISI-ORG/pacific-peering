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
from collections.abc import Callable
from dataclasses import dataclass

from pacific_peering.analysis.feasibility import great_circle_km, min_feasible_rtt_ms
from pacific_peering.analysis.hop_geolocation import resolve_hostname
from pacific_peering.discovery.economy_coordinates import ECONOMY_LATLON, ECONOMY_SPREAD_KM, EXTERNAL_HUB_LATLON

logger = logging.getLogger(__name__)

HUB_OK = "ok"
HUB_TOO_FAST = "too_fast"  # answered faster than fibre allows from the source to that city
HUB_UNMAPPED = "unmapped"  # city has no EXTERNAL_HUB_LATLON entry, so no floor

PtrResolver = Callable[[str], "str | None"]


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
    verdict: str  # HUB_OK | HUB_TOO_FAST | HUB_UNMAPPED

    def note(self) -> str:
        floor = "no hub coordinates" if self.floor_ms is None else f"floor {self.floor_ms}ms"
        return (
            f"router hub: hop {self.hop} {self.address} {self.hostname} -> {self.city}, "
            f"{self.min_rtt_ms}ms ({floor}, {self.verdict})"
        )


@functools.lru_cache(maxsize=4096)
def reverse_dns(address: str) -> str | None:
    """PTR lookup; None on any failure. Cached: a nightly batch meets the same backbone routers again and again."""
    try:
        return socket.gethostbyaddr(address)[0]
    except OSError:
        return None


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
        location = resolve_hostname(hostname) if hostname else None
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
