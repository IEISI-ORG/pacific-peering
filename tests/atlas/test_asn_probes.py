"""Tests for the ASN probe registry build (atlas/asn_probes.py)."""

from __future__ import annotations

import json

from pacific_peering.atlas import asn_probes


class _Resp:
    def __init__(self, results):
        self._results = results

    def raise_for_status(self):
        pass

    def json(self):
        return {"results": self._results}


def test_probe_asn_override_moves_62046_to_fsm_telecom(monkeypatch, tmp_path):
    economy = type("E", (), {"cc": "FM"})()
    results = [{"id": 7448, "asn_v4": 139759}, {"id": 62046, "asn_v4": 14593}]
    monkeypatch.setattr(asn_probes.requests, "get", lambda url, params, timeout: _Resp(results))

    registry = asn_probes.build_asn_probe_registry(economies=(economy,), output_path=tmp_path / "r.json")

    assert registry == {139759: [7448, 62046]}
    assert json.loads((tmp_path / "r.json").read_text()) == {"139759": [7448, 62046]}
