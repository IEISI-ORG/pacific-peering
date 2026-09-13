"""Cross-check Atlas traceroutes against RIS-observed neighbors (Validation Rule 1).

Resolves each traceroute hop to an ASN, collapses the result into an
AS-level path, and checks whether the AS immediately upstream of the
target ASN in that path also shows up as a RIS-observed neighbor (Phase
1a's `fishbowl.json`). Per task_plan.md's Validation Rules, an
ASN-to-ASN adjacency only counts as established once RIS and an Atlas
traceroute agree on it — this module is that agreement check, not a
full topology map yet (that needs many more measurements than the one
Phase 1b has produced so far).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from pacific_peering.analysis.fishbowl import DEFAULT_SUMMARY_PATH
from pacific_peering.ris.ripestat import resolve_ip_to_asns

logger = logging.getLogger(__name__)

DEFAULT_ATLAS_PARSED_DIR = Path("data/atlas/parsed")
DEFAULT_TRIANGULATION_DIR = Path("data/analysis/triangulation")


@dataclass(frozen=True)
class HopResolution:
    """One traceroute hop resolved to whichever ASN(s) its address(es) belong to.

    An empty `asns` is itself informative, not a failure — it's the
    signature of an IXP peering-LAN address, which is often not
    announced in global BGP at all (see `resolve_ip_to_asns`).
    """

    hop: int
    addresses: tuple[str, ...]
    asns: tuple[int, ...]


def resolve_traceroute_hops(hops: list[dict]) -> list[HopResolution]:
    """Resolve every hop's responding address(es) to ASN(s).

    Args:
        hops: the `hops` list from one parsed Atlas traceroute record
            (each a dict with "hop" and "addresses").
    """
    resolved: list[HopResolution] = []
    for hop in hops:
        addresses = tuple(hop.get("addresses", []))
        asns: set[int] = set()
        for address in addresses:
            asns.update(resolve_ip_to_asns(address))
        resolved.append(
            HopResolution(hop=hop["hop"], addresses=addresses, asns=tuple(sorted(asns)))
        )
    return resolved


def extract_as_sequence(resolved_hops: list[HopResolution]) -> list[int]:
    """Collapse resolved hops into an ordered AS-level path.

    Unresolved hops (no ASN) are dropped rather than treated as a gap;
    consecutive repeats of the same ASN are collapsed (multiple router
    hops within one AS, or per-packet load-balancing). Hops that resolve
    to more than one ASN (ambiguous) are also dropped rather than guessed.
    """
    sequence: list[int] = []
    for hop in resolved_hops:
        if len(hop.asns) != 1:
            continue
        asn = hop.asns[0]
        if not sequence or sequence[-1] != asn:
            sequence.append(asn)
    return sequence


def check_neighbor_agreement(
    as_sequence: list[int], target_asn: int, fishbowl_path: Path = DEFAULT_SUMMARY_PATH
) -> dict:
    """Check whether the traceroute-observed upstream of `target_asn` is a RIS neighbor too.

    Args:
        as_sequence: Resolved AS-level path from `extract_as_sequence`.
        target_asn: The ASN the traceroute was aimed at.
        fishbowl_path: Path to Phase 1a's `fishbowl.json` (RIS-observed neighbors).

    Returns:
        A dict recording the traceroute-observed upstream ASN (if any)
        and whether RIS independently observed that same ASN as a
        neighbor of `target_asn`.
    """
    fishbowl = json.loads(fishbowl_path.read_text())
    ris_neighbors = fishbowl.get(str(target_asn), {}).get("neighbors", {})

    if target_asn not in as_sequence:
        return {
            "traceroute_upstream_asn": None,
            "ris_agrees": False,
            "note": "target ASN not resolved anywhere in the traceroute AS sequence",
        }

    target_index = as_sequence.index(target_asn)
    if target_index == 0:
        return {
            "traceroute_upstream_asn": None,
            "ris_agrees": False,
            "note": "target ASN was the first resolved hop; no upstream to compare",
        }

    upstream_asn = as_sequence[target_index - 1]
    ris_count = ris_neighbors.get(str(upstream_asn))
    return {
        "traceroute_upstream_asn": upstream_asn,
        "ris_agrees": ris_count is not None,
        "ris_observation_count": ris_count,
    }


def analyze_measurement(
    measurement_id: int,
    target_asn: int,
    atlas_parsed_dir: Path = DEFAULT_ATLAS_PARSED_DIR,
    fishbowl_path: Path = DEFAULT_SUMMARY_PATH,
    output_dir: Path = DEFAULT_TRIANGULATION_DIR,
) -> dict:
    """Run the RIS/Atlas agreement check for every probe in one measurement and persist it."""
    parsed_path = atlas_parsed_dir / f"{measurement_id}.json"
    traceroutes = json.loads(parsed_path.read_text())

    per_probe = []
    for traceroute in traceroutes:
        resolved_hops = resolve_traceroute_hops(traceroute["hops"])
        as_sequence = extract_as_sequence(resolved_hops)
        agreement = check_neighbor_agreement(as_sequence, target_asn, fishbowl_path)
        per_probe.append({"probe_id": traceroute["probe_id"], "as_sequence": as_sequence, **agreement})

    result = {"measurement_id": measurement_id, "target_asn": target_asn, "probes": per_probe}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{measurement_id}.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Defaults to Phase 1b's first live measurement (Guam -> PNG DataCo).
    result = analyze_measurement(measurement_id=210901499, target_asn=17828)
    for probe in result["probes"]:
        logger.info(
            "Probe %s: AS-sequence=%s upstream-of-target=%s RIS-agrees=%s",
            probe["probe_id"],
            probe["as_sequence"],
            probe.get("traceroute_upstream_asn"),
            probe.get("ris_agrees"),
        )


if __name__ == "__main__":
    main()
