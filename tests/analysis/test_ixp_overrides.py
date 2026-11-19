"""Hand-verified IXP overrides take precedence over stale PeeringDB data.

Fiji-IXP (ix 3085) is the first case: PeeringDB's record dates from 2020
and gives 103.147.194.10 to Digicel AS45355, where the exchange's own
port plan and 2026-10-17 traces put Vodafone AS38442. These tests use the
real `IXP_OVERRIDES` entry, so a typo in that data fails here too.
"""

from __future__ import annotations

import ipaddress
import json
import logging

import pytest

from pacific_peering.analysis import traceroute_topology
from pacific_peering.analysis.ip_resolution_cache import IpResolutionCache
from pacific_peering.analysis.ixp_lan_registry import (
    IxpLanEntry,
    classify_ixp_fabric,
    confirm_ixp_region,
    load_ixp_lan_registry,
    _save_registry,
)
from pacific_peering.discovery.ixp_overrides import IXP_OVERRIDES

FIJI_IXP = 3085

# What PeeringDB gives us today: the /23 only, no IPv6 LAN.
REGISTRY = {
    FIJI_IXP: IxpLanEntry(
        ix_id=FIJI_IXP,
        name="Fiji-IXP",
        city="Suva",
        country="FJ",
        in_fishbowl=True,
        prefixes=("103.147.194.0/23",),
    )
}


def _no_lookup(*args, **kwargs):
    raise AssertionError("an overridden port must not fall through to BGP or PeeringDB")


@pytest.fixture
def cache(tmp_path):
    return IpResolutionCache(path=tmp_path / "cache.json", entries={})


def test_override_port_beats_a_stale_cached_netixlan_answer(cache, monkeypatch):
    # Fails if the override is checked after the cache (or not at all).
    monkeypatch.setattr(traceroute_topology, "resolve_ip_to_asns", _no_lookup)
    monkeypatch.setattr(traceroute_topology, "resolve_ip_via_netixlan", _no_lookup)
    cache.set("103.147.194.10", 45355, "peeringdb_netixlan", None)

    asn, source, ctx = traceroute_topology._resolve_address(
        "103.147.194.10", cache, REGISTRY
    )

    assert (asn, source) == (38442, "ixp_override")
    assert ctx["ix_id"] == FIJI_IXP
    assert cache.get("103.147.194.10")[:2] == (38442, "ixp_override")


def test_route_server_hop_is_not_credited_to_a_member(cache, monkeypatch, caplog):
    # Fails if route servers are treated as member ports (or not overridden).
    monkeypatch.setattr(traceroute_topology, "resolve_ip_to_asns", _no_lookup)
    monkeypatch.setattr(traceroute_topology, "resolve_ip_via_netixlan", _no_lookup)

    with caplog.at_level(logging.WARNING):
        asn, source, ctx = traceroute_topology._resolve_address(
            "103.147.194.1", cache, REGISTRY
        )

    assert (asn, source) == (None, "ixp_route_server")
    assert ctx["ix_id"] == FIJI_IXP
    assert "route server" in caplog.text


def test_ipv6_port_resolves_inside_the_override_lan(cache, monkeypatch):
    # Fails if IPv6 ports or the override /64 are missing, or if the
    # address isn't normalised (PeeringDB-style upper case must match).
    monkeypatch.setattr(traceroute_topology, "resolve_ip_to_asns", _no_lookup)
    monkeypatch.setattr(traceroute_topology, "resolve_ip_via_netixlan", _no_lookup)

    asn, source, ctx = traceroute_topology._resolve_address(
        "2001:DF2:A280:333::30", cache, REGISTRY
    )

    assert (asn, source) == (45349, "ixp_override")
    assert ctx["ix_id"] == FIJI_IXP


def test_override_lan_counts_as_fabric_when_peeringdb_lacks_it():
    # Fails if classify_ixp_fabric ignores override LANs.
    entry = classify_ixp_fabric("2001:df2:a280:333::99", REGISTRY)

    assert entry is not None and entry.ix_id == FIJI_IXP


def test_override_lan_needs_the_exchange_in_the_registry():
    # An override adds prefixes; it never invents an exchange or its
    # in/out-of-fishbowl classification, which stays a human decision.
    assert classify_ixp_fabric("2001:df2:a280:333::99", {}) is None


