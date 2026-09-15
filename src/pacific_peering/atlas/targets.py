"""Pick a representative destination IP for a target ASN's traceroutes.

Reuses the Phase 1a RIS cache (`data/ris/raw/<asn>.json`) rather than
re-querying RIPEstat, since real originated prefixes are already on disk
for every in-scope ASN.
"""

from __future__ import annotations

import ipaddress
import json
from pathlib import Path

from pacific_peering.discovery.peeringdb import fetch_ixp_members
from pacific_peering.ris.bulk import DEFAULT_CACHE_DIR


def pick_target_ip(asn: int, cache_dir: Path = DEFAULT_CACHE_DIR) -> str:
    """Return an IPv4 address inside a prefix originated by `asn`.

    Uses the first cached prefix's first usable host address (network + 1).
    Not guaranteed to respond to ICMP — traceroute still reveals upstream
    hops even when the final hop doesn't reply.

    Raises:
        FileNotFoundError: If `asn` has no cached RIS data (run
            `pacific-peering-fishbowl` first).
        ValueError: If the ASN has cached data but no observed prefixes.
    """
    return list_target_ips(asn, cache_dir)[0]


def list_target_ips(asn: int, cache_dir: Path = DEFAULT_CACHE_DIR) -> list[str]:
    """Return one candidate IPv4 address per prefix `asn` originates, in a stable order.

    `pick_target_ip` only ever returns the first of these -- fine for a
    single test, but a real limitation once a specific target address
    turns out to be a bad probe: **a routing loop or dead path can be a
    property of one specific destination address, not the whole ASN**.
    Confirmed concretely (per the project owner's own direct testing,
    corroborated here): the first AS7131->AS9241 attempt went totally
    dark; retrying against a *different* AS9241 prefix's address instead
    surfaced a real, resolvable routing loop inside AS6939's own backbone
    that the original address never revealed at all. Any caller that
    hits a fully-dark or looping result should retry against the next
    entry here rather than concluding the corridor itself is a dead end.

    Raises:
        FileNotFoundError: If `asn` has no cached RIS data (run
            `pacific-peering-fishbowl` first).
        ValueError: If the ASN has cached data but no observed prefixes.
    """
    cache_path = cache_dir / f"{asn}.json"
    if not cache_path.exists():
        raise FileNotFoundError(
            f"No cached RIS data for AS{asn} at {cache_path}; run "
            "pacific-peering-fishbowl (or the ris smoketest) first"
        )
    records = json.loads(cache_path.read_text())
    prefixes = sorted({record["target_prefix"] for record in records})
    if not prefixes:
        raise ValueError(f"AS{asn} has no cached originated prefixes")
    return [
        str(ipaddress.ip_network(prefix, strict=False).network_address + 1)
        for prefix in prefixes
    ]


def has_routing_loop(hops: list[dict], target: str | None = None) -> bool:
    """True if the traceroute shows a real, blocking routing loop, not just hop-repeat noise.

    First version of this function flagged *any* consecutive repeated
    address as a loop -- too sensitive, caught live against a second
    real measurement moments after being built: a normal, successful
    traceroute (one that reaches its real target IP at the final hop)
    can still show one hop replying twice in a row, almost certainly
    ECMP/load-balancing noise, not a real loop. The defining property of
    the actual problem case (found via the project owner's own direct
    testing, then reproduced here): the packets get stuck cycling and
    **never reach the destination at all**, with RTT climbing hop over
    hop before the trace goes dark. So: only a real loop if a repeated
    address occurs *and* `target` (when given) never appears anywhere in
    the resolved hops -- a repeat alongside a successful arrival at the
    real target is normal noise, not a blocking loop.

    Args:
        hops: the `hops` list from one parsed Atlas traceroute record.
        target: the traceroute's actual destination IP, if known -- when
            given, a repeat is only treated as a real loop if this
            address is never seen in `hops` at all.
    """
    saw_repeat = False
    saw_target = False
    previous: str | None = None
    for hop in hops:
        addresses = hop.get("addresses") or []
        current = addresses[0] if len(addresses) == 1 else None
        if current is not None and current == previous:
            saw_repeat = True
        if target is not None and target in addresses:
            saw_target = True
        previous = current
    if not saw_repeat:
        return False
    return not saw_target if target is not None else True


def pick_ixp_member_target(
    ix_id: int, exclude_asns: int | set[int] | None = None
) -> tuple[int, str]:
    """Pick one real member's peering-LAN address at a known IXP, to traceroute directly.

    The active counterpart to `pick_target_ip`'s incidental approach:
    rather than waiting for a member's IXP-fabric address to turn up as
    a hop in some unrelated traceroute, fetch the exchange's real
    membership from PeeringDB and target one deliberately. This is the
    method for actively probing for hidden/unlisted peering at a known
    in-fishbowl exchange, rather than only noticing it after the fact.

    Args:
        ix_id: PeeringDB exchange ID to pick a member from.
        exclude_asns: Skip these ASN(s) — a single ASN or a set. Pass the
            measurement's own source ASN (to avoid a trivially-local
            "target" that never leaves the source's own network), and/or
            every member already probed, to walk through an exchange's
            full membership one measurement at a time.

    Returns:
        (member_asn, ipaddr4) for the lowest-numbered eligible member ASN
        — arbitrary but deterministic, so repeat runs pick the same
        target unless the membership list itself changes.

    Raises:
        ValueError: If the exchange has no eligible members on record
            (empty membership, or every member is excluded).
    """
    excluded = (
        {exclude_asns} if isinstance(exclude_asns, int) else set(exclude_asns or ())
    )
    members = fetch_ixp_members(ix_id)
    eligible = {asn: ips for asn, ips in members.items() if asn not in excluded and ips}
    if not eligible:
        raise ValueError(f"ix_id={ix_id} has no eligible member addresses on record")
    asn = min(eligible)
    return asn, eligible[asn][0]
