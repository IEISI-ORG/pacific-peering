"""Tests for the unattended daily check's facts collector and email renderer."""

from __future__ import annotations

from datetime import datetime, timezone

from pacific_peering.reports import daily_facts, status_email

LOG = """=== nightly corridor testing: 2026-09-30T15:00:01Z ===
2026-10-01 01:03:41,154 WARNING Measurement 217486797 still Ongoing after 180s; returning partial results
2026-10-01 01:06:55,893 WARNING AS17456 -> AS9246: 1 of 3 probe(s) proxy-corrupted (Starlink), continuing with 2 clean
2026-10-01 01:13:01,596 INFO Batch done: 7 corridor(s) tested in 743s (budget 7200s)
2026-10-01 01:13:01,596 INFO Outcomes: {'confirmed_detour': 6, 'confirmed_local_transit': 1}
Committed and pushed.
=== done: 2026-09-30T15:13:05Z ===
=== nightly corridor testing: 2026-10-01T15:00:01Z ===
Traceback (most recent call last):
"""


def test_cron_runs_keep_real_problems_and_drop_routine_partial_results():
    first, second = daily_facts.cron_runs(LOG)
    assert first["finished"] == "2026-09-30T15:13:05Z" and first["pushed"]
    assert first["batch"].startswith("7 corridor(s)")
    assert len(first["problems"]) == 1 and "proxy-corrupted" in first["problems"][0]
    assert second["finished"] is None and second["problems"] == ["Traceback (most recent call last):"]


def test_escalations_split_resolved_and_recent():
    text = ("# Escalations\n\n## A\n- flagged: 2026-09-19T00:00:00+00:00\n- resolved: yes\n\n"
            "## B\n- flagged: 2026-10-01T02:00:00+00:00\n\n## C\n- flagged: 2026-09-20T00:00:00+00:00\n")
    summary = daily_facts.escalation_summary(text, datetime(2026, 9, 30, tzinfo=timezone.utc))
    assert summary["total"] == 3 and summary["unresolved"] == 2
    assert len(summary["flagged_in_window"]) == 1 and summary["flagged_in_window"][0].startswith("## B")


def test_backlog_candidates():
    assert daily_facts.backlog_candidates("Candidates: 4 | New probes since last run: 0") == 4


STATUS = {
    "run_at": "2026-10-02T07:30:00+10:00", "mode": "dry-run", "overall": "attention",
    "headline": "Nightly run finished; one finding <needs> a look.",
    "stats": [{"label": "Findings", "value": 245}],
    "needs_attention": [{"title": "AS1 -> AS2", "severity": "medium", "detail": "x & y",
                         "suggested_action": "retest", "refs": ["measurement 1"]}],
    "escalated": [], "checks": [{"name": "Cron", "status": "ok", "summary": "pushed"}],
    "links": [{"label": "Site", "url": "https://pacific-peering.ieisi.org"}],
}


def test_html_escapes_and_marks_dry_run():
    out = status_email.render_html(STATUS)
    assert "&lt;needs&gt;" in out and "x &amp; y" in out and "<needs>" not in out
    assert "Dry run: drafted, not sent." in out and "Needs a look" in out
    assert "<style" not in out  # inline styles only, for Gmail


def test_text_alternative_lists_attention_and_empty_escalations():
    out = status_email.render_text(STATUS)
    assert "[medium] AS1 -> AS2" in out and "Suggested: retest" in out
    assert "ESCALATED THIS RUN\n- nothing" in out
