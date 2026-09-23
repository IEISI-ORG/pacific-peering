"""Tests for tracing Starlink-hosted probes to public DNS anchors.

Hop fixtures mirror the real 2026-09-23 KI/MH measurements (task_plan.md):
KI probe 1008228 died inside Starlink's private/CGNAT space, MH probe 64237
reached AS14593's routed range and handed off to AS6453.
"""

from __future__ import annotations

from pacific_peering.atlas import starlink_anchors


def _hop(n, addresses, rtt=None):
    return {"hop": n, "addresses": addresses, "min_rtt_ms": rtt}


def test_find_starlink_probes_keeps_only_connected_as14593():
    listing = {
        "KI": [
            {"id": 1008228, "status": "Connected", "asn_v4": 14593},
            {"id": 3630, "status": "Abandoned", "asn_v4": 14593},
        ],
        "MH": [{"id": 64237, "status": "Connected", "asn_v4": 14593}],
        "FJ": [{"id": 60575, "status": "Connected", "asn_v4": 141695}],
        "WS": [],
    }

    assert starlink_anchors.find_starlink_probes(listing) == {"KI": [1008228], "MH": [64237]}


def test_summary_flags_a_trace_that_never_leaves_private_or_cgnat_space():
    traceroute = {
        "probe_id": 1008228,
        "target": "1.1.1.1",
        "hops": [
            _hop(1, ["192.168.1.1"], 1.0),
            _hop(2, ["100.64.0.1"], 49.5),  # CGNAT: not is_private, but not global either
            _hop(3, ["172.16.251.0"], 45.0),
            _hop(4, ["172.16.251.115"], 44.6),
            _hop(5, []),
            _hop(6, []),
        ],
    }

    s = starlink_anchors.summarize_anchor_trace(traceroute)

    assert s.reached_target is False
    assert s.first_public_hop is None
    assert (s.last_hop, s.last_address, s.last_rtt_ms) == (4, "172.16.251.115", 44.6)


def test_summary_records_first_public_hop_and_reaching_the_anchor():
    traceroute = {
        "probe_id": 64237,
        "target": "8.8.8.8",
        "hops": [
            _hop(1, ["192.168.1.1"], 1.0),
            _hop(2, ["100.64.0.1"], 53.8),
            _hop(3, ["172.16.250.10"], 52.4),
            _hop(4, ["206.224.70.194"], 55.0),
            _hop(5, ["8.8.8.8"], 90.1),
        ],
    }

    s = starlink_anchors.summarize_anchor_trace(traceroute)

    assert s.reached_target is True
    assert s.first_public_hop == 4
    assert s.last_address == "8.8.8.8"


def test_run_fires_one_measurement_per_anchor_with_all_probes(monkeypatch):
    calls = []

    def _fire_and_persist(source_type, source_value, target_ip, description, probe_count):
        calls.append((source_type, source_value, target_ip, probe_count))
        return 1000 + len(calls)

    monkeypatch.setattr(starlink_anchors, "_fire_and_persist", _fire_and_persist)

    ids = starlink_anchors.run_starlink_anchor_traces([64237, 1008228, 1008229, 65337])

    assert ids == [1001, 1002]
    assert calls == [
        ("probes", "64237,1008228,1008229,65337", "1.1.1.1", 4),
        ("probes", "64237,1008228,1008229,65337", "8.8.8.8", 4),
    ]


def test_main_without_fire_spends_nothing(monkeypatch):
    monkeypatch.setattr(
        starlink_anchors,
        "load_probe_listing",
        lambda: {"KI": [{"id": 1008228, "status": "Connected", "asn_v4": 14593}]},
    )

    def _fire(*args, **kwargs):
        raise AssertionError("dry run must not create measurements")

    monkeypatch.setattr(starlink_anchors, "_fire_and_persist", _fire)
    monkeypatch.setattr("sys.argv", ["pacific-peering-starlink-anchors"])

    starlink_anchors.main()
