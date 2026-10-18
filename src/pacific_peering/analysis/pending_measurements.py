"""Corridor measurements parked because their results weren't readable in time.

A corridor test waits a few minutes for its Atlas traceroute. When the
status check errors, or the probe hasn't reported by then, the measurement
is still running (and already paid for), so `auto_classify` parks it here
instead of failing the corridor or firing it again. Each nightly batch
(`auto_classify.run_batch`) collects parked measurements at its start and
end, and classifies any whose results have arrived. Per the owner
(2026-10-06): wait up to 24 hours, i.e. into the next nightly run, then
give up -- the corridor is left untested and fired fresh on a later run.

Parked corridors are excluded from the batch's normal picks until then,
so a slow corridor isn't fired again while its first measurement is out.
Local state (`data/` is gitignored), like `reverify_queue.json`.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from pacific_peering.analysis.corridor_backlog import CorridorCandidate
from pacific_peering.atlas.client import _TERMINAL_STATUSES, fetch_measurement_status, fetch_raw_results
from pacific_peering.atlas.smoketest import persist_results

logger = logging.getLogger(__name__)

DEFAULT_PENDING_PATH = Path("data/analysis/pending_measurements.json")
MAX_AGE = timedelta(hours=24)
# A measurement whose results are in but whose classification keeps failing
# is re-parked (it's paid for) up to this many times, then dropped -- a
# deterministic failure mustn't be retried forever.
MAX_CLASSIFY_ATTEMPTS = 3
# Batches collect at their start and end, two hours apart; spacing retries
# keeps one bad night (say, an outside service down) from using every attempt.
MIN_RETRY_INTERVAL = timedelta(hours=12)


@dataclass(frozen=True)
class PendingMeasurement:
    candidate: CorridorCandidate
    measurement_id: int
    created_at: datetime
    reason: str
    attempts: int = 0  # failed classifications so far
    last_attempt_at: datetime | None = None  # when the latest one failed


def load_pending(path: Path | None = None) -> list[PendingMeasurement]:
    path = path or DEFAULT_PENDING_PATH
    if not path.exists():
        return []
    return [
        PendingMeasurement(
            candidate=CorridorCandidate(**entry["candidate"]),
            measurement_id=entry["measurement_id"],
            created_at=datetime.fromisoformat(entry["created_at"]),
            reason=entry["reason"],
            attempts=entry.get("attempts", 0),
            last_attempt_at=(
                datetime.fromisoformat(entry["last_attempt_at"]) if entry.get("last_attempt_at") else None
            ),
        )
        for entry in json.loads(path.read_text()).get("pending", [])
    ]


def _save(entries: list[PendingMeasurement], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pending": [
            {
                "measurement_id": e.measurement_id,
                "created_at": e.created_at.isoformat(),
                "reason": e.reason,
                "attempts": e.attempts,
                "last_attempt_at": e.last_attempt_at.isoformat() if e.last_attempt_at else None,
                "candidate": asdict(e.candidate),
            }
            for e in entries
        ]
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")


def add_pending(
    candidate: CorridorCandidate,
    measurement_id: int,
    reason: str,
    created_at: datetime | None = None,
    path: Path | None = None,
    attempts: int = 0,
    last_attempt_at: datetime | None = None,
) -> None:
    """Park a measurement. Callers running concurrently must hold their write lock."""
    path = path or DEFAULT_PENDING_PATH
    entries = [e for e in load_pending(path) if e.measurement_id != measurement_id]
    entries.append(
        PendingMeasurement(
            candidate, measurement_id, created_at or datetime.now(timezone.utc), reason, attempts, last_attempt_at
        )
    )
    _save(entries, path)
    logger.warning(
        "AS%d -> AS%d: measurement %d parked (%s); collecting on a later run, up to %dh",
        candidate.source_asn, candidate.target_asn, measurement_id, reason, MAX_AGE // timedelta(hours=1),
    )


def pending_pairs(path: Path | None = None) -> set[tuple[int, int]]:
    """(source_asn, target_asn) pairs with a measurement still out."""
    return {(e.candidate.source_asn, e.candidate.target_asn) for e in load_pending(path)}


def collect_ready(path: Path | None = None) -> list[PendingMeasurement]:
    """Fetch every parked measurement; return the ones ready to classify.

    Ready means Atlas has finished it (results, if any, are persisted to
    the Atlas cache here); one that finished with none goes back to
    `classify_corridor`'s own zero-probe escalation. A measurement still
    running isn't ready even with results in: its other probes may not have
    reported yet (224431120, 2026-10-19, was collected 13s after parking
    and filed inconclusive from a partial set). One-offs stop about 5-6
    minutes after creation, so this costs at most a batch. Past `MAX_AGE`,
    a running measurement is classified on whatever results it has, or
    dropped if it has none. Ready entries leave the file here; a
    caller whose classification of one fails re-parks it with `attempts + 1`
    (`auto_classify._classify_collected`). A re-parked entry is retried from
    the cache no sooner than `MIN_RETRY_INTERVAL` after its last failure,
    whatever its age, and is dropped after `MAX_CLASSIFY_ATTEMPTS` failures. Call only while no batch worker
    is running: it rewrites the file without a lock.
    """
    path = path or DEFAULT_PENDING_PATH
    if not path.exists():
        return []
    now = datetime.now(timezone.utc)
    ready: list[PendingMeasurement] = []
    keep: list[PendingMeasurement] = []
    for entry in load_pending(path):
        mid, cand = entry.measurement_id, entry.candidate
        if entry.attempts >= MAX_CLASSIFY_ATTEMPTS:
            logger.warning(
                "AS%d -> AS%d: parked measurement %d failed classification %d times (%s); "
                "dropping it, corridor left untested for a fresh test",
                cand.source_asn, cand.target_asn, mid, entry.attempts, entry.reason,
            )
            continue
        if entry.attempts:
            # Its results were fetched and cached when it was first collected
            # or fired, so retry from the cache: no fetch, no age limit.
            if entry.last_attempt_at and now - entry.last_attempt_at < MIN_RETRY_INTERVAL:
                keep.append(entry)
            else:
                ready.append(entry)
            continue
        try:
            status = fetch_measurement_status(mid)
            results = fetch_raw_results(mid)
        except requests.RequestException as exc:
            status, results = f"unreachable ({exc})", []
        expired = now - entry.created_at > MAX_AGE
        if status in _TERMINAL_STATUSES or (results and expired):
            if results:
                persist_results(mid, results)
            if status not in _TERMINAL_STATUSES:
                logger.warning(
                    "AS%d -> AS%d: parked measurement %d still %s after %s; classifying the %d result(s) in",
                    cand.source_asn, cand.target_asn, mid, status, now - entry.created_at, len(results),
                )
            logger.info("AS%d -> AS%d: collected parked measurement %d (%s)", cand.source_asn, cand.target_asn, mid, status)
            ready.append(entry)
        elif expired:
            logger.warning(
                "AS%d -> AS%d: parked measurement %d still has no results after %s (%s); "
                "dropping it, corridor left untested for a fresh test",
                cand.source_asn, cand.target_asn, mid, now - entry.created_at, status,
            )
        else:
            keep.append(entry)
    _save(keep, path)
    return ready
