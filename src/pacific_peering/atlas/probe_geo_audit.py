"""Audit RIPE Atlas probe geography against this project's own ASN->economy classification.

`asn_probe_registry.json` (built per-economy, via `atlas.asn_probes`) and
`asn_registry.json` (Phase 0b's per-ASN WHOIS/APNIC-based economy
classification) are two independent data sources. The first records which
ASNs *anywhere among the 20 tracked economies* currently have a connected
probe; the second labels each tracked ASN with one economy. For almost
every ASN the two agree by construction, but a regional organization with
one ASN and infrastructure spread across several countries breaks that
one-ASN-one-country assumption -- and `atlas.probes`'s own docstring
already documents why this matters in practice: source selection fires by
Atlas *country* targeting, not the specific ASN, so a mislabeled economy
silently changes which real vantage point a "confirmed" finding gets
attributed to.

Two real cases found this way (2026-09-19): AS141695 (Pacific Community)
was tracked as New Caledonia but its only connected probe live-geolocates
to Fiji (since reclassified); AS24390 (University of the South Pacific) is
correctly tracked as Fiji for the organization, but its only connected
probe live-geolocates to Tonga, a real USP satellite campus -- not
reclassified, since USP genuinely has a Fiji home base, but quarantined
from being used as a Fiji source (see `load_quarantine`).

This checks every ASN in `asn_probe_registry.json` (i.e. every ASN this
project could actually fire a measurement from) against each of its
connected probes' live Atlas country_code and geometry -- 20 economies'
worth of ASNs is a handful of probes, so a live per-probe API call each
run is cheap and avoids trusting a geographic classification that could
have gone stale (probes reconnect on different networks; RIPE Atlas
`country_code` is authoritative for where the equipment actually is).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

from pacific_peering.atlas.asn_probes import DEFAULT_REGISTRY_PATH, load_asn_probe_registry
from pacific_peering.discovery.registry import DEFAULT_OUTPUT_PATH as DEFAULT_ASN_REGISTRY_PATH

logger = logging.getLogger(__name__)

ATLAS_BASE_URL = "https://atlas.ripe.net/api/v2"
_DEFAULT_TIMEOUT = 30.0
_REQUEST_DELAY_SECONDS = 0.15  # be polite to Atlas's free, unauthenticated endpoint

DEFAULT_QUARANTINE_PATH = Path("data/atlas/probe_quarantine.json")


@dataclass(frozen=True)
class ProbeGeoRecord:
    """One connected probe's live geography, checked against its ASN's registry economy."""

    probe_id: int
    asn: int
    registry_cc: str  # this ASN's economy per asn_registry.json ("??" if untracked/external)
    live_country_code: str | None
    live_lat: float | None
    live_lon: float | None
    mismatch: bool


def fetch_probe_geometry(probe_id: int, timeout: float = _DEFAULT_TIMEOUT) -> dict:
    """Live country_code + lat/lon for one probe, straight from Atlas -- not the local cache."""
    response = requests.get(f"{ATLAS_BASE_URL}/probes/{probe_id}/", timeout=timeout)
    response.raise_for_status()
    data = response.json()
    coords = (data.get("geometry") or {}).get("coordinates")
    lon, lat = (coords[0], coords[1]) if coords else (None, None)
    return {"country_code": data.get("country_code"), "lat": lat, "lon": lon}


def audit_tracked_probes(
    probe_registry_path: Path = DEFAULT_REGISTRY_PATH,
    asn_registry_path: Path = DEFAULT_ASN_REGISTRY_PATH,
) -> list[ProbeGeoRecord]:
    """Check every currently-tracked (connected-probe) ASN's live probe geography.

    "Tracked" here means present in `asn_probe_registry.json` -- the exact
    set of ASNs `corridor_backlog.enumerate_candidate_corridors` could pick
    as a candidate source. Everything else (probes Atlas lists but this
    project has never selected as a source) isn't in scope for this check.
    """
    probe_registry = load_asn_probe_registry(probe_registry_path)
    asn_registry = json.loads(asn_registry_path.read_text())
    asn_to_cc = {asn: cc for cc, entry in asn_registry.items() for asn in entry["asns"]}

    records: list[ProbeGeoRecord] = []
    for asn, probe_ids in probe_registry.items():
        registry_cc = asn_to_cc.get(asn, "??")
        for probe_id in probe_ids:
            geo = fetch_probe_geometry(probe_id)
            time.sleep(_REQUEST_DELAY_SECONDS)
            records.append(
                ProbeGeoRecord(
                    probe_id=probe_id,
                    asn=asn,
                    registry_cc=registry_cc,
                    live_country_code=geo["country_code"],
                    live_lat=geo["lat"],
                    live_lon=geo["lon"],
                    mismatch=geo["country_code"] != registry_cc,
                )
            )
    return records


def write_quarantine(
    records: list[ProbeGeoRecord], path: Path = DEFAULT_QUARANTINE_PATH
) -> dict[int, dict]:
    """Persist "do not use as a source for their registry economy" for every mismatched probe.

    Deliberately keyed by probe ID, not ASN: a regional-org ASN (AS24390)
    can have some probes that genuinely match their registry economy and
    others that don't -- quarantine is a per-probe fact, not a per-ASN one.
    Doesn't touch `EXTERNAL_NON_CANDIDATE_ASNS` (Renater, Starlink) --
    those are already excluded from candidacy entirely regardless of
    geography, so flagging their probes here would just be noise.
    """
    now = datetime.now(timezone.utc).isoformat()
    quarantine = {
        str(r.probe_id): {**asdict(r), "checked_at": now} for r in records if r.mismatch
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(quarantine, indent=2, sort_keys=True) + "\n")
    logger.info(
        "Probe geo-audit: %d/%d tracked probes quarantined (live location doesn't match "
        "their ASN's registry economy)",
        len(quarantine),
        len(records),
    )
    return quarantine


def load_quarantine(path: Path = DEFAULT_QUARANTINE_PATH) -> dict[int, dict]:
    """Load the persisted quarantine, keyed by probe ID (int)."""
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    return {int(probe_id): record for probe_id, record in payload.items()}


def is_asn_quarantined_for(asn: int, cc: str, quarantine: dict[int, dict] | None = None) -> bool:
    """True if every one of `asn`'s connected probes is quarantined against economy `cc`.

    An ASN with at least one probe genuinely verified in `cc` is still a
    valid source for it, even if the ASN also has other, quarantined
    probes elsewhere (the regional-org case) -- so this only excludes the
    ASN when *none* of its probes back up the claimed economy.
    """
    quarantine = quarantine if quarantine is not None else load_quarantine()
    asn_records = [r for r in quarantine.values() if r["asn"] == asn and r["registry_cc"] == cc]
    if not asn_records:
        return False
    all_probes_for_asn = set(load_asn_probe_registry().get(asn, []))
    quarantined_probes = {r["probe_id"] for r in asn_records}
    return all_probes_for_asn.issubset(quarantined_probes) and bool(all_probes_for_asn)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    records = audit_tracked_probes()
    quarantine = write_quarantine(records)
    for probe_id, record in sorted(quarantine.items()):
        logger.info(
            "AS%s probe %s: registry says %s, live location is %s (%s, %s) -- quarantined",
            record["asn"], probe_id, record["registry_cc"], record["live_country_code"],
            record["live_lat"], record["live_lon"],
        )


if __name__ == "__main__":
    main()
