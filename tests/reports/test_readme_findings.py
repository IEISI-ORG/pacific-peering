"""Tests for the weekly README findings-summary refresh (reports/readme_findings.py)."""

from __future__ import annotations

import sqlite3

import pytest

from pacific_peering.analysis import store
from pacific_peering.discovery import quarantined_asns
from pacific_peering.reports import readme_findings as rf

VAKANET = 152093


@pytest.fixture(autouse=True)
def _pinned_quarantine(monkeypatch):
    """Pin the quarantine so these tests don't follow the live list."""
    monkeypatch.setattr(quarantined_asns, "QUARANTINED_ASN_SET", frozenset({VAKANET}))
    monkeypatch.setattr(quarantined_asns, "HELD_FINDING_KEYS", frozenset())

REGISTRY = {
    "94": {"name": "Equinix Sydney", "in_fishbowl": False},
    "780": {"name": "MegaIX Sydney", "in_fishbowl": False},
    "3085": {"name": "FJIX", "in_fishbowl": True},
    "9999": {"name": "New IX", "in_fishbowl": None},
}


def _detour(conn, *, source_cc="VU", source_asn=9249, target_cc="FJ", target_asn=4638,
            hub="Sydney", ix="Equinix Sydney", measurement_id=1):
    fid = store.create_finding(
        conn, kind=store.KIND_CONFIRMED_DETOUR, source_cc=source_cc, source_asn=source_asn,
        target_cc=target_cc, target_asn=target_asn, detour_hub=hub, detour_ix_name=ix,
    )
    store.add_corroboration(conn, finding_id=fid, measurement_id=measurement_id, vantage_point_cc=source_cc)
    return fid


def _db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(store._SCHEMA)
    _detour(conn, target_asn=4638, measurement_id=1)
    _detour(conn, target_asn=4639, measurement_id=2)
    _detour(conn, target_asn=4640, hub="Los Angeles", ix="Any2West", measurement_id=3)
    _detour(conn, source_cc="FJ", target_asn=136921, measurement_id=4)  # same economy
    # A second corroboration reusing measurement 1 must not be counted twice.
    store.add_corroboration(conn, finding_id=1, measurement_id=1, vantage_point_cc="VU")
    lt = store.create_finding(
        conn, kind=store.KIND_CONFIRMED_LOCAL_TRANSIT, source_cc="FJ", source_asn=4638,
        target_cc="TO", target_asn=38201,
    )
    store.add_corroboration(conn, finding_id=lt, measurement_id=5, vantage_point_cc="FJ")
    # Quarantined: in the DB, out of every tally (same rule as the public report).
    _detour(conn, target_cc="CK", target_asn=VAKANET, measurement_id=6)
    return conn


def test_summary_counts_exclude_quarantined_findings():
    s = rf.summarize(_db(), REGISTRY)
    assert s.total == 5
    assert s.by_kind == {"confirmed_detour": 4, "confirmed_local_transit": 1, "candidate_peering": 0}
    assert s.measurements == 5


def test_summary_ranks_hubs_and_exchanges_by_count():
    s = rf.summarize(_db(), REGISTRY)
    assert s.hubs == (("Sydney", 3), ("Los Angeles", 1))
    assert s.exchanges == (("Equinix Sydney", 3), ("Any2West", 1))


def test_summary_counts_same_economy_detours():
    assert rf.summarize(_db(), REGISTRY).same_economy_detours == 1


def test_summary_counts_registry_classifications():
    s = rf.summarize(_db(), REGISTRY)
    assert (s.ixp_total, s.ixp_in, s.ixp_out, s.ixp_unconfirmed) == (4, 1, 2, 1)


def test_rendered_block_states_the_numbers():
    text = rf.render_block(rf.summarize(_db(), REGISTRY), as_of="2026-10-18")
    assert "Counts as of 2026-10-18" in text
    assert "holds 5 findings, backed by 5 RIPE Atlas traceroute measurements" in text
    assert "| Confirmed detour | 4 |" in text
    assert "| Sydney | 3 |\n| Los Angeles | 1 |" in text
    assert "| Equinix Sydney | 3 |\n| Any2West | 1 |" in text
    assert "In 1 detour, both ends are in the same economy." in text
    assert "4 exchanges, 1 in the fishbowl, 2 outside, 1 unconfirmed" in text


