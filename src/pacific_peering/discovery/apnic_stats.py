"""Fetch and parse APNIC's delegated-extended stats file for ASN allocations.

File format (pipe-delimited), one record per line:
    registry|cc|type|start|value|date|status[|opaque-id]

For `type == "asn"`, `start` is the first ASN in the block and `value` is
the number of consecutive ASNs allocated/assigned starting from `start`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

APNIC_DELEGATED_STATS_URL = (
    "https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-extended-latest"
)

_RELEVANT_STATUSES = ("allocated", "assigned")


@dataclass(frozen=True)
class AsnAllocation:
    """A single ASN allocated or assigned to an economy."""

    cc: str
    asn: int
    date: str
    status: str


def fetch_delegated_stats(url: str = APNIC_DELEGATED_STATS_URL, timeout: float = 60.0) -> str:
    """Download the raw APNIC delegated-extended stats file.

    Args:
        url: Source URL for the stats file.
        timeout: Request timeout in seconds.

    Returns:
        The raw file contents as text.

    Raises:
        requests.HTTPError: If the download fails.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_asn_allocations(raw_text: str, country_codes: set[str]) -> list[AsnAllocation]:
    """Parse ASN allocation/assignment records for the given country codes.

    Args:
        raw_text: Raw contents of the delegated-extended stats file.
        country_codes: ISO 3166-1 alpha-2 codes to keep (others are dropped).

    Returns:
        One `AsnAllocation` per individual ASN found in-scope.
    """
    allocations: list[AsnAllocation] = []
    for line in raw_text.splitlines():
        if line.startswith("#") or not line:
            continue
        fields = line.split("|")
        if len(fields) < 7:
            continue
        _registry, cc, record_type, start, value, date, status = fields[:7]
        if record_type != "asn" or cc not in country_codes or status not in _RELEVANT_STATUSES:
            continue
        try:
            start_asn = int(start)
            count = int(value)
        except ValueError:
            logger.warning("Skipping unparsable ASN record: %s", line)
            continue
        for asn in range(start_asn, start_asn + count):
            allocations.append(AsnAllocation(cc=cc, asn=asn, date=date, status=status))
    return allocations
