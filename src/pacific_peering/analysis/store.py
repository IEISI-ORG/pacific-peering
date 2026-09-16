"""SQLite-backed findings store -- replaces the hand-written-prose dataclass
files (`confirmed_detours.py`, `confirmed_local_transit.py`,
`candidate_peering.py`) as the project's source of truth for filed findings.

Why this exists: through the first ~250 findings, every corridor was
classified and written up by an LLM reading raw traceroute/RIS data and
hand-crafting a dataclass entry with narrative prose. That doesn't scale --
it's slow, costly, and (as this project's own `task_plan.md` documents
several times) error-prone in exactly the mechanical ways a script doesn't
get wrong: measurement-ID transcription, corroboration counting, `target=`
kwargs silently defaulting. The project owner's explicit direction: move
classification and filing into deterministic `uv run` scripts, with an LLM
(or a human) only in the loop for genuine escalations -- a routing loop at
an address never seen before, a RIS neighbor-list check that resolves
nothing, anything the classifier's own rules can't confidently resolve.

Two-layer storage, mirroring how this project already treats
`report.txt`/`report.html`/`corridor_backlog.md` as regenerated artifacts:

- `data/analysis/findings.db` (gitignored, per `data/*` in `.gitignore`) is
  the live SQLite database -- what `auto_classify.py` reads and writes
  directly, fast structured queries instead of grepping Python source.
- `findings_export.jsonl` (repo root, committed, one finding per line) is
  the actual git-tracked source of truth -- regenerated from the database
  before every commit, the same way the other report artifacts are. This is
  what makes `git diff`/`git log` still show readable, line-by-line changes
  to findings even though the working store is a binary SQLite file that
  never itself gets committed. `import_jsonl()` rebuilds the database from
  this file on a fresh clone or if the local `.db` is ever deleted.

Schema. A single logical model covers all three of the legacy shapes
(`ConfirmedDetour`, `ConfirmedLocalTransit`, `CandidatePeering`), because on
inspection they were never three structurally different things -- each is
"some adjacency (upstream ASN <-> target ASN), corroborated by one or more
traceroutes from various vantage points," differing only in presentation
convention (`ConfirmedDetour` gave each source economy its own top-level
entry; `ConfirmedLocalTransit`/`CandidatePeering` gave the adjacency one
entry and appended corroborations to its note as prose). Here that's one
`findings` row (the adjacency + its classification) with N `corroborations`
rows (one per traceroute that touched it) -- corroboration count is a
`COUNT(*)`, not something parsed back out of hand-written English.

Legacy migration note: every pre-migration finding's full historical note
(often a multi-corroboration narrative built up over many tranches) is
preserved verbatim in `findings.legacy_note` rather than being parsed apart
into synthetic corroboration rows -- prose isn't structured data, and
guessing at where one corroboration's description ends and the next begins
risks silently corrupting real research history. Migrated findings get
exactly one corroboration row (from their own `measurement_id`/
`ris_observation_count`/source fields) so counts and queries stay
consistent; the rich narrative lives in `legacy_note` and renders as-is.
Every corroboration recorded *after* the migration is fully structured
(chain, per-probe RIS agreement, loop status) with no free-text narrative
required.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB_PATH = Path("data/analysis/findings.db")
DEFAULT_EXPORT_PATH = Path("findings_export.jsonl")

# The three legacy shapes, now just a classification on one unified model.
KIND_CONFIRMED_DETOUR = "confirmed_detour"
KIND_CONFIRMED_LOCAL_TRANSIT = "confirmed_local_transit"
KIND_CANDIDATE_PEERING = "candidate_peering"
VALID_KINDS = (KIND_CONFIRMED_DETOUR, KIND_CONFIRMED_LOCAL_TRANSIT, KIND_CANDIDATE_PEERING)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK(kind IN ('confirmed_detour', 'confirmed_local_transit', 'candidate_peering')),
    -- The adjacency itself. For confirmed_detour, source_cc/source_asn is
    -- the traceroute's own source economy (each source economy is its own
    -- finding row, matching the legacy "new entry per source" convention).
    -- For confirmed_local_transit/candidate_peering, source_* is the
    -- provider/upstream side of the adjacency -- the thing being reached,
    -- not the vantage point (which lives per-corroboration instead).
    -- source_asn is nullable: the legacy ConfirmedDetour shape only ever
    -- recorded the source *economy*, never a literal source ASN, so
    -- migrated detour findings honestly carry NULL there rather than a
    -- guessed value -- every finding created going forward always has it.
    source_cc TEXT NOT NULL,
    source_asn INTEGER,
    source_name TEXT,
    target_cc TEXT NOT NULL,
    target_asn INTEGER NOT NULL,
    target_name TEXT,
    detour_ix_name TEXT,          -- confirmed_detour only
    detour_hub TEXT,               -- confirmed_detour only
    probe_agreement TEXT,          -- candidate_peering only, e.g. "3/3 probes"
    legacy_note TEXT,              -- verbatim pre-migration narrative, if any
    created_at TEXT NOT NULL
);

-- Identity is economy-scoped for confirmed_detour (it never records a
-- literal source ASN -- see the source_asn comment above) but ASN-scoped
-- for the other two kinds, whose source_* is the upstream/provider ASN
-- itself, not a vantage-point economy. A single UNIQUE(kind, source_cc,
-- target_asn) previously covered all three kinds, which is wrong for the
-- ASN-scoped pair: find_existing() already looks up by source_asn, so two
-- distinct upstream ASNs sharing a country and target would pass that
-- lookup and then hit the constraint on insert (an uncaught
-- sqlite3.IntegrityError, silently swallowed by run_batch()'s per-corridor
-- exception handler, permanently stranding that corridor untested). Two
-- partial unique indexes, one per identity scheme, replace it.
CREATE UNIQUE INDEX IF NOT EXISTS idx_findings_identity_detour
    ON findings(kind, source_cc, target_asn) WHERE kind = 'confirmed_detour';
CREATE UNIQUE INDEX IF NOT EXISTS idx_findings_identity_asn
    ON findings(kind, source_asn, target_asn) WHERE kind != 'confirmed_detour';

CREATE TABLE IF NOT EXISTS corroborations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id INTEGER NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    measurement_id INTEGER NOT NULL,
    vantage_point_cc TEXT NOT NULL,
    vantage_point_asn INTEGER,
    chain TEXT,                    -- e.g. "AS55885 -> AS9471 -> AS6939 -> AS7131"
    ris_observation_count INTEGER,
    ris_agrees INTEGER,            -- 0/1/NULL (unknown)
    has_loop INTEGER NOT NULL DEFAULT 0,
    loop_note TEXT,
    crosses_ixp TEXT,
    note_extra TEXT,               -- freeform: reserved for a genuine escalation's resolution notes
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_findings_target ON findings(target_asn);
CREATE INDEX IF NOT EXISTS idx_findings_source ON findings(source_asn);
CREATE INDEX IF NOT EXISTS idx_corrob_finding ON corroborations(finding_id);
"""


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open (creating if needed) the findings database, schema applied, FKs on."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    return conn


