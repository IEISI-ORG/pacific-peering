# Pacific Peering — session start

Run this check at the start of every session in this repo, before anything else:

```bash
uv run pacific-peering-corridor-backlog  # cheap, local -- reports the current candidate count
```

The real data-freshness and corridor-testing work now runs unattended via system cron
(`crontab -l`, not Claude's own session-scoped CronCreate), so don't re-derive it by hand
each session:

- **Weekly discovery refresh** — `scripts/weekly_discovery_refresh.sh`, Sunday 1am
  (`0 1 * * 0`). Free APIs only (APNIC/RIS/PeeringDB/IRR/probe-registry), no Atlas credits,
  no LLM. Regenerates the corridor backlog against fresh data and commits+pushes
  `corridor_backlog.md`/`outputs/runs/*` if anything changed. Per the project owner: not
  expected to need to run more often than this.
- **Nightly corridor testing** — `scripts/nightly_corridor_testing.sh`, Mon–Sat 1am
  (`0 1 * * 1-6`, deliberately skips Sunday so it never races the discovery refresh).
  Runs `pacific-peering-auto-classify-batch --hours 2 --max-concurrent 5` — fits as many
  corridor tests as possible into a 2-hour budget, firing concurrently across different
  source-economy probes (see `auto_classify.run_batch()`'s docstring for why concurrency,
  not just a longer queue, is the actual throughput lever). Spends real Atlas credits, but
  only when a genuine untested corridor exists. Commits+pushes findings/reports/viz if
  anything changed; escalates anything it can't confidently resolve to `escalations.md`
  instead of guessing.

Both scripts log to `logs/cron.log` (gitignored). If you want to run either by hand mid-session
rather than wait for its schedule, just invoke the script directly — same as cron does.

Read `task_plan.md` for the full narrative history and `CHANGELOG.md` for the terse log
before picking up new work.
