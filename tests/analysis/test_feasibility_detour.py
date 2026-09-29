"""Validation Rule 2 on detour claims (analysis/feasibility.py), wired into
nightly classification 2026-09-29 after a report-only sweep of the corpus."""

from __future__ import annotations

from types import SimpleNamespace

from pacific_peering.analysis import feasibility as fz

NC, SYDNEY, SUVA = (-22.2758, 166.4580), (-33.8688, 151.2093), (-18.1416, 178.4419)
EQUINIX_SYD = 1
TARGET = "103.101.240.1"


def _check(probe_id, hops, target=TARGET, spreads=(0.0, 0.0)):
    """hops: (hop, rtt, addresses, ix_id or None)."""
    trace = {"probe_id": probe_id, "target": target,
             "hops": [{"hop": h, "min_rtt_ms": rtt, "addresses": addrs} for h, rtt, addrs, _ in hops]}
    resolved = [SimpleNamespace(hop=h, asns=(), ixp_context={"ix_id": ix} if ix else None) for h, _, _, ix in hops]
    return fz.check_detour_trace(trace, resolved, NC, SYDNEY, "Sydney", SUVA, {EQUINIX_SYD: "Sydney"}, *spreads)


def test_offshore_target_breaks_the_via_hub_floor():
    # Real shape of #115 (msm 212237062): Sydney crossing fine, target answers too fast for Suva.
    c = _check(7018, [(1, 0.4, ["a"], None), (4, 23.7, ["ix"], EQUINIX_SYD), (6, 37.3, ["b"], None),
                      (8, 37.0, [TARGET], None)])
    assert c["hub"]["verdict"] == fz.VERDICT_OK
    assert c["target_via_hub"]["verdict"] == fz.VERDICT_IMPOSSIBLE and c["target_via_hub"]["hop"] == 8
    assert fz.probe_verdict(c) == fz.VERDICT_IMPOSSIBLE


def test_trace_that_never_reached_the_target_is_not_target_checked():
    # A target network's Sydney PoP answering at 25ms, then dark: not evidence against the detour.
    c = _check(1, [(4, 23.7, ["ix"], EQUINIX_SYD), (5, 25.0, ["pop"], None), (255, 25.1, ["pop"], None)])
    assert c["target_via_hub"]["verdict"] == fz.VERDICT_NO_HOP
    assert _check(1, [(8, 30.0, [TARGET], None)], target=None)["target_via_hub"]["verdict"] == fz.VERDICT_NO_HOP


def test_spread_lowers_every_floor():
    hops = [(4, 23.7, ["ix"], EQUINIX_SYD), (8, 45.0, [TARGET], None)]
    tight, loose = _check(1, hops), _check(1, hops, spreads=(450, 700))
    assert loose["target_via_hub"]["floor_ms"] < tight["target_via_hub"]["floor_ms"]
    assert tight["target_via_hub"]["verdict"] == fz.VERDICT_IMPOSSIBLE
    assert loose["target_via_hub"]["verdict"] == fz.VERDICT_OK


def test_ecmp_hop_supplies_no_rtt():
    c = _check(1, [(4, 23.7, ["ix"], EQUINIX_SYD), (8, 20.0, [TARGET, "near"], None)])
    assert c["target_via_hub"]["verdict"] == fz.VERDICT_NO_HOP


def test_hub_hop_below_floor_is_impossible():
    assert _check(1, [(3, 5.0, ["ix"], EQUINIX_SYD)])["hub"]["verdict"] == fz.VERDICT_IMPOSSIBLE


def test_claim_probes_prefer_hub_crossers_even_without_an_rtt():
    crossed = _check(1, [(4, 23.7, ["ix"], EQUINIX_SYD), (8, 70.0, [TARGET], None)])
    crossed_no_rtt = _check(2, [(4, None, ["ix"], EQUINIX_SYD)])
    direct = _check(3, [(3, 14.0, [TARGET], None)])  # another source ASN going direct
    assert fz.claim_probes([crossed, direct]) == [crossed]
    assert fz.claim_probes([crossed_no_rtt, direct]) == [crossed_no_rtt]
    assert fz.claim_probes([direct]) == [direct]
    assert fz.claim_verdict([crossed]) == fz.VERDICT_OK
    assert fz.claim_verdict([crossed, direct]) == fz.VERDICT_MIXED
    assert fz.claim_verdict([crossed_no_rtt]) == fz.VERDICT_NO_HOP
