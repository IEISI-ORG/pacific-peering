"""Minimal RIPE Atlas REST client: create one-off traceroutes, fetch results.

Kept deliberately thin (plain `requests` calls against the Atlas v2 API)
rather than pulling in the `ripe.atlas.cousteau` SDK, matching this
project's existing RIPEstat/PeeringDB clients.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

from pacific_peering.atlas.secrets import load_atlas_api_key

logger = logging.getLogger(__name__)

ATLAS_BASE_URL = "https://atlas.ripe.net/api/v2"
_DEFAULT_TIMEOUT = 30.0
_TERMINAL_STATUSES = (
    "Stopped", "Forced to stop", "No suitable probes", "Failed", "Archived",
)
# A measurement genuinely stuck here will never produce results no matter
# how long we retry -- distinct from the other terminal statuses, where an
# empty first fetch can still just be Atlas's results endpoint lagging its
# own status endpoint (see wait_for_results). Retrying a "No suitable
# probes" measurement for results only wastes empty_result_retries *
# empty_result_retry_delay seconds for a result that was already knowable
# from the status alone.
_NO_RETRY_STATUSES = ("No suitable probes",)


@dataclass(frozen=True)
class TracerouteHop:
    """One hop of a traceroute, as reported by one probe."""

    hop: int
    addresses: tuple[str, ...]
    min_rtt_ms: float | None = None


@dataclass(frozen=True)
class TracerouteResult:
    """One probe's full traceroute toward a target."""

    measurement_id: int
    probe_id: int
    target: str
    hops: tuple[TracerouteHop, ...]


def create_traceroute_measurement(
    source_type: str,
    source_value: int | str,
    target: str,
    description: str,
    probe_count: int = 3,
    api_key: str | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
    af: int = 4,
) -> int:
    """Create a one-off traceroute measurement to `target`.

    Args:
        source_type: Atlas probe-selector type, e.g. "asn" or "country". ASN
            selection fails outright for economies with no probe hosted on
            that exact ASN (common here — see `atlas.probes`); "country"
            is the practical fallback, since it finds any connected probe
            in that economy regardless of which local ISP hosts it.
        source_value: The selector value (an ASN int for "asn", an ISO
            country code for "country").
        target: Destination address (IPv4 or IPv6, matching `af`) or hostname.
        description: Human-readable measurement description. Must not
            contain "<" or ">" — Atlas rejects these outright with a 400
            ("Text contains disallowed characters"), which previously
            surfaced as a confusing one-off failure until traced to the
            "->" arrows this project's descriptions used to include.
        probe_count: Number of probes to request.
        api_key: RIPE Atlas API key; loaded from `secrets.yaml` if not given.
        timeout: Request timeout in seconds.
        af: Address family, 4 or 6. Defaults to 4, which every measurement
            before 2026-09-24 used (then hardcoded). IPv6 support started
            with the Starlink DNS-anchor traces (`atlas.starlink_anchors`);
            corridor testing itself is still IPv4-only.

    Returns:
        The created measurement's ID.

    Raises:
        ValueError: If `description` contains a disallowed character or is
            255+ characters long, or `af` isn't 4 or 6.
    """
    _validate_definition(description, af)
    api_key = api_key or load_atlas_api_key()
    payload = {
        "definitions": [
            {
                "target": target,
                "description": description,
                "type": "traceroute",
                "af": af,
                "protocol": "ICMP",
                "is_oneoff": True,
            }
        ],
        "probes": [{"type": source_type, "value": source_value, "requested": probe_count}],
    }
    response = requests.post(
        f"{ATLAS_BASE_URL}/measurements/",
        json=payload,
        headers={"Authorization": f"Key {api_key}"},
        timeout=timeout,
    )
    response.raise_for_status()
    measurement_id = response.json()["measurements"][0]
    logger.info(
        "Created Atlas traceroute measurement %d (%s=%s -> %s, %d probes requested)",
        measurement_id,
        source_type,
        source_value,
        target,
        probe_count,
    )
    return measurement_id