def test_unlisted_fabric_address_still_uses_the_normal_path(cache, monkeypatch):
    # .21 answers but isn't in the port plan; it must not be guessed.
    monkeypatch.setattr(traceroute_topology, "resolve_ip_to_asns", lambda ip: [])
    monkeypatch.setattr(traceroute_topology, "resolve_ip_via_netixlan", lambda ip: None)

    asn, source, ctx = traceroute_topology._resolve_address(
        "103.147.194.21", cache, REGISTRY
    )

    assert (asn, source) == (None, "ixp_lan_registry")
    assert ctx["ix_id"] == FIJI_IXP


def test_cached_address_picks_up_a_new_override_lan(cache, monkeypatch):
    # Fails if a cache hit returns the context it was first cached with:
    # ::21 cached before the IPv6 LAN was known must still count as fabric.
    monkeypatch.setattr(traceroute_topology, "resolve_ip_to_asns", _no_lookup)
    monkeypatch.setattr(traceroute_topology, "resolve_ip_via_netixlan", _no_lookup)
    cache.set("2001:df2:a280:333::21", None, None, None)

    asn, source, ctx = traceroute_topology._resolve_address(
        "2001:df2:a280:333::21", cache, REGISTRY
    )

    assert asn is None
    assert ctx is not None and ctx["ix_id"] == FIJI_IXP


def test_route_server_hop_is_a_gap_in_the_as_path(cache, monkeypatch):
    # Guard: unlike "private" hops, a route server must break contiguity,
    # since it isn't a forwarding hop of either neighbour.
    monkeypatch.setattr(
        traceroute_topology,
        "resolve_ip_to_asns",
        lambda ip: [4638] if ip == "202.62.126.21" else [38442],
    )
    monkeypatch.setattr(traceroute_topology, "resolve_ip_via_netixlan", _no_lookup)
    monkeypatch.setattr(
        traceroute_topology.IpResolutionCache, "load", lambda path: cache
    )
    hops = [
        {"hop": 1, "addresses": ["202.62.126.21"]},
        {"hop": 2, "addresses": ["103.147.194.1"]},
        {"hop": 3, "addresses": ["203.123.1.1"]},
    ]

    resolved = traceroute_topology.resolve_traceroute_hops(
        hops, ixp_registry_path=_registry_file(cache), persist=False
    )
    sequence = traceroute_topology.extract_as_sequence(resolved)

    assert [a.asn for a in sequence] == [4638, 38442]
    assert sequence[1].contiguous_with_previous is False


def _registry_file(cache):
    path = cache.path.with_name("ixp_lan_registry.json")
    _save_registry(REGISTRY, path)
    return path


def test_saved_registry_never_absorbs_override_lans(tmp_path):
    # Guard: overrides apply at lookup time, so retiring one takes effect
    # at once. Fails if a load/save round trip (as confirm_ixp_region
    # does) ever starts persisting override prefixes.
    path = tmp_path / "ixp_lan_registry.json"
    _save_registry(REGISTRY, path)

    confirm_ixp_region(FIJI_IXP, True, registry_path=path)

    assert load_ixp_lan_registry(path)[FIJI_IXP].prefixes == ("103.147.194.0/23",)


@pytest.mark.parametrize("override", IXP_OVERRIDES.values(), ids=lambda o: o.name)
def test_every_override_port_sits_inside_its_own_lans(override):
    # Catches a mistyped address in the hand-maintained data.
    lans = [ipaddress.ip_network(lan) for lan in override.lans]
    for port in override.ports:
        address = ipaddress.ip_address(port.address)
        assert any(address in lan for lan in lans), port.address


# --- Per-prefix ASN overrides for unannounced infrastructure space ---------

from pacific_peering.discovery.prefix_asn_overrides import PREFIX_ASN_OVERRIDES  # noqa: E402

