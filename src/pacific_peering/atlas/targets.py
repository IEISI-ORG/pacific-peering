"""Pick a representative destination IP for a target ASN's traceroutes.

Reuses the Phase 1a RIS cache (`data/ris/raw/<asn>.json`) rather than
re-querying RIPEstat, since real originated prefixes are already on disk
for every in-scope ASN.
"""

from __future__ import annotations

import ipaddress
import json
from pathlib import Path

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
