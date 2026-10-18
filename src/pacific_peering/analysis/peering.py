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


def infer_adjacencies(
    aspaths_by_asn: dict[int, list[BgpStateRecord]], in_scope: set[int]
) -> dict[int, Counter[int]]:
    """Count every ASN seen next to each in-scope ASN anywhere in a path, either side.

    `infer_neighbors` only looks at the AS just before each path's origin,
    so a link where the in-scope ASN is *transit* never shows up there:
    FINTEL AS9241 -> TFL AS45349 is seen only on paths to AS4638's
    prefixes. This is for RIS-agreement checks only; `neighbors` keeps its
    origin-upstream meaning for the backlog and offshore screens.

    Args:
        aspaths_by_asn: Origin ASN to its AS-path observations, as for
            `infer_neighbors`.
        in_scope: ASNs to record adjacencies for (other ASNs still count
            as the far side of a pair).

    Returns:
        In-scope ASN to a Counter of {adjacent_asn: observation_count}, one
        count per (prefix, vantage point) record that shows the pair.
    """
    adjacent: dict[int, Counter[int]] = {}
    for records in aspaths_by_asn.values():
        for record in records:
            normalized = normalize_path(record.path)
            for left, right in zip(normalized, normalized[1:]):
                if left in in_scope:
                    adjacent.setdefault(left, Counter())[right] += 1
                if right in in_scope:
                    adjacent.setdefault(right, Counter())[left] += 1
    return adjacent
