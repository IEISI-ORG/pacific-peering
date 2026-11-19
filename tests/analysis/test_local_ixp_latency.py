"""The local-IXP latency check judges the exchange hop by the time it adds, not its absolute RTT.

Owner rule queued 2026-10-05, built 2026-11-02. The old check flagged any
in-fishbowl crossing whose own reply took over 10ms from the probe. Two
things made that misfire: exchange routers answer ICMP slowly (the hop
after MARIIX was faster than MARIIX itself in all five 2026-10-05 flags),
and some probes already sit ~10ms out before any IXP (Guam's 60689/64953).
The check now takes the minimum RTT over the IXP hop and every hop after
it, minus the last answering hop before the IXP. Fixtures are real parsed
hops: (hop, min_rtt_ms).

Owner, 2026-11-19 (review_ixp_latency.md, option B): the flat 10ms assumed
probe, exchange and member router all sit in one metro. Remote member ports
(PNCC's Guam IX .18 on a router in Koror, CenPac's .24 in Nauru) and cable
legs into the exchange flagged every rotation. The allowance is now
10ms + leg_in + leg_out at stretch 1.5 on plain great-circle floors:
leg_in from the probe's economy to the exchange's, less what the hop before
the exchange already paid; leg_out only for ports confirmed remote
(REMOTE_IXP_PORTS; code review of fbbb5e8, owner 2026-11-19).
"""

from __future__ import annotations

import pytest

from pacific_peering.analysis.auto_classify import (
    LOCAL_IXP_CABLE_STRETCH,
    LOCAL_IXP_LATENCY_THRESHOLD_MS,
    _economy_floor_ms,
    _local_ixp_check,
    _local_ixp_excess_ms,
)


def _hops(*pairs: tuple[int, float | None]) -> list[dict]:
    return [{"hop": n, "addresses": [] if rtt is None else ["192.0.2.1"], "min_rtt_ms": rtt} for n, rtt in pairs]


# 213204603, probe 64953 (GU -> GU): MARIIX at hop 6 is 15.7ms, the next hop 9.8ms.
_MARIIX_SLOW_REPLY = _hops((1, 0.957), (2, 1.139), (3, None), (4, 12.976), (5, 10.796),
                           (6, 15.741), (7, 9.8), (8, 9.7), (9, None))
# 229249301, probe 60689 (GU -> GU): MARIIX at hop 8 is 10.07ms; the probe was already 25ms out at hop 7.
_MARIIX_PROBE_BASELINE = _hops((1, 0.887), (2, 45.538), (3, 10.703), (4, 9.3), (5, 14.912),
                               (6, 10.723), (7, 25.243), (8, 10.067), (9, 27.341))
# 228736784, probe 7018 (NC -> FJ AS45355): FINTEL 16.0ms (the cable), Fiji-IXP .20 16.45ms.
_FIJI_IXP_AFTER_CABLE = _hops((1, 0.32), (2, 0.434), (3, 1.289), (4, None), (5, None), (6, None),
                              (7, 15.972), (8, 16.45), (9, None), (10, 17.534), (11, 18.0))
# 228735988, probe 33674 (NC -> FJ AS4638): FINTEL 16.0ms, TFL's port .30 40.3ms, TFL core 39.0ms.
_FIJI_IXP_TFL_STEP = _hops((1, 0.282), (2, 0.695), (3, 1.322), (4, None), (5, None), (6, None),
                           (7, 15.994), (8, 40.32), (9, 39.024), (10, None), (11, 42.988))
# 228736794, probe 7385 (GU -> PW): PNCC's Guam IX port .18 answers 19.1ms out (remote port).
_GUAM_IX_REMOTE_PORT = _hops((1, 0.249), (2, 19.128), (3, 19.3))


@pytest.mark.parametrize("hops, ixp_hop", [
    (_MARIIX_SLOW_REPLY, 6),
    (_MARIIX_PROBE_BASELINE, 8),
    (_FIJI_IXP_AFTER_CABLE, 8),
])
def test_ordinary_crossings_are_within_the_threshold(hops, ixp_hop):
    assert _local_ixp_excess_ms(ixp_hop, hops) <= LOCAL_IXP_LATENCY_THRESHOLD_MS


@pytest.mark.parametrize("hops, ixp_hop, expected", [
    (_FIJI_IXP_TFL_STEP, 8, 39.024 - 15.994),
    (_GUAM_IX_REMOTE_PORT, 2, 19.128 - 0.249),
])
def test_the_excess_is_the_step_at_the_exchange(hops, ixp_hop, expected):
    assert _local_ixp_excess_ms(ixp_hop, hops) == pytest.approx(expected)
    assert _local_ixp_excess_ms(ixp_hop, hops) > LOCAL_IXP_LATENCY_THRESHOLD_MS


