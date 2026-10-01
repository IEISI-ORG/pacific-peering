"""Tests for the offshore check's second chances (atlas/offshore_alternates.py)."""

from __future__ import annotations

import json

from pacific_peering.atlas import offshore_alternates as alt


def test_parse_nmap_grepable_keeps_rdns():
    text = ("# Nmap 7.94 scan\nHost: 202.4.251.133 ()\tStatus: Up\n"
            "Host: 103.36.147.1 (103-36-147-1.clients.wantok.vu)\tStatus: Up\nHost: 10.0.0.9 ()\tStatus: Down\n")
    assert alt.parse_nmap_grepable(text) == {"202.4.251.133": "", "103.36.147.1": "103-36-147-1.clients.wantok.vu"}


def test_sweep_targets_cap_large_prefixes_and_skip_v6():
    assert alt.sweep_targets(["168.123.0.0/16", "202.4.251.0/24", "2401:4d20::/32"]) == ["168.123.0.0/22", "202.4.251.0/24"]


def test_cached_responders_finds_hops_inside_prefix(tmp_path):
    (tmp_path / "1.json").write_text(json.dumps([
        {"hops": [{"addresses": ["45.127.172.89"]}, {"addresses": ["202.4.251.170"]}]},
        {"hops": [{"addresses": ["202.4.251.170"]}, {"addresses": ["202.4.251.9"]}]},
    ]))
    assert alt.cached_responders(["202.4.251.0/24"], tmp_path) == ["202.4.251.170", "202.4.251.9"]


def test_alternates_prefer_cache_and_skip_sweep_when_enough(tmp_path, monkeypatch):
    monkeypatch.setattr(alt, "cached_responders", lambda prefixes: ["192.0.2.5", "192.0.2.6", "192.0.2.7", "192.0.2.8"])
    monkeypatch.setattr(alt, "nmap_sweep", lambda prefixes: (_ for _ in ()).throw(AssertionError("no sweep")))
    picked, swept = alt.alternate_addresses(["192.0.2.0/24"], exclude={"192.0.2.5"})
    assert picked == ["192.0.2.6", "192.0.2.7", "192.0.2.8"] and swept == {}


def test_alternates_fall_back_to_sweep(monkeypatch):
    monkeypatch.setattr(alt, "cached_responders", lambda prefixes: [])
    monkeypatch.setattr(alt, "nmap_sweep", lambda prefixes: {"192.0.2.1": "", "192.0.2.9": "h.example", "192.0.2.4": ""})
    picked, swept = alt.alternate_addresses(["192.0.2.0/24"], exclude={"192.0.2.1"})
    assert picked == ["192.0.2.4", "192.0.2.9"] and swept["192.0.2.9"] == "h.example"


CLASSES = {9280: ("Servers Australia", "Unknown"), 174: ("Cogent", "T1"), 7575: ("AARNet", "Carrier"),
           13335: ("Cloudflare", "Content")}
IN_SCOPE = {131995, 18200, 45345}


def test_screen_flags_sole_foreign_hosting_upstream():
    fishbowl = {"131995": {"neighbors": {"9280": 350}}}
    lead = alt.upstream_screen(131995, fishbowl, IN_SCOPE, CLASSES)
    assert lead["upstreams"] == [{"asn": 9280, "name": "Servers Australia", "class": "Unknown", "observations": 350}]


def test_screen_passes_tier1_research_and_in_region_upstreams():
    assert alt.upstream_screen(1, {"1": {"neighbors": {"174": 800, "13335": 5}}}, IN_SCOPE, CLASSES) is None
    assert alt.upstream_screen(2, {"2": {"neighbors": {"7575": 336}}}, IN_SCOPE, CLASSES) is None
    assert alt.upstream_screen(45345, {"45345": {"neighbors": {"18200": 1668}}}, IN_SCOPE, CLASSES) is None
    assert alt.upstream_screen(3, {}, IN_SCOPE, CLASSES) is None
