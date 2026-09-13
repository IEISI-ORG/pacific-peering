"""Phase 0c smoke test: prove we can pull a live ASPATH for one in-scope ASN.

Loads the ASN registry built in Phase 0b, picks the first available ASN,
and fetches live AS-paths for a handful of its prefixes via RIPEstat.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pacific_peering.discovery.registry import DEFAULT_OUTPUT_PATH
from pacific_peering.ris.ripestat import fetch_aspaths_for_asn

logger = logging.getLogger(__name__)


def pick_sample_asn(registry_path: Path = DEFAULT_OUTPUT_PATH) -> tuple[str, int]:
    """Return (economy_cc, asn) for the first in-scope ASN with data.

    Raises:
        FileNotFoundError: If the registry hasn't been built yet (run
            `pacific-peering-discover-asns` first).
        ValueError: If the registry has no ASNs for any economy.
    """
    registry = json.loads(registry_path.read_text())
    for cc, entry in sorted(registry.items()):
        if entry["asns"]:
            return cc, entry["asns"][0]
    raise ValueError(f"No ASNs found in registry at {registry_path}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cc, asn = pick_sample_asn()
    logger.info("Smoke-testing RIPEstat ASPATH pull for AS%d (%s)", asn, cc)

    records = fetch_aspaths_for_asn(asn, max_prefixes=3)
    distinct_prefixes = len({record.target_prefix for record in records})
    logger.info(
        "Retrieved %d AS-path observations across %d prefixes", len(records), distinct_prefixes
    )
    for record in records[:5]:
        path_str = " ".join(str(hop) for hop in record.path)
        logger.info("  %s via %s: %s", record.target_prefix, record.source_id, path_str)

    if not records:
        raise RuntimeError("Smoke test failed: no AS-path records retrieved")


if __name__ == "__main__":
    main()
