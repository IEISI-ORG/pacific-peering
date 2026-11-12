"""fetch_rpki_status must survive a transient RIPEstat failure.

The weekly Cloudflare ROV test (2026-11-11) never fired: RIPEstat returned
500 on prefix-overview for 2606:4700:7000::6715:f409 during the pre-check, and
fetch_rpki_status raised on the first try. The same URL answered 200 an hour
later. It still raises once retries are exhausted, so a failed lookup is
never mistaken for an RPKI state.
"""

from __future__ import annotations

import pytest
import requests

from pacific_peering.ris import ripestat


class _Resp:
    def __init__(self, payload, status_code=200):
        self._payload, self.status_code = payload, status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Server Error", response=self)

    def json(self):
        return self._payload


OVERVIEW = {"data": {"resource": "2606:4700:7000::/48", "asns": [{"asn": 13335}]}}
VALIDATION = {"data": {"status": "invalid_length"}}


def _scripted_get(monkeypatch, outcomes):
    calls = []
    outcomes = iter(outcomes)

    def _get(url, params=None, timeout=None):
        calls.append(url)
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(ripestat.requests, "get", _get)
    monkeypatch.setattr(ripestat.time, "sleep", lambda seconds: None)
    return calls


def test_a_server_error_on_prefix_overview_is_retried(monkeypatch):
    calls = _scripted_get(monkeypatch, [_Resp({}, 500), _Resp(OVERVIEW), _Resp(VALIDATION)])

    status = ripestat.fetch_rpki_status("2606:4700:7000::6715:f409")

    assert status.status == "invalid_length"
    assert status.origin_asn == 13335
    assert len(calls) == 3


def test_still_raises_when_every_attempt_fails(monkeypatch):
    calls = _scripted_get(monkeypatch, [_Resp({}, 500)] * 3)

    with pytest.raises(requests.HTTPError):
        ripestat.fetch_rpki_status("2606:4700:7000::6715:f409")
    assert len(calls) == 3  # first try + 2 retries
