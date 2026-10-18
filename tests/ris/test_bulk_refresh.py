"""A weekly RIS refetch must refresh paths without losing them on a bad fetch.

Until 2026-10-18 `build_fishbowl` always read `data/ris/raw/` when a file
existed, so every Sunday refresh since 2026-09-14 rebuilt fishbowl.json from
the same paths. Refetching every week makes a failed RIPEstat call routine,
and it used to write `[]` over the ASN's cached paths: the ASN's neighbours
would vanish, then come back the next good week as "new RIS relationships".
"""

from __future__ import annotations

import json

from pacific_peering.ris import bulk
from pacific_peering.ris.ripestat import BgpStateRecord

OLD = BgpStateRecord(target_prefix="202.62.118.0/24", source_id="rrc00", path=(174, 45349, 4638))
NEW = BgpStateRecord(target_prefix="202.62.118.0/24", source_id="rrc00", path=(9241, 45349, 4638))


def _setup(tmp_path):
    registry = tmp_path / "asn_registry.json"
    registry.write_text(json.dumps({"FJ": {"name": "Fiji", "subregion": "Melanesia", "asns": [4638]}}))
    cache_dir = tmp_path / "raw"
    bulk._write_cache(cache_dir, 4638, [OLD])
    return registry, cache_dir


def test_refetch_replaces_cached_paths(tmp_path, monkeypatch):
    # Fails if use_cache=False still reads the old file.
    registry, cache_dir = _setup(tmp_path)
    monkeypatch.setattr(bulk, "fetch_aspaths_for_asn", lambda asn, max_prefixes: [NEW])

    result = bulk.fetch_aspaths_for_registry(registry, cache_dir=cache_dir, use_cache=False)

    assert result[4638] == [NEW]
    assert bulk._load_cached(cache_dir, 4638) == [NEW]


def test_failed_refetch_keeps_the_previous_paths(tmp_path, monkeypatch):
    # Fails if a RIPEstat error overwrites the cache with [].
    registry, cache_dir = _setup(tmp_path)

    def _fail(asn, max_prefixes):
        raise ConnectionError("RIPEstat timeout")

    monkeypatch.setattr(bulk, "fetch_aspaths_for_asn", _fail)

    result = bulk.fetch_aspaths_for_registry(registry, cache_dir=cache_dir, use_cache=False)

    assert result[4638] == [OLD]
    assert bulk._load_cached(cache_dir, 4638) == [OLD]


def test_failed_first_fetch_is_retried_next_run(tmp_path, monkeypatch):
    # Fails if a failure with nothing cached writes [], which a cached run
    # then treats as "AS originates nothing" forever.
    registry, _ = _setup(tmp_path)
    cache_dir = tmp_path / "empty"

    def _fail(asn, max_prefixes):
        raise ConnectionError("RIPEstat timeout")

    monkeypatch.setattr(bulk, "fetch_aspaths_for_asn", _fail)

    result = bulk.fetch_aspaths_for_registry(registry, cache_dir=cache_dir)

    assert result[4638] == []
    assert bulk._load_cached(cache_dir, 4638) is None
