#!/bin/bash
# Weekly discovery refresh -- runs unattended via system cron, no LLM involved.
#
# Per the project owner: a full discovery refresh (APNIC/RIS/PeeringDB/IRR/
# probe-registry -- all free APIs) once a week is enough; this isn't expected
# to change more often than that. Firing it more often risks the PeeringDB
# rate-limiting this project has already hit once on a single run.
#
# Scope, deliberately: only re-derives the free-API-backed registries and
# regenerates the corridor backlog against them, plus staging this week's
# reverification ration (see below). Never fires an Atlas traceroute itself
# (that costs real account credits and needs a real candidate to exist
# first -- the nightly job, scripts/nightly_corridor_testing.sh, does that
# on its own cadence).
#
# Also stages the oldest-verified quarter of all findings for this week's
# nightly runs to re-test -- per the project owner: a rolling reverification
# (oldest 1/4 each week) rather than one big periodic re-check, so it never
# competes with new-corridor testing for a whole night's budget, and every
# finding gets a fresh look roughly every 4 weeks. See
# auto_classify.write_reverification_queue()/run_batch() for how the
# nightly job actually drains this queue.
#
# Also re-checks every candidate_peering finding against Cloudflare Radar's
# ASPA data (an ASPA record is the target AS's own cryptographically-signed
# statement of its authorized providers -- see analysis/cloudflare_radar and
# auto_classify.recheck_aspa_candidates()), promoting any newly-confirmed
# ones to confirmed_local_transit. Unlike reverification this needs no Atlas
# credits at all (one cached snapshot lookup), so it isn't rationed across
# nightly runs -- it just re-checks anything not already checked in the
# last 30 days, every time this script runs.
#
# cron runs with a minimal environment (no ~/.local/bin on PATH, no shell
# profile), so this uses uv's full path and cd's into the repo before
# anything else -- secrets.yaml and pyproject.toml are both resolved
# relative to cwd.

set -euo pipefail

REPO_DIR="/home/terry/pacific-peering"
UV="/home/terry/.local/bin/uv"

cd "$REPO_DIR"

echo "=== weekly discovery refresh: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

"$UV" run pacific-peering-pipeline
"$UV" run pacific-peering-corridor-backlog
"$UV" run pacific-peering-reverify-enqueue
"$UV" run pacific-peering-aspa-recheck

# Git-tracked outputs of the steps above -- data/* (the registries and the
# SQLite store itself) is gitignored by design. A promoted ASPA finding
# touches findings_export.jsonl and the reports/viz derived from it, same
# as the nightly job's own tracked-paths list; a plain candidate recheck
# with zero promotions still touches findings_export.jsonl (every checked
# finding's aspa_checked_at moves) even though the reports/backlog only
# get their timestamp line bumped. Scoped `git add`, not `-A`, so this
# unattended job can never sweep in unrelated in-progress work sitting in
# the tree.
TRACK_PATHS=(corridor_backlog.md outputs/runs findings_export.jsonl outputs/reports outputs/viz)
if [ -n "$(git status --porcelain -- "${TRACK_PATHS[@]}")" ]; then
    git add "${TRACK_PATHS[@]}"
    git commit -m "$(cat <<EOF
chore(pipeline): weekly discovery refresh ($(date -u +%Y-%m-%dT%H:%M:%SZ))

Unattended system cron, no LLM involved -- see scripts/weekly_discovery_refresh.sh.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Vh4Lba9QazDQiRvaW5zTor
EOF
)"
    git push
    echo "Committed and pushed."
else
    echo "No git-tracked changes (backlog and run manifest unchanged)."
fi

echo "=== done: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