def test_an_exchange_at_the_first_answering_hop_is_measured_from_the_probe():
    assert _local_ixp_excess_ms(1, _hops((1, 12.5), (2, 13.0))) == pytest.approx(12.5)


def test_unknown_hop_falls_back_to_none():
    assert _local_ixp_excess_ms(99, _GUAM_IX_REMOTE_PORT) is None


# --- The two-leg allowance (owner, 2026-11-19) ----------------------------------------------

GUAM_IX, FIJI_IXP = 4494, 3085  # PeeringDB ix_id


def _crossing(hop: int, rtt: float, *member_asns: int, ix_id: int = GUAM_IX) -> dict:
    return {"hop": hop, "min_rtt_ms": rtt, "member_asns": list(member_asns), "ix_id": ix_id, "in_fishbowl": True}


# 235634536, probe 7385 (GU -> PW): PNCC AS17893's Guam IX port .18 at 19.05ms. The router is
# in Koror (anchoring mesh 86005050: Guam anchor -> .18 18.90 -> Koror anchor 19.10).
_GU_TO_PNCC_PORT = _hops((1, 0.354), (2, 19.05), (3, 19.032))
# 234928910, probe 7455 (PW -> NR): PNCC's Koror routers, then CenPac AS55722's Guam IX port .24
# at 54.483ms on a router in Nauru (CenPac core 0.005-0.03ms behind it).
_PW_TO_CENPAC_PORT = _hops((1, 0.178), (2, 0.221), (3, 54.483), (4, 54.488), (5, 54.51))
# 234926407, probe 7448 (FM -> PW): FSMTC's Guam routers at 19.7ms, then PNCC's .18 at 38.6ms.
_FM_TO_PNCC_PORT = _hops((1, 0.19), (2, 0.318), (3, 19.746), (4, 19.81), (5, 38.649), (6, 38.749))
# 235633070, probe 7018 (NC -> FJ AS4638): FINTEL 16.0ms, TFL AS45349's Fiji-IXP port .30 39.2ms.
# Forward is local; TFL's reply comes back via Sydney (anchoring 31472919, probe 60575).
_NC_TO_TFL_PORT = _hops((1, 0.432), (2, 0.436), (3, 1.414), (4, None), (5, None), (6, None),
                        (7, 16.007), (8, 39.157), (9, 38.52), (10, None), (11, 39.12))


@pytest.mark.parametrize("hops, crossing, probe_cc, ixp_cc", [
    # Remote port from the exchange's own economy: leg_out GU -> PW only.
    (_GU_TO_PNCC_PORT, _crossing(2, 19.05, 17893), "GU", "GU"),
    # The pre-2026-11-19 fixture of the same shape (228736794), which used to flag.
    (_GUAM_IX_REMOTE_PORT, _crossing(2, 19.128, 17893), "GU", "GU"),
    # Two remote legs: Koror -> Guam IX in, Guam IX -> Nauru out.
    (_PW_TO_CENPAC_PORT, _crossing(3, 54.483, 55722), "PW", "GU"),
    # FM -> Guam leg already paid before the exchange, then PNCC's remote port.
    (_FM_TO_PNCC_PORT, _crossing(5, 38.649, 17893), "FM", "GU"),
    # Fiji-IXP .20 just after the NC -> FJ cable (228736784).
    (_FIJI_IXP_AFTER_CABLE, _crossing(8, 16.45, 45355, ix_id=FIJI_IXP), "NC", "FJ"),
])
def test_remote_ports_and_cable_legs_are_not_flagged(hops, crossing, probe_cc, ixp_cc):
    assert _local_ixp_check(crossing, hops, probe_cc, ixp_cc) is None


@pytest.mark.parametrize("hops, crossing, excess, allowance", [
    # leg_in = 1.5 x 13.33 (NC -> FJ) - 16.007 (FINTEL) ~ 4.0; leg_out 0 (TFL is in Fiji).
    (_NC_TO_TFL_PORT, _crossing(8, 39.157, 45349, ix_id=FIJI_IXP), 38.52 - 16.007, 14.0),
    (_FIJI_IXP_TFL_STEP, _crossing(8, 40.32, 45349, ix_id=FIJI_IXP), 39.024 - 15.994, 14.0),
])
def test_the_tfl_return_via_sydney_is_still_flagged(hops, crossing, excess, allowance):
    flag = _local_ixp_check(crossing, hops, "NC", "FJ")
    assert flag is not None
    assert flag.excess_ms == pytest.approx(excess)
    assert flag.leg_out_ms == 0.0
    assert flag.allowance_ms == pytest.approx(allowance, abs=0.1)


