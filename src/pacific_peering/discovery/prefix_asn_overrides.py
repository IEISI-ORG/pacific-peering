"""Hand-verified ASNs for unannounced infrastructure prefixes.

Some Pacific carriers number their core routers from space they never
announce in BGP, so every traceroute hop there resolves to no ASN and
breaks the AS path into a gap. TFL's core, 202.137.178.0/24, is the first
case: it sits between Connect/TFL (AS4638) and every TFL exit, including
the crossing into Vodafone at Fiji-IXP behind finding #276.

`analysis.hop_investigation` keeps WHOIS-style reasoning out of the
automatic resolver so that a gap is never upgraded silently. An entry
here is the explicit exception: hand-verified, requested by the project
owner, and labelled `prefix_override` in every resolution, so the
provenance stays visible. It wins over BGP and the IP-resolution cache
for addresses inside it (`traceroute_topology._resolve_address`), so if
the prefix is ever announced, retire the entry by hand: delete it and
drop its addresses from `data/analysis/ip_resolution_cache.json`.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass


@dataclass(frozen=True)
class PrefixAsnOverride:
    """One unannounced prefix and the ASN whose routers use it."""

    prefix: str
    asn: int
    holder: str
    evidence: str
    verified: str  # ISO date the entry was last checked
    # True: a step that is contiguous only through this prefix's hops counts as an adjacency
    # only when RIS agrees (`traceroute_topology.check_neighbor_agreement`). The entry says
    # whose routers the space is, not who they hand traffic to. Owner, 2026-11-19 (F1 option 2),
    # for Superloop; TFL's core keeps False (owner accepted its steps with the #276 relabel).
    needs_ris_for_adjacency: bool = False


PREFIX_ASN_OVERRIDES: tuple[PrefixAsnOverride, ...] = (
    PrefixAsnOverride(
        prefix="202.137.178.0/24",
        asn=45349,
        holder="Telecom Fiji Limited",
        evidence=(
            "Not announced in BGP (RIPEstat, 2026-10-18). APNIC RDAP: netname "
            "CORE-NETWORK, 'Core Network Infrastructure Assignment', abuse contact "
            "IRT-TFL-FJ. AS45349 (TFL-AS-AP) announces the neighbouring "
            "202.137.176.0/23, .177, .179, .180/22 and .181, and holds TFL's Fiji-IXP "
            "port .30; traces crossing .30 into TFL next reach 202.137.178.77/.55. "
            "AS4638 (Connect, IS-FJ) announces no 202.137.x space. That these routers "
            "belong to AS45349 rather than AS4638 is an inference the owner accepted "
            "(2026-10-18, with the #276 relabel)."
        ),
        verified="2026-10-18",
    ),
    PrefixAsnOverride(
        prefix="103.200.13.0/24",
        asn=38195,
        holder="Superloop (Australia) Pty Ltd",
        evidence=(
            "Not announced in BGP (RIPEstat routing-status, 2026-11-19: 0 of 320 RIS peers, "
            "no less-specific). WHOIS: 103.200.12.0 - 103.200.15.0 (103.200.12.0/22), netname "
            "SUPERLOOP-AU, 'SUPERLOOP (AUSTRALIA) PTY LTD', AU; AS38195 announces only "
            "103.200.14.0/24 and 103.200.15.0/24 of the /22. RADB route object 103.200.13.0/24, "
            "origin AS38195. RIS routing history: AS38195 originated 103.200.13.0/24 from "
            "2016-10-02 to 2021-05-20, the last BGP origin seen. In traces the neighbouring hops "
            "are Superloop (125.63.12.157, announced by AS38195) and the Any2West LAN. "
            "103.200.13.168 is HundredGigE0-0-1-2.921.bdr01-ipt-624sgran-lax.us.as38195.net, "
            "Superloop's Los Angeles border router (240073513, NC -> FM, 2026-11-18: three "
            "'router address has no single BGP owner' escalations). Added at the owner's "
            "request, 2026-11-19 (F1 of the escalation review)."
        ),
        verified="2026-11-19",
        # 211259107 (NC -> GU AS3605): the override alone makes AS38195 -> AS3605 contiguous,
        # an adjacency RIS has never seen; kept out of the findings in September.
        needs_ris_for_adjacency=True,
    ),
)


def find_prefix_override(address: str) -> PrefixAsnOverride | None:
    """Return the most specific override whose prefix contains `address`, if any."""
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return None
    matches = [
        o for o in PREFIX_ASN_OVERRIDES if parsed in ipaddress.ip_network(o.prefix)
    ]
    return max(
        matches, key=lambda o: ipaddress.ip_network(o.prefix).prefixlen, default=None
    )
