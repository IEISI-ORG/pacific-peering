"""Minimal PeeringDB client: resolve real-world IXP membership for ASNs.

Used to answer "which in-scope ASNs are present at which IXPs" — a
verifiable signal for IXP-routing analysis, independent of and
complementary to AS-path data from RIS (an IXP's route-server ASN
typically does not appear in AS-paths, so this can't be inferred from
paths alone).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

PEERINGDB_BASE_URL = "https://www.peeringdb.com/api"
_DEFAULT_TIMEOUT = 30.0
_CHUNK_SIZE = 50


@dataclass(frozen=True)
class IxpMembership:
    """One ASN's presence at one IXP, per PeeringDB."""

    ix_id: int
    name: str
    city: str
    country: str


def _chunked(items: list[int], size: int = _CHUNK_SIZE) -> list[list[int]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def resolve_ip_via_netixlan(
    ip: str, timeout: float = _DEFAULT_TIMEOUT, max_retries: int = 2
) -> int | None:
    """Resolve an IXP peering-LAN address to its member ASN via PeeringDB.

    This exists because RIPEstat's BGP-based IP-to-ASN lookup
    (`ris.ripestat.resolve_ip_to_asns`) frequently returns nothing for
    IXP fabric addresses, since they're often not announced in global
    BGP at all — but PeeringDB's `netixlan` table records exactly which
    member ASN holds each such address, from the IXP's own membership
    records. Use this as a fallback when the BGP-based lookup is empty,
    not a replacement — it only knows about IXP fabric addresses, not
    general internet addresses.

    A 429 (rate limited) degrades to "unresolved" after retrying with
    backoff, rather than raising — this is a best-effort enrichment
    step, not something that should crash an entire measurement's
    analysis over PeeringDB's fair-use limits.

    Args:
        ip: An IPv4 address that might be an IXP peering-LAN address.
        timeout: Request timeout in seconds.
        max_retries: Retries on 429 before giving up, with a short
            (1s, 2s, ...) backoff between attempts.

    Returns:
        The member ASN if `ip` is a known netixlan address, else None.
    """
    for attempt in range(max_retries + 1):
        response = requests.get(
            f"{PEERINGDB_BASE_URL}/netixlan", params={"ipaddr4": ip}, timeout=timeout
        )
        if response.status_code == 429:
            if attempt < max_retries:
                logger.warning(
                    "PeeringDB rate-limited netixlan lookup for %s, retrying (attempt %d/%d)",
                    ip,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(2**attempt)
                continue
            logger.warning("PeeringDB still rate-limiting netixlan lookup for %s; giving up", ip)
            return None
        response.raise_for_status()
        records = response.json()["data"]
        return records[0]["asn"] if records else None
    return None


def _fetch_netixlan_records(asns: list[int], timeout: float = _DEFAULT_TIMEOUT) -> list[dict]:
    """Fetch raw netixlan records (asn <-> ix_id) for the given ASNs, chunked."""
    records: list[dict] = []
    for chunk in _chunked(asns):
        response = requests.get(
            f"{PEERINGDB_BASE_URL}/netixlan",
            params={"asn__in": ",".join(str(asn) for asn in chunk)},
            timeout=timeout,
        )
        response.raise_for_status()
        records.extend(response.json()["data"])
    return records


def _fetch_ix_records(ix_ids: list[int], timeout: float = _DEFAULT_TIMEOUT) -> dict[int, dict]:
    """Fetch IXP metadata (name, city, country) for the given ix_ids, chunked."""
    ix_by_id: dict[int, dict] = {}
    for chunk in _chunked(ix_ids):
        response = requests.get(
            f"{PEERINGDB_BASE_URL}/ix",
            params={"id__in": ",".join(str(ix_id) for ix_id in chunk)},
            timeout=timeout,
        )
        response.raise_for_status()
        for record in response.json()["data"]:
            ix_by_id[record["id"]] = record
    return ix_by_id


def fetch_ixp_membership(asns: list[int]) -> dict[int, list[IxpMembership]]:
    """Resolve real-world IXP membership for a list of ASNs via PeeringDB.

    Args:
        asns: ASNs to look up (deduplicated internally).

    Returns:
        Mapping of ASN to the list of IXPs it is registered at in
        PeeringDB. ASNs absent from PeeringDB, or with no IXP presence,
        map to an empty list.
    """
    unique_asns = sorted(set(asns))
    logger.info("Fetching PeeringDB netixlan records for %d ASNs", len(unique_asns))
    netixlan_records = _fetch_netixlan_records(unique_asns)

    ix_ids = sorted({record["ix_id"] for record in netixlan_records})
    ix_by_id = _fetch_ix_records(ix_ids) if ix_ids else {}

    membership: dict[int, list[IxpMembership]] = {asn: [] for asn in unique_asns}
    seen: set[tuple[int, int]] = set()
    for record in netixlan_records:
        asn, ix_id = record["asn"], record["ix_id"]
        if (asn, ix_id) in seen or asn not in membership:
            continue
        seen.add((asn, ix_id))
        ix = ix_by_id.get(ix_id, {})
        membership[asn].append(
            IxpMembership(
                ix_id=ix_id,
                name=ix.get("name", f"ix-{ix_id}"),
                city=ix.get("city", ""),
                country=ix.get("country", ""),
            )
        )
    return membership
