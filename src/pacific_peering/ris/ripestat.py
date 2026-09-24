"""Minimal RIPEstat client: pull live ASPATHs for a given ASN.

Flow: `ris-prefixes(ASN)` -> originated prefixes -> `bgp-state(prefix)` ->
AS-paths as currently seen by RIS route collectors. This is the smallest
slice proving we can build the "fish bowl" view end-to-end for one ASN;
Phase 1a's full analysis fans this out across every in-scope ASN.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

RIPESTAT_BASE_URL = "https://stat.ripe.net/data"
_DEFAULT_TIMEOUT = 30.0


@dataclass(frozen=True)
class BgpStateRecord:
    """One AS-path observation for a prefix, from a single RIS vantage point."""

    target_prefix: str
    source_id: str
    path: tuple[int, ...]


def fetch_originated_prefixes(
    asn: int, af: str = "v4", timeout: float = _DEFAULT_TIMEOUT
) -> list[str]:
    """Return prefixes originated by `asn`, per RIPEstat's `ris-prefixes` call.

    Args:
        asn: Origin ASN (without the "AS" prefix).
        af: Address family, "v4" or "v6".
        timeout: Request timeout in seconds.
    """
    response = requests.get(
        f"{RIPESTAT_BASE_URL}/ris-prefixes/data.json",
        params={"resource": f"AS{asn}", "list_prefixes": "true", "types": "o", "af": af},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["data"]["prefixes"][af]["originating"]


def fetch_bgp_state(prefix: str, timeout: float = _DEFAULT_TIMEOUT) -> list[BgpStateRecord]:
    """Return the AS-paths RIS currently sees toward `prefix`, one per vantage point."""
    response = requests.get(
        f"{RIPESTAT_BASE_URL}/bgp-state/data.json",
        params={"resource": prefix},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    records = payload["data"].get("bgp_state", [])
    return [
        BgpStateRecord(
            target_prefix=record["target_prefix"],
            source_id=record["source_id"],
            path=tuple(record["path"]),
        )
        for record in records
    ]


def resolve_ip_to_asns(
    ip: str, timeout: float = _DEFAULT_TIMEOUT, max_retries: int = 2
) -> list[int]:
    """Resolve an IP address to its holding ASN(s) via RIPEstat's `network-info` call.

    Used to turn Atlas traceroute hop addresses into AS-level hops so they
    can be compared against RIS-observed neighbors (see Validation Rules
    in task_plan.md). Returns an empty list for addresses with no globally
    routed covering prefix — notably including many IXP peering-LAN
    addresses, which are often not announced in global BGP at all. That
    "no ASN" result is itself informative (a candidate IXP-fabric hop),
    not a failure.

    A transient network failure (timeout, connection error) degrades to
    "unresolved" after retrying, rather than raising — discovered via a
    real crash mid-analysis (loop tranche, French Polynesia -> Vanuatu
    measurement): one slow RIPEstat response took down the entire
    triangulation run over a single hop, which is exactly the kind of
    fragility a recurring pipeline can't tolerate.

    Args:
        ip: An IPv4 or IPv6 address (not a prefix).
        timeout: Request timeout in seconds.
        max_retries: Retries on a network error before giving up on this address.
    """
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(
                f"{RIPESTAT_BASE_URL}/network-info/data.json",
                params={"resource": ip},
                timeout=timeout,
            )
            response.raise_for_status()
            asns = response.json()["data"].get("asns", [])
            return [int(asn) for asn in asns]
        except requests.exceptions.RequestException:
            if attempt < max_retries:
                logger.warning(
                    "Network error resolving %s via RIPEstat, retrying (attempt %d/%d)",
                    ip,
                    attempt + 1,
                    max_retries,
                )
                continue
            logger.warning("RIPEstat resolution for %s failed after retries; treating as unresolved", ip)
            return []
    return []


@dataclass(frozen=True)
class RoutingVisibility:
    """How visible an exact address is in global BGP, per RIS's own route collectors.

    `network-info`/`resolve_ip_to_asns` answers "what ASN, if any" for an
    address; this answers the sharper question "has BGP ever actually
    carried a route for this, anywhere" — the two can disagree. An
    address can belong to a real, WHOIS-allocated block (so it isn't a
    bogon) while still never appearing in `ris_peers_seeing` at all,
    because the allocation holder deliberately never announces that
    specific sub-block (see `less_specifics` — empty means no covering
    announcement exists either, not just the exact prefix). This is the
    concrete, reusable version of the manual check that explained the
    unresolved AS45345->AS3605 hops as real, unannounced Superloop
    infrastructure space rather than an unknown intermediary AS.
    """

    ris_peers_seeing: int
    total_ris_peers: int
    less_specifics: tuple[str, ...]

    @property
    def ever_announced(self) -> bool:
        """True if RIS has ever seen a BGP announcement covering this address at all."""
        return self.ris_peers_seeing > 0 or bool(self.less_specifics)


def fetch_routing_visibility(
    ip: str, timeout: float = _DEFAULT_TIMEOUT, max_retries: int = 2
) -> RoutingVisibility | None:
    """Check whether `ip` has ever actually appeared in global BGP, via RIPEstat's `routing-status`.

    Degrades to `None` on a network error after retrying, same policy as
    `resolve_ip_to_asns` — a single flaky lookup must not take down a
    larger analysis run.
    """
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(
                f"{RIPESTAT_BASE_URL}/routing-status/data.json",
                params={"resource": ip},
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()["data"]
            visibility = data.get("visibility", {}).get("v4", {})
            return RoutingVisibility(
                ris_peers_seeing=visibility.get("ris_peers_seeing", 0),
                total_ris_peers=visibility.get("total_ris_peers", 0),
                less_specifics=tuple(data.get("less_specifics", [])),
            )
        except requests.exceptions.RequestException:
            if attempt < max_retries:
                logger.warning(
                    "Network error fetching routing-status for %s, retrying (attempt %d/%d)",
                    ip,
                    attempt + 1,
                    max_retries,
                )
                continue
            logger.warning("RIPEstat routing-status for %s failed after retries", ip)
            return None
    return None


@dataclass(frozen=True)
class InetnumInfo:
    """The WHOIS allocation record covering an address — who it really belongs to."""

    inetnum: str | None
    netname: str | None
    descr: str | None
    country: str | None
    status: str | None


def fetch_whois_inetnum(
    ip: str, timeout: float = _DEFAULT_TIMEOUT, max_retries: int = 2
) -> InetnumInfo | None:
    """Look up the WHOIS allocation record covering `ip`, via RIPEstat's `whois` call.

    The attribution method of last resort for a hop BGP can't explain at
    all: even address space with zero BGP visibility is still someone's
    real RIR allocation, and the `netname`/`descr` fields usually name
    the actual holder plainly (e.g. `SUPERLOOP-AU`) — not proof of which
    ASN originates traffic from it, but real corroborating context for a
    human reading a "gap" in a traceroute.
    """
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(
                f"{RIPESTAT_BASE_URL}/whois/data.json",
                params={"resource": ip},
                timeout=timeout,
            )
            response.raise_for_status()
            records = response.json()["data"].get("records", [])
            if not records:
                return None
            fields = {kv["key"]: kv["value"] for kv in records[0] if kv.get("key")}
            return InetnumInfo(
                inetnum=fields.get("inetnum"),
                netname=fields.get("netname"),
                descr=fields.get("descr"),
                country=fields.get("country"),
                status=fields.get("status"),
            )
        except requests.exceptions.RequestException:
            if attempt < max_retries:
                logger.warning(
                    "Network error fetching whois for %s, retrying (attempt %d/%d)",
                    ip,
                    attempt + 1,
                    max_retries,
                )
                continue
            logger.warning("RIPEstat whois for %s failed after retries", ip)
            return None
    return None


def fetch_aspaths_for_asn(
    asn: int, af: str = "v4", max_prefixes: int | None = None
) -> list[BgpStateRecord]:
    """Pull live ASPATHs for prefixes `asn` originates.

    Args:
        asn: Origin ASN to inspect.
        af: Address family, "v4" or "v6".
        max_prefixes: If set, only fetch bgp-state for the first N prefixes
            (keeps smoke tests / demos fast and light on the public API).
    """
    prefixes = fetch_originated_prefixes(asn, af=af)
    if max_prefixes is not None:
        prefixes = prefixes[:max_prefixes]
    logger.info(
        "AS%d originates %d prefixes (af=%s); fetching bgp-state for %d",
        asn,
        len(prefixes),
        af,
        len(prefixes),
    )

    records: list[BgpStateRecord] = []
    for prefix in prefixes:
        records.extend(fetch_bgp_state(prefix))
    return records


@dataclass(frozen=True)
class RpkiStatus:
    """RPKI origin-validation state of the route covering one address."""

    prefix: str | None
    origin_asn: int | None
    status: str  # RIPEstat's value: "valid", "invalid", "invalid_asn", "invalid_length", "unknown"; "unresolved" if no route


def fetch_rpki_status(ip: str, timeout: float = _DEFAULT_TIMEOUT) -> RpkiStatus:
    """Look up the covering route for `ip` and its RPKI validation state.

    Two RIPEstat calls: `prefix-overview` for the announced prefix and its
    origin, then `rpki-validation` for that (origin, prefix) pair. Added
    2026-09-24 for `atlas.rov_cloudflare`, which checks Cloudflare's
    deliberately valid/invalid test prefixes are still in the expected state
    before spending credits on traceroutes toward them. Raises on network
    errors -- unlike `resolve_ip_to_asns`, a caller gating a measurement on
    this must not mistake "lookup failed" for an answer.
    """
    overview = requests.get(
        f"{RIPESTAT_BASE_URL}/prefix-overview/data.json", params={"resource": ip}, timeout=timeout
    )
    overview.raise_for_status()
    data = overview.json()["data"]
    asns = [a["asn"] for a in data.get("asns", [])]
    prefix = data.get("resource") if asns else None
    if not asns or not prefix:
        return RpkiStatus(prefix=None, origin_asn=None, status="unresolved")
    validation = requests.get(
        f"{RIPESTAT_BASE_URL}/rpki-validation/data.json",
        params={"resource": asns[0], "prefix": prefix},
        timeout=timeout,
    )
    validation.raise_for_status()
    return RpkiStatus(prefix=prefix, origin_asn=int(asns[0]), status=validation.json()["data"]["status"])
