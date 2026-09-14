"""RIPEstat ingestion: live ASPATHs and IP-to-ASN resolution, single-ASN or registry-wide."""

from .bulk import fetch_aspaths_for_registry
from .ripestat import (
    BgpStateRecord,
    InetnumInfo,
    RoutingVisibility,
    fetch_aspaths_for_asn,
    fetch_bgp_state,
    fetch_originated_prefixes,
    fetch_routing_visibility,
    fetch_whois_inetnum,
    resolve_ip_to_asns,
)

__all__ = [
    "BgpStateRecord",
    "InetnumInfo",
    "RoutingVisibility",
    "fetch_aspaths_for_asn",
    "fetch_aspaths_for_registry",
    "fetch_bgp_state",
    "fetch_originated_prefixes",
    "fetch_routing_visibility",
    "fetch_whois_inetnum",
    "resolve_ip_to_asns",
]
