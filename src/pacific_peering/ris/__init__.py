"""RIPEstat ingestion: live ASPATHs and IP-to-ASN resolution, single-ASN or registry-wide."""

from .bulk import fetch_aspaths_for_registry
from .ripestat import (
    BgpStateRecord,
    fetch_aspaths_for_asn,
    fetch_bgp_state,
    fetch_originated_prefixes,
    resolve_ip_to_asns,
)

__all__ = [
    "BgpStateRecord",
    "fetch_aspaths_for_asn",
    "fetch_aspaths_for_registry",
    "fetch_bgp_state",
    "fetch_originated_prefixes",
    "resolve_ip_to_asns",
]
