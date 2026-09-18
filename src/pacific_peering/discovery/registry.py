"""Build the canonical Pacific Peering ASN registry (economy -> ASNs).

This registry is primarily APNIC-delegation-based: it captures which
ASNs are directly delegated to each in-scope economy. It does not
confirm which of those ASNs are actively announcing routes — that
cross-check happens against RIS data in a later phase.

It also merges in `discovery.supplementary_asns.SUPPLEMENTARY_ASNS` —
real, individually-verified ASNs delegated under a *different* RIR
(e.g. ARIN) that APNIC's delegated-stats file necessarily can't see.
Confirmed via a live cross-RIR audit (RIPEstat's `country-resource-list`
against all 20 economies) that this gap is real, not just theoretical,
though narrow: of 11 candidate ASNs the audit surfaced, only one held
up under direct verification (see that module for the other 10, and
why they were confirmed *not* real Pacific presence rather than added).

Symmetrically, it removes `discovery.excluded_asns.EXCLUDED_ASNS` —
ASNs APNIC *does* delegate to an in-scope economy but that this
project has individually verified aren't real Pacific networks (e.g.
AS24013/DNS.SB, a global anycast DNS resolver opportunistically
registered under a Solomon Islands country code).

It also moves `discovery.reclassified_asns.RECLASSIFIED_ASNS` — ASNs
APNIC delegates to one economy (typically a regional organization's
registered headquarters) but whose real, verified Pacific presence
this project cares about is physically in a different one (e.g.
AS141695/Pacific Community: delegated to New Caledonia, but its only
connected probe is in Fiji). Applied last, so it survives every future
`build_registry()` refresh instead of being a one-off hand-edit to the
generated output that the next refresh would silently undo.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TypedDict

from pacific_peering.discovery.apnic_stats import fetch_delegated_stats, parse_asn_allocations
from pacific_peering.discovery.economies import ECONOMIES
from pacific_peering.discovery.excluded_asns import EXCLUDED_ASNS
from pacific_peering.discovery.reclassified_asns import RECLASSIFIED_ASNS
from pacific_peering.discovery.supplementary_asns import SUPPLEMENTARY_ASNS

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("data/asn_registry.json")


class EconomyRegistryEntry(TypedDict):
    """One economy's entry in the ASN registry JSON."""

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
    for supplementary in SUPPLEMENTARY_ASNS:
        if supplementary.asn not in registry[supplementary.country_cc]["asns"]:
            registry[supplementary.country_cc]["asns"].append(supplementary.asn)
    for excluded in EXCLUDED_ASNS:
        if excluded.asn in registry[excluded.country_cc]["asns"]:
            registry[excluded.country_cc]["asns"].remove(excluded.asn)
    for reclassified in RECLASSIFIED_ASNS:
        if reclassified.asn in registry[reclassified.from_cc]["asns"]:
            registry[reclassified.from_cc]["asns"].remove(reclassified.asn)
        if reclassified.asn not in registry[reclassified.to_cc]["asns"]:
            registry[reclassified.to_cc]["asns"].append(reclassified.asn)
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
