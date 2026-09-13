"""Infer observed peering relationships from RIS AS-paths.

For each in-scope origin ASN, the AS immediately adjacent to it in an
observed path is its directly observed neighbor (an upstream provider or
peer, from the outside vantage point's perspective) — this is the
cheapest reliable peering-relationship signal extractable from AS-paths
without a full relationship-inference algorithm (e.g. Gao-style
provider/peer/customer classification), which is out of scope for now.
"""

from __future__ import annotations

from collections import Counter

from pacific_peering.ris.ripestat import BgpStateRecord


def normalize_path(path: tuple[int, ...]) -> tuple[int, ...]:
    """Collapse consecutive duplicate ASNs (AS-path prepending) in a path."""
    normalized: list[int] = []
    for asn in path:
        if not normalized or normalized[-1] != asn:
            normalized.append(asn)
    return tuple(normalized)


def infer_neighbors(
    aspaths_by_asn: dict[int, list[BgpStateRecord]],
) -> dict[int, Counter[int]]:
    """Derive observed-neighbor counts for each origin ASN.

    Args:
        aspaths_by_asn: Mapping of origin ASN to its raw AS-path
            observations (as returned by `ris.bulk.fetch_aspaths_for_registry`).

    Returns:
        Mapping of origin ASN to a Counter of {neighbor_asn: observation_count},
        counting how many distinct (prefix, vantage point) observations
        placed that neighbor immediately upstream of the origin.
    """
    neighbors_by_asn: dict[int, Counter[int]] = {}
    for asn, records in aspaths_by_asn.items():
        counter: Counter[int] = Counter()
        for record in records:
            normalized = normalize_path(record.path)
            if normalized and normalized[-1] == asn and len(normalized) >= 2:
                counter[normalized[-2]] += 1
        neighbors_by_asn[asn] = counter
    return neighbors_by_asn
