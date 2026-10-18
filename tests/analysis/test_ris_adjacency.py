"""RIS agreement must see an adjacency wherever it sits in an AS path.

`neighbors` in fishbowl.json only records the AS just before each path's
*origin*. FINTEL AS9241 -> TFL AS45349 appears 42 times in local RIS data,
always on paths to AS4638's prefixes where AS45349 is transit, so it never
reached `neighbors` and finding #275 read "RIS disagrees" (2026-10-18).
"""

from __future__ import annotations

import json

from pacific_peering.analysis import fishbowl as fishbowl_module
from pacific_peering.analysis.peering import infer_adjacencies
from pacific_peering.analysis.traceroute_topology import _bidirectional_ris_check
from pacific_peering.ris.ripestat import BgpStateRecord


def _record(*path: int) -> BgpStateRecord:
    return BgpStateRecord(target_prefix="202.62.118.0/24", source_id="rrc00", path=path)


# AS4638's prefixes as seen from a collector: AS45349 is transit here.
PATHS_TO_4638 = {
    4638: [_record(3356, 9241, 45349, 4638), _record(174, 45349, 45349, 4638)]
}


def test_transit_adjacency_is_recorded_for_the_in_scope_asn():
    # Fails if only the origin's immediate upstream is counted.
    adjacent = infer_adjacencies(PATHS_TO_4638, in_scope={4638, 45349, 9241})

    assert adjacent[45349][9241] == 1
    assert adjacent[9241][45349] == 1
    assert adjacent[45349][4638] == 2  # prepending collapsed, one per record


def test_out_of_scope_asns_get_no_entry_of_their_own():
    # Keeps fishbowl.json to in-scope ASNs, as `neighbors` is.
    adjacent = infer_adjacencies(PATHS_TO_4638, in_scope={4638, 45349})

    assert 3356 not in adjacent and 174 not in adjacent
    assert adjacent[45349][174] == 1


def test_ris_check_falls_back_to_any_position_adjacency():
    # Fails if the check ignores `adjacent` (the #275 miss).
    fishbowl = {
        "9241": {"neighbors": {"174": 830}},
        "45349": {"neighbors": {"4648": 584}, "adjacent": {"9241": 42}},
    }

    assert _bidirectional_ris_check(fishbowl, 45349, 9241) == (True, 42)


def test_origin_upstream_neighbors_still_take_precedence():
    # Guard: an existing `neighbors` hit keeps its count, as before.
    fishbowl = {"9241": {"neighbors": {"45349": 7}, "adjacent": {"45349": 42}}}

    assert _bidirectional_ris_check(fishbowl, 45349, 9241) == (True, 7)


def test_fishbowl_built_before_adjacent_existed_still_works():
    # Guard: a fishbowl.json without the new field behaves as before.
    fishbowl = {
        "9241": {"neighbors": {"174": 830}},
        "45349": {"neighbors": {"4648": 584}},
    }

    assert _bidirectional_ris_check(fishbowl, 45349, 9241) == (False, None)


def test_build_fishbowl_writes_adjacent_and_leaves_neighbors_alone(
    tmp_path, monkeypatch
):
    # Fails if build_fishbowl doesn't persist `adjacent`, or if `neighbors`
    # (read by the backlog's new-RIS-relationship diff and the offshore
    # screen) changes meaning.
    registry = tmp_path / "asn_registry.json"
    registry.write_text(
        json.dumps(
            {
                "FJ": {
                    "name": "Fiji",
                    "subregion": "Melanesia",
                    "asns": [4638, 45349, 9241],
                }
            }
        )
    )
    monkeypatch.setattr(
        fishbowl_module,
        "fetch_aspaths_for_registry",
        lambda registry_path, use_cache: PATHS_TO_4638,
    )
    monkeypatch.setattr(
        fishbowl_module,
        "fetch_ipv6_prefix_counts_for_registry",
        lambda registry_path: {},
    )
    monkeypatch.setattr(
        fishbowl_module,
        "_fetch_peeringdb_data",
        lambda *args: {
            "on_peeringdb": [],
            "ixp_memberships": {},
            "facility_presence": {},
        },
    )

    fishbowl_module.build_fishbowl(
        registry_path=registry, summary_path=tmp_path / "fishbowl.json"
    )
    result = json.loads(
        (tmp_path / "fishbowl.json").read_text()
    )  # what every consumer reads

    assert result["45349"]["adjacent"] == {"4638": 2, "9241": 1, "174": 1}
    assert result["4638"]["neighbors"] == {"45349": 2}
    assert result["45349"]["neighbors"] == {}


def test_build_fishbowl_refetches_ris_paths_by_default(tmp_path, monkeypatch):
    # Fails if the weekly refresh (pipeline -> build_fishbowl()) reads the
    # RIS path cache instead of refetching: fishbowl.json stayed frozen at
    # 2026-09-14 paths until 2026-10-18.
    registry = tmp_path / "asn_registry.json"
    registry.write_text(
        json.dumps({"FJ": {"name": "Fiji", "subregion": "Melanesia", "asns": [4638]}})
    )
    calls = []

    def _fetch(registry_path, use_cache):
        calls.append(use_cache)
        return PATHS_TO_4638

    monkeypatch.setattr(fishbowl_module, "fetch_aspaths_for_registry", _fetch)
    monkeypatch.setattr(
        fishbowl_module, "fetch_ipv6_prefix_counts_for_registry", lambda registry_path: {}
    )
    monkeypatch.setattr(
        fishbowl_module,
        "_fetch_peeringdb_data",
        lambda *args: {"on_peeringdb": [], "ixp_memberships": {}, "facility_presence": {}},
    )

    fishbowl_module.build_fishbowl(registry_path=registry, summary_path=tmp_path / "f.json")
    fishbowl_module.build_fishbowl(
        registry_path=registry, summary_path=tmp_path / "f.json", refresh_ris=False
    )

    assert calls == [False, True]
