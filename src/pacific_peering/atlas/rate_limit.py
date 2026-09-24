"""Atlas account-level pre-flight check, shared by every job that fires measurements.

Owner's request (2026-09-24), after the offshore check hit Atlas's per-account
cap ("You are not permitted to run more than 100 concurrent measurements") by
being refused mid-run. Before creating measurements, a caller asks
`wait_for_headroom(n)`: it reads how many of this account's measurements are
still in flight (Specified/Scheduled/Ongoing, one `/measurements/my/` call) and
waits until `n` more fit under `ACCOUNT_CONCURRENCY_CAP - HEADROOM_MARGIN`.

Wired in at the two points every measurement passes through:
`smoketest._fire_and_persist` (all traceroutes: the nightly corridor batch's
workers, the Starlink/IPv6/ROV steps, one-off checks) and
`offshore_check._measure` (each ping batch). The per-*target* cap (25
concurrent measurements to one address, e.g. 1.1.1.1) is a different limit,
handled where it applies by the anchor fallback in `starlink_anchors`.

Fails open: if the in-flight count can't be read, it logs and lets the caller
proceed -- the refusal handling each caller already has is the backstop, and a
flaky stats endpoint must not stall the nightly run.
"""

from __future__ import annotations

import logging
import time

import requests

from pacific_peering.atlas.secrets import load_atlas_api_key

logger = logging.getLogger(__name__)

ATLAS_MY_MEASUREMENTS_URL = "https://atlas.ripe.net/api/v2/measurements/my/"
ATLAS_CREDITS_URL = "https://atlas.ripe.net/api/v2/credits/"
ACCOUNT_CONCURRENCY_CAP = 100  # Atlas's own per-account limit, as its refusal message states
HEADROOM_MARGIN = 5  # room for another job that starts between our check and our create
IN_FLIGHT_STATUSES = "0,1,2"  # Specified, Scheduled, Ongoing
LOW_BALANCE_WARNING = 100_000  # credits; the balance was ~101M on 2026-09-24


def count_in_flight(api_key: str | None = None, timeout: float = 30.0) -> int | None:
    """This account's measurements not yet finished, or None if Atlas couldn't be asked."""
    try:
        response = requests.get(
            ATLAS_MY_MEASUREMENTS_URL,
            params={"status__in": IN_FLIGHT_STATUSES, "page_size": 1},
            headers={"Authorization": f"Key {api_key or load_atlas_api_key()}"},
            timeout=timeout,
        )
        response.raise_for_status()
        return int(response.json()["count"])
    except (requests.RequestException, KeyError, ValueError) as e:
        logger.warning("Couldn't read Atlas in-flight count (%s); proceeding without the pre-flight check", e)
        return None


def wait_for_headroom(
    needed: int = 1,
    max_wait_s: float = 1800.0,
    poll_s: float = 60.0,
    counter=count_in_flight,
    sleep=time.sleep,
) -> bool:
    """Block until `needed` more measurements fit under the account cap.

    Returns True when there's room (or the count couldn't be read -- fails
    open), False if still full after `max_wait_s`; callers then fire anyway and
    rely on their existing refusal handling.
    """
    limit = ACCOUNT_CONCURRENCY_CAP - HEADROOM_MARGIN
    waited = 0.0
    while True:
        in_flight = counter()
        if in_flight is None or in_flight + needed <= limit:
            return True
        if waited >= max_wait_s:
            logger.warning("Atlas still at %d in flight after %ds; firing anyway", in_flight, int(waited))
            return False
        logger.info("Atlas pre-flight: %d in flight, need %d more (limit %d); waiting %ds",
                    in_flight, needed, limit, int(poll_s))
        sleep(poll_s)
        waited += poll_s


def credit_status(api_key: str | None = None, timeout: float = 30.0) -> dict | None:
    """Balance and recent spend from `/credits/`; logs a warning if the balance is low."""
    try:
        response = requests.get(
            ATLAS_CREDITS_URL, headers={"Authorization": f"Key {api_key or load_atlas_api_key()}"}, timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as e:
        logger.warning("Couldn't read Atlas credit status (%s)", e)
        return None
    status = {k: data.get(k) for k in ("current_balance", "past_day_credits_spent", "estimated_daily_income")}
    if (status["current_balance"] or 0) < LOW_BALANCE_WARNING:
        logger.warning("Atlas credit balance low: %s", status["current_balance"])
    return status
