"""Regression tests for known_anomalies.py, frozen from real traces."""

from pacific_peering.analysis.known_anomalies import classify_loop_address
from pacific_peering.atlas.targets import looping_address

# Probe 60575 (AS141695) -> FNPF 203.55.68.1, measurement 227408126 (2026-10-25).
FNPF_EDGE_HOPS = [
    {"hop": 1, "addresses": ["192.168.3.37"], "min_rtt_ms": 0.51},
    {"hop": 2, "addresses": ["192.168.8.9"], "min_rtt_ms": 0.523},
    {"hop": 3, "addresses": ["202.0.156.1"], "min_rtt_ms": 0.468},
    {"hop": 4, "addresses": ["202.0.158.254"], "min_rtt_ms": 0.547},
    {"hop": 5, "addresses": ["202.62.126.21"], "min_rtt_ms": 1.431},
    {"hop": 6, "addresses": [], "min_rtt_ms": None},
    {"hop": 7, "addresses": [], "min_rtt_ms": None},
    {"hop": 8, "addresses": [], "min_rtt_ms": None},
    {"hop": 9, "addresses": ["202.62.124.41"], "min_rtt_ms": 2.227},
    {"hop": 10, "addresses": ["202.62.124.42"], "min_rtt_ms": 1.215},
    {"hop": 11, "addresses": [], "min_rtt_ms": None},
    # The real reply carries err=H (host unreachable); added 2026-11-02 when
    # the parser started keeping ICMP errors.
    {"hop": 12, "addresses": ["202.62.124.42"], "min_rtt_ms": 1.551, "error_addresses": ["202.62.124.42"]},
]


def test_fnpf_edge_tail_is_not_a_loop() -> None:
    # .42 answers again only to report the target unreachable: FNPF's filtered
    # edge, not a cycle (owner rule queued 2026-10-05, built 2026-11-02).
    assert looping_address(FNPF_EDGE_HOPS, target="203.55.68.1") is None


def test_fnpf_edge_tail_without_the_error_would_be_a_known_location() -> None:
    hops = [dict(h) for h in FNPF_EDGE_HOPS]
    hops[-1].pop("error_addresses")
    address = looping_address(hops, target="203.55.68.1")
    assert address == "202.62.124.42"
    loc = classify_loop_address(address)
    assert loc is not None
    assert loc.asn == 4638


def test_fnpf_edge_entry_stays_narrow() -> None:
    assert classify_loop_address("202.62.124.41") is not None
    assert classify_loop_address("202.62.124.44") is None
    assert classify_loop_address("202.62.126.21") is None
