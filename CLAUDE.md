# Pacific Peering — session start

Run this check at the start of every session in this repo, before anything else:

```bash
uv run pacific-peering-pipeline          # free APIs only: APNIC/RIS/IXP-LAN/IRR/probe-registry
uv run pacific-peering-corridor-backlog  # regenerate corridor_backlog.md against that fresh data
```

Then report the candidate count. If it's non-zero, pull corridors via
`uv run pacific-peering-auto-classify` (see `src/pacific_peering/analysis/auto_classify.py`
for the full pipeline — fires a traceroute, triangulates against RIS, classifies, files a
finding, marks the corridor tested, regenerates artifacts, and escalates anything it can't
confidently resolve to `escalations.md`).

Cadence agreement with the project owner: prefer firing across several different source
economies' probes in parallel over batching many corridors against one probe (a single
source ASN's probe queue serializes measurements — see `task_plan.md` for the Niue/AS55885
case that established this).

Don't re-run the full pipeline more than once per session start or once genuine time has
passed — it hits PeeringDB/APNIC/RIS live, and re-checking seconds apart just risks rate
limiting for no new data.

Read `task_plan.md` for the full narrative history and `CHANGELOG.md` for the terse log
before picking up new work.
