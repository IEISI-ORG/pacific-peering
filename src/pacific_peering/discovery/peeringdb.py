"""Minimal PeeringDB client: resolve real-world IXP membership for ASNs.

Used to answer "which in-scope ASNs are present at which IXPs" — a
verifiable signal for IXP-routing analysis, independent of and
complementary to AS-path data from RIS (an IXP's route-server ASN
typically does not appear in AS-paths, so this can't be inferred from
paths alone).
"""

from __future__ import annotations

import logging
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
