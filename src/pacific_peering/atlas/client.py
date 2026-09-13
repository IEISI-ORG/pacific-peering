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
_TERMINAL_STATUSES = ("Stopped", "Forced to stop", "No suitable probes")


@dataclass(frozen=True)
class TracerouteHop:
    """One hop of a traceroute, as reported by one probe."""

    hop: int
    addresses: tuple[str, ...]


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
        target: Destination IPv4 address or hostname.
        description: Human-readable measurement description.
        probe_count: Number of probes to request.
        api_key: RIPE Atlas API key; loaded from `secrets.yaml` if not given.
        timeout: Request timeout in seconds.

    Returns:
        The created measurement's ID.
    """
    api_key = api_key or load_atlas_api_key()
    payload = {
        "definitions": [
            {
                "target": target,
                "description": description,
                "type": "traceroute",
                "af": 4,
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
) -> list[dict]:
    """Poll until a one-off measurement finishes, then return its raw results.

    Args:
        measurement_id: Atlas measurement ID.
        poll_interval: Seconds between status checks.
        max_wait: Give up (and return whatever results exist) after this long.
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
    return fetch_raw_results(measurement_id)


def parse_traceroute_results(raw_results: list[dict]) -> list[TracerouteResult]:
    """Parse raw Atlas traceroute JSON into `TracerouteResult` records."""
    parsed: list[TracerouteResult] = []
    for result in raw_results:
        hops: list[TracerouteHop] = []
        for hop_result in result.get("result", []):
            addresses = tuple(
                sorted({r["from"] for r in hop_result.get("result", []) if "from" in r})
            )
            hops.append(TracerouteHop(hop=hop_result.get("hop", -1), addresses=addresses))
        parsed.append(
            TracerouteResult(
                measurement_id=result.get("msm_id"),
                probe_id=result.get("prb_id"),
                target=result.get("dst_addr") or result.get("dst_name", ""),
                hops=tuple(hops),
            )
        )
    return parsed
