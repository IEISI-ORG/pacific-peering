"""ASN/economy discovery: APNIC delegated stats, PeeringDB, and the resulting registry."""

from .apnic_stats import AsnAllocation, fetch_delegated_stats, parse_asn_allocations
from .economies import ECONOMIES, ECONOMIES_BY_CC, Economy
from .economy_coordinates import ECONOMY_LATLON, EXTERNAL_HUB_LATLON
from .peeringdb import (
    FacilityPresence,
    IxpMembership,
    fetch_facility_presence,
    fetch_ixp_membership,
    fetch_ixp_prefixes,
    resolve_ip_via_netixlan,
)
from .registry import build_registry
from .supplementary_ixps import SUPPLEMENTARY_IXPS, SupplementaryIxp

__all__ = [
    "AsnAllocation",
    "fetch_delegated_stats",
    "parse_asn_allocations",
    "ECONOMIES",
    "ECONOMIES_BY_CC",
    "Economy",
    "ECONOMY_LATLON",
    "EXTERNAL_HUB_LATLON",
    "IxpMembership",
    "FacilityPresence",
    "fetch_facility_presence",
    "fetch_ixp_membership",
    "fetch_ixp_prefixes",
    "resolve_ip_via_netixlan",
    "build_registry",
    "SUPPLEMENTARY_IXPS",
    "SupplementaryIxp",
]