# Measurement 219066887 (finding #276), SPC probe 60575 -> Vodafone, frozen.
TRACE_219066887 = [
    {"hop": 1, "addresses": ["192.168.3.37"]},
    {"hop": 2, "addresses": ["192.168.8.9"]},
    {"hop": 3, "addresses": ["202.0.156.1"]},
    {"hop": 4, "addresses": ["202.0.158.254"]},
    {"hop": 5, "addresses": ["202.62.126.21"]},
    {"hop": 6, "addresses": []},
    {"hop": 7, "addresses": []},
    {"hop": 8, "addresses": ["202.137.178.55"]},
    {"hop": 9, "addresses": ["202.137.178.54"]},
    {"hop": 10, "addresses": ["103.147.194.10"]},
    {"hop": 11, "addresses": ["183.81.136.189"]},
    {"hop": 12, "addresses": ["183.81.128.114"]},
    {"hop": 13, "addresses": []},
    {"hop": 14, "addresses": ["103.244.230.1"]},
]
BGP_219066887 = {
    "202.0.156.1": [141695],
    "202.0.158.254": [141695],
    "202.62.126.21": [4638],
    "183.81.136.189": [38442],
    "183.81.128.114": [38442],
    "103.244.230.1": [38442],
}


def test_unannounced_tfl_core_resolves_past_a_cached_gap(cache, monkeypatch):
    # Fails if the prefix override is missing or checked after the cache,
    # which holds 202.137.178.55 as unresolved.
    monkeypatch.setattr(traceroute_topology, "resolve_ip_to_asns", _no_lookup)
    monkeypatch.setattr(traceroute_topology, "resolve_ip_via_netixlan", _no_lookup)
    cache.set("202.137.178.55", None, None, None)

    asn, source, ctx = traceroute_topology._resolve_address(
        "202.137.178.55", cache, REGISTRY
    )

    assert (asn, source, ctx) == (45349, "prefix_override", None)


def test_neighbouring_announced_space_still_uses_bgp(cache, monkeypatch):
    # 202.137.179.0/24 is announced by AS45349 itself; the override must
    # not reach outside its own /24.
    monkeypatch.setattr(traceroute_topology, "resolve_ip_to_asns", lambda ip: [45349])

    asn, source, _ctx = traceroute_topology._resolve_address(
        "202.137.179.1", cache, REGISTRY
    )

    assert (asn, source) == (45349, "bgp")


def test_finding_276_trace_reaches_vodafone_contiguously_from_tfl(
    cache, monkeypatch, tmp_path
):
    # Regression for #276: TFL core -> Vodafone's Fiji-IXP port -> Vodafone.
    # Fails if either override goes (Digicel reappears, or the gap returns).
    monkeypatch.setattr(
        traceroute_topology, "resolve_ip_to_asns", lambda ip: BGP_219066887.get(ip, [])
    )
    monkeypatch.setattr(traceroute_topology, "resolve_ip_via_netixlan", _no_lookup)
    monkeypatch.setattr(
        traceroute_topology.IpResolutionCache, "load", lambda path: cache
    )

    resolved = traceroute_topology.resolve_traceroute_hops(
        TRACE_219066887, ixp_registry_path=_registry_file(cache), persist=False
    )
    sequence = traceroute_topology.extract_as_sequence(resolved)

    assert [a.asn for a in sequence] == [141695, 4638, 45349, 38442]
    assert sequence[-1].contiguous_with_previous is True


def test_unannounced_superloop_la_router_resolves_to_as38195(cache, monkeypatch):
    # 240073513 (NC -> FM, 2026-11-18): hop 7, Superloop's Los Angeles border
    # router, sits in 103.200.13.0/24, which no RIS peer sees. Fails if the
    # override is missing, so the router-hub guard gets no owner for it.
    monkeypatch.setattr(traceroute_topology, "resolve_ip_to_asns", _no_lookup)
    monkeypatch.setattr(traceroute_topology, "resolve_ip_via_netixlan", _no_lookup)
    cache.set("103.200.13.168", None, None, None)

    asn, source, ctx = traceroute_topology._resolve_address(
        "103.200.13.168", cache, REGISTRY
    )

    assert (asn, source, ctx) == (38195, "prefix_override", None)


def test_superloop_override_stays_inside_its_own_24(cache, monkeypatch):
    # 103.200.14.0/24 is announced by AS38195; BGP still answers for it.
    monkeypatch.setattr(traceroute_topology, "resolve_ip_to_asns", lambda ip: [38195])

    asn, source, _ctx = traceroute_topology._resolve_address(
        "103.200.14.1", cache, REGISTRY
    )

    assert (asn, source) == (38195, "bgp")


@pytest.mark.parametrize("override", PREFIX_ASN_OVERRIDES, ids=lambda o: o.prefix)
def test_prefix_overrides_are_valid_networks(override):
    # Catches a mistyped prefix (host bits set, bad syntax).
    ipaddress.ip_network(override.prefix)


