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
    QuarantinedAsn(
        asn=151647,
        country_cc="PG",
        name="Rural Tech Development",
        since="2026-10-01",
        release_when=(
            "a host in 103.98.52.0/24 answers and its latency places it, or a "
            "trace reaches Rural Tech's own space instead of looping at Parsun"
        ),
        note=(
            "Registered in PNG (APNIC registrant ORG-RTD1-AP). Sole RIS upstream "
            "is AS31732 (Parsun Network Solutions, AU). 2026-10-01 traceroutes "
            "to 103.98.52.1 from AU probes 1011163 and 19917 (measurement "
            "217755233) and PG probe 50365 (217755235) all end in a genuine "
            "routing loop on 188.209.155.250, in Parsun's own 188.209.155.0/24: "
            "4.9ms from an AU probe, 38ms from PG, so the loop sits in "
            "Australia and nothing beyond it is reachable. An nmap ping sweep "
            "of 103.98.52.0/24 from Brisbane found no responsive host. Whether "
            "the space is used in PNG, hosted in Australia, or not in use at "
            "all can't be told from this. No findings held. Quarantined at "
            "the owner's direction: no proof of routing."
        ),
    ),
)

QUARANTINED_ASN_SET: frozenset[int] = frozenset(q.asn for q in QUARANTINED_ASNS)


@dataclass(frozen=True)
class HeldFinding:
    """One finding held out of tallies, the map and reverification, without
    quarantining either of its ASNs (whose other findings stand). Keyed by the
    finding's identity, not its row id, which an import_jsonl rebuild may change."""

    kind: str
    source_asn: int
    target_asn: int
    since: str  # ISO date held
    release_when: str
    note: str


HELD_FINDINGS: tuple[HeldFinding, ...] = (
    HeldFinding(
        kind="candidate_peering",
        source_asn=38198,  # Digicel Tonga
        target_asn=140504,  # Digicel Nauru
        since="2026-10-05",
        release_when=(
            "latency and other evidence support a direct TO-NR adjacency, or a "
            "trace shows the hidden middle (owner, 2026-10-05)"
        ),
        note=(
            "Finding #273, measurement 218712900 from probe 1018023. Digicel's "
            "202.43.14.173 at hop 4 (9.8ms), then the target 103.49.173.1 at "
            "hop 5 (339.7ms, +330ms in one hop). The target's replies carry "
            "ittl=240 for a TTL-5 probe packet, so the forward TTL was reset "
            "past hop 4 and about 15 routers are out of view each way. RIS "
            "(2026-10-04) lists AS3605 (Guam) as AS140504's only neighbour, and "
            "the TV-NR trace 218707166 (#161) crosses JPIX Tokyo then AS3605. "
            "The recorded direct adjacency isn't shown by the trace."
        ),
    ),
    *(
        HeldFinding(
            kind="candidate_peering",
            source_asn=140627,  # OneQode (AU-registered, no in-scope economy)
            target_asn=target_asn,
            since="2026-10-09",
            release_when=(
                "a trace shows OneQode adjacent to the target with no dark hops "
                "or TTL jump in between, or RIS lists the adjacency (owner, "
                "2026-10-09)"
            ),
            note=(
                f"Finding #{finding_id}, measurement {msm} from NR probe 1018134 "
                "(CenpacNet AS55722). Path is Nauru -> AS7131 (~36ms) -> "
                "OneQode's Sydney router 103.151.64.7 (~106ms) -> dark hops -> "
                "target at 236-254ms; 220522848's target reply TTL (244 vs 60) "
                "puts ~6 routers out of view. RIPEstat (2026-10-08) lists no "
                "AS140627 neighbour for any of the four targets. The trace "
                "doesn't show a direct adjacency."
            ),
        )
        for finding_id, target_asn, msm in (
            (286, 9241, 220501321),  # FINTEL (FJ)
            (288, 45349, 220508737),  # Telecom Fiji (FJ)
            (291, 139609, 220522848),  # SISCC (SB)
            (294, 142279, 220526456),  # Solitech (SB)
        )
    ),
)

HELD_FINDING_KEYS: frozenset[tuple[str, int, int]] = frozenset(
    (h.kind, h.source_asn, h.target_asn) for h in HELD_FINDINGS
)
