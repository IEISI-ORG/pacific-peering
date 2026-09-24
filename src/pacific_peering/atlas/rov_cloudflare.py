"""Weekly ROV test: where do traceroutes to Cloudflare's RPKI-invalid prefix stop?

Project owner's idea (2026-09-24): Cloudflare announces deliberately
RPKI-valid and RPKI-invalid test prefixes (the ones behind
valid/invalid.rpki.cloudflare.com). A network doing Route Origin Validation
drops the invalid route, so from every probe we trace both. Where the valid
trace gets through but the invalid one dies, something on that path is
filtering, and the last ASN the invalid trace reached is where it died.

Per probe and address family, one of three labels:
- `not_filtered`: the invalid target answered, or the invalid trace reached
  Cloudflare's own network (AS13335) -- every network before it carried the
  invalid route. (Seen 2026-09-24: PG 50365's invalid trace reached AS13335
  and died inside it; that is not filtering on the path.)
- `filtered`: the valid target answered, the invalid one didn't.
  `drop_asn` is the last ASN the invalid trace reached: that network had no
  route to the invalid prefix, because it filters or its upstream does --
  a traceroute can't tell those two apart. None means the trace died
  before its first public hop (inside the probe's own site or CGNAT).
- `inconclusive`: no result for one of the pair, the valid target itself
  didn't answer (no baseline), or the path starts at a known proxy
  (`auto_classify.KNOWN_PROXY_ASNS`) -- that tests the proxy, not the
  probe's own network.

`diverged` records where the valid and invalid AS paths first differ
(e.g. PG 50365: valid via AS4826, invalid via AS7474). A network that
drops the invalid route can push its customer's invalid traffic onto a
different upstream, so a divergence is ROV evidence even when the invalid
trace still gets through.

Cloudflare is anycast: some paths never leave the probe's own network
(e.g. NC's ~0.6ms Cloudflare IPv6), in which case the test only speaks for
the probe's own ISP. That's still the most useful thing it can say.

Runs Wednesdays from `scripts/nightly_corridor_testing.sh` (4 measurements:
valid/invalid x IPv4/IPv6). Before firing, checks via RIPEstat that the
targets are still RPKI valid/invalid; if Cloudflare ever changes them the
run stops rather than recording meaningless verdicts. Results go to
`outputs/reports/rov_cloudflare.txt` and `rov_cloudflare_history.jsonl`.
`main()` only checks targets and prints the plan unless `--fire` is given.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pacific_peering.analysis.auto_classify import KNOWN_PROXY_ASNS
from pacific_peering.analysis.traceroute_topology import extract_as_sequence, resolve_traceroute_hops
from pacific_peering.atlas.probes import load_probe_listing
from pacific_peering.atlas.smoketest import refetch_parsed
from pacific_peering.atlas.starlink_anchors import run_starlink_anchor_traces, summarize_anchor_trace
from pacific_peering.ris.ripestat import fetch_rpki_status

logger = logging.getLogger(__name__)

HISTORY_PATH = Path("outputs/reports/rov_cloudflare_history.jsonl")
REPORT_PATH = Path("outputs/reports/rov_cloudflare.txt")
MEASUREMENT_LABEL = "rov-cloudflare"

# (primary, fallback) per role and family -- the A/AAAA records of
# valid/invalid.rpki.cloudflare.com as of 2026-09-24. Fallback on Atlas's
# per-target concurrency cap, same as the DNS anchors.
ROV_TARGETS: dict[int, dict[str, tuple[str, str]]] = {
    4: {
        "valid": ("104.17.230.6", "104.17.231.6"),
        "invalid": ("103.21.244.8", "103.21.244.9"),
    },
    6: {
        "valid": ("2606:4700::6811:e606", "2606:4700::6811:e706"),
        "invalid": ("2606:4700:7000::6715:f408", "2606:4700:7000::6715:f409"),
    },
}
EXPECTED_RPKI = {"valid": {"valid"}, "invalid": {"invalid", "invalid_asn", "invalid_length"}}

ORIGIN_ASN = 13335  # Cloudflare, origin of every target prefix

FILTERED = "filtered"
NOT_FILTERED = "not_filtered"
INCONCLUSIVE = "inconclusive"


def check_targets() -> tuple[bool, dict[str, str]]:
    """Confirm every target is still in its expected RPKI state; returns (ok, {address: status})."""
    statuses, ok = {}, True
    for roles in ROV_TARGETS.values():
        for role, addresses in roles.items():
            for address in addresses:
                status = fetch_rpki_status(address).status
                statuses[address] = status
                if status not in EXPECTED_RPKI[role]:
                    logger.error("ROV target %s (%s) is RPKI %r, expected %s", address, role, status, EXPECTED_RPKI[role])
                    ok = False
    return ok, statuses


def probes_for_af(listing: dict[str, list[dict]], af: int) -> dict[int, dict]:
    """Connected probes with an ASN for this family: {probe_id: {cc, asn}}."""
    key = f"asn_v{af}"
    return {
        p["id"]: {"cc": cc, "asn": p[key]}
        for cc, probes in listing.items()
        for p in probes
        if p["status"] == "Connected" and p.get(key)
    }


def as_path(trace: dict) -> list[int]:
    """The trace's AS-level path (hops resolved via RIPEstat/PeeringDB, private hops skipped)."""
    return [hop.asn for hop in extract_as_sequence(resolve_traceroute_hops(trace["hops"]))]


