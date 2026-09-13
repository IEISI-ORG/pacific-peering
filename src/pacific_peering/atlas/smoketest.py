"""Phase 1b smoke test: prove we can run a real RIPE Atlas traceroute end-to-end.

Fires one cheap one-off traceroute (a handful of probes, single shot) and
stores raw + parsed results. This is the minimal live proof before any
larger measurement campaign — deferred deliberately (see task_plan.md),
not an oversight.

Source selection: ASN-based probe selection turned out to fail for most
in-scope ASNs — Atlas has very sparse, often-abandoned probe coverage in
this region (see `atlas.probes`). This smoke test instead picks the
best-covered in-scope economy (by connected-probe count) as the source,
and targets Papua New Guinea (AS17828), which has both a local IXP (PNG
Neutral IX) and Sydney IXP presence per Phase 1a's data — a direct test
of whether Pacific-to-Pacific traffic actually stays regional.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pacific_peering.atlas.client import (
    create_traceroute_measurement,
    parse_traceroute_results,
    wait_for_results,
)
from pacific_peering.atlas.probes import pick_best_covered_economy
from pacific_peering.atlas.targets import pick_target_ip
from pacific_peering.discovery.economies import ECONOMIES_BY_CC

logger = logging.getLogger(__name__)

DEFAULT_RAW_DIR = Path("data/atlas/raw")
DEFAULT_PARSED_DIR = Path("data/atlas/parsed")

DEFAULT_TARGET_ASN = 17828  # PNG DataCo Limited
DEFAULT_TARGET_CC = "PG"


def run_smoketest(
    target_asn: int = DEFAULT_TARGET_ASN,
    target_cc: str = DEFAULT_TARGET_CC,
    probe_count: int = 3,
) -> int:
    """Fire one one-off traceroute toward `target_asn` and persist results.

    The source economy is chosen automatically as whichever in-scope
    economy (other than `target_cc`) has the most connected Atlas probes.

    Returns:
        The created measurement's ID.
    """
    source_cc = pick_best_covered_economy(exclude_cc=target_cc)
    source_name = ECONOMIES_BY_CC[source_cc].name
    target_ip = pick_target_ip(target_asn)
    description = (
        f"pacific-peering smoketest {source_cc} -> AS{target_asn} ({target_ip})"
    )
    logger.info("Selected source economy: %s (%s)", source_name, source_cc)
    measurement_id = create_traceroute_measurement(
        source_type="country",
        source_value=source_cc,
        target=target_ip,
        description=description,
        probe_count=probe_count,
    )
    raw_results = wait_for_results(measurement_id)

    DEFAULT_RAW_DIR.mkdir(parents=True, exist_ok=True)
    (DEFAULT_RAW_DIR / f"{measurement_id}.json").write_text(
        json.dumps(raw_results, indent=2) + "\n"
    )

    parsed = parse_traceroute_results(raw_results)
    parsed_payload = [
        {
            "measurement_id": r.measurement_id,
            "probe_id": r.probe_id,
            "target": r.target,
            "hops": [
                {"hop": h.hop, "addresses": list(h.addresses), "min_rtt_ms": h.min_rtt_ms}
                for h in r.hops
            ],
        }
        for r in parsed
    ]
    DEFAULT_PARSED_DIR.mkdir(parents=True, exist_ok=True)
    (DEFAULT_PARSED_DIR / f"{measurement_id}.json").write_text(
        json.dumps(parsed_payload, indent=2) + "\n"
    )
    return measurement_id


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    measurement_id = run_smoketest()

    parsed_path = DEFAULT_PARSED_DIR / f"{measurement_id}.json"
    parsed = json.loads(parsed_path.read_text())
    logger.info("Measurement %d: %d probe traceroutes returned", measurement_id, len(parsed))
    for traceroute in parsed:
        logger.info("Probe %s -> %s:", traceroute["probe_id"], traceroute["target"])
        for hop in traceroute["hops"]:
            addrs = ", ".join(hop["addresses"]) or "*"
            logger.info("  hop %2d: %s", hop["hop"], addrs)


if __name__ == "__main__":
    main()
