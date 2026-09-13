"""Resolve real-world IXP membership for every ASN in the registry.

Thin wrapper over `discovery.peeringdb` scoped to the project's ASN
registry, kept separate so analysis code doesn't import discovery's data
directly and so this can later be extended with derived signals (e.g.
flagging economies with zero IXP presence).
"""

from __future__ import annotations

import json
from pathlib import Path

from pacific_peering.discovery.peeringdb import IxpMembership, fetch_ixp_membership
from pacific_peering.discovery.registry import DEFAULT_OUTPUT_PATH


def fetch_ixp_membership_for_registry(
    registry_path: Path = DEFAULT_OUTPUT_PATH,
) -> dict[int, list[IxpMembership]]:
    """Fetch PeeringDB IXP membership for every ASN in the registry.

    Args:
        registry_path: Path to the Phase 0b `asn_registry.json`.

    Returns:
        Mapping of ASN to its list of `IxpMembership` records.
    """
    registry = json.loads(registry_path.read_text())
    asns = sorted({asn for entry in registry.values() for asn in entry["asns"]})
    return fetch_ixp_membership(asns)
