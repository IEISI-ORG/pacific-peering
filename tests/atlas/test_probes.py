"""Tests for the any-status probe listing's per-probe fields."""

from __future__ import annotations

from pacific_peering.atlas import probes
from pacific_peering.discovery.economies import ECONOMIES_BY_CC


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_probes_keeps_asn_v6_and_only_system_ipv6_tags(monkeypatch):
    # Shape of Atlas's live answer for KI probe 1008228 on 2026-09-24.
    payload = {
        "results": [
            {
                "id": 1008228,
                "status": {"name": "Connected", "since": "2026-09-23T00:00:00Z"},
                "asn_v4": 14593,
                "asn_v6": 14593,
                "tags": [
                    {"slug": "system-ipv6-doesnt-work"},
                    {"slug": "system-ipv4-works"},
                    {"slug": "system-ipv6-capable"},
                    {"slug": "home"},
                ],
            },
            {"id": 64237, "status": {"name": "Connected"}, "asn_v4": 14593, "asn_v6": None, "tags": []},
        ]
    }
    monkeypatch.setattr(probes.requests, "get", lambda url, params, timeout: _FakeResponse(payload))

    result = probes.fetch_probes_for_economy("KI")

    assert result[0]["asn_v6"] == 14593
    assert result[0]["ipv6_tags"] == ["system-ipv6-capable", "system-ipv6-doesnt-work"]
    assert result[1]["asn_v6"] is None
    assert result[1]["ipv6_tags"] == []


# Probes physically in an in-scope economy but registered by Atlas under another
# country are invisible to a country_code query: the OneQode Guam anchor 6923
# (gu-pit-as140627, Atlas country US) was never listed (found 2026-10-03).
def _fake_atlas(by_country, by_id):
    def _get(url, params, timeout):
        if "country_code" in params:
            return _FakeResponse({"results": by_country.get(params["country_code"], [])})
        ids = [int(i) for i in params["id__in"].split(",")]
        return _FakeResponse({"results": [p for p in by_id if p["id"] in ids]})
    return _get


_GU_OWN = {"id": 7385, "status": {"name": "Connected"}, "asn_v4": 152735, "asn_v6": None, "tags": [], "country_code": "GU"}
_ONEQODE = {"id": 6923, "status": {"name": "Connected"}, "asn_v4": 140627, "asn_v6": 140627, "tags": [], "country_code": "US"}


def test_listing_adds_override_probe_to_its_physical_economy(monkeypatch, tmp_path):
    monkeypatch.setattr(probes, "PROBE_ECONOMY_OVERRIDES", {6923: "GU"})
    monkeypatch.setattr(probes.requests, "get", _fake_atlas({"GU": [_GU_OWN]}, [_ONEQODE]))
    gu = ECONOMIES_BY_CC["GU"]

    listing = probes.build_probe_listing(economies=(gu,), output_path=tmp_path / "listing.json")

    assert [p["id"] for p in listing["GU"]] == [7385, 6923]
    assert listing["GU"][1]["atlas_country"] == "US"
    assert "atlas_country" not in listing["GU"][0]


def test_override_probe_is_not_duplicated_once_atlas_files_it_correctly(monkeypatch, tmp_path):
    monkeypatch.setattr(probes, "PROBE_ECONOMY_OVERRIDES", {6923: "GU"})
    fixed = {**_ONEQODE, "country_code": "GU"}
    monkeypatch.setattr(probes.requests, "get", _fake_atlas({"GU": [_GU_OWN, fixed]}, [fixed]))
    gu = ECONOMIES_BY_CC["GU"]

    listing = probes.build_probe_listing(economies=(gu,), output_path=tmp_path / "listing.json")

    assert [p["id"] for p in listing["GU"]] == [7385, 6923]
