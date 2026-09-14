"""Shared report data assembly (Phase 1f).

Both the ASCII and HTML reports render from the exact same assembled
data structure — per task_plan.md's Phase 1f spec ("generate ASCII
report and HTML report from the same underlying analysis output"), so
the two formats can never drift apart on what they claim to show.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from pacific_peering.analysis.candidate_peering import CANDIDATE_PEERING
from pacific_peering.analysis.confirmed_detours import CONFIRMED_DETOURS
from pacific_peering.analysis.confirmed_local_transit import CONFIRMED_LOCAL_TRANSIT
from pacific_peering.analysis.fishbowl import DEFAULT_SUMMARY_PATH
from pacific_peering.analysis.ixp_lan_registry import DEFAULT_REGISTRY_PATH
from pacific_peering.discovery.registry import DEFAULT_OUTPUT_PATH

# Shared across every report format so a reader who lands on any one of
# them (this project's own audience, or an external one — e.g. RIPE
# NCC, if this report is used to make the case for new Atlas probes in
# the region) gets the same explanation of this project's central
# methodological framing, not a different one per format.
FISHBOWL_EXPLANATION = (
    "What is \"the fish bowl\"? RIS (BGP route-collector) data and PeeringDB "
    "membership records are an outside-looking-in view: they show which "
    "routes get announced and which exchanges/facilities a network claims "
    "to join, but not how traffic actually moves once it's inside a "
    "network -- we can see the bowl from outside, not get in it. Active "
    "RIPE Atlas traceroutes are the only way this project can partially "
    "see inside: a real packet, actually forwarded hop by hop. This project's "
    "rule follows from that limit: no topology claim is accepted on one "
    "source alone -- a finding only counts once RIS and an Atlas traceroute "
    "independently agree (an IRR AS-SET declaration or a PeeringDB IXP "
    "membership can support a finding, but never substitute for that "
    "agreement). \"In-fishbowl\" / \"out-of-fishbowl\" describes whether an "
    "exchange or ASN sits inside this project's study region (Melanesia, "
    "Polynesia, Micronesia, and Guam) or outside it (e.g. Sydney, Los "
    "Angeles, Tokyo) -- an out-of-fishbowl hop on a path between two "
    "in-region economies is this project's definition of a sub-optimal route."
)


@dataclass(frozen=True)
class EconomySummary:
    """One economy's counts, as shown in the economies table of both report formats."""

    cc: str
    name: str
    subregion: str
    asn_count: int
    asns_with_neighbors: int
    asns_with_ixp: int
    asns_with_facility: int


@dataclass(frozen=True)
class IxpSummary:
    """One IXP's row in both report formats' IXP table."""

    ix_id: int
    name: str
    city: str
    country: str
    in_fishbowl: bool | str
    member_count: int


@dataclass(frozen=True)
class ReportData:
    """Everything both report formats render from."""

    generated_at: str
    total_economies: int
    total_asns: int
    asns_with_neighbors: int
    asns_with_ixp: int
    asns_with_facility: int
    ixp_registry_in_fishbowl: int
    ixp_registry_out_of_fishbowl: int
    ixp_registry_tba: int
    economies: tuple[EconomySummary, ...]
    ixps: tuple[IxpSummary, ...]
    confirmed_detours: tuple[dict, ...]
    confirmed_local_transit: tuple[dict, ...]
    candidate_peering: tuple[dict, ...]

    def to_dict(self) -> dict:
        """Return a plain, JSON-serializable dict of this report data."""
        return asdict(self)


def build_report_data(
    registry_path: Path = DEFAULT_OUTPUT_PATH,
    fishbowl_path: Path = DEFAULT_SUMMARY_PATH,
    ixp_registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> ReportData:
    """Assemble the shared report data structure from this project's own outputs.

    Args:
        registry_path: Path to the Phase 0b ASN registry.
        fishbowl_path: Path to Phase 1a's fishbowl dataset.
        ixp_registry_path: Path to the Phase 1e IXP LAN subnet registry.

    Returns:
        A `ReportData` instance, ready for either report renderer.
    """
    registry = json.loads(registry_path.read_text())
    fishbowl = json.loads(fishbowl_path.read_text())
    ixp_registry = json.loads(ixp_registry_path.read_text())

    economies: list[EconomySummary] = []
    for cc, entry in sorted(registry.items()):
        asns = entry["asns"]
        with_neighbors = sum(1 for asn in asns if fishbowl.get(str(asn), {}).get("neighbors"))
        with_ixp = sum(1 for asn in asns if fishbowl.get(str(asn), {}).get("ixp_memberships"))
        with_facility = sum(
            1 for asn in asns if fishbowl.get(str(asn), {}).get("facility_presence")
        )
        economies.append(
            EconomySummary(
                cc=cc,
                name=entry["name"],
                subregion=entry["subregion"],
                asn_count=len(asns),
                asns_with_neighbors=with_neighbors,
                asns_with_ixp=with_ixp,
                asns_with_facility=with_facility,
            )
        )

    member_counts: dict[int, int] = {}
    for asn_entry in fishbowl.values():
        for ix in asn_entry.get("ixp_memberships", []):
            member_counts[ix["ix_id"]] = member_counts.get(ix["ix_id"], 0) + 1

    ixps = tuple(
        IxpSummary(
            ix_id=int(ix_id),
            name=v["name"],
            city=v["city"],
            country=v["country"],
            in_fishbowl=v["in_fishbowl"],
            member_count=member_counts.get(int(ix_id), 0),
        )
        for ix_id, v in sorted(ixp_registry.items(), key=lambda kv: kv[1]["name"])
    )

    confirmed_detours = tuple(asdict(detour) for detour in CONFIRMED_DETOURS)
    confirmed_local_transit = tuple(asdict(t) for t in CONFIRMED_LOCAL_TRANSIT)
    candidate_peering = tuple(asdict(c) for c in CANDIDATE_PEERING)

    return ReportData(
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_economies=len(registry),
        total_asns=len(fishbowl),
        asns_with_neighbors=sum(1 for v in fishbowl.values() if v["neighbors"]),
        asns_with_ixp=sum(1 for v in fishbowl.values() if v["ixp_memberships"]),
        asns_with_facility=sum(1 for v in fishbowl.values() if v["facility_presence"]),
        ixp_registry_in_fishbowl=sum(
            1 for v in ixp_registry.values() if v["in_fishbowl"] is True
        ),
        ixp_registry_out_of_fishbowl=sum(
            1 for v in ixp_registry.values() if v["in_fishbowl"] is False
        ),
        ixp_registry_tba=sum(1 for v in ixp_registry.values() if v["in_fishbowl"] == "TBA"),
        economies=tuple(economies),
        ixps=ixps,
        confirmed_detours=confirmed_detours,
        confirmed_local_transit=confirmed_local_transit,
        candidate_peering=candidate_peering,
    )
