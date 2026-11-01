"""The local-IXP latency check judges the exchange hop by the time it adds, not its absolute RTT.

Owner rule queued 2026-10-05, built 2026-11-02. The old check flagged any
in-fishbowl crossing whose own reply took over 10ms from the probe. Two
things made that misfire: exchange routers answer ICMP slowly (the hop
after MARIIX was faster than MARIIX itself in all five 2026-10-05 flags),
and some probes already sit ~10ms out before any IXP (Guam's 60689/64953).
The check now takes the minimum RTT over the IXP hop and every hop after
it, minus the last answering hop before the IXP. Fixtures are real parsed
hops: (hop, min_rtt_ms).
"""

from __future__ import annotations

import pytest

from pacific_peering.analysis.auto_classify import LOCAL_IXP_LATENCY_THRESHOLD_MS, _local_ixp_excess_ms


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
def test_a_real_step_at_the_exchange_is_still_flagged(hops, ixp_hop, expected):
    assert _local_ixp_excess_ms(ixp_hop, hops) == pytest.approx(expected)
    assert _local_ixp_excess_ms(ixp_hop, hops) > LOCAL_IXP_LATENCY_THRESHOLD_MS


def test_an_exchange_at_the_first_answering_hop_is_measured_from_the_probe():
    assert _local_ixp_excess_ms(1, _hops((1, 12.5), (2, 13.0))) == pytest.approx(12.5)


def test_unknown_hop_falls_back_to_none():
    assert _local_ixp_excess_ms(99, _GUAM_IX_REMOTE_PORT) is None
