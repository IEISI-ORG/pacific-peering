"""Tests for the leasing-marker check (discovery/leasing_check.py)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pacific_peering.discovery import leasing_check as lc

NOW = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)


def _whois(records=(), irr=(), authorities=("apnic",)):
    as_rec = lambda pairs: [{"key": k, "value": v} for k, v in pairs]  # noqa: E731
    return {"records": [as_rec(r) for r in records], "irr_records": [as_rec(r) for r in irr],
            "authorities": list(authorities)}


def _kinds(markers):
    return sorted(m["kind"] for m in markers)


def test_larus_leased_afrinic_block_flags_broker_and_registry():
    # 154.197.42.0/24 under AS58460 Digicel PNG, 2026-10-01.
    whois = _whois(
        records=[[("inetnum", "154.197.42.0/24"), ("netname", "Digicel_PNG_Limited"), ("country", "PG"),
                  ("mnt-by", "CIL1-MNT"), ("mnt-by", "LARUS-SERVICE-MNT")]],
        irr=[[("route", "154.197.42.0/24"), ("mnt-by", "MAINT-LARUS")]],
        authorities=["afrinic"],
    )
    markers = lc.find_markers(whois, "PG")
    assert _kinds(markers) == ["broker", "broker", "foreign_registry"]
    assert {m["detail"].split(" ")[0] for m in markers if m["kind"] == "broker"} == {"Cloud", "Larus"}


def test_ipxo_markers_and_geofeed():
    whois = _whois(records=[[("country", "MH"), ("mnt-by", "IPXO-MNT"), ("geofeed", "https://geofeed.ipxo.com/geofeed.txt")]],
                   authorities=["ripe"])
    markers = lc.find_markers(whois, "MH")
    assert "broker" in _kinds(markers) and "foreign_registry" in _kinds(markers)
    assert {"kind": "geofeed", "detail": "https://geofeed.ipxo.com/geofeed.txt"} in markers


def test_self_registered_abroad_is_flagged():
    whois = _whois(records=[[("netname", "WANTOK-NETWORK-AU"), ("country", "AU")]])
    assert _kinds(lc.find_markers(whois, "VU")) == ["registered_abroad"]


def test_shared_registrations_and_us_space_are_not_flagged():
    gu_pool = _whois(records=[[("country", "GU")]])
    assert lc.find_markers(gu_pool, "MP") == []
    arin_us = _whois(records=[[("Country", "US")]], authorities=["arin"])
    assert lc.find_markers(arin_us, "AS") == []
    assert _kinds(lc.find_markers(arin_us, "PF")) == ["foreign_registry", "registered_abroad"]


def test_upstream_route_objects_alone_are_not_flagged():
    whois = _whois(records=[[("country", "VU")]], irr=[[("mnt-by", "MAINT-EQUINIXPAC"), ("descr", "Speedcast")]])
    assert lc.find_markers(whois, "VU") == []


def test_acknowledged_prefixes_never_escalate():
    results = {"154.197.42.0/24": {"asn": 58460, "cc": "PG", "markers": [{"kind": "broker", "detail": "Larus"}]},
               "198.51.100.0/24": {"asn": 64500, "cc": "PG", "markers": [{"kind": "broker", "detail": "IPXO"}]}}
    assert lc.new_flags([], results) == [(64500, "198.51.100.0/24", "broker")]


def test_flags_escalate_once():
    results = {"198.51.100.0/24": {"asn": 64500, "cc": "PG", "markers": [{"kind": "broker", "detail": "IPXO"}]}}
    history = [{"flags": [[64500, "198.51.100.0/24", "broker"]]}]
    assert lc.new_flags(history, results) == []


def test_schedule_monthly_then_new_asns_then_skip():
    registry = {1: "FJ", 2: "TO"}
    assert lc.plan_run(registry, [], NOW) == ("full", [1, 2])
    recent = [{"mode": "full", "run_at": (NOW - timedelta(days=3)).isoformat(), "asns": [1], "complete": True}]
    assert lc.plan_run(registry, recent, NOW) == ("new", [2])
    recent[0]["asns"] = [1, 2]
    assert lc.plan_run(registry, recent, NOW) == ("skip", [])
    stale = [{**recent[0], "run_at": (NOW - timedelta(days=31)).isoformat()}]
    assert lc.plan_run(registry, stale, NOW)[0] == "full"
