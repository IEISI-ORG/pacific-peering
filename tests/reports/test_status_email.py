"""Status email rendering (reports/status_email.py).

Caught by the first forced dry run, 2026-10-03: the agent writes `run_at` in
UTC, so a 07:30 Brisbane run was headed with the previous day's date; and an
empty "needs attention" list printed `- [] Nothing.` in the text version.
"""

from __future__ import annotations

import time

import pytest

from pacific_peering.reports import status_email

# The dry run's own status.json values (logs/unattended/2026-10-03T0859-dry-run).
_STATUS = {
    "run_at": "2026-10-02T23:02:00+00:00",
    "mode": "dry-run",
    "overall": "ok",
    "headline": "All clear.",
    "stats": [],
    "needs_attention": [],
    "escalated": [],
    "checks": [],
    "links": [],
}


@pytest.fixture
def brisbane(monkeypatch):
    """The cron host's zone, pinned so the test doesn't depend on where it runs."""
    monkeypatch.setenv("TZ", "Australia/Brisbane")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def test_text_heading_uses_the_local_date_not_utc(brisbane):
    first_line = status_email.render_text(_STATUS).splitlines()[0]
    assert first_line.startswith("Pacific Peering daily check 2026-10-03 ")


def test_html_heading_uses_the_local_date_not_utc(brisbane):
    html = status_email.render_html(_STATUS)
    assert "2026-10-03" in html and "2026-10-02" not in html


def test_text_with_nothing_needing_attention_has_no_empty_severity():
    text = status_email.render_text(_STATUS)
    section = text.split("NEEDS YOUR ATTENTION\n")[1].split("\n\n")[0]
    assert section == "- nothing"
