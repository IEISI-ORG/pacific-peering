"""LEGAL_NOTICE: the closing notice shared by every report and the public site."""

from __future__ import annotations

from pacific_peering.reports.data import LEGAL_NOTICE


def test_router_details_paragraph_follows_observations():
    headings = [h for h, _ in LEGAL_NOTICE]
    assert headings.index("Router details") == headings.index("Observations, not judgements") + 1


def test_router_details_says_public_traceroute_data_and_points_to_issues():
    text = dict(LEGAL_NOTICE)["Router details"]
    assert "traceroute" in text and "public" in text
    assert "GitHub" in text
