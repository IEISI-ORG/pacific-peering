"""Offshore-hosting check: are an in-scope ASN's addresses physically in its economy?

Owner's request (2026-09-24), after AS136996 (Pacific Networks, VU) turned
out to announce address space hosted in Sydney (`discovery.excluded_asns`,
category `offshore_hosted`). Pings up to `MAX_PREFIXES_PER_ASN` addresses per
in-scope ASN (one per originated prefix, `atlas.targets.list_target_ips`) from
probes in likely hosting countries (AU/NZ/US/JP), then applies a physics test:
light in fibre covers about 100 km of round-trip distance per millisecond, so a
probe that measures RTT below `PHYSICS_MARGIN` x (distance from that probe to
the economy's capital / 100) has proven the address is *not* in that economy.

Per address: `offshore` (some probe beat physics -- the probe, its RTT and the
physical minimum are recorded), `consistent` (answered, nothing beat physics),
`no_response`, or `not_measured` (Atlas refused the measurement). An ASN is
`offshore` if any of its tested addresses is. Flags are candidates for the
owner, never auto-excluded: each new one is appended to `escalations.md`.

Scheduling (owner): monthly, plus whenever new ASNs are added. Run nightly by
`scripts/nightly_corridor_testing.sh`; each run decides for itself -- a full
check if the last full run is `FULL_RECHECK_DAYS`+ days old, otherwise only
registry ASNs never checked before, otherwise nothing (no credits).
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from pacific_peering.atlas.client import create_ping_measurement, fetch_raw_results
from pacific_peering.atlas.smoketest import DEFAULT_RAW_DIR
from pacific_peering.atlas.targets import list_target_ips
from pacific_peering.discovery.economy_coordinates import ECONOMY_LATLON

logger = logging.getLogger(__name__)

HISTORY_PATH = Path("outputs/reports/offshore_check_history.jsonl")
REPORT_PATH = Path("outputs/reports/offshore_check.txt")
ESCALATIONS_PATH = Path("escalations.md")
REGISTRY_PATH = Path("data/asn_registry.json")

HUB_PROBE_SPECS = (
    {"type": "country", "value": "AU", "requested": 3},
    {"type": "country", "value": "NZ", "requested": 2},
    {"type": "country", "value": "US", "requested": 3},
    {"type": "country", "value": "JP", "requested": 2},
)
MAX_PREFIXES_PER_ASN = 3
PHYSICS_MARGIN = 0.7  # headroom for capital-vs-island distance and coordinate slop
FIBRE_KM_PER_MS_RTT = 100.0
FULL_RECHECK_DAYS = 30
BATCH_SIZE = 20

OFFSHORE = "offshore"
CONSISTENT = "consistent"
NO_RESPONSE = "no_response"
NOT_MEASURED = "not_measured"


def great_circle_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    (la1, lo1), (la2, lo2) = [(math.radians(x), math.radians(y)) for x, y in (a, b)]
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def physical_min_rtt_ms(probe_latlon: tuple[float, float], cc: str) -> float:
    return great_circle_km(probe_latlon, ECONOMY_LATLON[cc]) / FIBRE_KM_PER_MS_RTT


def judge_address(results: list[dict], cc: str, probe_latlon: dict[int, tuple[float, float]]) -> dict:
    """Verdict for one address from its raw Atlas ping results."""
    answered, violations = 0, []
    for r in results:
        rtt = r.get("min")
        if rtt is None or rtt < 0:
            continue
        answered += 1
        where = probe_latlon.get(r["prb_id"])
        if where is None:
            continue
        needed = physical_min_rtt_ms(where, cc)
        if rtt < PHYSICS_MARGIN * needed:
            violations.append({"probe": r["prb_id"], "rtt_ms": round(rtt, 2), "physical_min_ms": round(needed, 1)})
    if violations:
        return {"verdict": OFFSHORE, "answered": answered, "violations": sorted(violations, key=lambda v: v["rtt_ms"])}
    return {"verdict": CONSISTENT if answered else NO_RESPONSE, "answered": answered, "violations": []}


def asn_verdict(addresses: dict[str, dict]) -> str:
    verdicts = {a["verdict"] for a in addresses.values()}
    for v in (OFFSHORE, CONSISTENT, NO_RESPONSE):
        if v in verdicts:
            return v
    return NOT_MEASURED


def load_history(path: Path = HISTORY_PATH) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def plan_run(registry_asns: dict[int, str], history: list[dict], now: datetime) -> tuple[str, list[int]]:
    """("full" | "new" | "skip", ASNs to check), per the monthly/new-ASN schedule."""
    fulls = [h for h in history if h["mode"] == "full"]
    if not fulls or (now - datetime.fromisoformat(fulls[-1]["run_at"])).days >= FULL_RECHECK_DAYS:
        return "full", sorted(registry_asns)
    seen = {int(a) for h in history for a in h["asns"]}
    new = sorted(a for a in registry_asns if a not in seen)
    return ("new", new) if new else ("skip", [])


def _probe_locations(probe_ids: set[int]) -> dict[int, tuple[float, float]]:
    locations: dict[int, tuple[float, float]] = {}
    ids = sorted(probe_ids)
    for i in range(0, len(ids), 400):
        response = requests.get(
            "https://atlas.ripe.net/api/v2/probes/",
            params={"id__in": ",".join(map(str, ids[i:i + 400])), "fields": "id,geometry", "page_size": 500},
            timeout=30,
        )
        response.raise_for_status()
        for p in response.json()["results"]:
            coords = (p.get("geometry") or {}).get("coordinates")
            if coords:
                locations[p["id"]] = (coords[1], coords[0])
    return locations


def _fire_all(targets: list[tuple[int, str, str]]) -> dict[str, int | None]:
    """Create ping measurements in batches; {address: measurement_id or None if refused}."""
    ids: dict[str, int | None] = {}
    for i in range(0, len(targets), BATCH_SIZE):
        for asn, cc, address in targets[i:i + BATCH_SIZE]:
            try:
                ids[address] = create_ping_measurement(
                    list(HUB_PROBE_SPECS), address, f"pacific-peering offshore-check AS{asn} {cc} to {address}"
                )
            except requests.HTTPError as e:
                detail = e.response.text[:300] if e.response is not None else str(e)
                logger.error("Atlas refused ping to %s (AS%d): %s", address, asn, detail)
                ids[address] = None
    return ids


def _collect(ids: dict[str, int | None], wait_s: float = 240.0) -> dict[str, list[dict]]:
    """Wait once for every measurement, then fetch and cache each one's raw results.

    Raw only: ping results don't go through the traceroute parser. Cached so a
    run can be re-judged later (e.g. with a different margin) at no cost.
    """
    time.sleep(wait_s)  # one-off pings finish in ~1-3 minutes; fetch once, after all have had time
    results: dict[str, list[dict]] = {}
    DEFAULT_RAW_DIR.mkdir(parents=True, exist_ok=True)
    for address, mid in ids.items():
        if mid is None:
            continue
        raw = fetch_raw_results(mid)
        (DEFAULT_RAW_DIR / f"{mid}.json").write_text(json.dumps(raw, indent=2) + "\n")
        results[address] = raw
    return results


def run_check(fire: bool, now: datetime | None = None, force_full: bool = False) -> dict | None:
    now = now or datetime.now(timezone.utc)
    registry = json.loads(REGISTRY_PATH.read_text())
    asn_cc = {a: cc for cc, e in registry.items() for a in e["asns"]}
    history = load_history()
    mode, asns = ("full", sorted(asn_cc)) if force_full else plan_run(asn_cc, history, now)
    targets: list[tuple[int, str, str]] = []
    untestable: list[int] = []
    for asn in asns:
        try:
            addresses = list_target_ips(asn)[:MAX_PREFIXES_PER_ASN]
        except (FileNotFoundError, ValueError):
            addresses = []
        if not addresses:
            untestable.append(asn)
        targets += [(asn, asn_cc[asn], a) for a in addresses]
    logger.info("Offshore check: mode=%s, %d ASNs, %d addresses, %d untestable (no originated prefix)",
                mode, len(asns), len(targets), len(untestable))
    if mode == "skip" or not fire:
        if not fire:
            logger.info("Dry run -- pass --fire to ping the addresses and record")
        return None
    ids = _fire_all(targets)
    raw = _collect(ids)
    locations = _probe_locations({r["prb_id"] for rs in raw.values() for r in rs})
    per_asn: dict[str, dict] = {}
    for asn, cc, address in targets:
        judged = judge_address(raw[address], cc, locations) if address in raw else {"verdict": NOT_MEASURED, "answered": 0, "violations": []}
        entry = per_asn.setdefault(str(asn), {"cc": cc, "addresses": {}})
        entry["addresses"][address] = {**judged, "measurement_id": ids.get(address)}
    for entry in per_asn.values():
        entry["verdict"] = asn_verdict(entry["addresses"])
    snapshot = {
        "run_at": now.isoformat(), "mode": mode, "asns": sorted(per_asn, key=int) + [str(a) for a in untestable],
        "untestable": untestable, "results": per_asn,
    }
    new_flags = _new_offshore(history, per_asn)
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a") as f:
        f.write(json.dumps(snapshot) + "\n")
    REPORT_PATH.write_text(render_report(snapshot, new_flags))
    _escalate(new_flags, per_asn, now)
    logger.info("Offshore check done: %d offshore flag(s), %d new", sum(e["verdict"] == OFFSHORE for e in per_asn.values()), len(new_flags))
    return snapshot


def _new_offshore(history: list[dict], per_asn: dict[str, dict]) -> list[str]:
    before = {a for h in history for a, e in h["results"].items() if e["verdict"] == OFFSHORE}
    return sorted((a for a, e in per_asn.items() if e["verdict"] == OFFSHORE and a not in before), key=int)


def render_report(snapshot: dict, new_flags: list[str]) -> str:
    res = snapshot["results"]
    counts = {v: sum(e["verdict"] == v for e in res.values()) for v in (OFFSHORE, CONSISTENT, NO_RESPONSE, NOT_MEASURED)}
    lines = [
        f"Offshore-hosting check -- {snapshot['run_at'][:10]} ({snapshot['mode']} run)",
        "Auto-generated by `pacific-peering-offshore-check` (atlas/offshore_check.py): monthly, plus new ASNs.",
        "Pings up to 3 addresses per in-scope ASN from AU/NZ/US/JP probes. `offshore` = some probe measured",
        f"an RTT below {PHYSICS_MARGIN} x the fibre minimum from that probe to the economy's capital -- physically",
        "impossible if the address were in its economy. Flags are for the owner to review; none is auto-excluded.",
        "",
        f"ASNs: {counts[OFFSHORE]} offshore, {counts[CONSISTENT]} consistent, {counts[NO_RESPONSE]} no response, "
        f"{counts[NOT_MEASURED]} not measured, {len(snapshot['untestable'])} untestable (no originated prefix).",
        f"New offshore flags this run: {', '.join('AS' + a for a in new_flags) or 'none'}",
        "",
        "Offshore candidates:",
    ]
    for asn, e in sorted(res.items(), key=lambda kv: int(kv[0])):
        if e["verdict"] != OFFSHORE:
            continue
        lines.append(f"  AS{asn} ({e['cc']})")
        for address, a in e["addresses"].items():
            if a["verdict"] == OFFSHORE:
                v = a["violations"][0]
                lines.append(f"    {address}: probe {v['probe']} {v['rtt_ms']}ms < physical min {v['physical_min_ms']}ms "
                             f"(measurement {a['measurement_id']}, {len(a['violations'])} probe(s) beat physics)")
            else:
                lines.append(f"    {address}: {a['verdict']}")
    if not counts[OFFSHORE]:
        lines.append("  (none)")
    return "\n".join(lines) + "\n"


def _escalate(new_flags: list[str], per_asn: dict[str, dict], now: datetime) -> None:
    if not new_flags:
        return
    blocks = []
    for asn in new_flags:
        e = per_asn[asn]
        detail = "; ".join(
            f"{addr}: probe {a['violations'][0]['probe']} {a['violations'][0]['rtt_ms']}ms < "
            f"{a['violations'][0]['physical_min_ms']}ms minimum (measurement {a['measurement_id']})"
            for addr, a in e["addresses"].items() if a["verdict"] == OFFSHORE
        )
        blocks.append(
            f"\n## AS{asn} ({e['cc']}) -- possible offshore-hosted address space\n"
            f"- reason: offshore-hosting check (atlas/offshore_check.py)\n- detail: {detail}\n"
            f"- action: owner review; if confirmed, add to discovery/excluded_asns.py (offshore_hosted)\n"
            f"- flagged: {now.isoformat()}\n"
        )
    with ESCALATIONS_PATH.open("a") as f:
        f.write("".join(blocks))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fire", action="store_true", help="ping the addresses (spends Atlas credits) and record")
    parser.add_argument("--full", action="store_true", help="check every ASN regardless of schedule")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_check(fire=args.fire, force_full=args.full)


if __name__ == "__main__":
    main()
