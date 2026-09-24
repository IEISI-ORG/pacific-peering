"""Tests for the report's ROV section (reports/rov_data.py + both renderers)."""

from __future__ import annotations

import json

from pacific_peering.reports import ascii_report, html_report
from pacific_peering.reports.rov_data import load_rov_summary

REGISTRY = {"NC": {"name": "New Caledonia", "asns": []}, "PG": {"name": "Papua New Guinea", "asns": []},
            "WS": {"name": "Samoa", "asns": []}}

SNAPSHOT = {
    "date": "2026-09-24",
    "measurement_ids": {"v4": [1, 2], "v6": [3, 4]},
    "economies": {"NC": {"v4": {"filtered": 5}, "v6": {"filtered": 3, "inconclusive": 1}},
                  "PG": {"v4": {"not_filtered": 1}}},
    "drop_asns": {"v4:18200": 2, "v6:None": 1},
    "probes": {
        "50365": {"cc": "PG", "v4": {"label": "not_filtered", "drop_asn": None, "reason": None,
                                     "diverged": {"after": 17828, "valid_next": 4826, "invalid_next": 7474}}},
        "7018": {"cc": "NC", "v4": {"label": "filtered", "drop_asn": 18200, "reason": None, "diverged": None}},
    },
}


def _write(tmp_path, *snapshots):
    path = tmp_path / "rov_history.jsonl"
    path.write_text("".join(json.dumps(s) + "\n" for s in snapshots))
    return path


def test_loads_latest_snapshot(tmp_path):
    older = {**SNAPSHOT, "date": "2026-09-17"}
    rov = load_rov_summary(REGISTRY, _write(tmp_path, older, SNAPSHOT))

    assert rov.date == "2026-09-24"
    nc = next(e for e in rov.economies if e.cc == "NC")
    assert (nc.name, nc.v4, nc.v6) == ("New Caledonia", (5, 0, 0), (3, 0, 1))
    assert next(e for e in rov.economies if e.cc == "PG").v6 is None
    assert [(d.af, d.asn, d.probes) for d in rov.drop_points] == [("v4", 18200, 2), ("v6", None, 1)]
    assert [(s.probe_id, s.valid_next, s.invalid_next) for s in rov.splits] == [("50365", 4826, 7474)]
    assert rov.untested == ("WS",)


def test_missing_history_means_none(tmp_path):
    assert load_rov_summary(REGISTRY, tmp_path / "absent.jsonl") is None


class _Data:
    """Just enough of ReportData for the ROV renderers."""

    def __init__(self, rov):
        self.rov = rov


def test_both_renderers_show_the_section(tmp_path):
    rov = load_rov_summary(REGISTRY, _write(tmp_path, SNAPSHOT))

    text = "\n".join(ascii_report._rov_section(_Data(rov)))
    page = html_report._rov_section_html(_Data(rov))

    for out in (text, page):
        assert "ROV" in out and "New Caledonia" in out
        assert "AS18200: 2 probe(s)" in out
        assert "valid via AS4826, invalid via AS7474" in out
        assert "Not testable (no connected probe): WS" in out
    assert "hasn't run yet" in "\n".join(ascii_report._rov_section(_Data(None)))
    assert "hasn't run yet" in html_report._rov_section_html(_Data(None))
