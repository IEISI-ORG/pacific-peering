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


# --- 2026-11-02: repeats that aren't cycles (owner-queued 2026-10-05) --------
# A cycle through a router needs at least two hops to come back to it, and a
# reply carrying an ICMP error (`err`) is the router reporting the target
# unreachable, not forwarding it round again.


def _numbered(*hops):
    """(hop, address-or-None, error?) tuples -> parsed-hop dicts."""
    out = []
    for n, addr, err in hops:
        hop = {"hop": n, "addresses": [] if addr is None else [addr]}
        if err:
            hop["error_addresses"] = [addr]
        out.append(hop)
    return out


def test_repeat_at_the_very_next_hop_is_not_a_loop():
    # 229251973 (GU AS7131 -> AS395400, probe 60689): 168.123.136.7 at hops 8-9, then dark.
    hops = _numbered((7, "103.115.193.5", False), (8, "168.123.136.7", False),
                     (9, "168.123.136.7", False), (10, None, False), (11, None, False))
    assert targets.looping_address(hops, target="168.123.0.1") is None


def test_repeat_carrying_an_icmp_error_is_not_a_loop():
    # 228277577 (NU -> KI, probe 64391): 180.87.60.189 at hop 10, again at 14 with err=H.
    hops = _numbered((9, "180.87.60.178", False), (10, "180.87.60.189", False),
                     (11, None, False), (12, None, False), (13, None, False),
                     (14, "180.87.60.189", True))
    assert targets.looping_address(hops, target="202.1.22.1") is None


def test_alternating_pair_inside_one_network_is_still_a_loop():
    # 228278355 (NU, probe 64391): 49.156.51.245/.246 alternate for 30 hops.
    hops = _numbered((3, "49.156.51.245", False), (4, "49.156.51.246", False),
                     (5, "49.156.51.245", False), (6, "49.156.51.246", False),
                     (7, "49.156.51.245", False))
    assert targets.looping_address(hops, target="49.156.48.1") == "49.156.51.245"


def test_recurrence_after_silent_hops_without_error_is_still_a_loop():
    # Shape of 216155931 (SISCC) without its ICMP error: an address recurring
    # three hops later still counts. (The real 216155931 hop 14 carries err=H,
    # so that trace is the router reporting unreachable, not a cycle.)
    hops = _numbered((10, "103.142.98.65", False), (11, "103.142.98.131", False),
                     (12, None, False), (13, None, False), (14, "103.142.98.131", False))
    assert targets.looping_address(hops, target="203.0.113.1") == "103.142.98.131"


def test_one_address_answering_every_hop_is_still_a_loop():
    # 217755235 (PG AS151647 via Parsun, probe 50365): 188.209.155.250 answers
    # hops 10-32 at a flat 37.9ms -- the trace is stuck (owner, 2026-10-01:
    # "a genuine loop"). Only an address answering exactly two hops is excused.
    hops = _numbered((9, "188.209.155.254", False),
                     *((n, "188.209.155.250", False) for n in range(10, 33)))
    assert targets.looping_address(hops, target="103.98.52.1") == "188.209.155.250"


def test_toko_sydney_hosted_prefix_is_not_a_target(tmp_path):
    # AS132831 TokoWireless (TO): WanTok's 103.36.146.0/24 is served from Vultr
    # Sydney (TCP/443 trace 230614528: 0.7ms from Sydney, 3 networks under the
    # Tonga floor); 103.134.118.0/24 tests local (owner, 2026-11-02).
    cache = _cache(tmp_path, 132831, ["103.124.187.0/24", "103.134.118.0/24", "103.36.146.0/24", "103.54.78.0/24"])
    assert targets.list_target_ips(132831, cache) == ["103.124.187.1", "103.134.118.1", "103.54.78.1"]
