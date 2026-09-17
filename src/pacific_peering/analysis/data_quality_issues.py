"""Durable, growing record of known data-quality issues in this project's
underlying sources -- surfaced in the report's "Low Data Quality Issues"
appendix, rather than staying implicit in registries that other parts
of this project already quietly filter against.

Not a new bookkeeping system: each issue here is backed by an existing,
already-verified record elsewhere in this project (right now, entirely
`discovery.excluded_asns.EXCLUDED_ASNS`) rather than duplicated data.
The point is visibility, not a second source of truth -- a reader of the
report should be able to see *why* the Economies/ASPA/PeeringDB-quality
tables show what they show, not just trust the counts.

Add a genuinely new, non-ASN-exclusion-shaped issue (a PeeringDB record
problem, an IXP misclassification, an ASPA discrepancy, etc.) directly
to `_ADDITIONAL_ISSUES` below when one turns up -- same verification bar
as everything else this project records (checked against real evidence,
not inferred from a hunch).
"""

from __future__ import annotations

from dataclasses import dataclass

from pacific_peering.discovery.excluded_asns import EXCLUDED_ASNS

_CATEGORY_LABELS = {
    "dns_anycast": "DNS anycast infrastructure, opportunistically registered",
}


@dataclass(frozen=True)
class DataQualityIssue:
    """One known, documented data-quality issue this project has found and
    already corrected for -- not an open question, a resolved one worth
    keeping visible."""

    title: str
    category_label: str
    description: str


def _from_excluded_asn(entry) -> DataQualityIssue:
    return DataQualityIssue(
        title=f"AS{entry.asn} ({entry.name}) -- registered {entry.country_cc}",
        category_label=_CATEGORY_LABELS.get(entry.category, entry.category),
        description=entry.note,
    )


# Hand-curated issues that aren't ASN-exclusion shaped go here directly,
# once a genuinely new kind of data-quality problem is confirmed.
_ADDITIONAL_ISSUES: tuple[DataQualityIssue, ...] = ()

DATA_QUALITY_ISSUES: tuple[DataQualityIssue, ...] = (
    tuple(_from_excluded_asn(e) for e in EXCLUDED_ASNS) + _ADDITIONAL_ISSUES
)
