"""In-scope ASNs held in quarantine: no proof yet of where their space is routed.

The cautious middle ground between keeping an ASN fully in play and
excluding it (`excluded_asns.py`). An excluded ASN has been *shown* not
to be a real Pacific network (offshore-hosted, anycast, VPN egress) and
is removed from the registry along with its findings. A quarantined ASN
hasn't been shown either way: every test so far goes dark before reaching
its space, no address in it answers, and nothing independent places it
in its economy. So:

- it stays in the registry and fishbowl (RIS monitoring continues, and
  the monthly offshore check keeps pinging it, so evidence can turn up);
- it is skipped as a corridor source and target (`corridor_backlog`), and
  its findings are left out of the weekly reverification ration -- re-
  firing the same dark traceroutes spends credits without adding proof;
- its findings stay in findings.db and the committed export, but are
  left out of the report's tallies and the map, and listed under the
  report's quarantine appendix instead;
- it leaves quarantine only on the project owner's direction, once
  routing is proven (released back into scope) or disproven (moved to
  `excluded_asns.py`).

Same verification bar as `excluded_asns.py`: each entry records the
actual evidence that left it unproven.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuarantinedAsn:
    """One in-scope ASN whose routing hasn't been proven, held out of testing and tallies."""

    asn: int
    country_cc: str
    name: str
    since: str  # ISO date quarantined
    release_when: str  # what evidence would resolve it, either way
    note: str


QUARANTINED_ASNS: tuple[QuarantinedAsn, ...] = (
    QuarantinedAsn(
        asn=152093,
        country_cc="CK",
        name="VakaNet Limited",
        since="2026-10-01",
        release_when=(
            "a host in 116.199.200.0/23 answers and its latency places it, or a "
            "trace from a Cook Islands probe reaches VakaNet's own space"
        ),
        note=(
            "Sole RIS upstream is AS9507 (NextHop, AU). 2026-10-01 traceroutes "
            "to 116.199.200.1 from AU probes (measurement 217757577) go dark "
            "right after NextHop's Sydney and Brisbane PEs "
            "(et11-90.pe04.syd01.nexthop.net.au at 8.7ms, "
            "po1.nxtpe01.bne01.nexthop.net.au at 2.8ms); the CK-sourced "
            "measurement (217757575) returned no results; an nmap ping sweep "
            "of all of 116.199.200.0/23 from Brisbane found no responsive "
            "host. That leaves Sydney hosting and a tunnel back to Rarotonga "
            "equally possible. Its 5 legacy confirmed_detour findings (#165-169, "
            "from GU/MP via Tokyo and NU/TV/VU via Sydney) rest on chains that "
            "end at AS9507 and never reach VakaNet, so they're held here. "
            "Quarantined at the owner's direction: no proof of routing."
        ),
    ),
)

QUARANTINED_ASN_SET: frozenset[int] = frozenset(q.asn for q in QUARANTINED_ASNS)
