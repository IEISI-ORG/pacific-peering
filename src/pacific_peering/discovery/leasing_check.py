"""Leasing-marker check: is an in-scope ASN announcing leased or foreign-registered space?

Owner's request (2026-10-01), after AS154410 ("Marshall Telecom", MH) turned
out to announce IPXO-leased blocks that ended in Paris. Leased space is
announced under the Pacific ASN but used wherever the lessee is, so it is a
lead for offshore hosting that the ping-based `atlas.offshore_check` can miss
(it can only judge addresses that answer). Free: RIPEstat WHOIS only, no Atlas
credits, no LLM.

For every IPv4 prefix each in-scope ASN originates (the RIS cache behind
`atlas.targets.list_target_ips`), fetch WHOIS -- the authoritative RIR record
plus IRR route objects -- and look for:

- `broker`: a known IPv4 leasing broker in any attribute (mnt-by, org,
  netname, descr, remarks, geofeed...), see `LEASING_BROKER_PATTERNS`;
- `registered_abroad`: the RIR record's country isn't the ASN's economy (nor
  a neighbour it legitimately shares space with, `SHARED_REGISTRATIONS`);
- `foreign_registry`: the block is held by RIPE NCC, AFRINIC or LACNIC (or
  ARIN, for an economy with no US association).

Those three are escalated to `escalations.md` the first time each
(ASN, prefix, kind) is seen, unless already reviewed (`ACKNOWLEDGED`).
Geofeed URLs are recorded in the report for context, not escalated. Nothing
is auto-excluded: a flag is a lead for a latency test (sweep the prefix for
live hosts, ping them from AU and home-economy probes), then the owner's call.

Scheduling: monthly, plus new ASNs, same as `atlas.offshore_check` -- run from
`scripts/weekly_discovery_refresh.sh`; each run decides for itself.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

from pacific_peering.ris.bulk import DEFAULT_CACHE_DIR
from pacific_peering.ris.ripestat import fetch_whois

logger = logging.getLogger(__name__)

HISTORY_PATH = Path("outputs/reports/leasing_check_history.jsonl")
REPORT_PATH = Path("outputs/reports/leasing_check.txt")
ESCALATIONS_PATH = Path("escalations.md")
REGISTRY_PATH = Path("data/asn_registry.json")
FULL_RECHECK_DAYS = 30
FETCH_WORKERS = 6

# Known IPv4 leasing brokers / lessors, matched case-insensitively against
# every WHOIS and IRR attribute value. Only ones actually seen on Pacific
# space so far, plus the large brokers with the same footprint.
LEASING_BROKER_PATTERNS: dict[str, str] = {
    r"\bIPXO\b|ipxo\.com": "IPXO",
    r"LARUS": "Larus",
    r"\bCIL1-MNT\b|Cloud Innovation": "Cloud Innovation",
    r"INTERLIR": "Interlir",
    r"HEFICED": "Heficed",
}

# Economies whose operators legitimately hold space registered to a
# neighbour: US-associated economies use ARIN/US-registered blocks; PTI and
# IT&E serve Guam and the CNMI from one pool; Bluesky serves American Samoa
# from Samoa-registered space.
SHARED_REGISTRATIONS: dict[str, frozenset[str]] = {
    "GU": frozenset({"US", "MP"}),
    "MP": frozenset({"US", "GU"}),
    "AS": frozenset({"US", "WS"}),
    "PW": frozenset({"US"}),
    "FM": frozenset({"US"}),
    "MH": frozenset({"US"}),
}
US_ASSOCIATED = frozenset(cc for cc, ok in SHARED_REGISTRATIONS.items() if "US" in ok)

# (ASN, prefix) already reviewed by the owner: reported, never escalated.
ACKNOWLEDGED: dict[tuple[int, str], str] = {
    (58460, "154.197.42.0/24"): "Larus/Cloud Innovation-leased AFRINIC space for Digicel PNG; "
    "nearest from PG (102ms), measurement 217769793 -- used in PNG (2026-10-01)",
    (58460, "154.81.51.0/24"): "Larus/Cloud Innovation-leased AFRINIC space for Digicel PNG; "
    "50ms from AU, 76ms from PG, measurement 217770948 -- used in PNG (2026-10-01)",
    (45935, "103.36.147.0/24"): "WanTok's own block registered AU; 54-59ms from AU and VU, "
    "rDNS clients.wantok.vu, measurement 217771311 -- in Vanuatu (2026-10-01)",
    (132468, "103.188.182.0/23"): "XconX Pty Ltd (AU); already Sydney-hosted in "
    "atlas.targets.EXCLUDED_TARGET_PREFIXES (2026-09-25)",
    (9246, "120.29.200.0/21"): "Tata Communications provider-assigned space (registered IN) (2026-10-01)",
    (56017, "38.51.136.0/24"): "Cogent provider-assigned ARIN space; VITI asks for its own PF geofeed (2026-10-01)",
    (56017, "38.51.139.0/24"): "Cogent provider-assigned ARIN space; VITI asks for its own PF geofeed (2026-10-01)",
}

ESCALATED_KINDS = ("broker", "registered_abroad", "foreign_registry")


def load_history(path: Path = HISTORY_PATH) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def plan_run(registry_asns: dict[int, str], history: list[dict], now: datetime) -> tuple[str, list[int]]:
    """("full" | "new" | "skip", ASNs to check): monthly, plus ASNs never checked."""
    fulls = [h for h in history if h["mode"] == "full" and h.get("complete", True)]
    if not fulls or (now - datetime.fromisoformat(fulls[-1]["run_at"])).days >= FULL_RECHECK_DAYS:
        return "full", sorted(registry_asns)
    seen = {int(a) for h in history for a in h.get("asns", [])}
    new = sorted(a for a in registry_asns if a not in seen)
    return ("new", new) if new else ("skip", [])


def cached_prefixes(asn: int, cache_dir: Path = DEFAULT_CACHE_DIR) -> list[str]:
    """IPv4 prefixes `asn` originates, per the RIS cache (empty if none cached)."""
    path = cache_dir / f"{asn}.json"
    if not path.exists():
        return []
    return sorted({r["target_prefix"] for r in json.loads(path.read_text()) if ":" not in r["target_prefix"]})


def find_markers(whois: dict, cc: str) -> list[dict]:
    """Leasing/foreign-registration markers in one prefix's WHOIS (`ris.ripestat.fetch_whois`)."""
    markers: list[dict] = []
    attrs = [(x["key"], x["value"]) for rec in whois["records"] + whois["irr_records"] for x in rec]
    brokers = {
        name: f"{key}: {value}"
        for key, value in attrs
        for pattern, name in LEASING_BROKER_PATTERNS.items()
        if re.search(pattern, value, re.IGNORECASE)
    }
    markers += [{"kind": "broker", "detail": f"{name} ({where})"} for name, where in sorted(brokers.items())]

    countries = {x["value"].upper() for rec in whois["records"] for x in rec if x["key"].lower() == "country"}
    abroad = sorted(countries - {cc} - SHARED_REGISTRATIONS.get(cc, frozenset()))
    if abroad:
        markers.append({"kind": "registered_abroad", "detail": f"RIR record country {', '.join(abroad)}, not {cc}"})

    foreign = sorted(
        a for a in whois["authorities"]
        if a in ("ripe", "afrinic", "lacnic") or (a == "arin" and cc not in US_ASSOCIATED)
    )
    if foreign:
        markers.append({"kind": "foreign_registry", "detail": f"held by {', '.join(a.upper() for a in foreign)}"})

    geofeeds = sorted({
        m.group(0) for key, value in attrs
        if "geofeed" in key.lower() or "geofeed" in value.lower()
        for m in [re.search(r"https?://\S+", value)] if m
    })
    markers += [{"kind": "geofeed", "detail": url} for url in geofeeds]
    return markers


