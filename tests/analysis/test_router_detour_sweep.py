"""router_detour_sweep: report-only, lists findings the router-location rule would reclassify."""

from __future__ import annotations

import json
import sqlite3

from pacific_peering.analysis import router_detour_sweep as sweep_mod
from pacific_peering.analysis import store

TATA_LA = "ix-xe-2-1-4-0.tcore2.lvw-losangeles.as6453.net"


def _db() -> sqlite3.Connection:
    # store.connect is blocked by tests/conftest.py; use an in-memory connection with the real schema.
    conn = sqlite3.connect(":memory:")
    conn.executescript(store._SCHEMA)
    return conn


def _trace(probe_id, hops):
    return {"measurement_id": 221439393, "probe_id": probe_id, "target": "202.43.12.1",
            "hops": [{"hop": h, "addresses": [a], "min_rtt_ms": r} for h, a, r in hops]}


def test_sweep_lists_local_transit_backed_by_an_la_router(tmp_path):
    conn = _db()
    fid = store.create_finding(conn, kind=store.KIND_CONFIRMED_LOCAL_TRANSIT, source_cc="FJ", source_asn=45355,
                               target_cc="TO", target_asn=38198)
    store.add_corroboration(conn, finding_id=fid, measurement_id=221439393, vantage_point_cc="MP")
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    (parsed / "221439393.json").write_text(json.dumps([
        _trace(65653, [(8, "64.86.252.73", 121.458), (18, "202.43.12.5", 212.954)]),
    ]))

    rows = sweep_mod.sweep(conn, parsed, [], {"64.86.252.73": TATA_LA}.get)

    assert len(rows) == 1
    row = rows[0]
    assert (row["finding_id"], row["kind"], row["measurement_id"], row["probe_id"]) == (
        fid, "confirmed_local_transit", 221439393, 65653)
    assert row["city"] == "Los Angeles" and row["verdict"] == "ok"
    text = sweep_mod.render(rows)
    assert f"#{fid}" in text and "lvw-losangeles" in text


def test_sweep_skips_traces_that_cross_an_off_region_ixp(tmp_path):
    import ipaddress

    conn = _db()
    fid = store.create_finding(conn, kind=store.KIND_CONFIRMED_LOCAL_TRANSIT, source_cc="FJ", source_asn=45355,
                               target_cc="TO", target_asn=38198)
    store.add_corroboration(conn, finding_id=fid, measurement_id=221439393, vantage_point_cc="MP")
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    (parsed / "221439393.json").write_text(json.dumps([
        _trace(65653, [(6, "45.127.172.46", 60.0), (8, "64.86.252.73", 121.458)]),
    ]))

    rows = sweep_mod.sweep(conn, parsed, [ipaddress.ip_network("45.127.172.0/22")], {"64.86.252.73": TATA_LA}.get)

    assert rows == []
