"""Starlink failover behind a probe's own public LAN must not pass rule 0.

Niue probe 64391 sits on public Telecom Niue space (49.156.50.5, gateway
49.156.50.254, AS55885). On 2026-11-11 06:10-17:35Z its site failed over to
Starlink. The egress trace 236238083 (frozen below) resolves to
[55885, 14593, 13335]: the site's own gateway first, then Starlink. Rule 0
and probe watch only looked at the first ASN, so both read it as AS55885.

The guard skips the probe's own LAN ASN (the ASN of its public source
address) only to see whether the next network is non-local. Paths from
probes on private LANs are unchanged: French Polynesia probes' traces start
at Hurricane Electric with Starlink on the *target* side (211699570), and
must keep their first ASN.
"""

from __future__ import annotations

from pacific_peering.analysis import auto_classify
from pacific_peering.analysis import traceroute_topology as tt
from pacific_peering.atlas import probe_watch as pw

from tests.analysis.test_auto_classify import _candidate, _patch_common

# Probe 64391's hops in measurement 236238083 (2026-11-11 15:01Z), first five.
FAILOVER_TRACE_64391 = {
    "measurement_id": 236238083,
    "probe_id": 64391,
    "target": "1.1.1.1",
    "source_address": "49.156.50.5",
    "hops": [
        {"hop": 1, "addresses": ["49.156.50.254"], "min_rtt_ms": 0.4},
        {"hop": 2, "addresses": ["14.1.76.1"], "min_rtt_ms": 50.1},
        {"hop": 3, "addresses": ["172.16.252.122"], "min_rtt_ms": 53.0},
        {"hop": 4, "addresses": ["206.224.69.76"], "min_rtt_ms": 53.2},
        {"hop": 5, "addresses": ["206.224.66.34"], "min_rtt_ms": 53.4},
    ],
}
ASN_OF = {
    "49.156.50.5": 55885, "49.156.50.254": 55885, "14.1.76.1": 14593,
    "206.224.69.76": 14593, "206.224.66.34": 14593,
}


def _fake_bgp(monkeypatch):
    monkeypatch.setattr(tt, "resolve_ip_to_asns", lambda ip: [ASN_OF[ip]] if ip in ASN_OF else [])
    monkeypatch.setattr(tt, "resolve_ip_via_netixlan", lambda ip: None)


def test_guard_sees_starlink_behind_the_probes_own_public_lan():
    assert auto_classify.egress_guard_asn([55885, 14593, 13335], source_lan_asn=55885) == 14593


def test_guard_keeps_the_first_asn_for_a_normal_public_lan_path():
    assert auto_classify.egress_guard_asn([55885, 4637, 13335], source_lan_asn=55885) == 55885


def test_guard_keeps_starlink_on_the_target_side_for_a_private_lan_probe():
    assert auto_classify.egress_guard_asn([6939, 14593, 154100], source_lan_asn=None) == 6939


def test_guard_still_catches_a_non_local_first_asn():
    assert auto_classify.egress_guard_asn([14593, 139759], source_lan_asn=None) == 14593


def test_source_lan_asn_resolves_only_a_public_source_address(monkeypatch, tmp_path):
    _fake_bgp(monkeypatch)
    kwargs = {"cache_path": tmp_path / "cache.json", "ixp_registry_path": tmp_path / "none.json"}
    assert tt.source_lan_asn(FAILOVER_TRACE_64391, **kwargs) == 55885
    assert tt.source_lan_asn({**FAILOVER_TRACE_64391, "source_address": "192.168.1.20"}, **kwargs) is None
    assert tt.source_lan_asn({"hops": []}, **kwargs) is None  # parsed before source_address was kept


def test_rule0_drops_a_starlink_failover_behind_a_public_lan(monkeypatch, tmp_path):
    probe = {
        "probe_id": 64391,
        "source_lan_asn": 55885,
        "as_sequence": [
            {"asn": asn, "resolution_source": "bgp", "contiguous_with_previous": True}
            for asn in (55885, 14593, 13335)
        ],
        "ixp_crossings": [],
        "traceroute_upstream_asn": 14593,
        "ris_agrees": False,
        "contiguous": True,
        "ris_observation_count": 0,
    }
    triangulation = {"measurement_id": 900000001, "target_asn": 24439, "probes": [probe]}
    _patch_common(monkeypatch, tmp_path, triangulation, [{"probe_id": 64391, "hops": []}])

    result = auto_classify.classify_corridor(_candidate())

    assert result.outcome == "escalated"
    assert "probe 64391 via Starlink" in result.escalations[0].detail


def test_probe_watch_reports_the_starlink_failover(monkeypatch, tmp_path):
    _fake_bgp(monkeypatch)
    monkeypatch.setattr(tt, "DEFAULT_CACHE_PATH", tmp_path / "cache.json")
    real_resolve = tt.resolve_traceroute_hops
    monkeypatch.setattr(
        pw, "resolve_traceroute_hops",
        lambda hops: real_resolve(hops, cache_path=tmp_path / "cache.json", ixp_registry_path=tmp_path / "x"),
    )
    monkeypatch.setattr(
        pw, "source_lan_asn",
        lambda trace: tt.source_lan_asn(trace, cache_path=tmp_path / "cache.json", ixp_registry_path=tmp_path / "x"),
    )

    assert pw.first_egress_asn(FAILOVER_TRACE_64391) == 14593


def test_feasibility_sweep_skips_the_starlink_failover(monkeypatch, tmp_path):
    from pacific_peering.analysis import feasibility_sweep as fs

    _fake_bgp(monkeypatch)
    kwargs = {"cache_path": tmp_path / "cache.json", "ixp_registry_path": tmp_path / "x"}
    sequence = tt.extract_as_sequence(tt.resolve_traceroute_hops(FAILOVER_TRACE_64391["hops"], **kwargs))
    monkeypatch.setattr(fs, "source_lan_asn", lambda trace, persist=False: tt.source_lan_asn(trace, **kwargs))

    assert fs._non_local_egress(FAILOVER_TRACE_64391, sequence)
    assert not fs._non_local_egress({**FAILOVER_TRACE_64391, "source_address": None}, sequence)
