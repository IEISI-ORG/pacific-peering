"""Tests for the ASN quarantine (discovery/quarantined_asns.py) and where it bites."""

from __future__ import annotations

import sqlite3

from pacific_peering.analysis import store
from pacific_peering.discovery.quarantined_asns import (
    HELD_FINDINGS,
    QUARANTINED_ASN_SET,
    QUARANTINED_ASNS,
)

VAKANET = 152093


def _db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(store._SCHEMA)
    held = store.create_finding(
        conn, kind=store.KIND_CONFIRMED_DETOUR, source_cc="VU", source_asn=9249,
        target_cc="CK", target_asn=VAKANET, detour_hub="Sydney",
    )
    kept = store.create_finding(
        conn, kind=store.KIND_CONFIRMED_DETOUR, source_cc="VU", source_asn=9249,
        target_cc="CK", target_asn=10131, detour_hub="Sydney",
    )
    return conn, held, kept


def test_vakanet_is_quarantined_with_evidence():
    assert VAKANET in QUARANTINED_ASN_SET
    entry = next(q for q in QUARANTINED_ASNS if q.asn == VAKANET)
    assert entry.release_when and "217757577" in entry.note


def test_is_quarantined_checks_both_ends():
    conn, held, kept = _db()
    by_id = {f.id: f for f in store.all_findings(conn)}
    assert store.is_quarantined(by_id[held])
    assert not store.is_quarantined(by_id[kept])


def test_loaders_hold_quarantined_findings_only_when_asked():
    conn, _, _ = _db()
    everything = store.load_confirmed_detours(conn)
    reported = store.load_confirmed_detours(conn, include_quarantined=False)
    assert {d.target_asn for d in everything} == {VAKANET, 10131}
    assert {d.target_asn for d in reported} == {10131}


# Per-finding holds: one finding, not every finding touching its ASNs.
def _held_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(store._SCHEMA)
    held = store.create_finding(
        conn, kind=store.KIND_CANDIDATE_PEERING, source_cc="TO", source_asn=38198,
        target_cc="NR", target_asn=140504, probe_agreement="1/1 probes",
    )
    same_target = store.create_finding(
        conn, kind=store.KIND_CONFIRMED_DETOUR, source_cc="TV", source_asn=23917,
        target_cc="NR", target_asn=140504, detour_hub="Los Angeles",
    )
    return conn, held, same_target


def test_finding_273_is_held_with_evidence():
    entry = next(h for h in HELD_FINDINGS if (h.source_asn, h.target_asn) == (38198, 140504))
    assert entry.kind == store.KIND_CANDIDATE_PEERING
    assert entry.release_when and "218712900" in entry.note


def test_held_finding_is_quarantined_but_its_asns_are_not():
    conn, held, same_target = _held_db()
    by_id = {f.id: f for f in store.all_findings(conn)}
    assert store.is_quarantined(by_id[held])
    assert not store.is_quarantined(by_id[same_target])
    assert 140504 not in QUARANTINED_ASN_SET and 38198 not in QUARANTINED_ASN_SET


def test_loaders_drop_held_finding_only_when_asked():
    conn, _, _ = _held_db()
    assert len(store.load_candidate_peering(conn)) == 1
    assert store.load_candidate_peering(conn, include_quarantined=False) == ()
    assert len(store.load_confirmed_detours(conn, include_quarantined=False)) == 1
