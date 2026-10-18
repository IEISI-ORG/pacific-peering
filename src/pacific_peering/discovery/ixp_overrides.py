"""Hand-verified corrections to PeeringDB's IXP records, used until the public record is fixed.

PeeringDB is the only public source for which member holds which
peering-LAN address, and some exchanges' records are years out of date.
Fiji-IXP's (ix 3085) was last edited in 2020: it lists three members,
puts Digicel on Vodafone's port, has no route servers and no IPv6 LAN.
An override here wins over PeeringDB for the addresses and LANs it names,
so traceroute hops through the exchange are credited to the right member.

Per the project owner (2026-10-18): this covers ports, route servers and
LANs, and is meant for any exchange, not just Fiji-IXP. Every entry is
hand-verified evidence (an exchange's own port plan, cross-checked by
traces), never inferred. **The owner retires an entry by hand** once
PeeringDB is corrected; nothing compares the two automatically.

What an override does and doesn't do:
- A listed port resolves to its ASN before the IP-resolution cache, BGP
  or PeeringDB are consulted (`traceroute_topology._resolve_address`).
  Route servers resolve to no ASN: they aren't a forwarding hop, so one
  in a trace is logged as a warning rather than credited to anyone.
- Override LANs are *added* to the exchange's PeeringDB prefixes at
  lookup time (`ixp_lan_registry.classify_ixp_fabric`), never written
  into `ixp_lan_registry.json`. A cached address inside an override LAN
  has its exchange context recomputed on each lookup.
- An override never adds an exchange to the registry or sets its
  in/out-of-fishbowl classification; that stays a human decision there.

Retiring an entry: delete it here, then drop its addresses from
`data/analysis/ip_resolution_cache.json`. Port answers are written back
to that cache on purpose, so they would otherwise outlive the entry.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass

MEMBER = "member"
ROUTE_SERVER = "route_server"


@dataclass(frozen=True)
class IxpPortOverride:
    """One peering-LAN address and who holds it."""

    address: str
    asn: int | None  # None for route servers
    holder: str
    role: str = MEMBER  # MEMBER or ROUTE_SERVER
    note: str = ""


@dataclass(frozen=True)
class IxpOverride:
    """Hand-verified LANs and ports for one exchange, keyed by PeeringDB ix_id."""

    ix_id: int
    name: str
    lans: tuple[str, ...]  # added to PeeringDB's prefixes, never replacing them
    ports: tuple[IxpPortOverride, ...]
    evidence: str
    verified: str  # ISO date the entry was last checked


def _fiji_port(
    octet: int, asn: int | None, holder: str, **kwargs
) -> tuple[IxpPortOverride, ...]:
    """Fiji-IXP numbers each port the same in both LANs: .N and ::N."""
    return (
        IxpPortOverride(f"103.147.194.{octet}", asn, holder, **kwargs),
        IxpPortOverride(f"2001:df2:a280:333::{octet}", asn, holder, **kwargs),
    )


IXP_OVERRIDES: dict[int, IxpOverride] = {
    3085: IxpOverride(
        ix_id=3085,
        name="Fiji-IXP",
        lans=("103.147.194.0/24", "2001:df2:a280:333::/64"),
        ports=(
            *_fiji_port(1, None, "Fiji-IXP RS-1", role=ROUTE_SERVER),
            *_fiji_port(2, None, "Fiji-IXP RS-2", role=ROUTE_SERVER),
            *_fiji_port(10, 38442, "Vodafone Fiji"),
            *_fiji_port(20, 45355, "Digicel Fiji"),
            *_fiji_port(30, 45349, "Telecom Fiji (TFL)"),
            *_fiji_port(40, 24390, "University of the South Pacific"),
            *_fiji_port(
                50,
                136921,
                "Fiji National University",
                note="reserved; silent on 2026-10-17, consistent with FNU not yet connected (#278)",
            ),
            *_fiji_port(60, 137890, "Walesi"),
            *_fiji_port(70, 9241, "FINTEL"),
        ),
        evidence=(
            "Fiji-IXP peering-LAN plan from implementation (late 2023), posted by the "
            "USP contact to the members thread on 2026-10-17 (task_plan.md). Every port "
            "seen as a crossing hop matched it on 2026-10-17: .10 into Vodafone, .30 into "
            "TFL (next hop 202.137.178.x), .70 into FINTEL (#275). PeeringDB (2020) has "
            "AS45349 at .4 and AS38442 at .5, both silent, and AS45355 at .10. LANs: the "
            "plan says /24 (PeeringDB keeps the APNIC /23); the IPv6 /64 is carved from "
            "TAOF-FJ's 2001:df2:a280::/47 'Used for IX'. .21 answers but isn't in the "
            "plan (probably Digicel's second interface), so it is left out. Digicel "
            "confirmed .20 on 2026-10-19 and moved its PeeringDB netixlan from .10 to .20 "
            "(IPv4 only; .21 not explained). Walesi's "
            "ASN is from its PeeringDB net record; FNU's is the origin of 103.99.43.0/24."
        ),
        verified="2026-10-17",
    ),
}


def in_override_lan(address: str) -> bool:
    """True if `address` falls inside any override's LANs."""
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(
        parsed in ipaddress.ip_network(lan)
        for override in IXP_OVERRIDES.values()
        for lan in override.lans
    )


def find_port_override(address: str) -> tuple[IxpOverride, IxpPortOverride] | None:
    """Return the override entry and port for `address`, if an override names it."""
    try:
        normalised = ipaddress.ip_address(address)
    except ValueError:
        return None
    for override in IXP_OVERRIDES.values():
        for port in override.ports:
            if ipaddress.ip_address(port.address) == normalised:
                return override, port
    return None
