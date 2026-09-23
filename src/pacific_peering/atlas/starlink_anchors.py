"""Trace every Starlink-hosted in-scope probe to well-known public DNS anchors.

TODO queued 2026-09-23 (task_plan.md, "trace all Starlink-hosted probes to
well-known public DNS anchors"): the KI probes' traceroutes toward AS154100
died inside Starlink's private/CGNAT space, which can't distinguish "this
probe's traceroute mechanism doesn't get out" from "this specific target/path
is genuinely dark". A destination that's essentially guaranteed to respond
(1.1.1.1, 8.8.8.8, or their secondaries) separates the two.

Starlink (AS14593) probes are in `EXTERNAL_NON_CANDIDATE_ASNS`, so normal
country-based candidacy never selects them -- sources by explicit probe ID,
found from the nightly-refreshed any-status probe listing
(`atlas.probes.load_probe_listing`) rather than a hardcoded ID list, so a
Starlink probe that appears or reconnects is picked up automatically.

IPv4 only for now: `atlas.client.create_traceroute_measurement` hardcodes
`af=4`, and IPv6 corridor testing is deliberately deferred project-wide. The
IPv6 anchors (2606:4700:4700::1111, 2001:4860:4860::8888) are the follow-up
once that lands -- see the `af=4` TODO in `reports/ascii_report.py`.

Spends real Atlas credits (one measurement per anchor, all probes in each),
so `main()` only prints the plan unless `--fire` is given.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import logging
from dataclasses import dataclass

import requests

from pacific_peering.atlas.probes import load_probe_listing
from pacific_peering.atlas.smoketest import DEFAULT_PARSED_DIR, _fire_and_persist

logger = logging.getLogger(__name__)

STARLINK_ASN = 14593
# (primary, fallback) per service. Atlas caps any one target at 25
# concurrent measurements and the primaries are routinely at that cap
# (both refused 2026-09-24); the same service's secondary address is the
# owner-approved fallback.
PUBLIC_DNS_ANCHORS_V4: tuple[tuple[str, str], ...] = (
    ("1.1.1.1", "1.0.0.1"),  # Cloudflare
    ("8.8.8.8", "8.8.4.4"),  # Google
)
_CONCURRENCY_CAP_TEXT = "concurrent measurements to the same target"
_ATLAS_GAP_LIMIT_HOP = 255


@dataclass(frozen=True)
class AnchorTraceSummary:
    """What one probe's traceroute to an anchor shows about getting out of Starlink."""

    probe_id: int
    target: str
    reached_target: bool
    first_public_hop: int | None  # None: no real hop showed a public address
    last_hop: int | None  # last real hop with any responding address
    last_address: str | None
    last_rtt_ms: float | None
    # Atlas stops after 5 consecutive silent hops and sends one final
    # TTL-255 packet to the destination; that reply is reported as "hop
    # 255". True means the path was invisible past `last_hop` but the
    # destination still answered (seen: KI probe 1008228 to 1.1.1.1,
    # measurement 214951531, 2026-09-24).
    gap_limited: bool


def find_starlink_probes(
    listing: dict[str, list[dict]], asn: int = STARLINK_ASN
) -> dict[str, list[int]]:
    """Return Connected probe IDs on `asn`, grouped by economy code."""
    result: dict[str, list[int]] = {}
    for cc, probes in listing.items():
        ids = [p["id"] for p in probes if p.get("asn_v4") == asn and p["status"] == "Connected"]
        if ids:
            result[cc] = sorted(ids)
    return result


def _is_public(address: str) -> bool:
    # not is_global covers RFC1918 *and* 100.64.0.0/10 CGNAT shared space,
    # which is_private alone misses.
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False


