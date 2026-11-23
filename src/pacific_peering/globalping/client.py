"""Minimal Globalping API client: probe list, create a measurement, poll for results.

Globalping (api.globalping.io, run by jsDelivr) works like RIPE Atlas: POST a
measurement, then GET it until it finishes. Used unauthenticated, so the
limits are 50 probes per measurement and 250 tests an hour per source IP. A
test is one probe's result, not one measurement. Every POST response carries
`X-RateLimit-Remaining`, which `create_measurement` returns so callers can
stop before the limit instead of collecting 429s.

Globalping probes have no stable ID. A probe is selected by location fields
(`country` + `asn` here), and results identify it only by its location
record. Results are public and kept for about six months.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.globalping.io/v1"
# Generic client name: no personal or project details go to outside services.
USER_AGENT = "measurement-research-client"
_TIMEOUT_S = 30


class RateLimited(RuntimeError):
    """Globalping refused a measurement with HTTP 429 (hourly test limit reached)."""


@dataclass(frozen=True)
class Created:
    """A measurement Globalping accepted."""

    measurement_id: str
    probes_count: int
    rate_limit_remaining: int | None


def _headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT, "Accept": "application/json"}


def fetch_probes() -> list[dict]:
    """Every probe online now, as Globalping lists them (no auth, no test cost)."""
    response = requests.get(f"{API_BASE}/probes", headers=_headers(), timeout=_TIMEOUT_S)
    response.raise_for_status()
    return response.json()


def create_measurement(target: str, locations: list[dict], protocol: str = "ICMP") -> Created:
    """Create one IPv4 traceroute from `locations` to `target`.

    Each location dict carries its own `limit`; Globalping rejects a global
    `limit` alongside per-location ones (checked live 2026-11-23).

    Raises:
        RateLimited: on HTTP 429.
        requests.HTTPError: on any other error status.
    """
    body: dict[str, Any] = {
        "type": "traceroute",
        "target": target,
        "locations": locations,
        # Targets are IPv4 literals, so no `ipVersion` (it only applies to hostnames).
        "measurementOptions": {"protocol": protocol},
    }
    response = requests.post(f"{API_BASE}/measurements", json=body, headers=_headers(), timeout=_TIMEOUT_S)
    if response.status_code == 429:
        raise RateLimited(response.text[:300])
    response.raise_for_status()
    payload = response.json()
    try:
        remaining: int | None = int(response.headers.get("X-RateLimit-Remaining", ""))
    except ValueError:
        remaining = None
    return Created(payload["id"], int(payload.get("probesCount") or 0), remaining)


def fetch_measurement(measurement_id: str) -> dict:
    response = requests.get(f"{API_BASE}/measurements/{measurement_id}", headers=_headers(), timeout=_TIMEOUT_S)
    response.raise_for_status()
    return response.json()


def wait_for_all(measurement_ids: list[str], timeout_s: float = 600, poll_s: float = 3.0) -> dict[str, dict]:
    """Poll every measurement until it leaves `in-progress` or `timeout_s` passes.

    Globalping allows 2 GETs a second per measurement; one poll per
    measurement every `poll_s` stays well under that. The deadline is checked
    before every GET, so a dead network costs at most `timeout_s` plus one
    request timeout. A measurement still running at the deadline is returned
    as last seen (its unfinished results carry their own `in-progress`
    status); one never fetched at all is left out.
    """
    pending = list(measurement_ids)
    done: dict[str, dict] = {}
    last_seen: dict[str, dict] = {}
    deadline = time.monotonic() + timeout_s
    while pending and time.monotonic() < deadline:
        still: list[str] = []
        for measurement_id in pending:
            if time.monotonic() >= deadline:
                still.append(measurement_id)
                continue
            try:
                measurement = fetch_measurement(measurement_id)
            except requests.RequestException as exc:
                logger.warning("Globalping %s poll failed, will retry: %s", measurement_id, exc)
                still.append(measurement_id)
                continue
            if measurement.get("status") == "in-progress":
                last_seen[measurement_id] = measurement
                still.append(measurement_id)
            else:
                done[measurement_id] = measurement
        pending = still
        if pending and time.monotonic() < deadline:
            time.sleep(poll_s)
    if pending:
        logger.warning("Globalping: %d measurement(s) unfinished at timeout", len(pending))
    for measurement_id in pending:
        if measurement_id in last_seen:
            done[measurement_id] = last_seen[measurement_id]
    return done
