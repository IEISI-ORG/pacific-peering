"""Phase 1a orchestration: build the full "fish bowl" dataset.

Combines the ASN registry (Phase 0b), RIS AS-paths for every in-scope ASN
(Phase 0c scaled up), observed-neighbor inference, and real-world IXP
membership from PeeringDB into one combined per-ASN dataset.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pacific_peering.analysis.ixp import fetch_ixp_membership_for_registry
from pacific_peering.analysis.peering import infer_neighbors
from pacific_peering.discovery.registry import DEFAULT_OUTPUT_PATH
from pacific_peering.ris.bulk import fetch_aspaths_for_registry

logger = logging.getLogger(__name__)

DEFAULT_SUMMARY_PATH = Path("data/analysis/fishbowl.json")


def build_fishbowl(
    registry_path: Path = DEFAULT_OUTPUT_PATH,
    summary_path: Path = DEFAULT_SUMMARY_PATH,
) -> dict[str, dict]:
    """Build and persist the combined RIS + IXP dataset for every in-scope ASN.

    Args:
        registry_path: Path to the Phase 0b `asn_registry.json`.
        summary_path: Where to write the combined per-ASN dataset.

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
    ixp_by_asn = fetch_ixp_membership_for_registry(registry_path=registry_path)

    fishbowl: dict[str, dict] = {}
    for asn, economy in asn_to_economy.items():
        records = aspaths_by_asn.get(asn, [])
        neighbors = neighbors_by_asn.get(asn, {})
        ixps = ixp_by_asn.get(asn, [])
        fishbowl[str(asn)] = {
            "economy": economy,
            "num_path_observations": len(records),
            "num_distinct_prefixes": len({record.target_prefix for record in records}),
            "neighbors": dict(sorted(neighbors.items(), key=lambda kv: -kv[1])),
            "ixp_memberships": [
                {"ix_id": ix.ix_id, "name": ix.name, "city": ix.city, "country": ix.country}
                for ix in ixps
            ],
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
    with_ixp = sum(1 for entry in fishbowl.values() if entry["ixp_memberships"])
    logger.info(
        "Fish bowl summary: %d ASNs, %d path observations, "
        "%d ASNs with >=1 observed neighbor, %d ASNs with >=1 IXP membership",
        len(fishbowl),
        total_paths,
        with_neighbors,
        with_ixp,
    )


if __name__ == "__main__":
    main()
