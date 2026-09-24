"""Appendix data: in-scope probes not placed optimally for regional testing, and why.

Owner's request (2026-09-25): a simple table. Built from what the pipeline
already acts on, so it can't drift from what the code does:
- probes on an ASN in `corridor_backlog.EXTERNAL_NON_CANDIDATE_ASNS` or
  `auto_classify.KNOWN_PROXY_ASNS` (reason from `PLACEMENT_REASONS`), and
- probes the geo-audit quarantined (`atlas.probe_geo_audit`): live location
  doesn't match their ASN's registered economy.
Only probes that are Connected or recently Disconnected are listed; long-dead
registrations (Abandoned, Written Off, Never Connected) are the probe-gap
report's job.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LISTING_PATH = Path("data/atlas/probe_listing.json")
DEFAULT_QUARANTINE_PATH = Path("data/atlas/probe_quarantine.json")
LISTED_STATUSES = {"Connected", "Disconnected"}

# One line per ASN the pipeline already sets aside as a vantage point. Kept
# next to the table rather than parsed out of code comments; a test checks
# every ASN in the exclusion lists has an entry here.
PLACEMENT_REASONS: dict[int, str] = {
    14593: "Starlink (AS14593): satellite egress via Starlink PoPs, not a local carrier; excluded from corridor candidacy",
    53813: "Zscaler (AS53813) proxy egress: paths describe the proxy's network, not the host's",
    23959: "Owl Limited (AS23959) VPN egress, served from Tokyo; excluded from scope",
    141695: "Pacific Community (AS141695): egresses via Zscaler (AS53813), so paths aren't Fiji's own; excluded as source and target",
    2200: "Renater (AS2200): backhauls straight to metropolitan France (~500ms), never touches Pacific transit",
}
# Not excluded, but worth stating: a regional academic network, not a commercial carrier.
ADVISORY_REASONS: dict[int, str] = {
    24390: "USP (AS24390, registered FJ): regional academic network via AARNet (Australia), not a local commercial carrier; valid source, path unverified",
}

# Per-probe measured facts. These *replace* the ASN-level reason for that probe:
# a probe's own verified path outranks a generic label for its ASN.
PROBE_NOTES: dict[int, str] = {
    # Checked 2026-09-25: Atlas's AS14593 label comes from the probe's public
    # control-plane address 14.1.90.35 (Starlink, 14.1.64.0/19), but all 33
    # cached traceroutes from it (2026-09-16..24) leave via AS139759 FSM
    # Telecom at <2ms -- a dual-uplink site (Pacific Community, Pohnpei).
    62046: "dual uplink: Atlas labels it Starlink from its control-plane address (14.1.90.35), but all 33 cached "
           "traceroutes (2026-09-16..24) leave via AS139759 FSM Telecom at <2ms -- in practice an FSM Telecom vantage "
           "point for measurements; could flip to Starlink if the site fails over",
}


@dataclass(frozen=True)
class MisplacedProbe:
    cc: str
    probe_id: int
    asn: int | None
    status: str
    reason: str


def load_misplaced_probes(
    registry: dict,
    listing_path: Path = DEFAULT_LISTING_PATH,
    quarantine_path: Path = DEFAULT_QUARANTINE_PATH,
) -> tuple[MisplacedProbe, ...]:
    if not listing_path.exists():
        return ()
    listing = json.loads(listing_path.read_text())
    quarantine = json.loads(quarantine_path.read_text()) if quarantine_path.exists() else {}
    names = {cc: e.get("name", cc) for cc, e in registry.items()}
    rows = []
    for cc, probes in listing.items():
        for p in probes:
            if p["status"] not in LISTED_STATUSES:
                continue
            asn = p.get("asn_v4")
            reasons = []
            if asn in PLACEMENT_REASONS:
                reasons.append(PLACEMENT_REASONS[asn])
            q = quarantine.get(str(p["id"]))
            if q and q.get("mismatch") and q.get("registry_cc") not in (None, "??") and asn not in PLACEMENT_REASONS:
                reasons.append(
                    f"ASN registered {names.get(q['registry_cc'], q['registry_cc'])} but probe physically in "
                    f"{names.get(q['live_country_code'], q['live_country_code'])} (geo-audit): counts as a "
                    f"{q['live_country_code']} vantage point, not {q['registry_cc']}"
                )
            if asn in ADVISORY_REASONS:
                reasons.append(ADVISORY_REASONS[asn])
            if reasons and p["id"] in PROBE_NOTES:
                reasons = [PROBE_NOTES[p["id"]]]
            if reasons:
                rows.append(MisplacedProbe(cc, p["id"], asn, p["status"], "; ".join(reasons)))
    return tuple(sorted(rows, key=lambda r: (r.cc, r.probe_id)))
