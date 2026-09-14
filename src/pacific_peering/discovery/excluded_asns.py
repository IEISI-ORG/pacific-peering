"""In-scope-by-delegation ASNs excluded as non-physical-presence entities.

The symmetric counterpart to `supplementary_asns.py`: that module adds
real ASNs the APNIC-delegation-based registry misses; this one removes
ASNs the registry *does* include, but that this project has confirmed
aren't real Pacific networks despite their APNIC country-code
delegation. A country code on an ASN registration records where the
entity chose to register, not where its network actually runs -- the
same caution already applied to PeeringDB's country field and to the
Marshall Islands shell-company ASNs `supplementary_asns.py` explicitly
declined to add.

**Only genuinely verified entries belong here** -- same restraint as
`supplementary_asns.py` and `supplementary_ixps.py`. Confirmed, not
inferred from a hunch: each entry here was checked against its actual
WHOIS/holder/target-IP data before exclusion, the same way every other
finding in this project is verified before being recorded.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExcludedAsn:
    """One APNIC-delegated ASN this project excludes as a non-physical-presence entity."""

    asn: int
    country_cc: str
    name: str
    note: str


EXCLUDED_ASNS: tuple[ExcludedAsn, ...] = (
    ExcludedAsn(
        asn=24013,
        country_cc="SB",
        name="SB Professional Services",
        note=(
            "Flagged as a likely anomaly as early as Phase 1a (Germany-only "
            "PeeringDB IXP records for a nominally Solomon Islands ASN -- "
            "logged then as \"likely anycast/hosting presence, not real network "
            "location\") but left in the registry until the corridor backlog "
            "picked it as a target and the anomaly could be checked directly "
            "rather than acted on from memory. Confirmed: `pick_target_ip(24013)` "
            "resolves to 185.222.222.1, which is RIPE NCC (not APNIC) address "
            "space -- WHOIS shows `inetnum 185.222.222.0/24`, `netname "
            "DNS-SB-IPV4-01`, `descr DNS.SB`, `country EU`. AS24013 is DNS.SB, a "
            "global anycast public DNS resolver service, not a Solomon Islands "
            "ISP -- its holder name (\"SB - SB Professional Services\") appears "
            "to be an opportunistic APNIC registration under the SB country code "
            "with no real Solomon Islands presence, the same pattern already "
            "confirmed and excluded for 8 \"Marshall Islands\"-registered shell "
            "ASNs in `supplementary_asns.py`. Excluded per the project owner's "
            "explicit direction (consulted directly rather than resolved "
            "unilaterally, per the standing order on anomalous data) rather than "
            "tested with a traceroute that would have measured anycast DNS "
            "reachability and mislabeled it as Solomon Islands connectivity."
        ),
    ),
)
