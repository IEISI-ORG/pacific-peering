"""Deterministic facts for the owner's unattended daily check (a local wrapper kept outside the repo).

Owner's request (2026-10-01): a fallback for days without an interactive
session -- an unattended Claude run checks the usual things, escalates
anything odd, and emails the owner. This module gathers the facts that need
no judgement (cron runs, git state, new findings, escalations, scheduled
check reports, the live site), so the agent spends its turns investigating
and judging rather than re-deriving them, and so the agent's tool allowlist
can stay small. Read-only: touches nothing but its own output.

`uv run pacific-peering-daily-facts [--hours 26] [--out FILE]` prints JSON.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

CRON_LOG = Path("logs/cron.log")
BACKLOG = Path("corridor_backlog.md")
ESCALATIONS = Path("escalations.md")
FINDINGS_DB = Path("data/analysis/findings.db")
SITE_URL = "https://pacific-peering.ieisi.org/"
SCHEDULED_REPORTS = {
    "offshore_check": Path("outputs/reports/offshore_check.txt"),
    "leasing_check": Path("outputs/reports/leasing_check.txt"),
    "ipv6_fleet": Path("outputs/reports/ipv6_fleet.txt"),
    "rov_cloudflare": Path("outputs/reports/rov_cloudflare.txt"),
}
# Warnings the nightly batch emits routinely (partial results after the
# 180s wait); anything else at WARNING or above is surfaced.
_ROUTINE_WARNING = re.compile(r"still (Ongoing|Scheduled) after \d+s; returning partial results")
_PROBLEM = re.compile(r"Traceback|\bERROR\b|\bCRITICAL\b|\bWARNING\b|failed \(see above\)|fatal:|rejected")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout.strip()


def cron_runs(text: str, limit: int = 3) -> list[dict]:
    """The last `limit` cron runs in the log, newest last, each with its problems."""
    runs: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        start = re.match(r"=== (nightly corridor testing|weekly discovery refresh): (\S+) ===", line)
        if start:
            current = {"job": start.group(1), "started": start.group(2), "finished": None,
                       "pushed": False, "outcomes": None, "batch": None, "problems": []}
            runs.append(current)
            continue
        if current is None:
            continue
        done = re.match(r"=== done: (\S+) ===", line)
        if done:
            current["finished"] = done.group(1)
            current = None
            continue
        if line.startswith("Committed and pushed"):
            current["pushed"] = True
        elif "Outcomes:" in line:
            current["outcomes"] = line.split("Outcomes:", 1)[1].strip()
        elif "Batch done:" in line:
            current["batch"] = line.split("Batch done:", 1)[1].strip()
        elif _PROBLEM.search(line) and not _ROUTINE_WARNING.search(line):
            current["problems"].append(line.strip()[:300])
    for run in runs:
        run["problems"] = run["problems"][:15]
    return runs[-limit:]


def backlog_candidates(text: str) -> int | None:
    m = re.search(r"Candidates: (\d+)", text)
    return int(m.group(1)) if m else None


def escalation_summary(text: str, since: datetime) -> dict:
    blocks = re.split(r"\n(?=## )", text)[1:]
    unresolved = [b for b in blocks if "- resolved:" not in b]
    recent = []
    for b in unresolved:
        m = re.search(r"- flagged: (\S+)", b)
        if not m:
            continue
        try:
            flagged = datetime.fromisoformat(m.group(1))
        except ValueError:
            continue
        if flagged.tzinfo is None:
            flagged = flagged.replace(tzinfo=timezone.utc)
        if flagged >= since:
            recent.append(b.strip()[:800])
    return {"total": len(blocks), "unresolved": len(unresolved), "flagged_in_window": recent}


def recent_findings(since: datetime, db_path: Path = FINDINGS_DB) -> dict:
    """Findings and corroborations created in the window, read-only."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
        rows = conn.execute(
            "SELECT f.id, f.kind, f.source_cc, f.source_asn, f.target_cc, f.target_asn, f.target_name, "
            "f.detour_hub, c.measurement_id, c.vantage_point_cc, c.chain, c.ris_agrees, "
            "c.ris_observation_count, c.has_loop, c.loop_note, c.created_at "
            "FROM corroborations c JOIN findings f ON f.id = c.finding_id "
            "WHERE c.created_at >= ? ORDER BY c.created_at",
            (since.isoformat(),),
        ).fetchall()
    finally:
        conn.close()
    return {"total_findings": total, "corroborations_in_window": [dict(r) for r in rows]}


def scheduled_reports() -> dict:
    out = {}
    for name, path in SCHEDULED_REPORTS.items():
        if path.exists():
            lines = path.read_text().splitlines()
            out[name] = {"first_line": lines[0] if lines else "",
                         "new_flags": next((ln for ln in lines if ln.startswith("New ")), None)}
    return out


def live_site() -> dict:
    try:
        r = requests.get(SITE_URL, timeout=20)
    except requests.exceptions.RequestException as exc:
        return {"url": SITE_URL, "error": str(exc)}
    m = re.search(r"Generated\s*([0-9T:\-\.+]+)", r.text)
    return {"url": SITE_URL, "status": r.status_code, "generated": m.group(1) if m else None}


def collect(hours: float = 26.0) -> dict:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    _git("fetch", "--quiet")
    return {
        "collected_at": now.isoformat(),
        "window_hours": hours,
        "git": {
            "head": _git("log", "-1", "--format=%h %ci %s"),
            "branch_status": _git("status", "-sb").splitlines()[0] if _git("status", "-sb") else "",
            "dirty": _git("status", "--porcelain").splitlines(),
            "commits_in_window": _git("log", f"--since={since.isoformat()}", "--format=%h %ci %s").splitlines(),
        },
        "cron_runs": cron_runs(CRON_LOG.read_text()) if CRON_LOG.exists() else [],
        "backlog_candidates": backlog_candidates(BACKLOG.read_text()) if BACKLOG.exists() else None,
        "findings": recent_findings(since) if FINDINGS_DB.exists() else None,
        "escalations": escalation_summary(ESCALATIONS.read_text(), since) if ESCALATIONS.exists() else None,
        "scheduled_reports": scheduled_reports(),
        "site": live_site(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hours", type=float, default=26.0, help="look-back window (default 26h)")
    parser.add_argument("--out", type=Path, help="write JSON here instead of stdout")
    args = parser.parse_args()
    text = json.dumps(collect(args.hours), indent=2, default=str) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
