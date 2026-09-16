#!/bin/bash
# Weekly discovery refresh -- runs unattended via system cron, no LLM involved.
#
# Per the project owner: a full discovery refresh (APNIC/RIS/PeeringDB/IRR/
# probe-registry -- all free APIs) once a week is enough; this isn't expected
# to change more often than that. Firing it more often risks the PeeringDB
# rate-limiting this project has already hit once on a single run.
#
# Scope, deliberately: only re-derives the free-API-backed registries and
# regenerates the corridor backlog against them. Never fires an Atlas
# traceroute (that costs real account credits and needs a real candidate to
# exist first -- see auto_classify.py, run separately/on its own cadence).
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

# Only these two paths are git-tracked outputs of the steps above --
# data/* (the registries themselves) is gitignored by design. Scoped
# `git add`, not `-A`, so this unattended job can never sweep in unrelated
# in-progress work sitting in the tree.
if ! git diff --quiet -- corridor_backlog.md || [ -n "$(git status --porcelain -- outputs/runs)" ]; then
    git add corridor_backlog.md outputs/runs
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
