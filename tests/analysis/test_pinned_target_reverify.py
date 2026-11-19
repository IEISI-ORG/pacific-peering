"""Nightly reverification of an AS23657 finding must trace the pinned address.

`run_batch` -> `_pop_reverify_candidate` -> `_candidate_from_finding` leaves
`target_ip` unset for an in-registry target, so `_classify_corridor` asks
`list_target_ips` and fires its first entry. The pin in
`atlas.targets.PINNED_TARGET_IPS` must therefore come first there, not only
in `pick_target_ip`. Before the pin, the RIS cache order moved #66's retests
from 202.4.47.1 (Sydney, via Vodafone Samoa) to 38.134.236.1 (Portland)
between 10-18 and 11-05 (owner, 2026-11-19).
"""

from __future__ import annotations

import json

from pacific_peering.analysis import auto_classify
from pacific_peering.analysis.corridor_backlog import CorridorCandidate
from pacific_peering.atlas import targets


def test_reverification_fires_the_pinned_address_first(monkeypatch, tmp_path):
    cache = tmp_path / "ris"
    cache.mkdir()
    # The 10-18 shape, where the sorted pick was 202.4.47.1.
    (cache / "23657.json").write_text(json.dumps(
        [{"target_prefix": p} for p in ["202.4.47.0/24", "38.134.236.0/22", "67.218.48.0/20"]]
    ))
    fired: list[str] = []

    def _fire(candidate, ip):
        fired.append(ip)
        return 900000066

    monkeypatch.setattr(auto_classify, "_load_asn_to_cc", lambda path=None: {})
    monkeypatch.setattr(auto_classify, "load_ixp_lan_registry", lambda path: {})
    monkeypatch.setattr(auto_classify, "list_target_ips", lambda asn: targets.list_target_ips(asn, cache))
    monkeypatch.setattr(auto_classify, "_fire_measurement", _fire)
    monkeypatch.setattr(
        auto_classify, "analyze_measurement",
        lambda mid, target_asn: {"measurement_id": mid, "target_asn": target_asn, "probes": []},
    )
    monkeypatch.setattr(auto_classify, "DEFAULT_ATLAS_PARSED_DIR", tmp_path)
    (tmp_path / "900000066.json").write_text("[]")
    monkeypatch.setattr(auto_classify, "fetch_measurement_status", lambda mid: "Stopped")
    monkeypatch.setattr(auto_classify, "mark_corridor_tested", lambda *a: None)
    monkeypatch.setattr(auto_classify, "_write_escalations", lambda escalations: None)
    # As `_candidate_from_finding` builds it for #66: in-registry target, no target_ip.
    candidate = CorridorCandidate(
        45345, "NC", "New Caledonia", 23657, "AS", "American Samoa", "test fixture",
        reverify_finding_id=66, target_ip=None,
    )

    auto_classify.classify_corridor(candidate, regenerate=False)

    assert fired == ["38.134.236.1"]
