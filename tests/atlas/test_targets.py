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


def _hops(*addrs):
    return [{"addresses": [] if a is None else [a]} for a in addrs]


def test_repeat_followed_by_new_routers_is_not_a_loop():
    # 217486797: Equinix Sydney fabric answers two hops, trace carries on to
    # Superloop/AS9280, then the (ICMP-silent) target never replies.
    hops = _hops("202.87.128.197", "45.127.172.89", "45.127.172.89",
                 "103.200.13.64", "103.200.13.125", "202.60.93.189", None, None)
    assert targets.has_routing_loop(hops, target="103.29.155.1") is False
    assert targets.looping_address(hops, target="103.29.155.1") is None


def test_alternating_pair_at_the_tail_is_a_loop():
    # 213188745: two routers bouncing the packet until TTL runs out.
    hops = _hops("10.0.0.1", "202.95.200.36", "202.95.200.35",
                 "202.95.200.36", "202.95.200.35", "202.95.200.36")
    assert targets.has_routing_loop(hops, target="203.0.113.1") is True
    assert targets.looping_address(hops, target="203.0.113.1") == "202.95.200.36"


def test_tail_repeat_across_silent_hop_is_a_loop():
    # 216155931 shape: one address recurs with an unanswered hop between.
    hops = _hops("210.176.152.242", "103.142.98.65", "103.142.98.131", None, None,
                 "103.142.98.131")
    assert targets.has_routing_loop(hops, target="203.0.113.1") is True


def test_loop_note_names_the_tail_address_not_an_earlier_repeat():
    hops = _hops("192.0.2.1", "192.0.2.1", "198.51.100.1", "198.51.100.2",
                 "198.51.100.1", "198.51.100.2")
    assert targets.looping_address(hops) == "198.51.100.1"


def test_reaching_the_target_is_never_a_loop():
    hops = _hops("192.0.2.1", "192.0.2.2", "192.0.2.1", "203.0.113.1")
    assert targets.has_routing_loop(hops, target="203.0.113.1") is False
