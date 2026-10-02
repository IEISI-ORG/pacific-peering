"""Check RIPE Atlas probe coverage across in-scope economies.

This turned out to matter immediately: several in-scope ASNs have zero
Atlas probes of their own (all historic probes abandoned/disconnected),
so ASN-based source selection frequently fails with "Your selected ASN
is not covered by our network." Country-based selection is the practical
fallback — it finds whatever probe exists in that economy, even if
hosted on a different local ISP's ASN than the one being studied.
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

DEFAULT_COVERAGE_PATH = Path("data/atlas/probe_coverage.json")
DEFAULT_LISTING_PATH = Path("data/atlas/probe_listing.json")


def fetch_probes_for_economy(country_code: str, timeout: float = _DEFAULT_TIMEOUT) -> list[dict]:
    """Every probe RIPE Atlas has ever registered for a country, any status.

    Deliberately unfiltered, unlike `count_connected_probes` (status=1
    only) -- the gap between "listed" (registered in Atlas at all) and
    "active" (status=1, Connected) is itself worth surfacing. A listed-
    but-not-connected probe is either a stale/abandoned registration (a
    data-quality issue an Atlas host or the community could clean up) or
    a real host that could be brought back online -- either way, this
    project's own reports can only point at a country/ASN in the
    aggregate unless the specific probe IDs and their status are kept.
    """
    response = requests.get(
        f"{ATLAS_BASE_URL}/probes/",
        params={"country_code": country_code},
        timeout=timeout,
    )
    response.raise_for_status()
    return [_listing_entry(p) for p in response.json()["results"]]


def _listing_entry(p: dict) -> dict:
    status = p.get("status") or {}
    return {
        "id": p["id"],
        "status": status.get("name", "Unknown"),
        "status_since": status.get("since"),
        "asn_v4": p.get("asn_v4"),
        # IPv6 (added 2026-09-24 for the Starlink IPv6 anchor
        # traces): asn_v6 is None for a probe with no IPv6 address.
        # Atlas's own system-ipv6-* tags (capable / works /
        # doesnt-work) come from its built-in measurements, kept
        # as-is so results can be read against them.
        "asn_v6": p.get("asn_v6"),
        "ipv6_tags": sorted(
            t["slug"] for t in p.get("tags") or [] if t.get("slug", "").startswith("system-ipv6")
        ),
    }


# Probes physically in an in-scope economy that Atlas registers under another
# country, so a country_code query never returns them. Each one verified by
# hand, never inferred from self-reported coordinates (Guam and Saipan are only
# ~220km apart). Found 2026-10-03: both Piti, Guam anchors, Atlas country US.
#   6923  gu-pit-as140627 (OneQode AS140627); Guam Exchange's 7385 pings it at 0.54ms.
#   7662  gu-pit-as141682-client (Arena-PAC AS141682, registered as APIDT), same site per its anchor record.
PROBE_ECONOMY_OVERRIDES: dict[int, str] = {6923: "GU", 7662: "GU"}


def fetch_probes_by_id(probe_ids: list[int], timeout: float = _DEFAULT_TIMEOUT) -> list[dict]:
    """Raw Atlas probe records for specific IDs, any status."""
    response = requests.get(
        f"{ATLAS_BASE_URL}/probes/",
        params={"id__in": ",".join(str(i) for i in probe_ids)},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["results"]


def build_probe_listing(
    economies: tuple[Economy, ...] = ECONOMIES,
    output_path: Path = DEFAULT_LISTING_PATH,
) -> dict[str, list[dict]]:
    """Persist every listed (any-status) probe per in-scope economy."""
    listing = {economy.cc: fetch_probes_for_economy(economy.cc) for economy in economies}
    overrides = [pid for pid, cc in PROBE_ECONOMY_OVERRIDES.items() if cc in listing]
    if overrides:
        for p in fetch_probes_by_id(overrides):
            cc = PROBE_ECONOMY_OVERRIDES[p["id"]]
            if all(existing["id"] != p["id"] for existing in listing[cc]):
                listing[cc].append({**_listing_entry(p), "atlas_country": p.get("country_code")})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(listing, indent=2) + "\n")
    listed_total = sum(len(v) for v in listing.values())
    active_total = sum(1 for v in listing.values() for p in v if p["status"] == "Connected")
    logger.info(
        "Probe listing: %d listed across %d economies, %d currently Connected",
        listed_total,
        len(economies),
        active_total,
    )
    return listing


def load_probe_listing(path: Path = DEFAULT_LISTING_PATH) -> dict[str, list[dict]]:
    """Load a previously-built probe listing from disk."""
    return json.loads(path.read_text())


def asn_listed_registry(listing: dict[str, list[dict]]) -> dict[int, list[int]]:
    """Group a probe listing's entries by ASN, any status.

    The "listed" counterpart to `atlas.asn_probes.load_asn_probe_registry`
    (which is Connected-only) -- same shape, so both can feed
    `reports.data._compute_pathway_coverage` the same way.
    """
    result: dict[int, list[int]] = {}
    for probes in listing.values():
        for p in probes:
            asn = p.get("asn_v4")
            if asn is not None:
                result.setdefault(asn, []).append(p["id"])
    return result


def count_connected_probes(country_code: str, timeout: float = _DEFAULT_TIMEOUT) -> int:
    """Return the number of currently-connected Atlas probes in a country."""
    response = requests.get(
        f"{ATLAS_BASE_URL}/probes/",
        params={"country_code": country_code, "status": 1},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["count"]


def build_probe_coverage(
    economies: tuple[Economy, ...] = ECONOMIES,
    output_path: Path = DEFAULT_COVERAGE_PATH,
) -> dict[str, int]:
    """Count connected Atlas probes for every in-scope economy and persist the result."""
    coverage = {economy.cc: count_connected_probes(economy.cc) for economy in economies}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(coverage, indent=2) + "\n")
    zero_coverage = [cc for cc, count in coverage.items() if count == 0]
    logger.info(
        "Atlas probe coverage: %d/%d economies have >=1 connected probe (%d have none: %s)",
        len(coverage) - len(zero_coverage),
        len(coverage),
        len(zero_coverage),
        ", ".join(sorted(zero_coverage)) or "none",
    )
    return coverage


def pick_best_covered_economy(
    exclude_cc: str | None = None, coverage: dict[str, int] | None = None
) -> str:
    """Return the in-scope economy (country code) with the most connected probes.

    Args:
        exclude_cc: Country code to exclude (e.g. the measurement's target economy).
        coverage: Precomputed coverage mapping; fetched fresh if not given.

    Raises:
        ValueError: If no economy (other than `exclude_cc`) has any connected probe.
    """
    coverage = coverage if coverage is not None else build_probe_coverage()
    candidates = {
        cc: count for cc, count in coverage.items() if count > 0 and cc != exclude_cc
    }
    if not candidates:
        raise ValueError("No in-scope economy (excluding exclude_cc) has a connected Atlas probe")
    return max(candidates, key=candidates.get)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    build_probe_coverage()


if __name__ == "__main__":
    main()