def test_leg_in_is_only_what_the_hops_before_the_exchange_have_not_paid():
    # Same NC -> FJ cable, but the hop before the exchange is the probe's LAN at 1ms:
    # the allowance now carries most of the 20ms cable leg.
    hops = _hops((1, 1.0), (2, 23.0), (3, 23.1))
    flag_or_none = _local_ixp_check(_crossing(2, 23.0, 45349), hops, "NC", "FJ")
    assert flag_or_none is None


def test_a_local_member_and_a_local_probe_keep_the_flat_10ms():
    hops = _hops((1, 0.5), (2, 12.0), (3, 12.1))
    flag = _local_ixp_check(_crossing(2, 12.0, 45349), hops, "FJ", "FJ")
    assert flag is not None
    assert (flag.leg_in_ms, flag.leg_out_ms) == (0.0, 0.0)
    assert flag.allowance_ms == LOCAL_IXP_LATENCY_THRESHOLD_MS


def test_an_unknown_member_or_probe_economy_adds_no_allowance():
    hops = _hops((1, 0.5), (2, 12.0), (3, 12.1))
    flag = _local_ixp_check(_crossing(2, 12.0, 64500), hops, None, "GU")
    assert flag is not None
    assert flag.allowance_ms == LOCAL_IXP_LATENCY_THRESHOLD_MS


def test_an_exchange_hop_under_10ms_is_never_flagged():
    hops = _hops((1, 0.5), (2, 9.0))
    assert _local_ixp_check(_crossing(2, 9.0), hops, "FJ", "FJ") is None


def test_an_uncomputable_excess_still_flags():
    flag = _local_ixp_check(_crossing(99, 30.0, 45349), _GUAM_IX_REMOTE_PORT, "FJ", "FJ")
    assert flag is not None
    assert flag.excess_ms is None


# --- leg_out only for ports confirmed remote (code review of fbbb5e8, owner 2026-11-19) -------
# FSMTC (AS10130, registered FM) has its Guam IX port on a router in Guam: its cached crossings
# add -5.4 to 2.9ms (228276710, 228277589, 234924588, 234926289). A home-economy leg_out gave it
# 24.6ms of slack, enough to hide a backhaul. Only PNCC .18 (Koror) and CenPac .24 (Nauru) are
# known remote ports.
_GU_LOCAL_PORT_BACKHAUL = _hops((1, 0.5), (2, 30.0), (3, 30.1))


def test_a_local_port_of_a_member_from_another_economy_gets_no_leg_out():
    flag = _local_ixp_check(_crossing(2, 30.0, 10130), _GU_LOCAL_PORT_BACKHAUL, "GU", "GU")
    assert flag is not None
    assert flag.leg_out_ms == 0.0
    assert flag.allowance_ms == LOCAL_IXP_LATENCY_THRESHOLD_MS


@pytest.mark.parametrize("members", [(3605, 10130), (10130, 3605), (6939, 10130), (17893, 10130)])
def test_member_order_does_not_decide_the_leg_out(members):
    # member_asns is sorted by ASN number, not by who owns the port: any member that is not a
    # confirmed remote port means no leg_out.
    flag = _local_ixp_check(_crossing(2, 30.0, *members), _GU_LOCAL_PORT_BACKHAUL, "GU", "GU")
    assert flag is not None
    assert flag.leg_out_ms == 0.0


def test_two_remote_members_get_the_shorter_leg():
    flag = _local_ixp_check(_crossing(2, 120.0, 17893, 55722), _hops((1, 0.5), (2, 120.0), (3, 120.1)),
                            "GU", "GU")
    assert flag is not None
    assert flag.leg_out_ms == pytest.approx(LOCAL_IXP_CABLE_STRETCH * _economy_floor_ms("GU", "PW"))


def test_a_remote_port_is_tied_to_its_exchange():
    # PNCC's port is remote at Guam IX; the same ASN at another exchange gets no leg_out.
    flag = _local_ixp_check(_crossing(2, 30.0, 17893, ix_id=FIJI_IXP), _GU_LOCAL_PORT_BACKHAUL, "FJ", "FJ")
    assert flag is not None
    assert flag.leg_out_ms == 0.0


def test_missing_member_asns_is_safe():
    crossing = {**_crossing(2, 30.0), "member_asns": None}
    flag = _local_ixp_check(crossing, _GU_LOCAL_PORT_BACKHAUL, "GU", "GU")
    assert flag is not None
    assert flag.leg_out_ms == 0.0
