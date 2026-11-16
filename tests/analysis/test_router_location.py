"""Tests for router_location: an off-region router placed by its hostname, checked against the fibre floor.

Fixtures are cut down from real parsed Atlas traces (measurement IDs in each
test). Per the project owner (2026-10-12): 221439393 (MP -> TO) left the
region via Tata Los Angeles with no IXP crossing, and the IXP-only detour
rule missed it.
"""

from __future__ import annotations


from pacific_peering.analysis import router_location as rl
from pacific_peering.discovery.economy_coordinates import EXTERNAL_HUB_LATLON

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


def test_a_too_fast_hop_is_not_rescued_by_a_later_genuine_one():
    # Too-fast hop 4 is not rescued by the genuine LA hop 8.
    hub = rl.find_router_hub(
        MP_TO_TRACE, "MP",
        _resolver({"103.57.234.108": "be1.ccr41.lax01.atlas.cogentco.com", "64.86.252.73": TATA_LA}),
    )
    assert (hub.hop, hub.verdict) == (4, rl.HUB_TOO_FAST)


AARNET_SYDNEY = "xe-0-0-2.pe1.bkvl.nsw.aarnet.net.au"  # real name, last hub of #109's traces (224429298)


def test_the_last_located_hop_is_the_hub():
    # Owner's rule (#58 2026-11-02, #33 2026-11-06): the hub is the last city outside the
    # region. Tata LA at hop 8 is only where the path picks up; hop 13 (170.5ms) is named Sydney.
    hub = rl.find_router_hub(
        MP_TO_TRACE | {"hops": MP_TO_TRACE["hops"] + [
            {"hop": 13, "addresses": ["202.84.143.69"], "min_rtt_ms": 170.517}]},
        "MP", _resolver({"64.86.252.73": TATA_LA, "202.84.143.69": AARNET_SYDNEY}),
    )
    assert (hub.hop, hub.address, hub.city, hub.verdict) == (13, "202.84.143.69", "Sydney", rl.HUB_OK)


def test_a_too_fast_hop_after_a_genuine_one_is_still_reported():
    # A later impossible name (LA at 40ms from Saipan, floor 94.63ms) must not hide behind
    # an earlier plausible hop (Tokyo at 30ms, floor 22.1ms).
    trace = {"probe_id": 65653, "hops": [
        {"hop": 5, "addresses": ["64.86.252.73"], "min_rtt_ms": 30.0},
        {"hop": 6, "addresses": ["202.84.143.25"], "min_rtt_ms": 40.0},
    ]}
    hub = rl.find_router_hub(trace, "MP", _resolver({
        "64.86.252.73": "if-ae-51-2.tcore1.tv2-tokyo.as6453.net", "202.84.143.25": "be1.ccr41.lax01.atlas.cogentco.com"}))
    assert (hub.hop, hub.city, hub.verdict) == (6, "Los Angeles", rl.HUB_TOO_FAST)


def test_unmapped_city_has_no_floor(monkeypatch):
    # Every city in the pattern table has coordinates (Hong Kong since 2026-11-17), so drop
    # one to exercise the unmapped path. OneQode Hong Kong (hk-mgi, 211527961).
    monkeypatch.delitem(EXTERNAL_HUB_LATLON, "Hong Kong")
    trace = {"probe_id": 65653, "hops": [{"hop": 6, "addresses": ["103.151.64.21"], "min_rtt_ms": 95.0}]}
    hub = rl.find_router_hub(trace, "MP", _resolver({"103.151.64.21": "hk-mgi-rt1.oneqode.net"}))
    assert (hub.city, hub.floor_ms, hub.verdict) == ("Hong Kong", None, rl.HUB_UNMAPPED)
    assert "no hub coordinates" in hub.note()


def test_san_francisco_is_mapped():
    # 224427229 probe 64953 (GU): Cogent San Francisco at 141.218ms, escalated as unmapped
    # until the hub was added (owner, 2026-10-21).
    trace = {"probe_id": 64953, "hops": [{"hop": 13, "addresses": ["154.54.43.9"], "min_rtt_ms": 141.218}]}
    hub = rl.find_router_hub(trace, "GU", _resolver({"154.54.43.9": "be3669.ccr21.sfo01.atlas.cogentco.com"}))
    assert (hub.city, hub.floor_ms, hub.verdict) == ("San Francisco", 92.95, rl.HUB_OK)


def test_hong_kong_is_mapped():
    # 212458784 probe 65337 (GU): Telstra Global hkck at 58.626ms, 0.1ms after HKIX.
    # Guam -> Hong Kong 3324km less GU's 50km spread: floor 33.27ms (owner, 2026-11-17).
    trace = {"probe_id": 65337, "hops": [{"hop": 9, "addresses": ["202.84.157.38"], "min_rtt_ms": 58.626}]}
    hub = rl.find_router_hub(trace, "GU", _resolver({"202.84.157.38": "i-96.hkck-core01.telstraglobal.net"}))
    assert hub is not None
    assert (hub.city, hub.floor_ms, hub.verdict) == ("Hong Kong", 33.27, rl.HUB_OK)


def test_in_region_hostname_is_skipped():
    # 103.151.64.6 sits on OneQode's Guam router (`<far end>-----<vlan>.gu-gnc-rt1`);
    # Guam is in scope, so not a hub.
    trace = {"probe_id": 50365, "hops": [{"hop": 5, "addresses": ["103.151.64.6"], "min_rtt_ms": 108.051}]}
    resolve = _resolver({"103.151.64.6": "au-gssyd-rt1-----Vlan780.gu-gnc-rt1.oneqode.net"})
    assert rl.find_router_hub(trace, "GU", resolve) is None


def test_oneqode_sydney_interface_from_guam_is_a_hub():
    # 223636622 probe 6923 (OneQode Guam): 0.229ms to the Guam router, then 103.151.64.7,
    # named for au-gssyd-rt1 (the router after the dot), at 70.375ms. Owner, 2026-11-16:
    # that is OneQode's Sydney router, not Guam. (The next hop, EdgeIX Sydney at 70.847ms,
    # is left unresolved here so only the OneQode name is judged.)
    trace = {"probe_id": 6923, "hops": [
        {"hop": 1, "addresses": ["103.151.64.30"], "min_rtt_ms": 0.229},
        {"hop": 2, "addresses": ["103.151.64.7"], "min_rtt_ms": 70.375},
        {"hop": 3, "addresses": ["202.77.88.26"], "min_rtt_ms": 70.847},
    ]}
    hub = rl.find_router_hub(trace, "GU", _resolver({"103.151.64.7": "gu-gnc-rt1-----Vlan780.au-gssyd-rt1.oneqode.net"}))
    assert hub is not None
    assert (hub.hop, hub.city, hub.verdict) == (2, "Sydney", rl.HUB_OK)
    assert hub.floor_ms is not None and hub.floor_ms < 70.375


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


# reverse_dns itself (unbound, rate cap, failure handling) is tested in test_ptr_lookup.py.
