"""Phase 1a orchestration: build the full "fish bowl" dataset.

Combines the ASN registry (Phase 0b), RIS AS-paths for every in-scope ASN
(Phase 0c scaled up), observed-neighbor inference, and real-world IXP
membership from PeeringDB into one combined per-ASN dataset.

PeeringDB data is cached for 30 days (`DEFAULT_PEERINGDB_CACHE_PATH`),
decoupled from the rest of this function's RIS-based fields, which stay
on the normal weekly `pacific-peering-pipeline` cadence: PeeringDB is the
one source here this project has already been rate-limited by once (see
`discovery/peeringdb.py`'s own docstring), and its own data changes far
less often than RIS paths do -- re-pulling it every week bought nothing
but rate-limit risk. Same `_is_stale`-style cache-file pattern as
`discovery/bgp_tools.py` already uses for its own rate-limit-sensitive
pulls.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from pacific_peering.analysis.ixp import fetch_ixp_membership_for_registry
from pacific_peering.analysis.peering import infer_neighbors
from pacific_peering.discovery.peeringdb import fetch_facility_presence, fetch_net_ids
from pacific_peering.discovery.registry import DEFAULT_OUTPUT_PATH
from pacific_peering.ris.bulk import fetch_aspaths_for_registry, fetch_ipv6_prefix_counts_for_registry

logger = logging.getLogger(__name__)

DEFAULT_SUMMARY_PATH = Path("data/analysis/fishbowl.json")
DEFAULT_PEERINGDB_CACHE_PATH = Path("data/peeringdb_cache.json")
_PEERINGDB_CACHE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60  # 30 days, per the project owner


def _is_stale(path: Path, max_age_seconds: float) -> bool:
    return not path.exists() or (time.time() - path.stat().st_mtime) > max_age_seconds


def _fetch_peeringdb_data(
    asns: list[int], registry_path: Path, cache_path: Path, refresh: bool
) -> dict:
    """Facility presence, IXP membership, and on-PeeringDB status for every
    in-scope ASN, cached for 30 days. Returns the same shape written to
    `cache_path`: `{"fetched_at": ..., "on_peeringdb": [...], "facility_presence":
    {asn: [...]}, "ixp_memberships": {asn: [...]}}`, all keyed by ASN as a string
    (JSON's own requirement) for the two per-ASN dicts.
    """
    if not refresh and not _is_stale(cache_path, _PEERINGDB_CACHE_MAX_AGE_SECONDS):
        logger.info("Using cached PeeringDB data (%s, < 30 days old)", cache_path)
        return json.loads(cache_path.read_text())

    logger.info("Fetching fresh PeeringDB data (facility/IXP/net presence) for %d ASNs", len(asns))
    net_ids = fetch_net_ids(asns)
    ixp_by_asn = fetch_ixp_membership_for_registry(registry_path=registry_path)
    facilities_by_asn = fetch_facility_presence(asns)

    data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "on_peeringdb": sorted(net_ids),
        "ixp_memberships": {
            str(asn): [
                {"ix_id": ix.ix_id, "name": ix.name, "city": ix.city, "country": ix.country}
                for ix in ixps
            ]
            for asn, ixps in ixp_by_asn.items()
        },
        "facility_presence": {
            str(asn): [
                {"name": fac.name, "city": fac.city, "country": fac.country}
                for fac in facilities
            ]
            for asn, facilities in facilities_by_asn.items()
        },
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data, indent=2) + "\n")
    return data


def build_fishbowl(
    registry_path: Path = DEFAULT_OUTPUT_PATH,
    summary_path: Path = DEFAULT_SUMMARY_PATH,
    peeringdb_cache_path: Path = DEFAULT_PEERINGDB_CACHE_PATH,
    refresh_peeringdb: bool = False,
) -> dict[str, dict]:
    """Build and persist the combined RIS + IXP dataset for every in-scope ASN.

    Args:
        registry_path: Path to the Phase 0b `asn_registry.json`.
        summary_path: Where to write the combined per-ASN dataset.
        peeringdb_cache_path: Where the 30-day PeeringDB cache lives.
        refresh_peeringdb: Force a live PeeringDB re-fetch even if the
            cache isn't 30 days stale yet.

    Returns:
        Mapping of ASN (as string, for JSON-compatibility) to its combined
        economy, RIS, and IXP data.
    """
    registry = json.loads(registry_path.read_text())
    asn_to_economy = {
        asn: {"cc": cc, "name": entry["name"], "subregion": entry["subregion"]}
        for cc, entry in registry.items()
        for asn in entry["asns"]
    }

    aspaths_by_asn = fetch_aspaths_for_registry(registry_path=registry_path)
    neighbors_by_asn = infer_neighbors(aspaths_by_asn)
    ipv6_prefix_counts = fetch_ipv6_prefix_counts_for_registry(registry_path=registry_path)
    peeringdb_data = _fetch_peeringdb_data(
        list(asn_to_economy), registry_path, peeringdb_cache_path, refresh_peeringdb
    )
    on_peeringdb = set(peeringdb_data["on_peeringdb"])
    ixp_by_asn = peeringdb_data["ixp_memberships"]
    facilities_by_asn = peeringdb_data["facility_presence"]

    fishbowl: dict[str, dict] = {}
    for asn, economy in asn_to_economy.items():
        records = aspaths_by_asn.get(asn, [])
        neighbors = neighbors_by_asn.get(asn, {})
        fishbowl[str(asn)] = {
            "economy": economy,
            "num_path_observations": len(records),
            "num_distinct_prefixes": len({record.target_prefix for record in records}),
            "num_ipv6_prefixes": ipv6_prefix_counts.get(asn, 0),
            "neighbors": dict(sorted(neighbors.items(), key=lambda kv: -kv[1])),
            # Whether this ASN has a PeeringDB `net` record at all --
            # distinct from (and a prerequisite for) having any real
            # facility/IXP membership content below. See
            # `discovery/peeringdb.py`'s `fetch_net_ids` docstring.
            "on_peeringdb": asn in on_peeringdb,
            "ixp_memberships": ixp_by_asn.get(str(asn), []),
            "facility_presence": facilities_by_asn.get(str(asn), []),
        }

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(fishbowl, indent=2) + "\n")
    logger.info("Wrote fish bowl dataset for %d ASNs to %s", len(fishbowl), summary_path)
    return fishbowl


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    fishbowl = build_fishbowl()

    total_paths = sum(entry["num_path_observations"] for entry in fishbowl.values())
    with_neighbors = sum(1 for entry in fishbowl.values() if entry["neighbors"])
    on_peeringdb = sum(1 for entry in fishbowl.values() if entry["on_peeringdb"])
    with_ixp = sum(1 for entry in fishbowl.values() if entry["ixp_memberships"])
    with_facility = sum(1 for entry in fishbowl.values() if entry["facility_presence"])
    logger.info(
        "Fish bowl summary: %d ASNs, %d path observations, %d ASNs with >=1 observed neighbor, "
        "%d ASNs on PeeringDB, %d ASNs with >=1 IXP membership, %d ASNs with >=1 facility presence",
        len(fishbowl),
        total_paths,
        with_neighbors,
        on_peeringdb,
        with_ixp,
        with_facility,
    )


if __name__ == "__main__":
    main()
