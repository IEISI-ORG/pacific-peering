"""Tests for hidden_hops: is anything out of view between the target and the hop before it?

Fixtures are cut down from real raw Atlas results (measurement IDs in each
test). Per the project owner (2026-10-09): a lack of real hop data is just
inconclusive every time.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pacific_peering.analysis.hidden_hops import hidden_hops_reason


def _hop(hop: int, address: str | None, ttl: int | None = None, ittl: int | None = None) -> dict:
    if address is None:
        return {"hop": hop, "result": [{"x": "*"}] * 3}
    reply: dict = {"from": address, "ttl": ttl, "rtt": 1.0}
    if ittl is not None:
        reply["ittl"] = ittl
    return {"hop": hop, "result": [reply] * 3}


def _result(dst: str, hops: list[dict]) -> dict:
    return {"dst_addr": dst, "prb_id": 1, "result": hops}


def test_plain_one_hop_step_shows_nothing_hidden():
    # 213206915 probe 60703: 103.142.153.22 ttl 253 -> target ttl 252.
    raw = _result("103.115.192.1", [_hop(3, "103.142.153.22", 253), _hop(4, "103.115.192.1", 252)])
    assert hidden_hops_reason(raw, target_hop=4) is None


def test_ittl_on_the_target_reply_is_a_forward_ttl_reset():
    # 218712900 (#273): target answered with ittl=240 for a TTL-5 packet.
    raw = _result(
        "103.49.173.1",
        [_hop(4, "202.43.14.173", 252), _hop(5, "103.49.173.1", 238, ittl=240)],
    )
    reason = hidden_hops_reason(raw, target_hop=5)
    assert reason is not None and "ittl=240" in reason


def test_return_ttl_jump_past_onequode_sydney_is_hidden_hops():
    # 220522848 (#291): OneQode 103.151.64.7 ttl 60 (4 back), SISCC ttl 244
    # (11 back) one forward hop later -- ~6 routers out of view.
    raw = _result("103.142.98.1", [_hop(5, "103.151.64.7", 60), _hop(6, "103.142.98.1", 244)])
    reason = hidden_hops_reason(raw, target_hop=6)
    assert reason is not None and "6" in reason


def test_excess_of_five_is_flagged():
    # 213206915 probe 329: 103.212.24.74 ttl 253 (2 back) at 1.9ms, target
    # ttl 247 (8 back) at 128ms one hop later.
    raw = _result("103.115.192.1", [_hop(6, "103.212.24.74", 253), _hop(7, "103.115.192.1", 247)])
    assert hidden_hops_reason(raw, target_hop=7) is not None


def test_excess_of_four_is_ordinary_return_asymmetry():
    # 213207618 probe 65337: HE 184.105.223.250 ttl 52 (12 back) -> target
    # ttl 238 (17 back) one hop later, RTT falling, not rising.
    raw = _result("103.115.192.1", [_hop(15, "184.105.223.250", 52), _hop(16, "103.115.192.1", 238)])
    assert hidden_hops_reason(raw, target_hop=16) is None


def test_dark_hops_are_skipped_back_to_the_last_responding_hop():
    # 220526456 (#294): hop 6 dark. The forward gap (2 hops) is credited
    # before the return-TTL comparison: OneQode ttl 60 (4 back), Solitech
    # ttl 52 (12 back) -> excess 6.
    raw = _result(
        "103.166.98.1",
        [_hop(5, "103.151.64.7", 60), _hop(6, None), _hop(7, "103.166.98.1", 52)],
    )
    assert hidden_hops_reason(raw, target_hop=7) is not None


def test_no_earlier_responding_hop_is_not_flagged():
    raw = _result("103.115.192.1", [_hop(1, None), _hop(2, "103.115.192.1", 254)])
    assert hidden_hops_reason(raw, target_hop=2) is None


def test_target_hop_without_replies_is_not_flagged():
    raw = _result("103.115.192.1", [_hop(1, "10.0.0.1", 64), _hop(2, None)])
    assert hidden_hops_reason(raw, target_hop=2) is None


# Regression set from real traces (owner, 2026-10-09: "the hop count
# scenarios will also make a good set of regression tests"). Built from the
# 610 target-reaching final segments in data/atlas/raw on 2026-10-09, cut
# down to (last responding hop .. target hop): every segment the rule flags,
# every unflagged one at excess 2-4, and a sample of ordinary (-1..+1) and
# negative ones. Each label was checked against the RTT step independently
# of the TTL rule.
_SCENARIOS = json.loads((Path(__file__).parent / "fixtures" / "hidden_hops_scenarios.json").read_text())


@pytest.mark.parametrize(
    "scenario", _SCENARIOS, ids=[f"{s['measurement_id']}-p{s['probe_id']}" for s in _SCENARIOS]
)
def test_real_trace_scenarios_keep_their_verdict(scenario):
    reason = hidden_hops_reason(scenario["raw"], scenario["target_hop"])
    assert (reason is not None) == scenario["hidden"], reason


def test_every_flagged_real_scenario_jumps_at_least_40ms_in_one_step():
    """The physical check behind the threshold: nothing is flagged on TTLs alone."""
    flagged = [s for s in _SCENARIOS if s["hidden"]]
    assert len(flagged) == 9
    assert all(after - before >= 40 for before, after in (s["rtt_step_ms"] for s in flagged))


def test_unflagged_borderline_real_scenarios_have_a_flat_rtt_step():
    borderline = [s for s in _SCENARIOS if not s["hidden"] and 2 <= s["excess"] <= 4]
    assert len(borderline) == 13
    assert all(after - before < 15 for before, after in (s["rtt_step_ms"] for s in borderline))
