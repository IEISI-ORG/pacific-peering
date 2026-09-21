"""Shared test fixtures: fail fast on any unmocked real network or DB access.

Every Atlas/PeeringDB/RIS call in this codebase goes through `requests`,
and every finding read/write goes through `analysis.store.connect`. Blocking
both here means a test that forgets to mock a call fails loudly and
immediately, instead of silently hitting a real API or writing into the
production findings database (data/analysis/findings.db).
"""

from __future__ import annotations

import pytest
import requests

from pacific_peering.analysis import store


def _blocked(*args, **kwargs):
    raise RuntimeError(
        "test attempted a real network call -- mock the relevant client "
        "function instead of calling through to requests"
    )


def _blocked_db(*args, **kwargs):
    raise RuntimeError(
        "test attempted to open the real findings DB -- mock "
        "analysis.store.connect (or pass an in-memory connection) instead"
    )


@pytest.fixture(autouse=True)
def _block_real_network(monkeypatch):
    monkeypatch.setattr(requests, "get", _blocked)
    monkeypatch.setattr(requests, "post", _blocked)


@pytest.fixture(autouse=True)
def _block_real_db(monkeypatch):
    monkeypatch.setattr(store, "connect", _blocked_db)
