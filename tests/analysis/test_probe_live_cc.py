"""Tests for `_probe_live_cc_by_asn`: which economies a source ASN's probes are live in."""

from __future__ import annotations

import json

from pacific_peering.analysis.corridor_backlog import _probe_live_cc_by_asn


def _listing(tmp_path, probes_by_cc):
    path = tmp_path / "probe_listing.json"
    path.write_text(json.dumps(probes_by_cc))
    return path


def test_probe_with_a_guessed_country_is_not_a_source(tmp_path):
    # 2026-10-22: AS45345's 1008625 ("Nautile Studio Felix") carries
    # system-auto-geoip-country and sits at New Caledonia's centroid; its
    # sibling 63050 was placed by its host. Only 63050 makes AS45345 an NC source.
    path = _listing(
        tmp_path,
        {
            "NC": [
                {"id": 1008625, "status": "Connected", "asn_v4": 45345, "auto_geoip": True},
                {"id": 63050, "status": "Connected", "asn_v4": 45345, "auto_geoip": False},
            ],
            "GU": [{"id": 1012513, "status": "Connected", "asn_v4": 152735, "auto_geoip": True}],
        },
    )

    result = _probe_live_cc_by_asn({45345: [1008625, 63050], 152735: [1012513]}, listing_path=path)

    assert result == {45345: {"NC"}}


def test_listing_built_before_the_flag_existed_still_gives_sources(tmp_path):
    path = _listing(tmp_path, {"NC": [{"id": 63050, "status": "Connected", "asn_v4": 45345}]})

    assert _probe_live_cc_by_asn({45345: [63050]}, listing_path=path) == {45345: {"NC"}}
