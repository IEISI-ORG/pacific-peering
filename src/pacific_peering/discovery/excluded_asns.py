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
    ExcludedAsn(
        asn=136996,
        country_cc="VU",
        name="PACIFICNETWORKS-AS-AP (Pacific Networks)",
        # Second category (owner, 2026-09-24): a genuine local company whose
        # announced address space is hosted outside its economy, so any
        # corridor "into" it measures a path to that foreign host instead --
        # contaminating real data, per the owner.
        category="offshore_hosted",
        note=(
            "A real Vanuatu company (APNIC org ORG-PN2-AP, LIR, country VU; "
            "pacificnetworks.net: \"a 100% Vanuatu owned private company based "
            "in Port Vila\", \"Vanuatu's First Starlink Authorized Reseller\") "
            "whose announced space is hosted in Sydney. Measured 2026-09-24: "
            "AU probe 31347 (northern Sydney) reaches `103.101.192.1` in 0.825ms "
            "right behind its sole upstream AS136557 (Host Universal Pty Ltd, "
            "AU) at 0.849ms, RTT rising with distance from Sydney "
            "(measurement 215206130); from Vanuatu itself the path goes "
            "AS9249 -> AS38442 (Vodafone Fiji) -> AS136557 at 173-240ms "
            "(measurement 215206410). Its customers are presumably served over "
            "Starlink, so its own ASN says nothing about paths into Vanuatu. "
            "Excluded at the owner's direction as contaminating real data; its "
            "one finding (NU -> VU, findings.db row 155, measurement "
            "212158127) and that finding's corroboration were removed."
        ),
    ),
    ExcludedAsn(
        asn=23959,
        country_cc="VU",
        name="OWL-AS-AP (Owl Limited)",
        category="offshore_hosted",
        note=(
            "Registered to a Port Vila address (APNIC org ORG-OL19-AP, "
            "country VU; its sponsoring LIR ORG-OL12-AP is also Owl Limited at "
            "the same address, per the owner-supplied aut-num and APNIC RDAP "
            "-- no foreign party in the registration) but its announced space "
            "is served from Japan via its sole upstream AS4785 (xTom JP). First "
            "flagged by the monthly offshore-hosting check "
            "(atlas/offshore_check.py, 2026-09-24): `194.127.166.1` "
            "(194.127.166.0/24, RIPE-region space originated by AS23959) "
            "answered two Tokyo probes in 11.2ms and 13.2ms (probes 1014094, "
            "1007464; measurement 215225380), everything else >=113ms, "
            "against a ~67ms physical minimum from Tokyo to Port Vila. Its "
            "other address, `194.114.136.1`, didn't answer. Excluded at the "
            "owner's direction; its two candidate_peering findings "
            "(findings.db rows 9 and 205, measurements 212141116 and "
            "213187876) and their corroborations were removed."
        ),
    ),
)
