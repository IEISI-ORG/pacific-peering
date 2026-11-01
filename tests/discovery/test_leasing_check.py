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


def test_latest_flagged_summarises_last_complete_full_run():
    results = {
        "154.197.42.0/24": {"asn": 58460, "cc": "PG", "markers": [{"kind": "broker", "detail": "Larus (mnt-by: MAINT-LARUS)"}]},
        "198.51.100.0/24": {"asn": 64500, "cc": "VU", "markers": [{"kind": "registered_abroad", "detail": "AU"},
                                                                  {"kind": "geofeed", "detail": "https://x/g.csv"}]},
        "203.0.113.0/24": {"asn": 64501, "cc": "FJ", "markers": []},
    }
    history = [
        {"mode": "full", "complete": True, "run_at": "2026-09-01T00:00:00+00:00", "results": {}},
        {"mode": "full", "complete": False, "run_at": "2026-10-02T00:00:00+00:00", "results": {}},
        {"mode": "full", "complete": True, "run_at": "2026-10-01T00:00:00+00:00", "results": results},
    ]
    summary = lc.latest_flagged(history)
    assert summary["run_at"].startswith("2026-10-01") and summary["prefixes_checked"] == 3
    assert summary["geofeed_prefixes"] == 1
    assert [(e["asn"], e["verdict"] is not None) for e in summary["entries"]] == [(58460, True), (64500, False)]
    assert lc.latest_flagged([]) is None


# --- 2026-11-02: a prefix with no delegation record --------------------------
# 103.16.15.0/24 (AS9249 Telecom Vanuatu): APNIC reclaimed SPIM's assignment on
# 2026-04-26, so RIPEstat returns only APNIC's own 103.0.0.0/8 block -- whose
# country AU used to raise a misleading `registered_abroad`.
_APNIC_PARENT_BLOCK = (
    ("inetnum", "103.0.0.0/8"), ("netname", "APNIC-AP"),
    ("descr", "Asia Pacific Network Information Centre"), ("country", "AU"),
    ("org", "ORG-APNI3-AP"), ("status", "ALLOCATED PORTABLE"), ("mnt-by", "APNIC-HM"), ("source", "APNIC"),
)


def test_rir_parent_block_only_is_no_delegation_not_registered_abroad():
    markers = lc.find_markers(_whois(records=[_APNIC_PARENT_BLOCK]), "VU")
    assert _kinds(markers) == ["no_delegation"]
    assert "103.0.0.0/8" in markers[0]["detail"]


def test_a_member_assignment_maintained_by_apnic_hm_is_not_no_delegation():
    # WanTok's 103.36.146.0/24: APNIC-HM maintains member records too.
    whois = _whois(records=[(("inetnum", "103.36.146.0 - 103.36.146.255"), ("netname", "WANTOK-NETWORK-AU"),
                             ("country", "AU"), ("mnt-by", "APNIC-HM"), ("source", "APNIC"))])
    assert _kinds(lc.find_markers(whois, "TO")) == ["registered_abroad"]


# Trimmed from rdap.apnic.net/history/ip/103.16.15.0/24 (2026-11-02).
_WHOWAS = {"records": [
    {"applicableFrom": "2011-12-06T00:00:00Z", "applicableUntil": "2018-02-06T00:00:00Z",
     "content": {"startAddress": "103.0.0.0", "endAddress": "103.255.255.255", "name": "APNIC-AP", "country": "AU"}},
    {"applicableFrom": "2025-11-18T00:00:00Z", "applicableUntil": "2026-04-26T05:12:00Z",
     "content": {"startAddress": "103.16.15.0", "endAddress": "103.16.15.255", "name": "SPIM-AP", "country": "VU"}},
    {"applicableFrom": "2013-01-30T02:28:44Z", "applicableUntil": "2014-09-06T03:56:53Z",
     "content": {"startAddress": "103.16.15.0", "endAddress": "103.16.15.255", "name": "SPIM-AP", "country": "VU"}},
    {"applicableFrom": "2026-04-26T05:12:00Z", "applicableUntil": None,
     "content": {"startAddress": "103.16.15.0", "endAddress": "103.16.15.255"}},
]}


def test_whowas_names_the_last_holder_of_the_exact_prefix():
    assert lc.last_holder(_WHOWAS, "103.16.15.0/24") == {"name": "SPIM-AP", "country": "VU", "until": "2026-04-26"}


def test_whowas_with_no_record_for_the_prefix_gives_none():
    assert lc.last_holder({"records": _WHOWAS["records"][:1]}, "103.16.15.0/24") is None


def test_scan_adds_the_last_holder_to_a_no_delegation_marker(monkeypatch):
    monkeypatch.setattr(lc, "fetch_whois", lambda prefix: _whois(records=[_APNIC_PARENT_BLOCK]))
    monkeypatch.setattr(lc, "fetch_whowas", lambda prefix: _WHOWAS)
    (marker,) = lc._scan([(9249, "VU", "103.16.15.0/24")])["103.16.15.0/24"]["markers"]
    assert marker["kind"] == "no_delegation"
    assert "SPIM-AP (VU) until 2026-04-26" in marker["detail"]