def _validate_definition(description: str, af: int) -> None:
    """Checks Atlas would otherwise fail mid-run with a 400; raise before posting instead."""
    if len(description) >= 255:
        raise ValueError(
            f"Atlas rejects measurement descriptions of 255+ characters (got {len(description)})"
        )
    if af not in (4, 6):
        raise ValueError(f"af must be 4 or 6, got {af!r}")
    if "<" in description or ">" in description:
        raise ValueError(
            f"Atlas rejects '<'/'>' in measurement descriptions (got: {description!r}); "
            'use "to" instead of "->", for example.'
        )


def create_ping_measurement(
    probe_specs: list[dict],
    target: str,
    description: str,
    packets: int = 3,
    api_key: str | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
    af: int = 4,
) -> int:
    """Create a one-off ping measurement to `target` from one or more probe selections.

    Added 2026-09-24 for `atlas.offshore_check`, which only needs minimum RTT
    (ping costs a fraction of a traceroute's credits). Unlike the traceroute
    creator, takes a list of Atlas probe specs, e.g.
    `[{"type": "country", "value": "AU", "requested": 3}, ...]`, so one
    measurement can draw probes from several countries.

    Raises:
        ValueError: Same pre-post checks as `create_traceroute_measurement`.
    """
    _validate_definition(description, af)
    api_key = api_key or load_atlas_api_key()
    payload = {
        "definitions": [
            {
                "target": target,
                "description": description,
                "type": "ping",
                "af": af,
                "packets": packets,
                "is_oneoff": True,
            }
        ],
        "probes": probe_specs,
    }
    response = requests.post(
        f"{ATLAS_BASE_URL}/measurements/",
        json=payload,
        headers={"Authorization": f"Key {api_key}"},
        timeout=timeout,
    )
    response.raise_for_status()
    measurement_id = response.json()["measurements"][0]
    logger.info("Created Atlas ping measurement %d (to %s, %d probe spec(s))", measurement_id, target, len(probe_specs))
    return measurement_id


def stop_measurement(measurement_id: int, api_key: str | None = None, timeout: float = _DEFAULT_TIMEOUT) -> bool:
    """Stop a running measurement (Atlas keeps every result it already has).

    Added 2026-09-24: one-off pings from several countries stay "Ongoing" for
    20+ minutes while a few probes never report, and every one counts against
    the account's 100-concurrent cap. Stopping once results are collected frees
    the slot immediately. Returns False (logged) instead of raising.
    """
    try:
        response = requests.delete(
            f"{ATLAS_BASE_URL}/measurements/{measurement_id}/",
            headers={"Authorization": f"Key {api_key or load_atlas_api_key()}"},
            timeout=timeout,
        )
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.warning("Couldn't stop measurement %d: %s", measurement_id, e)
        return False


def fetch_measurement_status(measurement_id: int, timeout: float = _DEFAULT_TIMEOUT) -> str:
    """Return a measurement's current status name (e.g. 'Ongoing', 'Stopped')."""
    response = requests.get(f"{ATLAS_BASE_URL}/measurements/{measurement_id}/", timeout=timeout)
    response.raise_for_status()
    return response.json()["status"]["name"]


def fetch_raw_results(measurement_id: int, timeout: float = _DEFAULT_TIMEOUT) -> list[dict]:
    """Fetch raw JSON results for a measurement."""
    response = requests.get(
        f"{ATLAS_BASE_URL}/measurements/{measurement_id}/results/", timeout=timeout
    )
    response.raise_for_status()
    return response.json()


