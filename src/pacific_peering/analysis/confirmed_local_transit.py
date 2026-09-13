"""Confirmed real intra-region ("in-fishbowl") transit relationships.

The counterpart to `confirmed_detours.py`: that module records real
detours through an out-of-fishbowl exchange (the sub-optimal-routing
findings this project exists to document); this one records the
opposite — an ASN-to-ASN adjacency confirmed by both RIS and Atlas
where *both* ends are in-scope ASNs, meaning at least this leg of the
journey stays entirely within the study region. Also hand-curated, same
reason as `confirmed_detours.py`: only a handful of measurements exist
so far.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfirmedLocalTransit:
    """One real intra-fishbowl transit relationship, confirmed by RIS + Atlas."""

    provider_cc: str
    provider_asn: int
    provider_name: str
    customer_cc: str
    customer_asn: int
    customer_name: str
    measurement_id: int
    vantage_point_cc: str  # economy the confirming traceroute was sourced from
    ris_observation_count: int
    note: str


CONFIRMED_LOCAL_TRANSIT: tuple[ConfirmedLocalTransit, ...] = (
    ConfirmedLocalTransit(
        provider_cc="FJ",
        provider_asn=38442,
        provider_name="Vodafone Fiji",
        customer_cc="VU",
        customer_asn=9249,
        customer_name="Telecom Vanuatu",
        measurement_id=210960114,
        vantage_point_cc="PF",
        ris_observation_count=1346,
        note=(
            "All 3 probes (sourced from French Polynesia, the best-covered "
            "available vantage point — not itself part of this adjacency) "
            "show AS38442 as the last resolved hop before AS9249, matching "
            "RIS's independently-observed neighbor count exactly. A real "
            "gap remains between AS38442 and AS9249 (checked directly: "
            "ordinary ICMP filtering, not an unlisted IXP), so the very "
            "last hop isn't proven — but the AS38442 adjacency itself is. "
            "Reinforced from the reverse direction by measurement 210970669 "
            "(Vanuatu -> FSM/AS38875, sourced from Vanuatu itself): AS38442 "
            "is the first resolved hop leaving AS9249's own network, "
            "matching this same adjacency from the other side. That "
            "measurement's actual target (AS38875) was not confirmed — "
            "RIS's only neighbor for AS38875 is AS10130, not the traceroute's "
            "last resolved hop (AS139759) — a correct negative result, not "
            "a new finding, and recorded here only as corroboration of the "
            "existing AS9249<->AS38442 adjacency."
        ),
    ),
)