def _scan(targets: list[tuple[int, str, str]]) -> dict[str, dict]:
    """{prefix: {"asn", "cc", "markers"} or {"asn", "cc", "error"}} for every target."""
    def one(target: tuple[int, str, str]) -> tuple[str, dict]:
        asn, cc, prefix = target
        try:
            return prefix, {"asn": asn, "cc": cc, "markers": find_markers(fetch_whois(prefix), cc)}
        except requests.exceptions.RequestException as exc:
            logger.warning("WHOIS fetch failed for %s (AS%d): %s", prefix, asn, exc)
            return prefix, {"asn": asn, "cc": cc, "error": str(exc)}

    with ThreadPoolExecutor(FETCH_WORKERS) as pool:
        return dict(pool.map(one, targets))


def _flag_keys(results: dict[str, dict]) -> set[tuple[int, str, str]]:
    return {
        (r["asn"], prefix, m["kind"])
        for prefix, r in results.items()
        for m in r.get("markers", [])
        if m["kind"] in ESCALATED_KINDS and (r["asn"], prefix) not in ACKNOWLEDGED
    }


def latest_flagged(history: list[dict]) -> dict | None:
    """The latest complete full run, summarised for the report appendix:
    {"run_at", "prefixes_checked", "geofeed_prefixes", "entries": [{"asn", "cc",
    "prefix", "markers": [str], "verdict": ACKNOWLEDGED note or None}]}; None if
    no complete full run exists yet."""
    fulls = [h for h in history if h["mode"] == "full" and h.get("complete")]
    if not fulls:
        return None
    run = fulls[-1]
    entries = []
    for prefix, r in sorted(run["results"].items(), key=lambda kv: (kv[1]["asn"], kv[0])):
        flagged = [m for m in r.get("markers", []) if m["kind"] in ESCALATED_KINDS]
        if flagged:
            entries.append({"asn": r["asn"], "cc": r["cc"], "prefix": prefix,
                            "markers": [f"{m['kind']}: {m['detail']}" for m in flagged],
                            "verdict": ACKNOWLEDGED.get((r["asn"], prefix))})
    geofeeds = sum(any(m["kind"] == "geofeed" for m in r.get("markers", [])) for r in run["results"].values())
    return {"run_at": run["run_at"], "prefixes_checked": len(run["results"]),
            "geofeed_prefixes": geofeeds, "entries": entries}


