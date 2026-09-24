#!/bin/bash
# Nightly corridor testing -- runs unattended via system cron, no LLM involved.
#
# Per the project owner: Monday-Saturday at 1am, fit as many corridor tests
# as possible into a 2-hour budget, processing whatever the weekly Sunday
# discovery refresh (weekly_discovery_refresh.sh) surfaced. Skips Sunday
# deliberately -- that's when the discovery refresh itself runs, and testing
# against data that's mid-refresh would be working from a moving target.
#
# Two sources of work, drained by the same run: genuinely new corridors from
# the backlog, and this week's reverification ration (the oldest-verified
# quarter of all findings, staged by the Sunday job) -- see
# auto_classify.run_batch()'s docstring for how a worker checks the
# reverification queue before falling back to a new corridor.
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
# finds a genuine untested corridor or a queued reverification to test, never
# speculatively.
#
# cron runs with a minimal environment, so this uses uv's full path and
# cd's into the repo first -- secrets.yaml and pyproject.toml both resolve
# relative to cwd.

set -euo pipefail

REPO_DIR="/home/terry/pacific-peering"
UV="/home/terry/.local/bin/uv"

cd "$REPO_DIR"

echo "=== nightly corridor testing: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# Full ASN probe registry refresh, Tuesday and Friday -- per the project
# owner, who wants new/returned probes found in a timely manner, not just
# once a week. `build_asn_probe_registry()` (data/atlas/asn_probe_registry.json)
# is the ASN-tracked, Connected-only registry `auto_classify.run_batch()`
# actually sources real measurements from; it's otherwise only refreshed
# once a week by weekly_discovery_refresh.sh's Sunday pipeline run. A probe
# that reconnects mid-week would otherwise sit unusable for ASN-based
# sourcing for days -- Tuesday+Friday (roughly every 3-4 days, spread
# across the Sunday-to-Sunday week) closes that gap without adding new
# cron entries, riding the existing Mon-Sat 1am job. Runs before the batch
# below so that day's own corridor testing benefits from the freshest
# registry. Read-only Atlas API lookup, no credits spent (same as the
# Sunday pipeline's own use of this step).
_dow="$(date +%u)"  # ISO: Monday=1 ... Sunday=7
if [ "$_dow" = "2" ] || [ "$_dow" = "5" ]; then
    echo "$(date +%A): refreshing the full ASN probe registry."
    "$UV" run pacific-peering-atlas-asn-probes
fi

"$UV" run pacific-peering-auto-classify-batch --hours 2 --max-concurrent 5

# Probe-gap report, regenerated daily rather than only on the weekly
# refresh -- per the project owner, cheap (40 unauthenticated Atlas calls,
# no credits -- one pass for connected-only coverage, one for the full
# any-status probe listing) and worth keeping current every night rather
# than letting it drift stale between Sunday runs.
"$UV" run pacific-peering-report-probe-gaps

# Offshore-hosting check (owner, 2026-09-24): monthly full run, plus any ASN
# the registry gained since the last run -- the module decides which each
# night, and usually fires nothing. Pings in-scope addresses from AU/NZ/US/JP
# probes; an RTT faster than fibre allows from the economy flags the address
# as hosted abroad (outputs/reports/offshore_check*, new flags appended to
# escalations.md for the owner -- never auto-excluded). Runs after the
# probe-gap report so the registry/listing are tonight's. Failure-tolerant,
# same as the Wednesday steps below.
"$UV" run pacific-peering-offshore-check --fire || echo "Offshore-hosting check failed (see above); continuing."

# Weekly IPv6 fleet check, Wednesday only -- per the project owner
# (2026-09-24): IPv6 is monitored, not corridor-tested, for now. Traces the
# public DNS IPv6 anchors from every connected probe with an IPv6 ASN
# (2 measurements, real Atlas credits) and records each probe's measured
# IPv6 access plus fleet-wide IPv6 deployment to outputs/reports/ipv6_fleet*
# (committed below). Runs after the probe-gap report so it reads tonight's
# freshly rebuilt probe listing. Allowed to fail without aborting the
# script: under `set -e` an Atlas refusal here would otherwise also block
# committing the corridor results above.
if [ "$_dow" = "3" ]; then
    echo "$(date +%A): weekly IPv6 fleet check."
    "$UV" run pacific-peering-ipv6-fleet --fire || echo "IPv6 fleet check failed (see above); continuing."
    # Cloudflare ROV test (owner, 2026-09-24): traces Cloudflare's RPKI-valid
    # and RPKI-invalid test prefixes from every connected probe (4
    # measurements) and records where invalid traces die, to
    # outputs/reports/rov_cloudflare*. Checks the targets' RPKI state first
    # and skips firing if they've changed. Same failure tolerance as above.
    echo "$(date +%A): weekly Cloudflare ROV test."
    "$UV" run pacific-peering-rov-cloudflare --fire || echo "Cloudflare ROV test failed (see above); continuing."
    # report.txt/html carry an ROV section (after ASPA) read from the history
    # file just written; the batch above only regenerates them on nights it
    # tests something, so rebuild them here or the section lags a week.
    { "$UV" run pacific-peering-report-ascii && "$UV" run pacific-peering-report-html; } \
        || echo "Report regeneration failed (see above); continuing."
fi

# Everything this step can change that's git-tracked: findings_export.jsonl,
# corridor_backlog.md, the ASCII/HTML reports, outputs/reports/probe_gaps.txt,
# the geographic map, and escalations.md if anything needed a human look
# (only added if it exists -- `git add` errors on a path that was never
# created, and no escalation may have happened tonight). data/* (the SQLite
# store itself) stays local/gitignored by design.
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