@dataclass(frozen=True)
class Finding:
    id: int
    kind: str
    source_cc: str
    source_asn: int
    source_name: str | None
    target_cc: str
    target_asn: int
    target_name: str | None
    detour_ix_name: str | None
    detour_hub: str | None
    probe_agreement: str | None
    legacy_note: str | None
    created_at: str
    corroboration_count: int = 0


@dataclass(frozen=True)
class Corroboration:
    id: int
    finding_id: int
    measurement_id: int
    vantage_point_cc: str
    vantage_point_asn: int | None
    chain: str | None
    ris_observation_count: int | None
    ris_agrees: bool | None
    has_loop: bool
    loop_note: str | None
    crosses_ixp: str | None
    note_extra: str | None
    created_at: str


def find_existing(
    conn: sqlite3.Connection, kind: str, source_asn: int, target_asn: int
) -> Finding | None:
    """Look up an existing finding for this exact (kind, source_asn, target_asn).

    Callers doing sibling-ASN resolution (e.g. a traceroute meant for one
    ASN lands on its sibling) should also try the resolved sibling's ASN
    directly -- this only matches the literal pair given.
    """
    row = conn.execute(
        "SELECT f.*, (SELECT COUNT(*) FROM corroborations c WHERE c.finding_id = f.id) AS corroboration_count "
        "FROM findings f WHERE f.kind = ? AND f.source_asn = ? AND f.target_asn = ?",
        (kind, source_asn, target_asn),
    ).fetchone()
    return _row_to_finding(row) if row else None