def path_divergence(valid_path: list[int], invalid_path: list[int]) -> dict | None:
    """Where the two AS paths first differ: {after, valid_next, invalid_next}, or None if they don't."""
    for i, (v, inv) in enumerate(zip(valid_path, invalid_path)):
        if v != inv:
            return {"after": valid_path[i - 1] if i else None, "valid_next": v, "invalid_next": inv}
    return None


def classify_probe(
    valid: dict | None,
    invalid: dict | None,
    valid_path: list[int],
    invalid_path: list[int],
) -> dict:
    """One probe's verdict for one family, from its valid and invalid traces and their AS paths."""
    verdict = {"label": INCONCLUSIVE, "drop_asn": None, "reason": None, "diverged": None}
    if valid is None or invalid is None:
        return {**verdict, "reason": "no result for one of the pair"}
    first = (valid_path or invalid_path or [None])[0]
    if first in KNOWN_PROXY_ASNS:
        return {**verdict, "reason": f"path starts at proxy AS{first} ({KNOWN_PROXY_ASNS[first]})"}
    verdict["diverged"] = path_divergence(valid_path, invalid_path)
    if summarize_anchor_trace(invalid).reached_target:
        return {**verdict, "label": NOT_FILTERED}
    if invalid_path and invalid_path[-1] == ORIGIN_ASN:
        return {**verdict, "label": NOT_FILTERED, "reason": "invalid trace reached Cloudflare's network; target silent"}
    if not summarize_anchor_trace(valid).reached_target:
        return {**verdict, "reason": "valid target unreached (no baseline)"}
    drop_asn = invalid_path[-1] if invalid_path else None
    reason = None if drop_asn else "died before first public hop"
    return {**verdict, "label": FILTERED, "drop_asn": drop_asn, "reason": reason}


def classify_measurements(
    traces: list[dict], af: int, probes: dict[int, dict], path_of=as_path
) -> dict[int, dict]:
    """Verdict per probe for one family, from all that family's valid+invalid traces."""
    role_of = {addr: role for role, pair in ROV_TARGETS[af].items() for addr in pair}
    by_probe: dict[int, dict[str, dict]] = {}
    for trace in traces:
        role = role_of.get(trace["target"])
        if role:
            by_probe.setdefault(trace["probe_id"], {})[role] = trace
    verdicts = {}
    for probe_id in probes:
        pair = by_probe.get(probe_id, {})
        valid, invalid = pair.get("valid"), pair.get("invalid")
        verdicts[probe_id] = classify_probe(
            valid, invalid, path_of(valid) if valid else [], path_of(invalid) if invalid else []
        )
    return verdicts


def build_snapshot(
    listing: dict[str, list[dict]],
    verdicts: dict[int, dict[int, dict]],
    measurement_ids: dict[int, list[int]],
    target_status: dict[str, str],
    now: datetime,
) -> dict:
    probes: dict[str, dict] = {}
    for af in (4, 6):
        for pid, info in probes_for_af(listing, af).items():
            entry = probes.setdefault(str(pid), {"cc": info["cc"]})
            entry[f"asn_v{af}"] = info["asn"]
            entry[f"v{af}"] = verdicts.get(af, {}).get(pid)
    economies: dict[str, dict[str, dict[str, int]]] = {}
    drop_asns: Counter = Counter()
    for entry in probes.values():
        for af in (4, 6):
            verdict = entry.get(f"v{af}")
            if verdict is None:
                continue
            economies.setdefault(entry["cc"], {}).setdefault(f"v{af}", Counter())[verdict["label"]] += 1
            if verdict["label"] == FILTERED:
                drop_asns[f"v{af}:{verdict['drop_asn']}"] += 1
    return {
        "date": now.strftime("%Y-%m-%d"),
        "measurement_ids": {f"v{af}": ids for af, ids in measurement_ids.items()},
        "target_rpki": target_status,
        "economies": {cc: {k: dict(v) for k, v in sorted(e.items())} for cc, e in sorted(economies.items())},
        "drop_asns": dict(drop_asns.most_common()),
        "probes": dict(sorted(probes.items(), key=lambda kv: int(kv[0]))),
    }


