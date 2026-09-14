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
    network = ipaddress.ip_network(prefixes[0], strict=False)
    return str(network.network_address + 1)


def pick_ixp_member_target(ix_id: int, exclude_asn: int | None = None) -> tuple[int, str]:
    """Pick one real member's peering-LAN address at a known IXP, to traceroute directly.

    The active counterpart to `pick_target_ip`'s incidental approach:
    rather than waiting for a member's IXP-fabric address to turn up as
    a hop in some unrelated traceroute, fetch the exchange's real
    membership from PeeringDB and target one deliberately. This is the
    method for actively probing for hidden/unlisted peering at a known
    in-fishbowl exchange, rather than only noticing it after the fact.

    Args:
        ix_id: PeeringDB exchange ID to pick a member from.
        exclude_asn: Skip this ASN (e.g. the measurement's own source
            ASN, to avoid a trivially-local "target" that never leaves
            the source's own network).

    Returns:
        (member_asn, ipaddr4) for the lowest-numbered eligible member ASN
        — arbitrary but deterministic, so repeat runs pick the same
        target unless the membership list itself changes.

    Raises:
        ValueError: If the exchange has no eligible members on record
            (empty membership, or every member is `exclude_asn`).
    """
    members = fetch_ixp_members(ix_id)
    eligible = {asn: ips for asn, ips in members.items() if asn != exclude_asn and ips}
    if not eligible:
        raise ValueError(f"ix_id={ix_id} has no eligible member addresses on record")
    asn = min(eligible)
    return asn, eligible[asn][0]