def wait_for_results(
    measurement_id: int,
    poll_interval: float = 5.0,
    max_wait: float = 180.0,
    empty_result_retries: int = 3,
    empty_result_retry_delay: float = 5.0,
) -> list[dict]:
    """Poll until a one-off measurement finishes, then return its raw results.

    Args:
        measurement_id: Atlas measurement ID.
        poll_interval: Seconds between status checks.
        max_wait: Give up (and return whatever results exist) after this long.
        empty_result_retries: Extra attempts to re-fetch if the first fetch
            right after reaching a terminal status comes back empty. Not
            applied when the status is one of `_NO_RETRY_STATUSES` (e.g.
            "No suitable probes"), where retrying can't ever help. Total
            wall clock can exceed `max_wait` by up to
            `empty_result_retries * empty_result_retry_delay` seconds.
        empty_result_retry_delay: Seconds to wait between those retries.
    """
    deadline = time.monotonic() + max_wait
    status = fetch_measurement_status(measurement_id)
    while status not in _TERMINAL_STATUSES and time.monotonic() < deadline:
        logger.info("Measurement %d status=%s, waiting...", measurement_id, status)
        time.sleep(poll_interval)
        status = fetch_measurement_status(measurement_id)
    if status not in _TERMINAL_STATUSES:
        logger.warning(
            "Measurement %d still %s after %.0fs; returning partial results",
            measurement_id,
            status,
            max_wait,
        )

    if status in _NO_RETRY_STATUSES:
        # A durable fact about the measurement, not a fetch race -- no
        # number of retries will ever produce results here.
        logger.warning(
            "Measurement %d: status=%s, not retrying for results", measurement_id, status
        )
        return fetch_raw_results(measurement_id)

    results = fetch_raw_results(measurement_id)
    # Atlas's own status and results endpoints aren't atomically consistent:
    # a measurement can read as terminal (e.g. "Stopped") moments before its
    # results are actually indexed, so the very first fetch after reaching
    # terminal status can come back empty even though real data lands
    # seconds later. Caught 2026-09-20 (measurement 213457173): an empty
    # result here was cached as "zero probes", which downstream in
    # auto_classify.py misfired as "all probes proxy-corrupted" -- a
    # misleading escalation for what was really just an early fetch, not a
    # genuine empty result. Retry a few times before accepting empty as real.
    attempt = 0
    while not results and attempt < empty_result_retries:
        time.sleep(empty_result_retry_delay)
        try:
            results = fetch_raw_results(measurement_id)
        except requests.RequestException as exc:
            # A single transient fetch error (timeout, 5xx) shouldn't throw
            # away the retries whose whole purpose is tolerating Atlas
            # flakiness -- treat it the same as an empty result and try again.
            logger.warning(
                "Measurement %d: results fetch failed (%s), retrying (%d/%d)",
                measurement_id, exc, attempt + 1, empty_result_retries,
            )
        attempt += 1
    if not results:
        logger.warning(
            "Measurement %d returned zero results after %d retries; likely genuinely empty",
            measurement_id,
            empty_result_retries,
        )
    return results


def parse_traceroute_results(raw_results: list[dict]) -> list[TracerouteResult]:
    """Parse raw Atlas traceroute JSON into `TracerouteResult` records.

    `min_rtt_ms` per hop is the minimum RTT across that hop's replies —
    the standard traceroute convention, since the minimum is the closest
    single sample to pure propagation delay (higher samples reflect
    queueing/jitter, not a longer physical path).
    """
    parsed: list[TracerouteResult] = []
    for result in raw_results:
        hops: list[TracerouteHop] = []
        for hop_result in result.get("result", []):
            replies = hop_result.get("result", [])
            addresses = tuple(sorted({r["from"] for r in replies if "from" in r}))
            rtts = [r["rtt"] for r in replies if "rtt" in r]
            min_rtt_ms = min(rtts) if rtts else None
            hops.append(
                TracerouteHop(
                    hop=hop_result.get("hop", -1), addresses=addresses, min_rtt_ms=min_rtt_ms
                )
            )
        parsed.append(
            TracerouteResult(
                measurement_id=result.get("msm_id"),
                probe_id=result.get("prb_id"),
                target=result.get("dst_addr") or result.get("dst_name", ""),
                hops=tuple(hops),
            )
        )
    return parsed
