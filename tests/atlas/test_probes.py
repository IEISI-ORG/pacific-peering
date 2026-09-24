"""Tests for the any-status probe listing's per-probe fields."""

from __future__ import annotations

from pacific_peering.atlas import probes


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
