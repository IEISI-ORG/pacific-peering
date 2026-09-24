"""Tests for target-address selection (atlas/targets.py)."""

from __future__ import annotations

import json

import pytest

from pacific_peering.atlas import targets


def _cache(tmp_path, asn, prefixes):
    (tmp_path / f"{asn}.json").write_text(json.dumps([{"target_prefix": p} for p in prefixes]))
    return tmp_path


def test_excluded_prefix_and_more_specifics_are_skipped(tmp_path):
    # AS10131's real shape: 202.65.33.0/24 is Sydney-hosted; a /25 inside it must go too.
    cache = _cache(tmp_path, 10131, ["202.65.32.0/24", "202.65.33.0/24", "202.65.33.128/25", "202.65.46.0/24"])
    assert targets.list_target_ips(10131, cache) == ["202.65.32.1", "202.65.46.1"]


def test_include_excluded_keeps_them_for_the_offshore_check(tmp_path):
    cache = _cache(tmp_path, 10131, ["202.65.32.0/24", "202.65.33.0/24"])
    assert targets.list_target_ips(10131, cache, include_excluded=True) == ["202.65.32.1", "202.65.33.1"]


def test_a_covering_prefix_is_not_excluded_by_a_smaller_excluded_one(tmp_path):
    # 103.188.182.0/23 is excluded; a /22 containing it is a different, larger announcement.
    cache = _cache(tmp_path, 132468, ["103.188.180.0/22", "103.188.182.0/23"])
    assert targets.list_target_ips(132468, cache) == ["103.188.180.1"]


def test_every_prefix_excluded_raises(tmp_path):
    cache = _cache(tmp_path, 132468, ["103.188.182.0/23"])
    with pytest.raises(ValueError, match="EXCLUDED_TARGET_PREFIXES"):
        targets.list_target_ips(132468, cache)


def test_duplicate_addresses_are_returned_once(tmp_path):
    # A covering /22 and a /24 at its start both give 202.65.32.1.
    cache = _cache(tmp_path, 10131, ["202.65.32.0/22", "202.65.32.0/24", "202.65.48.0/24"])
    assert targets.list_target_ips(10131, cache) == ["202.65.32.1", "202.65.48.1"]