def _readme(block: str) -> str:
    return f"# Title\n\n## Findings so far\n\n{rf.START}\n{block}\n{rf.END}\n\nHand-written text.\n"


def test_update_replaces_only_the_marked_block():
    old = _readme("old numbers")
    new = rf.update_readme(old, rf.summarize(_db(), REGISTRY), as_of="2026-10-18")
    assert "old numbers" not in new
    assert "holds 5 findings" in new
    assert new.startswith("# Title\n\n## Findings so far\n\n")
    assert new.endswith(f"{rf.END}\n\nHand-written text.\n")


def test_update_leaves_readme_untouched_when_only_the_date_would_change():
    s = rf.summarize(_db(), REGISTRY)
    last_week = _readme(rf.render_block(s, as_of="2026-10-11"))
    assert rf.update_readme(last_week, s, as_of="2026-10-18") == last_week


def test_update_refuses_a_readme_without_markers():
    with pytest.raises(ValueError, match="markers"):
        rf.update_readme("# Title\n\nNo markers here.\n", rf.summarize(_db(), REGISTRY), as_of="2026-10-18")


def test_rendered_block_handles_detours_without_an_exchange_name():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(store._SCHEMA)
    _detour(conn, ix=None)
    text = rf.render_block(rf.summarize(conn, REGISTRY), as_of="2026-10-18")
    assert "| Sydney | 1 |" in text
    assert "Exchange or carrier" not in text


def test_summary_excludes_held_findings(monkeypatch):
    monkeypatch.setattr(
        quarantined_asns, "HELD_FINDING_KEYS",
        frozenset({(store.KIND_CONFIRMED_DETOUR, 9249, 4638)}),
    )
    assert rf.summarize(_db(), REGISTRY).by_kind["confirmed_detour"] == 3


def _run_main(monkeypatch, tmp_path, db_path):
    readme = tmp_path / "README.md"
    readme.write_text(_readme("old numbers"))
    registry = tmp_path / "registry.json"
    registry.write_text("{}")
    monkeypatch.setattr("sys.argv", ["prog", "--readme", str(readme), "--registry", str(registry),
                                     "--db", str(db_path)])
    return readme


def test_main_refuses_a_missing_database(monkeypatch, tmp_path):
    readme = _run_main(monkeypatch, tmp_path, tmp_path / "absent.db")
    with pytest.raises(SystemExit) as exc:
        rf.main()
    assert "no findings database" in str(exc.value.code)
    assert "old numbers" in readme.read_text()
    assert not (tmp_path / "absent.db").exists()


def test_main_refuses_an_empty_database(monkeypatch, tmp_path):
    db = tmp_path / "empty.db"
    db.touch()

    def _empty(_path):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(store._SCHEMA)
        return conn

    monkeypatch.setattr(store, "connect", _empty)
    readme = _run_main(monkeypatch, tmp_path, db)
    with pytest.raises(SystemExit) as exc:
        rf.main()
    assert "0 reportable findings" in str(exc.value.code)
    assert "old numbers" in readme.read_text()


def test_external_names_cannot_inject_markdown():
    """Exchange names come from PeeringDB, so treat them as untrusted text."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(store._SCHEMA)
    hostile = f"Evil | IX\n[click](https://example.invalid) {rf.END} <b>x</b>"
    _detour(conn, ix=hostile)
    text = rf.render_block(rf.summarize(conn, REGISTRY), as_of="2026-10-18")
    row = next(line for line in text.splitlines() if line.startswith("| Evil"))
    assert row.count(" | ") == 1  # still exactly two cells
    assert "\n[click]" not in text and "[click](" not in text
    assert rf.END not in text
    assert "<b>" not in text
