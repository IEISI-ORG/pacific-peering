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

**Standing rule, not just an accumulating list of one-offs: global DNS
anycast infrastructure (root-server instances, public anycast
resolvers) is excluded whenever it turns up registered under an
in-scope economy's country code.** Two confirmed instances of this
exact pattern so far (AS24013/DNS.SB, AS137064/ISC F-root) -- an
anycast DNS operator's registered country reflects administrative/
engineering convenience (which RIR delegated the block, which IXP an
instance announces at), never a genuine local network operator with
real Pacific presence. Any future ASN confirmed to be root-server or
public-resolver anycast infrastructure gets excluded under this same
rule, not re-litigated as a fresh one-off case.

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
    category: str  # e.g. "dns_anycast" -- which standing rule this falls under
    note: str


EXCLUDED_ASNS: tuple[ExcludedAsn, ...] = (
    ExcludedAsn(
        asn=24013,
        country_cc="SB",
        name="SB Professional Services",
        category="dns_anycast",
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
    ExcludedAsn(
        asn=137064,
        country_cc="PG",
        name="ISC-AS-POM1",
        category="dns_anycast",
        note=(
            "Surfaced by a direct sanity check on ABQIX (Albuquerque, US, "
            "ix_id 3322, already correctly out-of-fishbowl): asked which "
            "in-scope Pacific ASN is a real member there, expecting the "
            "answer to matter. Cross-checked two independent sources before "
            "excluding, same as AS24013: bgp.tools names it \"ISC F-ROOT "
            "ABQ1\"; PeeringDB's own `net` record gives `aka: F-ROOT`, "
            "`info_type: Network Services`; RIPEstat WHOIS gives the "
            "authoritative `as-name: ISC-AS-POM1` with `descr: For use by "
            "ISC/F-Root exclusively for announcements at POM1/PNGIXP` (POM1 "
            "= Port Moresby, PNG's own IXP). All three agree: this is ISC's "
            "F-root DNS anycast infrastructure, not a Papua New Guinea "
            "network with a real footprint in Albuquerque -- its PG "
            "registration reflects where ISC arranged BGP announcement for "
            "this specific instance (PNGIXP), not a genuine local operator. "
            "Checked for siblings before excluding just this one ASN: swept "
            "all 163 then-in-scope ASNs' bgp.tools names and PeeringDB net "
            "names/akas for anycast-DNS-operator keywords (root, isc, "
            "verisign, netnod, icann, pch, quad9, opendns, cloudflare, "
            "google, etc.) -- one other hit (AS139609/SISCC) was a false "
            "positive (\"isc\" substring-matching inside \"SISCC\"'s own "
            "`aka\", a real, already-extensively-verified Solomon Islands "
            "submarine cable operator), no other genuine anycast instance "
            "found. No prior findings or tested-pairs history involved "
            "AS137064 -- a clean exclusion, nothing else to unwind."
        ),
    ),
)
