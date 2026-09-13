"""Build the canonical Pacific Peering ASN registry (economy -> ASNs).

This registry is APNIC-delegation-based: it captures which ASNs are
directly delegated to each in-scope economy. It does not yet confirm which
of those ASNs are actively announcing routes, or catch ASNs delegated
elsewhere but operating in-region — that cross-check happens against RIS
data in a later phase.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TypedDict

from pacific_peering.discovery.apnic_stats import fetch_delegated_stats, parse_asn_allocations
from pacific_peering.discovery.economies import ECONOMIES

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("data/asn_registry.json")


class EconomyRegistryEntry(TypedDict):
    name: str
    subregion: str
    asns: list[int]


def build_registry(output_path: Path = DEFAULT_OUTPUT_PATH) -> dict[str, EconomyRegistryEntry]:
    """Fetch APNIC delegated stats and build the economy -> ASN registry.

    Args:
        output_path: Where to write the resulting JSON registry.

    Returns:
        Mapping of country code to economy name, subregion, and ASN list.
    """
    country_codes = {economy.cc for economy in ECONOMIES}
    raw_text = fetch_delegated_stats()
    allocations = parse_asn_allocations(raw_text, country_codes)

    registry: dict[str, EconomyRegistryEntry] = {
        economy.cc: {"name": economy.name, "subregion": economy.subregion, "asns": []}
        for economy in ECONOMIES
    }
    for allocation in allocations:
        registry[allocation.cc]["asns"].append(allocation.asn)
    for entry in registry.values():
        entry["asns"].sort()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(registry, indent=2) + "\n")
    logger.info("Wrote ASN registry for %d economies to %s", len(registry), output_path)
    return registry


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    registry = build_registry()
    total_asns = sum(len(entry["asns"]) for entry in registry.values())
    empty = [cc for cc, entry in registry.items() if not entry["asns"]]
    logger.info("Total ASNs discovered: %d across %d economies", total_asns, len(registry))
    if empty:
        logger.info("No directly-delegated ASNs found for: %s", ", ".join(sorted(empty)))


if __name__ == "__main__":
    main()
