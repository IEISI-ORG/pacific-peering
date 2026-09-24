"""Tests for the probe-placement appendix (reports/probe_placement.py)."""

from __future__ import annotations

import json

from pacific_peering.analysis.auto_classify import KNOWN_PROXY_ASNS
from pacific_peering.analysis.corridor_backlog import EXTERNAL_NON_CANDIDATE_ASNS
from pacific_peering.reports import probe_placement as pp

REGISTRY = {"FJ": {"name": "Fiji"}, "TO": {"name": "Tonga"}, "GU": {"name": "Guam"},
            "MP": {"name": "Northern Mariana Islands"}, "KI": {"name": "Kiribati"}, "NC": {"name": "New Caledonia"}}


def test_every_excluded_or_proxy_asn_has_a_stated_reason():
    missing = (set(EXTERNAL_NON_CANDIDATE_ASNS) | set(KNOWN_PROXY_ASNS)) - set(pp.PLACEMENT_REASONS)
    assert not missing, f"add a PLACEMENT_REASONS entry for {sorted(missing)}"


def _write(tmp_path, listing, quarantine):
    (tmp_path / "listing.json").write_text(json.dumps(listing))
    (tmp_path / "q.json").write_text(json.dumps(quarantine))
    return tmp_path / "listing.json", tmp_path / "q.json"


def test_rows_from_exclusions_quarantine_and_advisories(tmp_path):
    listing = {
        "KI": [{"id": 1008228, "status": "Connected", "asn_v4": 14593},
               {"id": 3630, "status": "Abandoned", "asn_v4": 14593}],  # long-dead: not listed
        "GU": [{"id": 60689, "status": "Connected", "asn_v4": 7131}],
        "TO": [{"id": 11691, "status": "Connected", "asn_v4": 24390}],
        "NC": [{"id": 7018, "status": "Connected", "asn_v4": 45345}],  # fine: not listed
    }
    quarantine = {
        "60689": {"mismatch": True, "registry_cc": "MP", "live_country_code": "GU"},
        "11691": {"mismatch": True, "registry_cc": "FJ", "live_country_code": "TO"},
    }
    rows = pp.load_misplaced_probes(REGISTRY, *_write(tmp_path, listing, quarantine))

    assert [(r.cc, r.probe_id) for r in rows] == [("GU", 60689), ("KI", 1008228), ("TO", 11691)]
    by_id = {r.probe_id: r.reason for r in rows}
    assert "Starlink" in by_id[1008228]
    assert "registered Northern Mariana Islands but probe physically in Guam" in by_id[60689]
    assert "physically in Tonga" in by_id[11691] and "AARNet" in by_id[11691]


def test_missing_listing_gives_no_rows(tmp_path):
    assert pp.load_misplaced_probes(REGISTRY, tmp_path / "none.json", tmp_path / "none2.json") == ()
