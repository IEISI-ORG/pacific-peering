"""One-time migration: load the ~250 hand-written-prose findings from
`confirmed_detours.py`, `confirmed_local_transit.py`, and `candidate_peering.py`
into the SQLite store (`store.py`), preserving every note verbatim in
`legacy_note`. See `store.py`'s module docstring for the full rationale.

Safe to re-run: wipes and reloads the findings/corroborations tables (not
the whole database) each time, so it's idempotent against re-running after
a code change, but NOT safe to run after `auto_classify.py` has started
writing genuinely new (non-legacy) findings into the same tables -- this
would discard them. Intended as a single cutover step.
"""

from __future__ import annotations

from dataclasses import asdict

from pacific_peering.analysis import store
from pacific_peering.analysis.candidate_peering import CANDIDATE_PEERING
from pacific_peering.analysis.confirmed_detours import CONFIRMED_DETOURS
from pacific_peering.analysis.confirmed_local_transit import CONFIRMED_LOCAL_TRANSIT


def migrate() -> dict[str, int]:
    conn = store.connect()
    # Wipe prior migration output (not the whole file) so this is safe to
    # re-run while iterating on the migration logic itself.
    conn.execute("DELETE FROM corroborations")
    conn.execute("DELETE FROM findings")
    conn.commit()

    counts = {"confirmed_detour": 0, "confirmed_local_transit": 0, "candidate_peering": 0}

    # The legacy "new entry per source economy" convention occasionally
    # collided with itself: the same source economy, via a genuinely
    # different literal measurement (e.g. a direct test plus a later
    # sibling-ASN-substitution test), sometimes produced two separate
    # dataclass instances for the same (source_cc, target_asn) pair. Under
    # the new normalized model that's correctly one finding with two
    # corroborations, not two findings -- merge rather than error.
    detour_finding_by_key: dict[tuple[str, int], int] = {}
    for d in CONFIRMED_DETOURS:
        row = asdict(d)
        key = (row["source_cc"], row["target_asn"])
        if key in detour_finding_by_key:
            finding_id = detour_finding_by_key[key]
            existing = conn.execute(
                "SELECT legacy_note FROM findings WHERE id = ?", (finding_id,)
            ).fetchone()
            merged_note = f"{existing['legacy_note']}\n\n---\n\n{row['note']}"
            conn.execute(
                "UPDATE findings SET legacy_note = ? WHERE id = ?", (merged_note, finding_id)
            )
        else:
            finding_id = store.create_finding(
                conn,
                kind=store.KIND_CONFIRMED_DETOUR,
                source_cc=row["source_cc"],
                source_asn=None,  # legacy shape never tracked this at the ASN level
                target_cc=row["target_cc"],
                target_asn=row["target_asn"],
                detour_ix_name=row["detour_ix_name"],
                detour_hub=row["detour_hub"],
                legacy_note=row["note"],
            )
            detour_finding_by_key[key] = finding_id
        store.add_corroboration(
            conn,
            finding_id=finding_id,
            measurement_id=row["measurement_id"],
            vantage_point_cc=row["source_cc"],
            ris_observation_count=row["ris_observation_count"],
            ris_agrees=True,  # every legacy ConfirmedDetour entry is, by definition, RIS-agreeing
        )
        counts["confirmed_detour"] += 1

    for t in CONFIRMED_LOCAL_TRANSIT:
        row = asdict(t)
        finding_id = store.create_finding(
            conn,
            kind=store.KIND_CONFIRMED_LOCAL_TRANSIT,
            source_cc=row["provider_cc"],
            source_asn=row["provider_asn"],
            source_name=row["provider_name"],
            target_cc=row["customer_cc"],
            target_asn=row["customer_asn"],
            target_name=row["customer_name"],
            legacy_note=row["note"],
        )
        store.add_corroboration(
            conn,
            finding_id=finding_id,
            measurement_id=row["measurement_id"],
            vantage_point_cc=row["vantage_point_cc"],
            ris_observation_count=row["ris_observation_count"],
            ris_agrees=True,
        )
        counts["confirmed_local_transit"] += 1

    # Same collision shape as ConfirmedDetour above: many CandidatePeering
    # entries are repeated corroborations of the identical sibling-ASN
    # substitution (e.g. GU->AS38875, tested 8 separate times), filed as 8
    # separate legacy dataclass instances instead of one finding with 8
    # corroborations. Merge on the same basis.
    candidate_finding_by_key: dict[tuple[str, int], int] = {}
    for c in CANDIDATE_PEERING:
        row = asdict(c)
        key = (row["upstream_cc"], row["target_asn"])
        if key in candidate_finding_by_key:
            finding_id = candidate_finding_by_key[key]
            existing = conn.execute(
                "SELECT legacy_note FROM findings WHERE id = ?", (finding_id,)
            ).fetchone()
            merged_note = f"{existing['legacy_note']}\n\n---\n\n{row['note']}"
            conn.execute(
                "UPDATE findings SET legacy_note = ? WHERE id = ?", (merged_note, finding_id)
            )
        else:
            finding_id = store.create_finding(
                conn,
                kind=store.KIND_CANDIDATE_PEERING,
                source_cc=row["upstream_cc"],
                source_asn=row["upstream_asn"],
                source_name=row["upstream_name"],
                target_cc=row["target_cc"],
                target_asn=row["target_asn"],
                target_name=row["target_name"],
                probe_agreement=row["probe_agreement"],
                legacy_note=row["note"],
            )
            candidate_finding_by_key[key] = finding_id
        store.add_corroboration(
            conn,
            finding_id=finding_id,
            measurement_id=row["measurement_id"],
            vantage_point_cc=row["vantage_point_cc"],
            ris_agrees=False,  # every legacy CandidatePeering entry is, by definition, RIS-disagreeing
        )
        counts["candidate_peering"] += 1

    conn.close()
    return counts


def main() -> None:
    counts = migrate()
    total = sum(counts.values())
    print(f"Migrated {total} legacy findings into {store.DEFAULT_DB_PATH}:")
    for kind, n in counts.items():
        print(f"  {kind}: {n}")


if __name__ == "__main__":
    main()