# --- Owner, 2026-11-19 (F1, option 2): an override never vouches for an adjacency by itself ------
# With 103.200.13.0/24 -> AS38195, the unannounced Superloop LA routers stop being a gap, so a
# trace AS38195 -> [103.200.13.x] -> AS3605 reads as a contiguous AS38195 -> AS3605 step. RIS has
# never seen that adjacency (task_plan.md, 211259107, September). A step that is contiguous only
# because of an override counts as contiguous only when RIS agrees.

from pacific_peering.analysis.traceroute_topology import (  # noqa: E402
    HopResolution,
    check_neighbor_agreement,
    extract_as_sequence,
)


def _hop(n, asn, source, address=None):
    return HopResolution(hop=n, addresses=(address or f"192.0.2.{n}",), asns=(asn,), resolution_source=source)


# Real addresses: Superloop's LA routers (guarded override) and TFL's core (not guarded).
_SUPERLOOP_LA = ("103.200.13.67", "103.200.13.168")
_TFL_CORE = "202.137.178.55"


def test_only_the_superloop_override_needs_ris_for_adjacency():
    # TFL's core override (owner, 2026-10-18, with the #276 relabel) makes Fiji-IXP chains
    # contiguous for candidate peerings #276/#279/#296/#313, which RIS by definition hasn't seen.
    flags = {o.prefix: o.needs_ris_for_adjacency for o in PREFIX_ASN_OVERRIDES}
    assert flags == {"202.137.178.0/24": False, "103.200.13.0/24": True}


def test_a_step_bridged_by_guarded_override_hops_is_marked():
    sequence = extract_as_sequence([
        _hop(4, 38195, "bgp"), _hop(6, 38195, "prefix_override", _SUPERLOOP_LA[0]),
        _hop(7, 38195, "prefix_override", _SUPERLOOP_LA[1]), _hop(8, 3605, "peeringdb_netixlan"),
    ])
    assert [(e.asn, e.contiguous_with_previous, e.contiguous_via_override) for e in sequence] == [
        (38195, True, False), (3605, True, True)]


def test_a_step_into_a_guarded_override_entry_is_marked():
    sequence = extract_as_sequence([
        _hop(1, 18200, "bgp"), _hop(2, 38195, "prefix_override", _SUPERLOOP_LA[1]), _hop(3, 3605, "bgp")])
    assert [e.contiguous_via_override for e in sequence] == [False, True, True]


def test_the_tfl_core_override_still_vouches_for_its_steps():
    sequence = extract_as_sequence([
        _hop(1, 45349, "ixp_override"), _hop(2, 45349, "prefix_override", _TFL_CORE), _hop(3, 38442, "bgp")])
    assert [(e.contiguous_with_previous, e.contiguous_via_override) for e in sequence] == [(True, False)] * 2


def test_a_step_with_no_override_hop_is_not_marked():
    sequence = extract_as_sequence([_hop(4, 38195, "bgp"), _hop(5, 38195, "bgp"), _hop(8, 3605, "bgp")])
    assert [e.contiguous_via_override for e in sequence] == [False, False]


def _fishbowl(tmp_path, neighbours_of_3605):
    path = tmp_path / "fishbowl.json"
    path.write_text(json.dumps({"3605": {"neighbors": {str(a): 10 for a in neighbours_of_3605}}}))
    return path


_BRIDGED = [_hop(4, 38195, "bgp"), _hop(7, 38195, "prefix_override", _SUPERLOOP_LA[1]),
            _hop(8, 3605, "peeringdb_netixlan")]


def test_an_override_bridged_step_ris_does_not_know_is_not_contiguous(tmp_path):
    result = check_neighbor_agreement(extract_as_sequence(_BRIDGED), 3605, _fishbowl(tmp_path, [9246]))
    assert result["contiguous"] is False
    assert result["override_step_unconfirmed"] is True
    assert "prefix-override hops" in result["note"]


def test_an_override_bridged_step_ris_agrees_with_stays_contiguous(tmp_path):
    result = check_neighbor_agreement(extract_as_sequence(_BRIDGED), 3605, _fishbowl(tmp_path, [38195]))
    assert result["contiguous"] is True
    assert result.get("override_step_unconfirmed", False) is False