def find_existing_detour(conn: sqlite3.Connection, source_cc: str, target_asn: int) -> Finding | None:
    """Look up an existing confirmed_detour finding by source *economy* (not
    ASN) -- the legacy ConfirmedDetour convention never tracked a literal
    source ASN, and `find_existing()` requires one, so detour lookups need
    this instead."""
    row = conn.execute(
        "SELECT f.*, (SELECT COUNT(*) FROM corroborations c WHERE c.finding_id = f.id) AS corroboration_count "
        "FROM findings f WHERE f.kind = ? AND f.source_cc = ? AND f.target_asn = ?",
        (KIND_CONFIRMED_DETOUR, source_cc, target_asn),
    ).fetchone()
    return _row_to_finding(row) if row else None


def find_by_target(conn: sqlite3.Connection, target_asn: int) -> list[Finding]:
    """All findings (any kind, any source) touching this target ASN -- the
    query that replaces grepping `target_asn=N,` across three .py files."""
    rows = conn.execute(
        "SELECT f.*, (SELECT COUNT(*) FROM corroborations c WHERE c.finding_id = f.id) AS corroboration_count "
        "FROM findings f WHERE f.target_asn = ? ORDER BY f.kind, f.source_cc",
        (target_asn,),
    ).fetchall()
    return [_row_to_finding(r) for r in rows]


def _row_to_finding(row: sqlite3.Row) -> Finding:
    return Finding(
        id=row["id"],
        kind=row["kind"],
        source_cc=row["source_cc"],
        source_asn=row["source_asn"],
        source_name=row["source_name"],
        target_cc=row["target_cc"],
        target_asn=row["target_asn"],
        target_name=row["target_name"],
        detour_ix_name=row["detour_ix_name"],
        detour_hub=row["detour_hub"],
        probe_agreement=row["probe_agreement"],
        legacy_note=row["legacy_note"],
        created_at=row["created_at"],
        corroboration_count=row["corroboration_count"],
    )


