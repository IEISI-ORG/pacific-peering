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
