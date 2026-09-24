"""Report data for the ROV section: the latest Cloudflare ROV test snapshot.

Reads the last line of `outputs/reports/rov_cloudflare_history.jsonl` (written
weekly by `atlas.rov_cloudflare`, git-tracked) and shapes it for the
ASCII/HTML reports, which place it right after ASPA (owner, 2026-09-24):
ASPA covers who has *published* route-security data; this covers whose
paths actually *enforce* origin validation. Kept out of `reports/data.py`,
which is already well past the project's file-size limit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROV_HISTORY_PATH = Path("outputs/reports/rov_cloudflare_history.jsonl")


@dataclass(frozen=True)
class RovEconomyRow:
    cc: str
    name: str
    v4: tuple[int, int, int]  # (filtered, not_filtered, inconclusive)
    v6: tuple[int, int, int] | None  # None: no IPv6 probe in this economy


@dataclass(frozen=True)
class RovDropPoint:
    af: str  # "v4" / "v6"
    asn: int | None  # None: died before the first public hop
    probes: int


@dataclass(frozen=True)
class RovSplit:
    probe_id: str
    cc: str
    af: str
    valid_next: int
    invalid_next: int


@dataclass(frozen=True)
class RovSummary:
    date: str
    measurement_ids: dict[str, list[int]]
    economies: tuple[RovEconomyRow, ...]
    drop_points: tuple[RovDropPoint, ...]
    splits: tuple[RovSplit, ...]
    untested: tuple[str, ...] = ()  # in-scope economies with no connected probe in that run


def _counts(fam: dict | None) -> tuple[int, int, int] | None:
    if fam is None:
        return None
    return (fam.get("filtered", 0), fam.get("not_filtered", 0), fam.get("inconclusive", 0))


def load_rov_summary(registry: dict, path: Path = DEFAULT_ROV_HISTORY_PATH) -> RovSummary | None:
    """The latest ROV snapshot, or None if the test hasn't run yet."""
    if not path.exists():
        return None
    lines = [line for line in path.read_text().splitlines() if line.strip()]
    if not lines:
        return None
    snapshot = json.loads(lines[-1])
    economies = tuple(
        RovEconomyRow(
            cc=cc,
            name=registry.get(cc, {}).get("name", cc),
            v4=_counts(fams.get("v4")) or (0, 0, 0),
            v6=_counts(fams.get("v6")),
        )
        for cc, fams in snapshot["economies"].items()
    )
    drop_points = tuple(
        RovDropPoint(af=key.split(":")[0], asn=None if key.split(":")[1] == "None" else int(key.split(":")[1]), probes=n)
        for key, n in snapshot["drop_asns"].items()
    )
    splits = tuple(
        RovSplit(pid, p["cc"], af, p[af]["diverged"]["valid_next"], p[af]["diverged"]["invalid_next"])
        for pid, p in snapshot["probes"].items()
        for af in ("v4", "v6")
        if p.get(af) and p[af].get("diverged")
    )
    return RovSummary(
        date=snapshot["date"],
        measurement_ids=snapshot["measurement_ids"],
        economies=economies,
        drop_points=drop_points,
        splits=splits,
        untested=tuple(sorted(set(registry) - set(snapshot["economies"]))),
    )