def create_finding(
    conn: sqlite3.Connection,
    *,
    kind: str,
    source_cc: str,
    source_asn: int,
    target_cc: str,
    target_asn: int,
    source_name: str | None = None,
    target_name: str | None = None,
    detour_ix_name: str | None = None,
    detour_hub: str | None = None,
    probe_agreement: str | None = None,
    legacy_note: str | None = None,
    created_at: str | None = None,
) -> int:
    if kind not in VALID_KINDS:
        raise ValueError(f"invalid kind: {kind!r}, must be one of {VALID_KINDS}")
    cur = conn.execute(
        "INSERT INTO findings (kind, source_cc, source_asn, source_name, target_cc, "
        "target_asn, target_name, detour_ix_name, detour_hub, probe_agreement, "
        "legacy_note, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            kind, source_cc, source_asn, source_name, target_cc, target_asn,
            target_name, detour_ix_name, detour_hub, probe_agreement,
            legacy_note, created_at or datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return cur.lastrowid


def add_corroboration(
    conn: sqlite3.Connection,
    *,
    finding_id: int,
    measurement_id: int,
    vantage_point_cc: str,
    vantage_point_asn: int | None = None,
    chain: str | None = None,
    ris_observation_count: int | None = None,
    ris_agrees: bool | None = None,
    has_loop: bool = False,
    loop_note: str | None = None,
    crosses_ixp: str | None = None,
    note_extra: str | None = None,
    created_at: str | None = None,
) -> int:
    cur = conn.execute(
        "INSERT INTO corroborations (finding_id, measurement_id, vantage_point_cc, "
        "vantage_point_asn, chain, ris_observation_count, ris_agrees, has_loop, "
        "loop_note, crosses_ixp, note_extra, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            finding_id, measurement_id, vantage_point_cc, vantage_point_asn, chain,
            ris_observation_count, None if ris_agrees is None else int(ris_agrees),
            int(has_loop), loop_note, crosses_ixp, note_extra,
            created_at or datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_corroborations(conn: sqlite3.Connection, finding_id: int) -> list[Corroboration]:
    rows = conn.execute(
        "SELECT * FROM corroborations WHERE finding_id = ? ORDER BY id", (finding_id,)
    ).fetchall()
    return [
        Corroboration(
            id=r["id"], finding_id=r["finding_id"], measurement_id=r["measurement_id"],
            vantage_point_cc=r["vantage_point_cc"], vantage_point_asn=r["vantage_point_asn"],
            chain=r["chain"], ris_observation_count=r["ris_observation_count"],
            ris_agrees=None if r["ris_agrees"] is None else bool(r["ris_agrees"]),
            has_loop=bool(r["has_loop"]), loop_note=r["loop_note"],
            crosses_ixp=r["crosses_ixp"], note_extra=r["note_extra"], created_at=r["created_at"],
        )
        for r in rows
    ]


def all_findings(conn: sqlite3.Connection) -> list[Finding]:
    rows = conn.execute(
        "SELECT f.*, (SELECT COUNT(*) FROM corroborations c WHERE c.finding_id = f.id) AS corroboration_count "
        "FROM findings f ORDER BY f.kind, f.target_asn, f.source_cc"
    ).fetchall()
    return [_row_to_finding(r) for r in rows]


def export_jsonl(conn: sqlite3.Connection, path: Path = DEFAULT_EXPORT_PATH) -> int:
    """Write every finding + its corroborations as one JSON object per line,
    sorted for a stable diff (unrelated rows shouldn't reorder on export).
    This file, not the .db, is what gets committed."""
    findings = all_findings(conn)
    lines = []
    for f in findings:
        corrobs = get_corroborations(conn, f.id)
        lines.append(
            json.dumps(
                {
                    "kind": f.kind,
                    "source_cc": f.source_cc,
                    "source_asn": f.source_asn,
                    "source_name": f.source_name,
                    "target_cc": f.target_cc,
                    "target_asn": f.target_asn,
                    "target_name": f.target_name,
                    "detour_ix_name": f.detour_ix_name,
                    "detour_hub": f.detour_hub,
                    "probe_agreement": f.probe_agreement,
                    "legacy_note": f.legacy_note,
                    "created_at": f.created_at,
                    "corroborations": [
                        {
                            "measurement_id": c.measurement_id,
                            "vantage_point_cc": c.vantage_point_cc,
                            "vantage_point_asn": c.vantage_point_asn,
                            "chain": c.chain,
                            "ris_observation_count": c.ris_observation_count,
                            "ris_agrees": c.ris_agrees,
                            "has_loop": c.has_loop,
                            "loop_note": c.loop_note,
                            "crosses_ixp": c.crosses_ixp,
                            "note_extra": c.note_extra,
                            "created_at": c.created_at,
                        }
                        for c in corrobs
                    ],
                },
                sort_keys=True,
            )
        )
    path.write_text("\n".join(lines) + ("\n" if lines else ""))
    return len(lines)


def import_jsonl(path: Path = DEFAULT_EXPORT_PATH, db_path: Path = DEFAULT_DB_PATH) -> int:
    """Rebuild the database from the committed export -- for a fresh clone,
    or recovery if the local .db is ever deleted. Wipes and reloads rather
    than merging, since the export is the source of truth."""
    if db_path.exists():
        db_path.unlink()
    conn = connect(db_path)
    n = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        finding_id = create_finding(
            conn,
            kind=obj["kind"],
            source_cc=obj["source_cc"],
            source_asn=obj["source_asn"],
            source_name=obj.get("source_name"),
            target_cc=obj["target_cc"],
            target_asn=obj["target_asn"],
            target_name=obj.get("target_name"),
            detour_ix_name=obj.get("detour_ix_name"),
            detour_hub=obj.get("detour_hub"),
            probe_agreement=obj.get("probe_agreement"),
            legacy_note=obj.get("legacy_note"),
            created_at=obj.get("created_at"),
        )
        for c in obj.get("corroborations", []):
            add_corroboration(
                conn,
                finding_id=finding_id,
                measurement_id=c["measurement_id"],
                vantage_point_cc=c["vantage_point_cc"],
                vantage_point_asn=c.get("vantage_point_asn"),
                chain=c.get("chain"),
                ris_observation_count=c.get("ris_observation_count"),
                ris_agrees=c.get("ris_agrees"),
                has_loop=c.get("has_loop", False),
                loop_note=c.get("loop_note"),
                crosses_ixp=c.get("crosses_ixp"),
                note_extra=c.get("note_extra"),
                created_at=c.get("created_at"),
            )
        n += 1
    conn.close()
    return n


def _note_for(finding: Finding, corrobs: list[Corroboration]) -> str:
    """The `note` text for a finding: verbatim legacy prose if this finding
    predates the store, else a short generated summary from its structured
    corroborations. Every finding in the database today has a legacy_note
    (the whole ~250-entry corpus was migrated, not re-authored) -- the
    generated branch exists for findings `auto_classify.py` creates going
    forward with no narrative required."""
    if finding.legacy_note:
        return finding.legacy_note
    if not corrobs:
        return "(no corroborations recorded)"
    lines = []
    for c in corrobs:
        bits = [f"measurement {c.measurement_id} (from {c.vantage_point_cc})"]
        if c.chain:
            bits.append(f"chain: {c.chain}")
        if c.ris_observation_count is not None:
            bits.append(f"RIS count {c.ris_observation_count}")
        bits.append("RIS agrees" if c.ris_agrees else "RIS disagrees")
        if c.has_loop:
            bits.append(f"loop noted ({c.loop_note or 'unspecified location'})")
        lines.append("; ".join(bits) + ".")
    return " ".join(lines)


def load_confirmed_detours(conn: sqlite3.Connection):
    """Reconstruct `ConfirmedDetour` instances from the database -- same
    type, same field shape, `reports/data.py` and every other consumer of
    the legacy module-level tuple keeps working unchanged."""
    from pacific_peering.analysis.confirmed_detours import ConfirmedDetour

    out = []
    for f in all_findings(conn):
        if f.kind != KIND_CONFIRMED_DETOUR:
            continue
        corrobs = get_corroborations(conn, f.id)
        first = corrobs[0] if corrobs else None
        out.append(
            ConfirmedDetour(
                source_cc=f.source_cc,
                target_cc=f.target_cc,
                target_asn=f.target_asn,
                detour_ix_name=f.detour_ix_name or "",
                detour_hub=f.detour_hub or "",
                measurement_id=first.measurement_id if first else 0,
                ris_observation_count=(first.ris_observation_count if first else None) or 0,
                note=_note_for(f, corrobs),
            )
        )
    return tuple(out)


def load_confirmed_local_transit(conn: sqlite3.Connection):
    from pacific_peering.analysis.confirmed_local_transit import ConfirmedLocalTransit

    out = []
    for f in all_findings(conn):
        if f.kind != KIND_CONFIRMED_LOCAL_TRANSIT:
            continue
        corrobs = get_corroborations(conn, f.id)
        first = corrobs[0] if corrobs else None
        out.append(
            ConfirmedLocalTransit(
                provider_cc=f.source_cc,
                provider_asn=f.source_asn or 0,
                provider_name=f.source_name or "",
                customer_cc=f.target_cc,
                customer_asn=f.target_asn,
                customer_name=f.target_name or "",
                measurement_id=first.measurement_id if first else 0,
                vantage_point_cc=first.vantage_point_cc if first else f.source_cc,
                ris_observation_count=(first.ris_observation_count if first else None) or 0,
                note=_note_for(f, corrobs),
            )
        )
    return tuple(out)


def load_candidate_peering(conn: sqlite3.Connection):
    from pacific_peering.analysis.candidate_peering import CandidatePeering

    out = []
    for f in all_findings(conn):
        if f.kind != KIND_CANDIDATE_PEERING:
            continue
        corrobs = get_corroborations(conn, f.id)
        first = corrobs[0] if corrobs else None
        out.append(
            CandidatePeering(
                upstream_cc=f.source_cc,
                upstream_asn=f.source_asn or 0,
                upstream_name=f.source_name or "",
                target_cc=f.target_cc,
                target_asn=f.target_asn,
                target_name=f.target_name or "",
                measurement_id=first.measurement_id if first else 0,
                vantage_point_cc=first.vantage_point_cc if first else f.source_cc,
                probe_agreement=f.probe_agreement or "",
                note=_note_for(f, corrobs),
            )
        )
    return tuple(out)


def main() -> None:
    """`uv run pacific-peering-findings-export` -- regenerate the committed
    JSONL export from the current database. Run this before every commit
    that touched findings, the same way report.txt/report.html are
    regenerated -- it's the file git actually tracks."""
    conn = connect()
    n = export_jsonl(conn)
    conn.close()
    print(f"Exported {n} findings to {DEFAULT_EXPORT_PATH}")


if __name__ == "__main__":
    main()
