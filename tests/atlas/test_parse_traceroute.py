"""Regression tests for `parse_traceroute_results`: replies that don't belong to the hop are dropped.

Both fixtures are real hops frozen from the local raw cache (2026-10-22).
"""

from pacific_peering.atlas.client import parse_traceroute_results


def _trace(msm_id: int, prb_id: int, dst: str, hops: list[dict]) -> dict:
    return {"msm_id": msm_id, "prb_id": prb_id, "dst_addr": dst, "result": hops}


# 211495010, probe 64953 (GU, AS3605 -> NU target 49.156.48.1). Hop 4's router
# 202.128.2.86 answered 3.9s late; its reply was logged again under hop 8
# ("late": 12), next to hop 8's own router 198.81.233.25.
_GU_HOP_4 = {
    "hop": 4,
    "result": [
        {"x": "*"},
        {"late": 1, "from": "202.128.2.86", "ttl": 252, "size": 28},
        {"from": "202.128.2.86", "ttl": 252, "size": 28, "rtt": 3928.808},
        {"x": "*"},
    ],
}
_GU_HOP_8 = {
    "hop": 8,
    "result": [
        {"from": "198.81.233.25", "ttl": 248, "size": 28, "rtt": 119.644},
        {"from": "198.81.233.25", "ttl": 248, "size": 28, "rtt": 122.277},
        {"late": 12, "from": "202.128.2.86", "ttl": 252, "size": 28},
        {"from": "198.81.233.25", "ttl": 248, "size": 28, "rtt": 124.072},
    ],
}

# 218710339, probe 1018023 (SPC container on Digicel Tonga, target 103.235.110.1).
# Every reply at hops 5-6 carries "edst": "193.0.0.164" -- an ICMP error for a
# packet the probe sent to RIPE NCC, not for this traceroute -- with RTTs of
# its own (0.071ms at hop 6).
_TO_HOP_5 = {
    "hop": 5,
    "result": [
        {"x": "*"},
        {"x": "*"},
        {"from": "10.8.3.1", "ttl": 64, "size": 68, "rtt": 933.26, "edst": "193.0.0.164"},
    ],
}
_TO_HOP_6 = {
    "hop": 6,
    "result": [
        {"from": "10.8.3.1", "ttl": 64, "size": 68, "rtt": 0.071, "edst": "193.0.0.164"},
        {"from": "10.8.3.1", "ttl": 64, "size": 68, "rtt": 0.082, "edst": "193.0.0.164"},
        {"late": 14, "from": "10.1.85.1", "ttl": 63, "size": 68, "edst": "193.0.0.164"},
        {"x": "*"},
    ],
}


def test_late_reply_from_an_earlier_hop_is_not_attributed_to_a_later_hop():
    [trace] = parse_traceroute_results([_trace(211495010, 64953, "49.156.48.1", [_GU_HOP_4, _GU_HOP_8])])
    hop_4, hop_8 = trace.hops
    assert hop_8.addresses == ("198.81.233.25",)
    assert hop_8.min_rtt_ms == 119.644


def test_late_reply_does_not_remove_a_hop_that_also_answered_on_time():
    [trace] = parse_traceroute_results([_trace(211495010, 64953, "49.156.48.1", [_GU_HOP_4])])
    assert trace.hops[0].addresses == ("202.128.2.86",)
    assert trace.hops[0].min_rtt_ms == 3928.808


def test_edst_replies_leave_the_hop_dark():
    [trace] = parse_traceroute_results([_trace(218710339, 1018023, "103.235.110.1", [_TO_HOP_5, _TO_HOP_6])])
    for hop in trace.hops:
        assert hop.addresses == ()
        assert hop.min_rtt_ms is None
