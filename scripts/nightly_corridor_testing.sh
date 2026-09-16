#!/bin/bash
# Nightly corridor testing -- runs unattended via system cron, no LLM involved.
#
# Per the project owner: Monday-Saturday at 1am, fit as many corridor tests
# as possible into a 2-hour budget, processing whatever the weekly Sunday
# discovery refresh (weekly_discovery_refresh.sh) surfaced. Skips Sunday
# deliberately -- that's when the discovery refresh itself runs, and testing
# against data that's mid-refresh would be working from a moving target.
#
# Concurrency, not just a longer queue: auto_classify.run_batch() fires
# measurements across several different source-economy probes at once
# (see its docstring) rather than serially waiting on one -- a single
# source ASN's probe queue serializes its own measurements no matter how
# fast we submit to it, so running several different ASNs concurrently is
# the actual throughput lever within the 2-hour window.
#
# This step spends real RIPE Atlas account credits (unlike the free-API-only
# weekly discovery refresh) -- only fires when pacific-peering-auto-classify-batch
# finds a genuine untested corridor to test, never speculatively.
#
# cron runs with a minimal environment, so this uses uv's full path and
# cd's into the repo first -- secrets.yaml and pyproject.toml both resolve
# relative to cwd.

set -euo pipefail

REPO_DIR="/home/terry/pacific-peering"
UV="/home/terry/.local/bin/uv"

cd "$REPO_DIR"

echo "=== nightly corridor testing: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

"$UV" run pacific-peering-auto-classify-batch --hours 2 --max-concurrent 5

# Everything this step can change that's git-tracked: findings_export.jsonl,
# corridor_backlog.md, the ASCII/HTML reports, the geographic map, and
# escalations.md if anything needed a human look (only added if it exists --
# `git add` errors on a path that was never created, and no escalation may
# have happened tonight). data/* (the SQLite store itself) stays local/
# gitignored by design.
TRACK_PATHS=(findings_export.jsonl corridor_backlog.md outputs/reports outputs/viz)
[ -f escalations.md ] && TRACK_PATHS+=(escalations.md)

if [ -n "$(git status --porcelain -- "${TRACK_PATHS[@]}")" ]; then
    git add "${TRACK_PATHS[@]}"
    git commit -m "$(cat <<EOF
feat(analysis): nightly corridor testing batch ($(date -u +%Y-%m-%dT%H:%M:%SZ))

Unattended system cron, no LLM involved -- see scripts/nightly_corridor_testing.sh
and analysis/auto_classify.py's run_batch().

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Vh4Lba9QazDQiRvaW5zTor
EOF
)"
    git push
    echo "Committed and pushed."
else
    echo "No git-tracked changes (nothing new was testable)."
fi

echo "=== done: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
