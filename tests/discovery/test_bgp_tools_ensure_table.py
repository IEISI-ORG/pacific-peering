"""bgp_tools.ensure_table: download the table dump only when the cache is stale."""

from __future__ import annotations

import os
import time

from pacific_peering.discovery import bgp_tools


def test_fresh_cache_is_not_downloaded(tmp_path, monkeypatch):
    cache = tmp_path / "table.jsonl"
    cache.write_text("")
    calls = []
    monkeypatch.setattr(bgp_tools, "_download", lambda url, dest, **kw: calls.append(url))
    assert bgp_tools.ensure_table(cache) == cache
    assert calls == []


def test_stale_or_missing_cache_is_downloaded(tmp_path, monkeypatch):
    cache = tmp_path / "table.jsonl"
    calls = []
    monkeypatch.setattr(bgp_tools, "_download", lambda url, dest, **kw: calls.append((url, dest)))
    bgp_tools.ensure_table(cache)
    cache.write_text("")
    old = time.time() - 3 * 60 * 60
    os.utime(cache, (old, old))
    bgp_tools.ensure_table(cache)
    assert calls == [("https://bgp.tools/table.jsonl", cache)] * 2
