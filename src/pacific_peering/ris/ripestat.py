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