def diff_snapshots(previous: dict | None, current: dict) -> list[str]:
    if previous is None:
        return ["First snapshot -- nothing to compare against."]
    changes = []
    for pid, now_entry in current["probes"].items():
        before = previous["probes"].get(pid, {})
        for af in ("v4", "v6"):
            was, now_ = before.get(af), now_entry.get(af)
            if not was or not now_ or INCONCLUSIVE in (was["label"], now_["label"]):
                continue
            if was["label"] != now_["label"]:
                changes.append(f"probe {pid} ({now_entry['cc']}) {af}: {was['label']} -> {now_['label']}")
            elif now_["label"] == FILTERED and was["drop_asn"] != now_["drop_asn"]:
                changes.append(f"probe {pid} ({now_entry['cc']}) {af}: drop point AS{was['drop_asn']} -> AS{now_['drop_asn']}")
    return changes


def _cell(verdict: dict | None) -> str:
    if verdict is None:
        return "-"
    if verdict["label"] == FILTERED:
        cell = f"filtered@AS{verdict['drop_asn']}" if verdict["drop_asn"] else "filtered@local"
    else:
        cell = verdict["label"]
    d = verdict.get("diverged")
    if d:
        cell += f" (split: valid AS{d['valid_next']} / invalid AS{d['invalid_next']})"
    return cell


def render_report(snapshot: dict, changes: list[str]) -> str:
    lines = [
        f"Cloudflare ROV test -- {snapshot['date']}",
        "Auto-generated weekly (Wednesday) by `pacific-peering-rov-cloudflare` (atlas/rov_cloudflare.py).",
        "Traces to Cloudflare's RPKI-valid and RPKI-invalid test prefixes from every connected probe.",
        "filtered@ASx = valid reached, invalid died; ASx is the last network the invalid trace reached",
        "(it, or its upstream, dropped the invalid route). filtered@local = died before the first public hop.",
        "Cloudflare is anycast, so a short path only speaks for the probe's own network.",
        "(split: ...) = valid and invalid traces left via different upstreams -- a sign one of them drops the invalid route.",
        f"Measurements: {snapshot['measurement_ids']}",
        "",
        "Changes since last snapshot:",
        *([f"  - {c}" for c in changes] or ["  (none)"]),
        "",
        "Where invalid traces died (filtered verdicts):",
        *([f"  {k.split(':')[0]}  {'AS' + k.split(':')[1] if k.split(':')[1] != 'None' else 'local'}: {n}"
           for k, n in snapshot["drop_asns"].items()] or ["  (none)"]),
        "",
        "Per economy (filtered / not_filtered / inconclusive):",
    ]
    for cc, fams in snapshot["economies"].items():
        cells = "   ".join(
            f"{af} {c.get(FILTERED, 0)}/{c.get(NOT_FILTERED, 0)}/{c.get(INCONCLUSIVE, 0)}" for af, c in fams.items()
        )
        lines.append(f"  {cc}  {cells}")
    lines += ["", "Per probe:"]
    for pid, p in snapshot["probes"].items():
        asn = f"AS{p.get('asn_v4') or p.get('asn_v6')}"
        lines.append(f"  {p['cc']}  {pid:>8}  {asn:<9} v4 {_cell(p.get('v4')):<24} v6 {_cell(p.get('v6'))}")
    return "\n".join(lines) + "\n"


def load_last_snapshot(path: Path = HISTORY_PATH) -> dict | None:
    if not path.exists():
        return None
    lines = [line for line in path.read_text().splitlines() if line.strip()]
    return json.loads(lines[-1]) if lines else None


def run_weekly_test(fire: bool, now: datetime | None = None) -> dict | None:
    """Check targets, optionally fire both families' pairs, classify, and record."""
    now = now or datetime.now(timezone.utc)
    ok, target_status = check_targets()
    if not ok:
        logger.error("ROV targets not in expected RPKI state; not firing (update ROV_TARGETS)")
        return None
    listing = load_probe_listing()
    plan = {af: probes_for_af(listing, af) for af in (4, 6)}
    logger.info("ROV test plan: IPv4 %d probes, IPv6 %d probes, 2 measurements each", len(plan[4]), len(plan[6]))
    if not fire:
        logger.info("Dry run -- pass --fire to trace the targets and record the snapshot")
        return None
    measurement_ids, verdicts = {}, {}
    for af, probes in plan.items():
        if not probes:
            continue
        pairs = (ROV_TARGETS[af]["valid"], ROV_TARGETS[af]["invalid"])
        measurement_ids[af] = run_starlink_anchor_traces(sorted(probes), anchors=pairs, af=af, label=MEASUREMENT_LABEL)
    for af, ids in measurement_ids.items():
        verdicts[af] = classify_measurements(refetch_parsed(ids), af, plan[af])
    snapshot = build_snapshot(listing, verdicts, measurement_ids, target_status, now)
    report = render_report(snapshot, diff_snapshots(load_last_snapshot(), snapshot))
    logger.info("Cloudflare ROV test:\n%s", report)
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a") as f:
        f.write(json.dumps(snapshot) + "\n")
    REPORT_PATH.write_text(report)
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fire", action="store_true", help="trace the targets (spends Atlas credits) and record")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_weekly_test(fire=args.fire)


if __name__ == "__main__":
    main()
