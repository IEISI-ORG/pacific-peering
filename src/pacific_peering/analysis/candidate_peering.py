"""Candidate ("possible") peering adjacencies: strong traceroute signal, RIS disagrees.

A third finding shape, distinct from both `confirmed_detours` and
`confirmed_local_transit`. Those two only exist once RIS and Atlas
*agree* (Validation Rule 1) — this module is for the opposite case: a
traceroute-observed adjacency that's clean and repeatable (multiple
probes, contiguous, no gap) but where RIS's independently-observed
neighbor list for the target ASN does not include the traceroute's
upstream hop. That disagreement is itself the finding, per Validation
Rule 4: it's exactly the shape a *real* unlisted/private peering
relationship would take (an adjacency real enough to route traffic, but
never announced where RIS's route collectors can see it) — but it's
equally consistent with a resolution artifact (the hop's address
happens to fall in a block the upstream ASN doesn't fully control).
This module records the possibility without picking one, and without
ever promoting an entry here into `confirmed_local_transit` on its own
say-so — that requires a second independent corroboration (e.g. an
inbound traceroute, a different vantage point, or direct outreach).

First entry: FSM (AS139759) -> Palau (AS17893), first surfaced in a
`/loop` tranche testing a new corridor, then sharpened once
`traceroute_topology._resolve_address` was fixed to check IXP-fabric
membership independently of ASN resolution (see `task_plan.md`) —
AS17893's own hop turned out to sit inside Guam IX's registered LAN,
directly corroborating its PeeringDB-claimed membership there even
though the upstream adjacency itself remains unconfirmed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidatePeering:
    """One traceroute-observed adjacency RIS does not independently confirm."""

    upstream_cc: str
    upstream_asn: int
    upstream_name: str
    target_cc: str
    target_asn: int
    target_name: str
    measurement_id: int
    vantage_point_cc: str  # economy the confirming traceroute was sourced from
    probe_agreement: str  # e.g. "3/3 probes" — how repeatable the observed hop is
    note: str


CANDIDATE_PEERING: tuple[CandidatePeering, ...] = (
    CandidatePeering(
        upstream_cc="FM",
        upstream_asn=139759,
        upstream_name="an FSM ASN (no PeeringDB org name on record)",
        target_cc="PW",
        target_asn=17893,
        target_name="Palau National Communications Corp",
        measurement_id=210986430,
        vantage_point_cc="FM",
        probe_agreement="3/3 probes",
        note=(
            "All 3 probes show the same clean, contiguous path: the source's own "
            "network -> AS139759 -> AS17893, with no external hub in between. But "
            "RIS's real neighbor list for AS17893 ({174: 1333, 140627: 139, 6939: 106, "
            "24482: 49, 2500: 5, 18106: 5, 9002: 5, 49544: 5, 35280: 5, 9498: 5, "
            "59105: 2, 9505: 2} -- all global/regional transit ASNs) does not include "
            "AS139759, and neither ASN shares a PeeringDB IXP membership, so no "
            "shared-fabric corroboration is available either. Not a missing-data "
            "artifact: AS17893 has plenty of RIS-visible neighbors, just not this one. "
            "Sharpened after fixing traceroute_topology._resolve_address to check "
            "IXP-fabric membership independently of ASN resolution: the hop "
            "immediately before the final target (103.142.153.18, resolved via "
            "PeeringDB netixlan to AS17893 itself) also falls inside Guam IX's "
            "registered LAN prefix (103.142.153.0/24) -- direct traceroute "
            "corroboration that AS17893 really does have a live interface at Guam "
            "IX, matching its PeeringDB-claimed membership there. That confirms "
            "AS17893's own presence at an in-fishbowl exchange, but not that "
            "AS139759 peers with it there specifically -- AS139759 has zero "
            "PeeringDB IXP memberships on record, so its side of this adjacency "
            "remains unconfirmed either way."
        ),
    ),
)
