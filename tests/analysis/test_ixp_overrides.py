"""Hand-verified IXP overrides take precedence over stale PeeringDB data.

Fiji-IXP (ix 3085) is the first case: PeeringDB's record dates from 2020
and gives 103.147.194.10 to Digicel AS45355, where the exchange's own
port plan and 2026-10-17 traces put Vodafone AS38442. These tests use the
real `IXP_OVERRIDES` entry, so a typo in that data fails here too.
"""

from __future__ import annotations

import ipaddress
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
        lambda ip: [4638] if ip == "202.137.178.55" else [38442],
    )
    monkeypatch.setattr(traceroute_topology, "resolve_ip_via_netixlan", _no_lookup)
    monkeypatch.setattr(
        traceroute_topology.IpResolutionCache, "load", lambda path: cache
    )
    hops = [
        {"hop": 1, "addresses": ["202.137.178.55"]},
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