def summarize_anchor_trace(traceroute: dict) -> AnchorTraceSummary:
    """Summarize one parsed traceroute (the `data/atlas/parsed/*.json` entry shape)."""
    target = traceroute["target"]
    first_public_hop = None
    last_hop = last_address = last_rtt = None
    gap_limited = False
    for hop in traceroute["hops"]:
        if hop["hop"] == _ATLAS_GAP_LIMIT_HOP:
            gap_limited = True
            continue
        if not hop["addresses"]:
            continue
        last_hop, last_address, last_rtt = hop["hop"], hop["addresses"][-1], hop["min_rtt_ms"]
        if first_public_hop is None and any(_is_public(a) for a in hop["addresses"]):
            first_public_hop = hop["hop"]
    reached = any(target in hop["addresses"] for hop in traceroute["hops"])
    return AnchorTraceSummary(
        probe_id=traceroute["probe_id"],
        target=target,
        reached_target=reached,
        first_public_hop=first_public_hop,
        last_hop=last_hop,
        last_address=last_address,
        last_rtt_ms=last_rtt,
        gap_limited=gap_limited,
    )


def _fire_anchor(probe_value: str, anchor: str, probe_count: int) -> int:
    description = f"pacific-peering starlink-anchor probes={probe_value} to {anchor}"
    logger.info("Sourcing from Starlink probe(s) %s toward anchor %s", probe_value, anchor)
    return _fire_and_persist("probes", probe_value, anchor, description, probe_count)


def run_starlink_anchor_traces(
    probe_ids: list[int],
    anchors: tuple[tuple[str, str], ...] = PUBLIC_DNS_ANCHORS_V4,
) -> list[int]:
    """Fire one traceroute per anchor service from all `probe_ids` together.

    Tries each service's primary address; if Atlas refuses it for its
    per-target concurrency cap, fires at the fallback address instead. Any
    other refusal (or a refused fallback) is logged and that service is
    skipped, never fatal to the remaining services. Nothing is created for
    a refused address.

    Returns:
        The created measurements' IDs.
    """
    probe_value = ",".join(str(p) for p in probe_ids)
    measurement_ids = []
    for primary, fallback in anchors:
        for anchor in (primary, fallback):
            try:
                measurement_ids.append(_fire_anchor(probe_value, anchor, len(probe_ids)))
                break
            except requests.HTTPError as e:
                detail = e.response.text[:500] if e.response is not None else str(e)
                if anchor == primary and _CONCURRENCY_CAP_TEXT in detail:
                    logger.warning("Atlas concurrency cap on %s, falling back to %s", primary, fallback)
                    continue
                logger.error("Atlas refused anchor %s, skipping: %s", anchor, detail)
                break
    return measurement_ids


def _log_summaries(measurement_id: int, probe_cc: dict[int, str]) -> None:
    parsed = json.loads((DEFAULT_PARSED_DIR / f"{measurement_id}.json").read_text())
    returned = {t["probe_id"] for t in parsed}
    for probe_id in sorted(set(probe_cc) - returned):
        logger.warning("Measurement %d: no result from probe %d (%s)", measurement_id, probe_id, probe_cc[probe_id])
    for traceroute in parsed:
        s = summarize_anchor_trace(traceroute)
        logger.info(
            "Measurement %d probe %d (%s) -> %s: reached=%s first_public_hop=%s last=hop %s %s (%s ms) gap_limited=%s",
            measurement_id, s.probe_id, probe_cc.get(s.probe_id, "?"), s.target, s.reached_target,
            s.first_public_hop, s.last_hop, s.last_address, s.last_rtt_ms, s.gap_limited,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fire", action="store_true", help="actually create measurements (spends Atlas credits)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    by_cc = find_starlink_probes(load_probe_listing())
    probe_cc = {pid: cc for cc, ids in by_cc.items() for pid in ids}
    if not probe_cc:
        logger.warning("No Connected AS%d probes in the current probe listing; nothing to fire", STARLINK_ASN)
        return
    logger.info(
        "Starlink probes: %s -> anchors %s (%d measurement(s), %d probe result(s) each)",
        by_cc, ", ".join(f"{p} (fallback {f})" for p, f in PUBLIC_DNS_ANCHORS_V4),
        len(PUBLIC_DNS_ANCHORS_V4), len(probe_cc),
    )
    if not args.fire:
        logger.info("Dry run -- pass --fire to create the measurements")
        return
    for measurement_id in run_starlink_anchor_traces(sorted(probe_cc)):
        _log_summaries(measurement_id, probe_cc)


if __name__ == "__main__":
    main()
