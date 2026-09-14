"""Registry of which specific in-scope ASNs have a connected RIPE Atlas probe.

Per the project owner: worth keeping a local record of "good probes"
(ones that would let a measurement be sourced from a specific ASN via
ASN-based selection, not just an economy generically) and refreshing
it monthly, the same cadence as the rest of the recurring pipeline.

Built ad hoc, one ASN at a time, for AS10130 (none), AS395400 (none),
and AS3605 (two) across three separate tranches before this existed —
this module replaces that with one persisted lookup instead of a fresh
live API call every time the question comes up.

**20 calls, not 163+.** Atlas's `/probes/` endpoint doesn't support
batching multiple ASNs in one query (confirmed empirically — `asn`
as a comma-separated list returns 400) — but a single per-economy
`country_code` query (the same one `atlas.probes.build_probe_coverage`
already makes) returns each matching probe's own `asn_v4`, so the
existing 20-call, one-per-economy pattern already carries everything
needed; this module only needed to capture the field.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

from pacific_peering.discovery.economies import ECONOMIES, Economy

logger = logging.getLogger(__name__)

ATLAS_BASE_URL = "https://atlas.ripe.net/api/v2"
_DEFAULT_TIMEOUT = 30.0

DEFAULT_REGISTRY_PATH = Path("data/atlas/asn_probe_registry.json")


def build_asn_probe_registry(
    economies: tuple[Economy, ...] = ECONOMIES,
    output_path: Path = DEFAULT_REGISTRY_PATH,
    timeout: float = _DEFAULT_TIMEOUT,
) -> dict[int, list[int]]:
    """List, for every economy, which ASN(s) its connected Atlas probes actually sit on.

    Args:
        economies: In-scope economies to check (one API call each).
        output_path: Where to persist the resulting registry.
        timeout: Per-request timeout in seconds.

    Returns:
        Mapping of ASN to the list of connected probe IDs hosted on it.
        An ASN absent from the result has zero connected probes —
        ASN-based Atlas measurement selection will fail for it (see
        `atlas.client.create_traceroute_measurement`'s `source_type`).
    """
    registry: dict[int, list[int]] = {}
    for economy in economies:
        response = requests.get(
            f"{ATLAS_BASE_URL}/probes/",
            params={"country_code": economy.cc, "status": 1},
            timeout=timeout,
        )
        response.raise_for_status()
        for probe in response.json()["results"]:
            asn = probe.get("asn_v4")
            if asn is not None:
                registry.setdefault(asn, []).append(probe["id"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n")
    logger.info(
        "ASN probe registry: %d ASNs across %d economies have >=1 connected probe",
        len(registry),
        len(economies),
    )
    return registry


def load_asn_probe_registry(path: Path = DEFAULT_REGISTRY_PATH) -> dict[int, list[int]]:
    """Load a previously-built ASN probe registry from disk."""
    payload = json.loads(path.read_text())
    return {int(asn): probe_ids for asn, probe_ids in payload.items()}


def has_connected_probe(asn: int, registry: dict[int, list[int]] | None = None) -> bool:
    """Return whether `asn` has at least one connected Atlas probe, per the registry.

    Args:
        asn: ASN to check.
        registry: Precomputed registry; loaded from disk if not given.
    """
    registry = registry if registry is not None else load_asn_probe_registry()
    return bool(registry.get(asn))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    build_asn_probe_registry()


if __name__ == "__main__":
    main()
