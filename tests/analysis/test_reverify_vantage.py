"""Reverification re-fires from where the original probes actually are.

Caught 2026-09-29: 7 legacy findings labelled FJ were fired from probe 11691
(USP Tonga Campus, live cc TO); re-firing `country=FJ` hit the Zscaler-bound
SPC probe 60575 and escalated every time. See `auto_classify._original_vantage`.
"""

from __future__ import annotations

import json

from pacific_peering.analysis.auto_classify import _original_vantage

LISTING = {
    "FJ": [{"id": 60575, "asn_v4": 141695, "status": "Connected"}],
    "TO": [{"id": 11691, "asn_v4": 24390, "status": "Connected"}],
    "GU": [{"id": 60689, "asn_v4": 7131, "status": "Connected"}, {"id": 62689, "asn_v4": 7131, "status": "Connected"}],
    "MP": [{"id": 65653, "asn_v4": 7131, "status": "Connected"}],
}


def _parsed(tmp_path, measurement_id, probe_ids):
    (tmp_path / f"{measurement_id}.json").write_text(json.dumps([{"probe_id": p, "hops": []} for p in probe_ids]))


def test_mislabelled_vantage_moves_to_probes_live_economy(tmp_path):
    _parsed(tmp_path, 1, [11691])
    assert _original_vantage(1, "FJ", tmp_path, LISTING) == ("TO", 24390)


def test_stored_economy_kept_when_any_original_probe_is_still_there(tmp_path):
    _parsed(tmp_path, 2, [60689, 62689, 65653])
    assert _original_vantage(2, "MP", tmp_path, LISTING) == ("MP", None)


def test_all_probes_elsewhere_moves_even_when_they_share_an_asn(tmp_path):
    _parsed(tmp_path, 3, [60689, 62689])
    assert _original_vantage(3, "MP", tmp_path, LISTING) == ("GU", 7131)


def test_unplaceable_or_missing_measurement_keeps_stored(tmp_path):
    _parsed(tmp_path, 4, [99999])
    assert _original_vantage(4, "FJ", tmp_path, LISTING) == ("FJ", None)
    assert _original_vantage(5, "FJ", tmp_path, LISTING) == ("FJ", None)


def test_probes_split_across_other_economies_keeps_stored(tmp_path):
    _parsed(tmp_path, 6, [11691, 60689])
    assert _original_vantage(6, "FJ", tmp_path, LISTING) == ("FJ", None)


def test_corrected_reverification_attaches_to_the_original_detour(monkeypatch):
    """Review 2026-09-29: find_existing_detour keys on source economy, so a
    TO-sourced re-test of FJ-labelled #31 would file a new finding and leave
    #31 stale forever unless the original finding id is carried through."""
    from types import SimpleNamespace

    from pacific_peering.analysis import auto_classify
    from pacific_peering.analysis.corridor_backlog import CorridorCandidate

    detour = SimpleNamespace(id=31, kind=auto_classify._store.KIND_CONFIRMED_DETOUR, target_asn=9751)
    monkeypatch.setattr(auto_classify._store, "all_findings", lambda conn: [detour])
    cand = CorridorCandidate(24390, "TO", "Tonga", 9751, "AS", "x", "test", reverify_finding_id=31)
    assert auto_classify._reverified_detour(None, cand) is detour
    other_target = CorridorCandidate(24390, "TO", "Tonga", 1, "AS", "x", "test", reverify_finding_id=31)
    assert auto_classify._reverified_detour(None, other_target) is None
    fresh = CorridorCandidate(24390, "TO", "Tonga", 9751, "AS", "x", "test")
    assert auto_classify._reverified_detour(None, fresh) is None
