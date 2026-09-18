"""Phase 1c: recurring pipeline orchestration.

Re-runs discovery, RIS/IXP/facility data, the IXP LAN subnet registry,
the IRR AS-SET leads sweep, and the ASN probe registry in sequence, and
writes a small versioned manifest recording what happened.

Deliberately scoped: this does NOT fire new RIPE Atlas measurements
automatically. Atlas measurements cost real account credits and need a
human choosing which AS pairs matter — an automatic recurring job
silently spending credits on unreviewed pairs is a materially different,
riskier decision than re-running free public-API pulls (RIPEstat,
PeeringDB, APNIC stats all need no auth), and isn't made here without
explicit sign-off. Atlas campaigns stay a deliberate, manually-triggered
activity (see `atlas.smoketest`). The ASN probe registry step is a
read-only Atlas API lookup (which ASNs have a connected probe), not a
measurement — no credits involved either.

Safe to re-run on a schedule: every step it calls is already idempotent
— registries rebuild in place, and IXP LAN classifications are
preserved across rebuilds, never reset (see `ixp_lan_registry`).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pacific_peering.analysis.fishbowl import build_fishbowl
from pacific_peering.analysis.irr_leads import build_irr_leads
from pacific_peering.analysis.ixp_lan_registry import build_ixp_lan_registry
from pacific_peering.atlas.asn_probes import build_asn_probe_registry
from pacific_peering.atlas.probe_geo_audit import audit_tracked_probes, write_quarantine
from pacific_peering.discovery.registry import build_registry

logger = logging.getLogger(__name__)

DEFAULT_RUNS_DIR = Path("outputs/runs")


def _summarize(step_name: str, result: Any) -> dict:
    """Small, JSON-safe summary per step — not the full result (too large to keep per-run)."""
    if step_name == "discovery":
        return {
            "economies": len(result),
            "total_asns": sum(len(entry["asns"]) for entry in result.values()),
        }
    if step_name == "fishbowl":
        return {
            "asns": len(result),
            "with_neighbors": sum(1 for v in result.values() if v["neighbors"]),
            "on_peeringdb": sum(1 for v in result.values() if v["on_peeringdb"]),
            "with_ixp": sum(1 for v in result.values() if v["ixp_memberships"]),
            "with_facility": sum(1 for v in result.values() if v["facility_presence"]),
        }
    if step_name == "ixp_lan_registry":
        return {
            "exchanges": len(result),
            "in_fishbowl": sum(1 for e in result.values() if e.in_fishbowl is True),
            "out_of_fishbowl": sum(1 for e in result.values() if e.in_fishbowl is False),
            "tba": sum(1 for e in result.values() if e.in_fishbowl == "TBA"),
        }
    if step_name == "irr_leads":
        return {
            "asns_with_declared_as_set": len(result),
            "resolved_to_trusted_data": sum(
                1
                for lead in result.values()
                if any(r.asns or r.nested_as_sets for r in lead.resolved)
            ),
        }
    if step_name == "asn_probe_registry":
        return {
            "asns_with_connected_probe": len(result),
            "total_connected_probes": sum(len(ids) for ids in result.values()),
        }
    if step_name == "probe_geo_audit":
        return {"probes_quarantined": len(result)}
    return {}


def _run_probe_geo_audit() -> dict:
    """Audit step wrapper: depends on the freshly-rebuilt asn_probe_registry above."""
    return write_quarantine(audit_tracked_probes())


def run_pipeline(runs_dir: Path = DEFAULT_RUNS_DIR) -> dict:
    """Run the recurring, free-API-only part of the pipeline and record a manifest.

    Steps: ASN registry -> fish bowl (RIS + IXP membership + facility
    presence) -> IXP LAN subnet registry -> IRR AS-SET leads -> ASN
    probe registry -> probe geo-audit. Each step's failure is caught and
    recorded rather than aborting the whole run, so a transient upstream
    API issue in one step doesn't prevent the others from completing.
    The final step re-checks every connected probe's live Atlas location
    against this project's ASN registry (see `atlas.probe_geo_audit`) --
    read-only, no credits, but only meaningful once asn_probe_registry
    is current, hence running last.

    Args:
        runs_dir: Directory to write this run's timestamped manifest under.

    Returns:
        The manifest dict (also written to `<runs_dir>/<timestamp>/manifest.json`).
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    run_dir = runs_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict = {"timestamp": timestamp, "steps": {}}
    steps: list[tuple[str, Callable[[], Any]]] = [
        ("discovery", build_registry),
        ("fishbowl", build_fishbowl),
        ("ixp_lan_registry", build_ixp_lan_registry),
        ("irr_leads", build_irr_leads),
        ("asn_probe_registry", build_asn_probe_registry),
        ("probe_geo_audit", _run_probe_geo_audit),
    ]

    for name, step in steps:
        logger.info("Running step: %s", name)
        try:
            result = step()
            manifest["steps"][name] = {"status": "ok", "summary": _summarize(name, result)}
        except Exception as exc:  # noqa: BLE001 - one step's failure must not sink the whole run
            logger.exception("Step %s failed", name)
            manifest["steps"][name] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}

    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    logger.info("Wrote run manifest to %s", manifest_path)
    return manifest


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    manifest = run_pipeline()
    for name, step_result in manifest["steps"].items():
        logger.info("%s: %s", name, step_result)


if __name__ == "__main__":
    main()
