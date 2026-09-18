"""APNIC-delegated ASNs whose registered country doesn't match their real Pacific presence.

A cousin of `excluded_asns.py`/`supplementary_asns.py`, but for a
different failure mode: not "this ASN has no real Pacific presence at
all" (excluded) and not "APNIC's delegation data misses this ASN
entirely" (supplementary) -- this is "APNIC delegates this ASN to one
economy, but its real connected-probe presence this project cares about
is physically in a different one." Regional organizations with a single
ASN and infrastructure spread across several Pacific countries hit this
exactly: their APNIC delegation reflects the organization's registered
account address (often its headquarters), not every economy it actually
operates real infrastructure in.

First confirmed instance (2026-09-19): AS141695 (Pacific Community/SPC).
APNIC delegates it to New Caledonia (SPC's Nouméa headquarters), but its
only connected RIPE Atlas probe (60575) live-geolocates to Suva, Fiji --
confirmed both by the probe's own live `country_code` and by its Atlas
`description` field, which reads verbatim "Pacific Community, Suva,
Fiji". Discovered because a full `build_registry()` refresh silently
reverted an earlier one-off hand-edit to `data/asn_registry.json` back
to NC -- that file is regenerated from live APNIC data on every pipeline
run, so any correction has to live here, not as a direct edit to the
generated file, to survive the next refresh.

Deliberately narrow in scope: this does NOT change where
`corridor_backlog.enumerate_candidate_corridors` sources measurements
from -- that already trusts each connected probe's own live location
directly (`_probe_live_cc_by_asn`), independent of this registry. This
override matters for the *other* things `asn_registry.json` still
drives: which economy's ASN list an ASN shows up in for reporting
(`probe_gap_report.py`'s per-economy breakdowns, Local IXP Presence
section), and target-side economy classification if the ASN is ever
picked as a traceroute target.

**Only genuinely verified entries belong here** -- same restraint as
`excluded_asns.py`/`supplementary_asns.py`. Confirmed via the probe's
own live Atlas API data before reclassifying, never from a hunch.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReclassifiedAsn:
    """One APNIC-delegated ASN this project files under a different economy than APNIC does."""

    asn: int
    from_cc: str  # APNIC's own delegation country -- kept for traceability, not re-derived
    to_cc: str
    name: str
    note: str


RECLASSIFIED_ASNS: tuple[ReclassifiedAsn, ...] = (
    ReclassifiedAsn(
        asn=141695,
        from_cc="NC",
        to_cc="FJ",
        name="Pacific Community (SPC)",
        note=(
            "APNIC delegates AS141695 to New Caledonia (SPC's Nouméa "
            "headquarters), but its only connected RIPE Atlas probe (60575) "
            "live-geolocates to Suva, Fiji -- confirmed via the probe's own "
            "live `country_code` (FJ) and its Atlas `description` field, "
            "which reads verbatim \"Pacific Community, Suva, Fiji\". Its "
            "only two RIS-observed neighbors (AS4638, AS45355) are both "
            "Fiji ASNs, with zero New Caledonia adjacencies -- this ASN's "
            "entire currently-visible footprint is Fiji, not NC. Two "
            "confirmed_detour findings (FJ->KI via AS134783 and AS154100) "
            "were relabeled from NC to FJ to match once this was confirmed."
        ),
    ),
)
