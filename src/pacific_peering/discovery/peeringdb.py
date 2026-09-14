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


@dataclass(frozen=True)
class FacilityPresence:
    """One ASN's physical colocation presence, per PeeringDB's `netfac`.

    A stronger signal than IXP membership: this is equipment in a
    building, not just a virtual peering session. An ASN can be
    out-of-region-dependent via colocation even with zero out-of-region
    IXP memberships.
    """

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


def fetch_ix_info(ix_ids: list[int], timeout: float = _DEFAULT_TIMEOUT) -> dict[int, dict]:
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
    ix_by_id = fetch_ix_info(ix_ids) if ix_ids else {}

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


def _fetch_net_ids(asns: list[int], timeout: float = _DEFAULT_TIMEOUT) -> dict[int, int]:
    """Map ASN -> PeeringDB internal `net` id, chunked."""
    asn_to_net_id: dict[int, int] = {}
    for chunk in _chunked(asns):
        response = requests.get(
            f"{PEERINGDB_BASE_URL}/net",
            params={"asn__in": ",".join(str(asn) for asn in chunk)},
            timeout=timeout,
        )
        response.raise_for_status()
        for record in response.json()["data"]:
            asn_to_net_id[record["asn"]] = record["id"]
    return asn_to_net_id


def fetch_facility_presence(asns: list[int]) -> dict[int, list[FacilityPresence]]:
    """Resolve real-world colocation facility presence for a list of ASNs.

    `netfac` (the facility-membership table) doesn't filter by ASN
    directly — it's keyed by PeeringDB's internal `net_id`, so this
    resolves ASN -> net_id via the `net` endpoint first, then queries
    `netfac` by `net_id__in`.

    Args:
        asns: ASNs to look up (deduplicated internally).

    Returns:
        Mapping of ASN to the list of facilities it's registered at.
        ASNs absent from PeeringDB, or with no facility presence, map to
        an empty list.
    """
    unique_asns = sorted(set(asns))
    asn_to_net_id = _fetch_net_ids(unique_asns)
    net_id_to_asn = {net_id: asn for asn, net_id in asn_to_net_id.items()}

    presence: dict[int, list[FacilityPresence]] = {asn: [] for asn in unique_asns}
    net_ids = sorted(net_id_to_asn)
    if not net_ids:
        return presence

    for chunk in _chunked(net_ids):
        response = requests.get(
            f"{PEERINGDB_BASE_URL}/netfac",
            params={"net_id__in": ",".join(str(net_id) for net_id in chunk)},
            timeout=_DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        for record in response.json()["data"]:
            asn = net_id_to_asn.get(record["net_id"])
            if asn is None:
                continue
            presence[asn].append(
                FacilityPresence(
                    name=record.get("name", ""),
                    city=record.get("city", ""),
                    country=record.get("country", ""),
                )
            )
    return presence


def fetch_ixp_members(
    ix_id: int, timeout: float = _DEFAULT_TIMEOUT, max_retries: int = 3
) -> dict[int, list[str]]:
    """Fetch one IXP's real member ASNs and their peering-LAN IPv4 addresses.

    This is what makes the "traceroute directly at a known IXP LAN
    address" method possible: rather than waiting for a member's address
    to show up incidentally as a hop in some unrelated traceroute, pick
    one deliberately from here and target it. `netixlan` supports
    filtering by `ix_id` directly (confirmed empirically — like
    `ixpfx`, despite records nominally keying off `ixlan_id`).

    Args:
        ix_id: PeeringDB exchange ID.
        max_retries: Retries on 429 before giving up on this exchange.

    Returns:
        Mapping of member ASN to its IPv4 address(es) at this exchange
        (usually one, occasionally more for route-server ports). Empty
        dict if the exchange has no members on record or still 429s
        after all retries — a caller should treat that the same as "no
        usable target here" rather than crashing.
    """
    for attempt in range(max_retries + 1):
        response = requests.get(
            f"{PEERINGDB_BASE_URL}/netixlan", params={"ix_id": ix_id}, timeout=timeout
        )
        if response.status_code == 429:
            if attempt < max_retries:
                logger.warning(
                    "PeeringDB rate-limited netixlan-members lookup for ix_id=%d, "
                    "retrying (%d/%d)",
                    ix_id,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(2**attempt)
                continue
            logger.warning(
                "PeeringDB still rate-limiting netixlan-members lookup for ix_id=%d; giving up",
                ix_id,
            )
            return {}
        response.raise_for_status()
        members: dict[int, list[str]] = {}
        for record in response.json()["data"]:
            ip = record.get("ipaddr4")
            if not ip:
                continue
            members.setdefault(record["asn"], []).append(ip)
        return members
    return {}


def fetch_ixp_prefixes(
    ix_ids: list[int], timeout: float = _DEFAULT_TIMEOUT, max_retries: int = 3
) -> dict[int, list[str]]:
    """Fetch each IXP's registered IPv4 LAN prefix(es) via PeeringDB's `ixpfx`.

    Queried one `ix_id` at a time rather than batched: `ixpfx` records
    carry `ixlan_id`, not `ix_id`, and while the two happen to match for
    every exchange checked so far, that's not guaranteed by the schema —
    querying one at a time avoids silently mis-attributing a prefix to
    the wrong exchange in a batch response. A small delay between
    requests plus retry-with-backoff on 429 — a couple dozen sequential
    calls was enough to rate-limit this project once already.

    Args:
        ix_ids: PeeringDB exchange IDs to look up.
        max_retries: Retries on 429 before giving up on that one ix_id.

    Returns:
        Mapping of ix_id to its list of IPv4 CIDR prefixes (IPv6 skipped
        — this project's Atlas measurements are IPv4-only so far). An
        ix_id that still 429s after all retries maps to an empty list
        rather than aborting the whole batch.
    """
    prefixes: dict[int, list[str]] = {}
    for ix_id in sorted(set(ix_ids)):
        for attempt in range(max_retries + 1):
            response = requests.get(
                f"{PEERINGDB_BASE_URL}/ixpfx", params={"ix_id": ix_id}, timeout=timeout
            )
            if response.status_code == 429:
                if attempt < max_retries:
                    logger.warning(
                        "PeeringDB rate-limited ixpfx lookup for ix_id=%d, retrying (%d/%d)",
                        ix_id,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(2**attempt)
                    continue
                logger.warning("PeeringDB still rate-limiting ix_id=%d; giving up", ix_id)
                prefixes[ix_id] = []
                break
            response.raise_for_status()
            prefixes[ix_id] = [
                record["prefix"]
                for record in response.json()["data"]
                if record.get("protocol") == "IPv4"
            ]
            break
        time.sleep(0.5)
    return prefixes
