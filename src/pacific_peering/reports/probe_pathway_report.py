"""Text report, one purpose: which specific RIPE Atlas probe has actually
contributed to which corridor -- a probe-level audit trail, complementing
`probe_gap_report.py`'s economy-level "where do we need a new probe next"
question and the main report's `pathway_coverage` table's economy-level
probe *counts*. Neither of those says what any one specific probe has
actually been used for.

The findings store's `corroborations` only ever record the source *ASN*
(`vantage_point_asn`), never which of that ASN's one-or-more connected
probes actually fired -- this report gets that missing granularity by
cross-referencing each corroboration's `measurement_id` against the raw
parsed Atlas measurement file (`data/atlas/parsed/<id>.json`), which does
record `probe_id` per probe that returned a result. Every measurement_id
this project's findings currently reference has its raw file on disk
(verified directly, not assumed) -- a probe absent from the resulting
map simply has never yet contributed a corroboration to a filed finding,
which is itself useful to know, not a data gap.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pacific_peering.discovery.registry import DEFAULT_OUTPUT_PATH as ASN_REGISTRY_PATH

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("outputs/reports/probe_pathways.txt")
DEFAULT_PROBE_REGISTRY_PATH = Path("data/atlas/asn_probe_registry.json")
DEFAULT_PARSED_DIR = Path("data/atlas/parsed")
DEFAULT_FINDINGS_PATH = Path("findings_export.jsonl")


def _pathway_label(corrob: dict, finding: dict) -> str:
    """Describe one corroboration's real pathway: where the traceroute
    actually originated -> the finding's target.

    Deliberately keyed off the *corroboration's own* `vantage_point_cc`/
    `vantage_point_asn`, not the finding's `source_cc`/`source_asn` --
    those two only coincide for `confirmed_detour` (verified directly:
    198/198 corroborations match). For `confirmed_local_transit`/
    `candidate_peering`, `source_*` names the upstream/provider being
    tested, not where the probe fired from -- a single finding can carry
    corroborations from several different real vantage points (e.g. one
    SISCC<->Solomon-Islands finding corroborated once from FM and once
    from NU). Using the finding-level fields here silently misattributes
    every probe involved in a non-detour finding to the wrong "source"
    economy -- caught by checking a probe whose pathway list looked
    anomalously broad, not a real Atlas anomaly.
    """
    vantage_cc = corrob.get("vantage_point_cc") or "?"
    vantage_asn = corrob.get("vantage_point_asn")
    vantage = f" (AS{vantage_asn})" if vantage_asn else ""
    target_name = f", {finding['target_name']}" if finding.get("target_name") else ""
    return (
        f"{vantage_cc}{vantage} -> "
        f"{finding['target_cc']} (AS{finding['target_asn']}{target_name})"
    )


def build_probe_pathways(
    probe_registry_path: Path = DEFAULT_PROBE_REGISTRY_PATH,
    parsed_dir: Path = DEFAULT_PARSED_DIR,
    findings_path: Path = DEFAULT_FINDINGS_PATH,
) -> dict[int, set[str]]:
    """Map each connected probe ID to the distinct pathways it has actually
    contributed a corroboration to.

    Returns:
        probe_id -> set of pathway labels (e.g. "GU (AS3605) -> PW (AS17893,
        Palau National Communications Corp)"). Every probe in
        `probe_registry_path` appears as a key, with an empty set if it
        has never contributed to a filed finding.
    """
    probe_registry: dict[str, list[int]] = json.loads(probe_registry_path.read_text())
    probe_to_pathways: dict[int, set[str]] = {
        pid: set() for ids in probe_registry.values() for pid in ids
    }

    if not findings_path.exists():
        return probe_to_pathways

    for line in findings_path.read_text().splitlines():
        if not line.strip():
            continue
        finding = json.loads(line)
        for corrob in finding.get("corroborations", []):
            label = _pathway_label(corrob, finding)
            mid = corrob.get("measurement_id")
            if mid is None:
                continue
            parsed_path = parsed_dir / f"{mid}.json"
            if not parsed_path.exists():
                logger.warning(
                    "measurement_id %s (finding %s) has no raw parsed file at %s -- "
                    "can't attribute it to a specific probe",
                    mid,
                    label,
                    parsed_path,
                )
                continue
            for probe_result in json.loads(parsed_path.read_text()):
                pid = probe_result.get("probe_id")
                if pid is None:
                    continue
                probe_to_pathways.setdefault(pid, set()).add(label)

    return probe_to_pathways


def render_probe_pathway_report(
    probe_registry: dict[str, list[int]],
    probe_pathways: dict[int, set[str]],
    asn_economy_label: dict[int, str] | None = None,
) -> str:
    """Render the probe-pathway report as plain text, grouped by economy then ASN."""
    lines: list[str] = []
    lines.append("PACIFIC PEERING -- PROBE-LEVEL PATHWAY AUDIT")
    lines.append(
        "Which specific connected Atlas probe has actually contributed to which "
        "corridor -- not just how many probes an economy has (see the main report's "
        "Pathway Coverage table) or where a new one is most needed (see probe_gaps.txt)."
    )
    lines.append("=" * 78)

    registry_ids = {pid for ids in probe_registry.values() for pid in ids}
    total_probes = len(registry_ids)
    used_probes = sum(1 for pid in registry_ids if probe_pathways.get(pid))
    lines.append("")
    lines.append(
        f"{used_probes} of {total_probes} currently-connected probes have contributed "
        "to at least one filed finding so far."
    )
    lines.append("")

    asn_economy_label = asn_economy_label or {}
    for asn_str in sorted(probe_registry, key=int):
        asn = int(asn_str)
        probe_ids = probe_registry[asn_str]
        economy = f"  {asn_economy_label[asn]}" if asn in asn_economy_label else ""
        lines.append(f"AS{asn}{economy}  ({len(probe_ids)} connected probe(s))")
        for pid in sorted(probe_ids):
            pathways = sorted(probe_pathways.get(pid, set()))
            lines.append(f"  probe {pid}:")
            if not pathways:
                lines.append("    (never contributed to a filed finding yet)")
            for pathway in pathways:
                lines.append(f"    {pathway}")
        lines.append("")

    stale_ids = sorted(set(probe_pathways) - registry_ids)
    if stale_ids:
        lines.append(
            f"PROBES SEEN IN PAST MEASUREMENTS, NO LONGER IN THE CURRENT REGISTRY ({len(stale_ids)})"
        )
        lines.append(
            "Contributed to a filed finding at some point, but the ASN probe registry "
            "(refreshed periodically, reflects current connectivity) no longer lists them "
            "as connected -- flagged rather than silently dropped."
        )
        for pid in stale_ids:
            pathways = sorted(probe_pathways[pid])
            lines.append(f"  probe {pid} ({len(pathways)} pathway(s)):")
            for pathway in pathways:
                lines.append(f"    {pathway}")
        lines.append("")

    lines.append("=" * 78)
    return "\n".join(lines)


def write_probe_pathway_report(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    probe_registry_path: Path = DEFAULT_PROBE_REGISTRY_PATH,
    parsed_dir: Path = DEFAULT_PARSED_DIR,
    findings_path: Path = DEFAULT_FINDINGS_PATH,
    asn_registry_path: Path = ASN_REGISTRY_PATH,
) -> Path:
    """Build the probe-to-pathway map, render it, and write it to disk."""
    probe_registry = json.loads(probe_registry_path.read_text())
    probe_pathways = build_probe_pathways(probe_registry_path, parsed_dir, findings_path)

    asn_economy_label: dict[int, str] = {}
    if asn_registry_path.exists():
        asn_registry = json.loads(asn_registry_path.read_text())
        for cc, entry in asn_registry.items():
            for asn in entry["asns"]:
                asn_economy_label[asn] = f"{entry['name']} ({cc})"

    text = render_probe_pathway_report(probe_registry, probe_pathways, asn_economy_label)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text + "\n")
    logger.info("Wrote probe-pathway report to %s", output_path)
    return output_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    write_probe_pathway_report()


if __name__ == "__main__":
    main()
