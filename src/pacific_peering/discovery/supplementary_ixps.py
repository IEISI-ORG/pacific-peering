"""Regional IXPs known to be real but absent or incomplete in PeeringDB.

Per task_plan.md's Validation Rules: "PeeringDB is a lead, never ground
truth." This module is the project's own supplementary record for cases
where that gap has been specifically confirmed, not merely suspected —
starting with the Solomon Islands, whose PeeringDB IXP count is zero
(`/api/ix?country=SB` returns no results, and PCH's independent global
IXP directory agrees) despite a real exchange existing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SupplementaryIxp:
    """One IXP this project has confirmed independently of PeeringDB."""

    name: str
    country_cc: str
    operator: str
    source_url: str
    note: str


SUPPLEMENTARY_IXPS: tuple[SupplementaryIxp, ...] = (
    SupplementaryIxp(
        name="Solomon Islands Internet Exchange Peering Point (SIIXP)",
        country_cc="SB",
        operator="Telecommunications Commission Solomon Islands (TCSI)",
        source_url="https://www.tcsi.org.sb/index.php/about/commissioner-s-welcome",
        note=(
            "Confirmed live by the project owner, who has first-hand domain "
            "knowledge of Pacific IXP development (see task_plan.md). Absent from "
            "both PeeringDB (zero results for country=SB) and PCH's independent "
            "global IXP directory as of loop tranche 1. The source page itself "
            "(TCSI's Commissioner's welcome, appears to date from ~2019) documents "
            "TCSI establishing SIIXP to 'complement the submarine cable and allow "
            "local content caching' — that page describes the establishment "
            "effort, not a live-status confirmation as of today; the live "
            "confirmation is the project owner's, not the page's own wording. "
            "Specific participant ASNs and exact location are not yet known — "
            "needs discovery, e.g. via Atlas traceroutes from a Solomon Islands "
            "probe (currently zero connected, per Phase 1b's atlas.probes "
            "coverage check) once one exists, or direct outreach to TCSI."
        ),
    ),
)
