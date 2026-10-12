"""Tests for router_location: an off-region router placed by its hostname, checked against the fibre floor.

Fixtures are cut down from real parsed Atlas traces (measurement IDs in each
test). Per the project owner (2026-10-12): 221439393 (MP -> TO) left the
region via Tata Los Angeles with no IXP crossing, and the IXP-only detour
rule missed it.
"""

from __future__ import annotations

import socket

from pacific_peering.analysis import router_location as rl

TATA_LA = "ix-xe-2-1-4-0.tcore2.lvw-losangeles.as6453.net"

# 221439393 probe 65653 (Saipan): AS7131 -> Tata LA -> Telstra Global -> Digicel Fiji -> Digicel Tonga.
MP_TO_TRACE = {
    "probe_id": 65653,
    "target": "202.43.12.1",
    "hops": [
        {"hop": 1, "addresses": ["192.168.1.1"], "min_rtt_ms": 1.416},
        {"hop": 4, "addresses": ["103.57.234.108"], "min_rtt_ms": 8.166},
        {"hop": 8, "addresses": ["64.86.252.73"], "min_rtt_ms": 121.458},
        {"hop": 12, "addresses": ["202.84.143.25"], "min_rtt_ms": 167.759},
        {"hop": 18, "addresses": ["202.43.12.5"], "min_rtt_ms": 212.954},
    ],
}


def _resolver(table: dict[str, str]):
    calls: list[str] = []

    def resolve(address: str) -> str | None:
        calls.append(address)
        return table.get(address)

    resolve.calls = calls
    return resolve


def test_tata_los_angeles_on_mp_to_to_is_a_hub():
    hub = rl.find_router_hub(MP_TO_TRACE, "MP", _resolver({"64.86.252.73": TATA_LA}))
    assert hub is not None
    assert (hub.probe_id, hub.hop, hub.address, hub.city) == (65653, 8, "64.86.252.73", "Los Angeles")
    assert hub.floor_ms == 94.63  # Saipan -> LA, less MP's 150km spread, fibre at 2/3 c
    assert hub.verdict == rl.HUB_OK
    assert "121.458ms" in hub.note() and "floor 94.63ms" in hub.note()


def test_hostname_too_fast_for_its_city():
    # A "lax" name on the 8.166ms PTI hop can't be in Los Angeles.
    hub = rl.find_router_hub(
        MP_TO_TRACE, "MP", _resolver({"103.57.234.108": "be1.ccr41.lax01.atlas.cogentco.com"})
    )
    assert (hub.hop, hub.city, hub.verdict) == (4, "Los Angeles", rl.HUB_TOO_FAST)


def test_only_the_first_located_hop_is_judged():
    # Too-fast hop 4 is not rescued by the genuine LA hop 8.
    hub = rl.find_router_hub(
        MP_TO_TRACE, "MP",
        _resolver({"103.57.234.108": "be1.ccr41.lax01.atlas.cogentco.com", "64.86.252.73": TATA_LA}),
    )
    assert (hub.hop, hub.verdict) == (4, rl.HUB_TOO_FAST)


def test_unmapped_city_has_no_floor():
    # 216155108 probe 7455 (VU): Cogent San Francisco at 140.259ms. No EXTERNAL_HUB_LATLON entry.
    trace = {"probe_id": 7455, "hops": [{"hop": 6, "addresses": ["154.54.168.254"], "min_rtt_ms": 140.259}]}
    hub = rl.find_router_hub(trace, "VU", _resolver({"154.54.168.254": "be5991.ccr22.sfo01.atlas.cogentco.com"}))
    assert (hub.city, hub.floor_ms, hub.verdict) == ("San Francisco", None, rl.HUB_UNMAPPED)
    assert "no hub coordinates" in hub.note()


def test_in_region_hostname_is_skipped():
    # 219060211: OneQode's router name carries a Guam token; Guam is in scope, so not a hub.
    trace = {"probe_id": 6923, "hops": [{"hop": 2, "addresses": ["103.151.64.7"], "min_rtt_ms": 70.4}]}
    resolve = _resolver({"103.151.64.7": "gu-gnc-rt1-----Vlan780.au-gssyd-rt1.oneqode.net"})
    assert rl.find_router_hub(trace, "GU", resolve) is None


def test_private_ecmp_and_rttless_hops_are_never_looked_up():
    trace = {"probe_id": 1, "hops": [
        {"hop": 1, "addresses": ["10.35.115.2"], "min_rtt_ms": 3.9},
        {"hop": 2, "addresses": ["64.86.252.73", "64.86.252.74"], "min_rtt_ms": 121.0},
        {"hop": 3, "addresses": ["64.86.252.73"], "min_rtt_ms": None},
    ]}
    resolve = _resolver({"64.86.252.73": TATA_LA, "10.35.115.2": TATA_LA})
    assert rl.find_router_hub(trace, "MP", resolve) is None
    assert resolve.calls == []


def test_no_ptr_record_means_no_hub():
    assert rl.find_router_hub(MP_TO_TRACE, "MP", _resolver({})) is None


def test_source_without_coordinates_means_no_hub():
    assert rl.find_router_hub(MP_TO_TRACE, "XX", _resolver({"64.86.252.73": TATA_LA})) is None


def test_reverse_dns_returns_none_on_lookup_failure(monkeypatch):
    def _fail(address):
        raise socket.herror(1, "Unknown host")

    rl.reverse_dns.cache_clear()
    monkeypatch.setattr(rl.socket, "gethostbyaddr", _fail)
    assert rl.reverse_dns("192.0.2.1") is None
    rl.reverse_dns.cache_clear()
