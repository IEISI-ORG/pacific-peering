"""Phase 1b/1d smoke tests: prove outbound and inbound Atlas traceroutes work.

Fires one cheap one-off traceroute (a handful of probes, single shot) and
stores raw + parsed results. This is the minimal live proof before any
larger measurement campaign — deferred deliberately (see task_plan.md),
not an oversight.

Two directions, per Validation Rule 3 ("the fish bowl needs both
directions"):
- `run_smoketest` (outbound): a Pacific-hosted/country probe tracing out
  to a target. Source selection uses country, not ASN — ASN-based
  selection fails for most in-scope ASNs (very sparse, often-abandoned
  Atlas probe coverage in this region; see `atlas.probes`).
- `run_inbound_smoketest` (inbound): a probe *outside* the Pacific
  tracing *in* to an in-scope ASN — the only way to see how external
  traffic actually arrives, which may differ from the outbound view.
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
from pacific_peering.atlas.targets import pick_ixp_member_target, pick_target_ip
from pacific_peering.discovery.economies import ECONOMIES_BY_CC

logger = logging.getLogger(__name__)

DEFAULT_RAW_DIR = Path("data/atlas/raw")
DEFAULT_PARSED_DIR = Path("data/atlas/parsed")

DEFAULT_TARGET_ASN = 17828  # PNG DataCo Limited
DEFAULT_TARGET_CC = "PG"
DEFAULT_EXTERNAL_SOURCE_CC = "US"  # outside the Pacific and outside AU/NZ


def _fire_and_persist(
    source_type: str, source_value: int | str, target_ip: str, description: str, probe_count: int
) -> int:
    """Create a one-off traceroute, wait for results, and persist raw + parsed JSON."""
    measurement_id = create_traceroute_measurement(
        source_type=source_type,
        source_value=source_value,
        target=target_ip,
        description=description,
        probe_count=probe_count,
    )
    raw_results = wait_for_results(measurement_id)
    if not raw_results:
        # wait_for_results already retries a genuinely empty fetch, so by
        # the time it's still empty here that's either a durable "No
        # suitable probes" fact or a real (rare) exhausted-retries case --
        # either way, worth a visible marker on the cached files, since an
        # empty raw/parsed pair on disk is otherwise indistinguishable from
        # a real zero-probe measurement to anything reprocessing the cache.
        logger.warning(
            "Measurement %d: zero raw results persisted to %s -- see logs above for why",
            measurement_id, DEFAULT_RAW_DIR,
        )

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


def run_smoketest(
    target_asn: int = DEFAULT_TARGET_ASN,
    target_cc: str = DEFAULT_TARGET_CC,
    probe_count: int = 3,
    source_cc: str | None = None,
) -> int:
    """Fire one outbound one-off traceroute toward `target_asn` and persist results.

    Args:
        target_asn: In-scope ASN to trace toward.
        target_cc: `target_asn`'s economy (excluded from auto source-pick).
        probe_count: Number of probes to request.
        source_cc: Force a specific source economy (e.g. to deliberately
            test a particular corridor). If not given, auto-picks
            whichever in-scope economy (other than `target_cc`) has the
            most connected Atlas probes — which will keep re-picking the
            same best-covered economy unless overridden here.

    Returns:
        The created measurement's ID.
    """
    source_cc = source_cc or pick_best_covered_economy(exclude_cc=target_cc)
    source_name = ECONOMIES_BY_CC[source_cc].name
    target_ip = pick_target_ip(target_asn)
    description = f"pacific-peering smoketest outbound {source_cc} to AS{target_asn} {target_ip}"
    logger.info("Selected source economy: %s (%s)", source_name, source_cc)
    return _fire_and_persist("country", source_cc, target_ip, description, probe_count)


def run_inbound_smoketest(
    target_asn: int = DEFAULT_TARGET_ASN,
    external_source_cc: str = DEFAULT_EXTERNAL_SOURCE_CC,
    probe_count: int = 3,
) -> int:
    """Fire one inbound one-off traceroute from outside the Pacific into `target_asn`.

    Args:
        target_asn: The in-scope ASN to trace into.
        external_source_cc: An ISO country code outside the study region
            (and outside AU/NZ, to avoid conflating "the alleged hub" with
            "an external vantage point") to source probes from.
        probe_count: Number of probes to request.

    Returns:
        The created measurement's ID.
    """
    target_ip = pick_target_ip(target_asn)
    description = (
        f"pacific-peering smoketest inbound {external_source_cc} to AS{target_asn} {target_ip}"
    )
    logger.info("External source economy: %s", external_source_cc)
    return _fire_and_persist("country", external_source_cc, target_ip, description, probe_count)


def run_ixp_member_probe(
    ix_id: int,
    source_cc: str,
    exclude_asns: int | set[int] | None = None,
    probe_count: int = 3,
) -> int:
    """Fire a traceroute from `source_cc` directly at a known IXP member's peering-LAN address.

    The active method for hidden-peering discovery (as opposed to
    `run_smoketest`'s incidental one): pick a real member address at a
    known exchange via `pick_ixp_member_target` and target it directly,
    so an in-fishbowl exchange's fabric can be probed deliberately
    rather than only noticed when it happens to sit on some other
    measurement's path.

    Args:
        ix_id: PeeringDB exchange ID to probe (see `ixp_lan_registry` for
            which ones are confirmed in-fishbowl).
        source_cc: Economy to source probes from.
        exclude_asns: Skip these member ASN(s) when picking a target
            (e.g. the source economy's own ASN, and/or members already
            probed in an earlier call — pass the growing set to walk
            through an exchange's full membership one measurement at a
            time).
        probe_count: Number of probes to request.

    Returns:
        The created measurement's ID.
    """
    member_asn, target_ip = pick_ixp_member_target(ix_id, exclude_asns=exclude_asns)
    description = (
        f"pacific-peering ixp-member-probe {source_cc} to ix_id={ix_id} "
        f"member AS{member_asn} {target_ip}"
    )
    logger.info(
        "Targeting AS%d (%s) at ix_id=%d from source economy %s",
        member_asn,
        target_ip,
        ix_id,
        source_cc,
    )
    return _fire_and_persist("country", source_cc, target_ip, description, probe_count)


def _log_measurement(measurement_id: int) -> None:
    parsed_path = DEFAULT_PARSED_DIR / f"{measurement_id}.json"
    parsed = json.loads(parsed_path.read_text())
    logger.info("Measurement %d: %d probe traceroutes returned", measurement_id, len(parsed))
    for traceroute in parsed:
        logger.info("Probe %s -> %s:", traceroute["probe_id"], traceroute["target"])
        for hop in traceroute["hops"]:
            addrs = ", ".join(hop["addresses"]) or "*"
            logger.info("  hop %2d: %s", hop["hop"], addrs)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _log_measurement(run_smoketest())


def main_inbound() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _log_measurement(run_inbound_smoketest())


if __name__ == "__main__":
    main()
