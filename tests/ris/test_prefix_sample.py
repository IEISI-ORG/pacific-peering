"""The per-ASN prefix sample must not depend on RIPEstat's list order.

`fetch_aspaths_for_asn` queries only the first `max_prefixes` prefixes. It
took them in RIPEstat's order, so a weekly refetch could sample different
prefixes for an unchanged ASN: 42 of 158 ASNs in the 2026-10-18 preview,
giving 50 of 63 changed neighbour pairs, and moving `list_target_ips`.
"""

from __future__ import annotations

from pacific_peering.ris import ripestat

PREFIXES = ["202.62.118.0/24", "103.1.0.0/22", "202.62.12.0/24", "202.62.0.0/16", "2.0.0.0/8"]


def _sample(monkeypatch, order):
    queried = []
    monkeypatch.setattr(ripestat, "fetch_originated_prefixes", lambda asn, af: list(order))
    monkeypatch.setattr(ripestat, "fetch_bgp_state", lambda p: queried.append(p) or [])
    ripestat.fetch_aspaths_for_asn(4638, max_prefixes=3)
    return queried


def test_sample_is_the_same_whatever_order_ripestat_returns(monkeypatch):
    # Fails if the cap is applied to RIPEstat's own order.
    assert _sample(monkeypatch, PREFIXES) == _sample(monkeypatch, PREFIXES[::-1])


def test_sample_is_in_numeric_address_order(monkeypatch):
    # Fails on a plain string sort, which puts 202.62.118 before 202.62.12
    # and 2.0.0.0 after 103.1.0.0.
    assert _sample(monkeypatch, PREFIXES[::-1]) == ["2.0.0.0/8", "103.1.0.0/22", "202.62.0.0/16"]
    assert _sample(monkeypatch, ["202.62.118.0/24", "202.62.12.0/24"]) == [
        "202.62.12.0/24",
        "202.62.118.0/24",
    ]
