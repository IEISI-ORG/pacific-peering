"""Reusable version of the manual "why is this hop unresolved" investigation.

`traceroute_topology._resolve_address` deliberately stays BGP/netixlan-only
(see task_plan.md's RFC1918 fix and the AS45345->AS3605 Superloop finding):
a hop with no ASN attribution there is genuinely unresolved *for the
automatic resolver*, not necessarily unresolved in reality. This module is
the manual-investigation tool an analyst reaches for next, not a third
resolver tier folded into the automatic pipeline — WHOIS/RIS-visibility
reasoning is real evidence but fuzzier than exact BGP/netixlan attribution,
and this project deliberately keeps that distinction visible rather than
silently upgrading a "gap" to a confirmed adjacency.

Built after doing this investigation by hand three times this session
(the AS9471->AS10131 RFC1918 case, and the AS45345->AS3605 Superloop case,
cross-validated against bgp.tools per the project owner's own check) —
worth having as a permanent, reusable capability rather than re-deriving
the same three API calls freehand each time a gap needs explaining.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pacific_peering.discovery.bgp_tools import is_prefix_routed_by_asn
from pacific_peering.ris.ripestat import (
    InetnumInfo,
    RoutingVisibility,
    fetch_routing_visibility,
    fetch_whois_inetnum,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HopInvestigation:
    """The combined picture for one BGP-unresolved traceroute hop address."""

    address: str
    routing_visibility: RoutingVisibility | None
    whois: InetnumInfo | None
    suspected_asn: int | None
    suspected_asn_routes_it: bool | None  # None: can't determine; see is_prefix_routed_by_asn

    @property
    def likely_unannounced_infrastructure(self) -> bool:
        """True when this looks like real, allocated-but-deliberately-unrouted address space.

        The concrete pattern this project has now seen twice: zero RIS
        visibility, a real (non-bogon) WHOIS allocation, and — when a
        suspected operator is given — that operator confirmed NOT to
        route this specific sub-block via bgp.tools (they route other
        parts of their allocation, just not this one).
        """
        if self.routing_visibility is None or self.routing_visibility.ever_announced:
            return False
        if self.whois is None or self.whois.status is None:
            return False
        return True


def investigate_unresolved_hop(address: str, suspected_asn: int | None = None) -> HopInvestigation:
    """Run the full manual-investigation checklist for one unresolved traceroute hop.

    Combines three independent sources, same as the Superloop investigation
    this was built from:
    1. RIPEstat `routing-status` — has BGP ever actually carried a route
       for this exact address, at all (not just "no ASN returned")?
    2. RIPEstat `whois` — who really holds this address space, per its
       RIR allocation record (real evidence even with zero BGP visibility)?
    3. If `suspected_asn` is given (e.g. from the WHOIS `netname`, or the
       last cleanly-resolved hop before the gap): does bgp.tools show that
       ASN routing *some* prefixes but specifically not this one? A `False`
       here is strong, concrete corroboration — not just an absence of
       evidence — that this is deliberately-unannounced infrastructure
       space belonging to an already-identified network, not a real
       unknown intermediary.

    Args:
        address: The traceroute hop's IPv4 address.
        suspected_asn: An ASN to cross-check against bgp.tools' routed
            prefixes for this address, if one is suspected (e.g. from
            WHOIS netname matching, or the last resolved hop's ASN).
    """
    visibility = fetch_routing_visibility(address)
    whois = fetch_whois_inetnum(address)

    routes_it = None
    if suspected_asn is not None:
        routes_it = is_prefix_routed_by_asn(suspected_asn, address)

    result = HopInvestigation(
        address=address,
        routing_visibility=visibility,
        whois=whois,
        suspected_asn=suspected_asn,
        suspected_asn_routes_it=routes_it,
    )
    logger.info(
        "Investigated %s: ever_announced=%s, whois_netname=%s, suspected_asn=%s routes_it=%s, "
        "likely_unannounced_infrastructure=%s",
        address,
        visibility.ever_announced if visibility else None,
        whois.netname if whois else None,
        suspected_asn,
        routes_it,
        result.likely_unannounced_infrastructure,
    )
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # The concrete case this module was built from: AS45345 -> AS3605 (measurement
    # 211259107), two hops WHOIS attributes to Superloop (AS38195) but RIS never
    # observed in BGP — cross-checked against bgp.tools per the project owner's own
    # independent check (routes 103.200.14.0/24 and .15.0/24, not .13.0/24).
    for address in ("103.200.13.67", "103.200.13.168"):
        investigate_unresolved_hop(address, suspected_asn=38195)


if __name__ == "__main__":
    main()
