"""Scale the Phase 0c RIPEstat proof-of-concept across the full ASN registry.

Fetches AS-paths for every in-scope ASN, capping prefixes per ASN to keep
load on the public RIPEstat API reasonable (full-history/full-prefix
coverage is a later refinement, not needed to prove the pipeline scales).
Each ASN's result is cached to disk so re-runs (e.g. the recurring
monthly job from Phase 1c) don't refetch unchanged data by default.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pacific_peering.discovery.registry import DEFAULT_OUTPUT_PATH
from pacific_peering.ris.ripestat import BgpStateRecord, fetch_aspaths_for_asn

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path("data/ris/raw")
DEFAULT_MAX_PREFIXES_PER_ASN = 5
DEFAULT_MAX_WORKERS = 8


def _cache_path(cache_dir: Path, asn: int) -> Path:
    return cache_dir / f"{asn}.json"


def _load_cached(cache_dir: Path, asn: int) -> list[BgpStateRecord] | None:
    path = _cache_path(cache_dir, asn)
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    return [
        BgpStateRecord(target_prefix=r["target_prefix"], source_id=r["source_id"], path=tuple(r["path"]))
        for r in raw
    ]


def _write_cache(cache_dir: Path, asn: int, records: list[BgpStateRecord]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = [
        {"target_prefix": r.target_prefix, "source_id": r.source_id, "path": list(r.path)}
        for r in records
    ]
    _cache_path(cache_dir, asn).write_text(json.dumps(payload) + "\n")


def _load_all_registry_asns(registry_path: Path) -> list[int]:
    registry = json.loads(registry_path.read_text())
    return sorted({asn for entry in registry.values() for asn in entry["asns"]})


def fetch_aspaths_for_registry(
    registry_path: Path = DEFAULT_OUTPUT_PATH,
    max_prefixes_per_asn: int = DEFAULT_MAX_PREFIXES_PER_ASN,
    max_workers: int = DEFAULT_MAX_WORKERS,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    use_cache: bool = True,
) -> dict[int, list[BgpStateRecord]]:
    """Fetch (or load cached) AS-paths for every ASN in the registry.

    Args:
        registry_path: Path to the Phase 0b `asn_registry.json`.
        max_prefixes_per_asn: Cap on prefixes queried per ASN, to bound API
            load — a partial view per ASN is enough to establish observed
            neighbors and is far cheaper than full coverage.
        max_workers: Thread pool size for concurrent per-ASN fetches.
        cache_dir: Directory to persist/read per-ASN raw results.
        use_cache: If True, skip fetching for ASNs already cached.

    Returns:
        Mapping of ASN to its list of `BgpStateRecord` observations.
    """
    asns = _load_all_registry_asns(registry_path)
    results: dict[int, list[BgpStateRecord]] = {}
    to_fetch: list[int] = []

    for asn in asns:
        cached = _load_cached(cache_dir, asn) if use_cache else None
        if cached is not None:
            results[asn] = cached
        else:
            to_fetch.append(asn)

    logger.info(
        "AS-path fetch: %d ASNs total, %d from cache, %d to fetch live",
        len(asns),
        len(asns) - len(to_fetch),
        len(to_fetch),
    )

    def _fetch_one(asn: int) -> tuple[int, list[BgpStateRecord]]:
        try:
            records = fetch_aspaths_for_asn(asn, max_prefixes=max_prefixes_per_asn)
        except Exception:
            logger.exception("Failed to fetch AS-paths for AS%d", asn)
            records = []
        return asn, records

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_fetch_one, asn) for asn in to_fetch]
        for future in as_completed(futures):
            asn, records = future.result()
            results[asn] = records
            _write_cache(cache_dir, asn, records)

    return results
