# Pacific Peering

Mapping every active AS-path across the ASNs homed in Melanesia, Polynesia, and
Micronesia — the APNIC-covered Oceania economies, excluding Australia and New
Zealand, excluding Hawaii, including Guam.

The project triangulates public BGP route data (RIPEstat) with active
measurement (RIPE Atlas traceroutes) to surface peering relationships, IXP
routing, and sub-optimal transpacific paths, on a recurring update cycle.

See [`GOALS.md`](GOALS.md) for the full project brief and
[`task_plan.md`](task_plan.md) for current build status.

## Status

ASN discovery, RIS ingestion, PeeringDB IXP membership, and RIPE Atlas
traceroute measurement are implemented and have produced live results,
including a real ASN-to-ASN adjacency confirmed by both RIS and Atlas.
See `task_plan.md` for phase-by-phase progress and current findings.

## Project layout

```
src/pacific_peering/
├── discovery/   # ASN / economy discovery
├── ris/         # RIPEstat ingestion, ASPATH + peering analysis
├── atlas/       # RIPE Atlas traceroute measurements
├── analysis/    # sub-optimal routing detection
├── viz/         # pathway visualization
└── reports/     # ASCII / HTML report generation

data/      # raw + derived data (gitignored)
outputs/   # generated reports/visualizations per run (gitignored)
docs/      # project documentation
```

## Setup

This project uses [`uv`](https://docs.astral.sh/uv/) for Python packaging.

```bash
uv sync
```

## License

CC BY-NC-SA 4.0 — see [`LICENSE`](LICENSE). Commercial use requires a paid
license; contact the author to arrange one.

## Support

If this project is useful to you, consider supporting it:
[Buy Me a Coffee](https://www.buymeacoffee.com/terrysweetser).
