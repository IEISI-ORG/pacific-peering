"""Tests for the website build (reports/site.py)."""

from __future__ import annotations

import pytest

from pacific_peering.reports import site


def _inputs(tmp_path, html, charts=("as_graph.svg",)):
    reports, viz = tmp_path / "reports", tmp_path / "viz"
    reports.mkdir()
    viz.mkdir()
    (reports / "report.html").write_text(html)
    (reports / "report.txt").write_text("text report")
    for c in charts:
        (viz / c).write_text("<svg/>")
    return reports, viz


def test_build_rewrites_chart_paths_and_copies_assets(tmp_path):
    reports, viz = _inputs(tmp_path, '<img src="../viz/as_graph.svg"><a href="../viz/as_graph.svg">x</a>')
    out = site.build_site(tmp_path / "dist", reports, viz)

    html = (out / "index.html").read_text()
    assert '../viz/' not in html and 'src="viz/as_graph.svg"' in html
    assert (out / "viz" / "as_graph.svg").exists()
    assert (out / "reports" / "report.txt").exists()
    assert not (out / "reports" / "probe_gaps.txt").exists()  # absent inputs are skipped


def test_missing_chart_fails_instead_of_publishing_broken_images(tmp_path):
    reports, viz = _inputs(tmp_path, '<img src="../viz/missing.svg">', charts=())
    with pytest.raises(FileNotFoundError, match="missing.svg"):
        site.build_site(tmp_path / "dist", reports, viz)