def new_flags(history: list[dict], results: dict[str, dict]) -> list[tuple[int, str, str]]:
    """Escalatable, unacknowledged markers no earlier run has already reported."""
    before = {(f[0], f[1], f[2]) for h in history for f in h.get("flags", [])}
    return sorted(_flag_keys(results) - before)


def run_check(now: datetime | None = None, force_full: bool = False) -> dict | None:
    now = now or datetime.now(timezone.utc)
    registry = json.loads(REGISTRY_PATH.read_text())
    asn_cc = {a: cc for cc, e in registry.items() for a in e["asns"]}
    history = load_history()
    mode, asns = ("full", sorted(asn_cc)) if force_full else plan_run(asn_cc, history, now)
    targets = [(asn, asn_cc[asn], p) for asn in asns for p in cached_prefixes(asn)]
    logger.info("Leasing check: mode=%s, %d ASNs, %d prefixes", mode, len(asns), len(targets))
    if mode == "skip":
        return None
    results = _scan(targets)
    fresh = new_flags(history, results)
    snapshot = {
        "run_at": now.isoformat(), "mode": mode, "asns": asns, "results": results,
        "flags": sorted(_flag_keys(results)),
        "complete": not any("error" in r for r in results.values()),
    }
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a") as f:
        f.write(json.dumps(snapshot) + "\n")
    REPORT_PATH.write_text(render_report(snapshot, fresh))
    _escalate(fresh, results, now)
    logger.info("Leasing check done: %d flag(s), %d new", len(snapshot["flags"]), len(fresh))
    return snapshot


def _lines(results: dict[str, dict], keep) -> list[str]:
    out = []
    for prefix, r in sorted(results.items(), key=lambda kv: (kv[1]["asn"], kv[0])):
        ms = [m for m in r.get("markers", []) if keep(r, prefix, m)]
        if ms:
            out.append(f"  AS{r['asn']} ({r['cc']}) {prefix}: " + "; ".join(f"{m['kind']}: {m['detail']}" for m in ms))
    return out


def render_report(snapshot: dict, fresh: list[tuple[int, str, str]]) -> str:
    res = snapshot["results"]
    flagged = lambda r, p, m: m["kind"] in ESCALATED_KINDS  # noqa: E731
    errors = sorted(p for p, r in res.items() if "error" in r)
    acked = [
        f"  AS{asn} {prefix}: {note}" for (asn, prefix), note in sorted(ACKNOWLEDGED.items())
        if prefix in res
    ]
    lines = [
        f"Leasing-marker check -- {snapshot['run_at'][:10]} ({snapshot['mode']} run)",
        "Auto-generated by `pacific-peering-leasing-check` (discovery/leasing_check.py): monthly, plus new ASNs.",
        "WHOIS (RIR record + IRR route objects) for every IPv4 prefix each in-scope ASN originates. Flags:",
        "`broker` (a known IPv4 leasing broker), `registered_abroad` (RIR country isn't the economy),",
        "`foreign_registry` (RIPE/AFRINIC/LACNIC, or ARIN outside US-associated economies). New, unreviewed",
        "flags go to escalations.md as leads for a latency test. Nothing is auto-excluded.",
        "",
        f"Prefixes checked: {len(res)} across {len(snapshot['asns'])} ASNs; WHOIS errors: {len(errors)}.",
        f"New flags this run: {', '.join(f'AS{a} {p} ({k})' for a, p, k in fresh) or 'none'}",
        "",
        "Flagged, not yet reviewed (escalated when first seen):",
        *(_lines(res, lambda r, p, m: flagged(r, p, m) and (r["asn"], p) not in ACKNOWLEDGED) or ["  (none)"]),
        "",
        "Reviewed (ACKNOWLEDGED in leasing_check.py; not escalated):",
        *(acked or ["  (none)"]),
        "",
        "Geofeeds published (context only):",
        *(_lines(res, lambda r, p, m: m["kind"] == "geofeed") or ["  (none)"]),
    ]
    if errors:
        lines += ["", "WHOIS fetch errors (retried next run):", *(f"  {p}" for p in errors)]
    return "\n".join(lines) + "\n"


def _escalate(fresh: list[tuple[int, str, str]], results: dict[str, dict], now: datetime) -> None:
    by_prefix: dict[tuple[int, str], list[str]] = {}
    for asn, prefix, kind in fresh:
        detail = next(m["detail"] for m in results[prefix]["markers"] if m["kind"] == kind)
        by_prefix.setdefault((asn, prefix), []).append(f"{kind}: {detail}")
    if not by_prefix:
        return
    blocks = [
        f"\n## AS{asn} ({results[prefix]['cc']}) -- {prefix} leased or foreign-registered space\n"
        f"- reason: leasing-marker check (discovery/leasing_check.py)\n- detail: {'; '.join(details)}\n"
        f"- action: sweep the prefix for live hosts and ping them from AU and home-economy probes; "
        f"then owner review (acknowledge, exclude the prefix as a target, or exclude the ASN)\n"
        f"- flagged: {now.isoformat()}\n"
        for (asn, prefix), details in sorted(by_prefix.items())
    ]
    with ESCALATIONS_PATH.open("a") as f:
        f.write("".join(blocks))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--full", action="store_true", help="check every ASN regardless of schedule")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_check(force_full=args.full)


if __name__ == "__main__":
    main()
