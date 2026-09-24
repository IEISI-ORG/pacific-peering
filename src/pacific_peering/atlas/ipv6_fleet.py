"""Weekly IPv6 check across the in-scope Atlas probe fleet.

Per the project owner (2026-09-24): this testbed can't do much IPv6 corridor
work yet (the Starlink probes gave no IPv6 data; see task_plan.md), so for now
IPv6 is *monitored*, not tested -- once a week, from the Wednesday nightly run
(`scripts/nightly_corridor_testing.sh`):

1. Snapshot IPv6 deployment across the fleet from the probe listing (free):
   per economy, how many connected probes have an IPv6 ASN and how many
   Atlas tags `system-ipv6-works`.
2. Trace the public DNS IPv6 anchors (`starlink_anchors.PUBLIC_DNS_ANCHORS_V6`,
   same primary/fallback handling) from every connected probe with an IPv6
   ASN, and record each probe's *measured* IPv6 access this week alongside
   Atlas's tags -- the tags come from Atlas's own built-in measurements and
   can disagree with what our traces see.
3. Append the snapshot to `outputs/reports/ipv6_fleet_history.jsonl` and
   write `outputs/reports/ipv6_fleet.txt` (current state plus what changed
   since the previous snapshot). Both are git-tracked via the nightly
   script's `outputs/reports` path.

Step 2 spends Atlas credits (2 measurements, one result per IPv6 probe
each), so `main()` only prints the report unless `--fire` is given; a dry
run writes nothing.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pacific_peering.atlas.client import fetch_raw_results
from pacific_peering.atlas.probes import load_probe_listing
from pacific_peering.atlas.smoketest import DEFAULT_PARSED_DIR, persist_results
from pacific_peering.atlas.starlink_anchors import (
    PUBLIC_DNS_ANCHORS_V6,
    run_starlink_anchor_traces,
    summarize_anchor_trace,
)

logger = logging.getLogger(__name__)

HISTORY_PATH = Path("outputs/reports/ipv6_fleet_history.jsonl")
REPORT_PATH = Path("outputs/reports/ipv6_fleet.txt")
MEASUREMENT_LABEL = "ipv6-fleet-anchor"

# Measured access values, per probe per week.
REACHED = "reached"  # reached at least one IPv6 anchor
NO_REACH = "no_reach"  # returned results, reached no anchor
NO_RESULT = "no_result"  # in the measurements, returned nothing
NOT_MEASURED = "not_measured"  # dry run, or no measurement could be created

# Per-anchor results are keyed by service, not address, so a week that fell
# back to a secondary address still compares against one that used the
# primary.
ANCHOR_SERVICES = {
    "2606:4700:4700::1111": "cloudflare",
    "2606:4700:4700::1001": "cloudflare",
    "2001:4860:4860::8888": "google",
    "2001:4860:4860::8844": "google",
}
SERVICE_ORDER = ("cloudflare", "google")


def ipv6_probes(listing: dict[str, list[dict]]) -> dict[int, dict]:
    """Connected probes with an IPv6 ASN: {probe_id: {cc, asn_v6, ipv6_tags}}."""
    return {
        p["id"]: {"cc": cc, "asn_v6": p["asn_v6"], "ipv6_tags": p.get("ipv6_tags", [])}
        for cc, probes in listing.items()
        for p in probes
        if p["status"] == "Connected" and p.get("asn_v6")
    }


def economy_counts(listing: dict[str, list[dict]]) -> dict[str, dict[str, int]]:
    """Per economy: connected probes, those with an IPv6 ASN, those Atlas tags ipv6-works."""
    counts = {}
    for cc, probes in sorted(listing.items()):
        connected = [p for p in probes if p["status"] == "Connected"]
        counts[cc] = {
            "connected": len(connected),
            "ipv6_asn": sum(1 for p in connected if p.get("asn_v6")),
            "ipv6_works_tag": sum(1 for p in connected if "system-ipv6-works" in p.get("ipv6_tags", [])),
        }
    return counts


def measured_access(parsed_traces: list[dict], probe_ids: list[int]) -> dict[int, str]:
    """Each probe's measured access from all this week's parsed anchor traces."""
    by_probe: dict[int, list[bool]] = {}
    for trace in parsed_traces:
        by_probe.setdefault(trace["probe_id"], []).append(summarize_anchor_trace(trace).reached_target)
    access = {}
    for probe_id in probe_ids:
        reached = by_probe.get(probe_id)
        if reached is None:
            access[probe_id] = NO_RESULT
        else:
            access[probe_id] = REACHED if any(reached) else NO_REACH
    return access


def _target_rtt(trace: dict) -> float | None:
    for hop in trace["hops"]:
        if trace["target"] in hop["addresses"]:
            return hop["min_rtt_ms"]
    return None


def per_anchor_results(parsed_traces: list[dict]) -> dict[int, dict[str, dict]]:
    """{probe_id: {service: {target, reached, rtt_ms, last_address}}} from this week's traces.

    Added 2026-09-24 after the baseline showed both PF (AS9471) probes
    reaching Cloudflare IPv6 but dying at `fc00:1::1` toward Google -- a
    split the any-anchor `access` value hides. `rtt_ms` is the RTT of the
    hop where the anchor itself answered (None if it didn't);
    `last_address` is the last real hop that answered.
    """
    results: dict[int, dict[str, dict]] = {}
    for trace in parsed_traces:
        service = ANCHOR_SERVICES.get(trace["target"], trace["target"])
        summary = summarize_anchor_trace(trace)
        results.setdefault(trace["probe_id"], {})[service] = {
            "target": trace["target"],
            "reached": summary.reached_target,
            "rtt_ms": _target_rtt(trace) if summary.reached_target else None,
            "last_address": summary.last_address,
        }
    return results


def build_snapshot(
    listing: dict[str, list[dict]],
    access: dict[int, str],
    measurement_ids: list[int],
    now: datetime,
    anchors: dict[int, dict[str, dict]] | None = None,
) -> dict:
    probes = ipv6_probes(listing)
    anchors = anchors or {}
    return {
        "date": now.strftime("%Y-%m-%d"),
        "measurement_ids": measurement_ids,
        "economies": economy_counts(listing),
        "probes": {
            str(pid): {**info, "access": access.get(pid, NOT_MEASURED), "anchors": anchors.get(pid, {})}
            for pid, info in sorted(probes.items())
        },
    }


def diff_snapshots(previous: dict | None, current: dict) -> list[str]:
    """Human-readable changes from `previous` to `current` (empty if nothing changed)."""
    if previous is None:
        return ["First snapshot -- nothing to compare against."]
    changes = []
    prev_p, cur_p = previous["probes"], current["probes"]
    for pid in sorted(set(cur_p) - set(prev_p), key=int):
        changes.append(f"probe {pid} ({cur_p[pid]['cc']}) gained an IPv6 ASN (AS{cur_p[pid]['asn_v6']})")
    for pid in sorted(set(prev_p) - set(cur_p), key=int):
        changes.append(f"probe {pid} ({prev_p[pid]['cc']}) no longer listed with IPv6 (or not Connected)")
    for pid in sorted(set(prev_p) & set(cur_p), key=int):
        before, after = prev_p[pid], cur_p[pid]
        if before["access"] != after["access"] and NOT_MEASURED not in (before["access"], after["access"]):
            changes.append(f"probe {pid} ({after['cc']}) measured access {before['access']} -> {after['access']}")
        # Snapshots from before 2026-09-24's per-anchor change have no "anchors".
        before_a, after_a = before.get("anchors", {}), after.get("anchors", {})
        for service in sorted(set(before_a) & set(after_a)):
            was, now_ = before_a[service]["reached"], after_a[service]["reached"]
            if was != now_:
                verb = "now reaches" if now_ else "no longer reaches"
                changes.append(f"probe {pid} ({after['cc']}) {verb} the {service} anchor")
        for tag in ("system-ipv6-works", "system-ipv6-doesnt-work"):
            had, has = tag in before["ipv6_tags"], tag in after["ipv6_tags"]
            if had != has:
                changes.append(f"probe {pid} ({after['cc']}) Atlas tag {tag} {'added' if has else 'removed'}")
    return changes


def _anchor_cell(result: dict | None) -> str:
    if result is None:
        return "-"
    if result["reached"]:
        rtt = result["rtt_ms"]
        return f"ok {rtt:.1f}ms" if rtt is not None else "ok"
    return f"dark@{result['last_address'] or '*'}"


def render_report(snapshot: dict, changes: list[str]) -> str:
    lines = [
        f"IPv6 fleet check -- {snapshot['date']}",
        "Auto-generated weekly (Wednesday) by `pacific-peering-ipv6-fleet` (atlas/ipv6_fleet.py).",
        f"Anchor measurements: {', '.join(map(str, snapshot['measurement_ids'])) or 'none'}",
        "",
        "Changes since last snapshot:",
        *([f"  - {c}" for c in changes] or ["  (none)"]),
        "",
        "Per economy (connected probes / with IPv6 ASN / Atlas ipv6-works tag):",
    ]
    for cc, c in snapshot["economies"].items():
        lines.append(f"  {cc}  {c['connected']:>2} / {c['ipv6_asn']:>2} / {c['ipv6_works_tag']:>2}")
    lines += [
        "",
        "IPv6 probes (measured access this week, per anchor, vs Atlas tags):",
        "  per anchor: ok <RTT> = reached; dark@<addr> = last hop that answered; - = no result",
    ]
    for pid, p in snapshot["probes"].items():
        tags = ", ".join(t.removeprefix("system-ipv6-") for t in p["ipv6_tags"]) or "none"
        cells = "  ".join(f"{svc} {_anchor_cell(p.get('anchors', {}).get(svc)):<18}" for svc in SERVICE_ORDER)
        lines.append(f"  {p['cc']}  {pid:>8}  AS{p['asn_v6']:<7} {p['access']:<12} {cells}  tags: {tags}")
    return "\n".join(lines) + "\n"


def load_last_snapshot(path: Path = HISTORY_PATH) -> dict | None:
    if not path.exists():
        return None
    lines = [line for line in path.read_text().splitlines() if line.strip()]
    return json.loads(lines[-1]) if lines else None


def _refetch_parsed(measurement_ids: list[int]) -> list[dict]:
    # wait_for_results returns partial results after 180s; by the time every
    # anchor has fired, the earlier ones have had minutes more -- re-fetch so
    # a late probe isn't recorded as no_result.
    traces = []
    for mid in measurement_ids:
        persist_results(mid, fetch_raw_results(mid))
        traces += json.loads((DEFAULT_PARSED_DIR / f"{mid}.json").read_text())
    return traces


def run_weekly_check(fire: bool, now: datetime | None = None) -> dict:
    """Snapshot fleet IPv6, optionally fire the anchor traces, and (when fired) record it."""
    now = now or datetime.now(timezone.utc)
    listing = load_probe_listing()
    probe_ids = sorted(ipv6_probes(listing))
    measurement_ids: list[int] = []
    access: dict[int, str] = {}
    anchors: dict[int, dict[str, dict]] = {}
    if fire and probe_ids:
        measurement_ids = run_starlink_anchor_traces(
            probe_ids, anchors=PUBLIC_DNS_ANCHORS_V6, af=6, label=MEASUREMENT_LABEL
        )
        if measurement_ids:
            traces = _refetch_parsed(measurement_ids)
            access = measured_access(traces, probe_ids)
            anchors = per_anchor_results(traces)
    snapshot = build_snapshot(listing, access, measurement_ids, now, anchors)
    report = render_report(snapshot, diff_snapshots(load_last_snapshot(), snapshot))
    logger.info("IPv6 fleet check (%d IPv6 probes):\n%s", len(probe_ids), report)
    if not fire:
        logger.info("Dry run -- pass --fire to trace the anchors and record the snapshot")
        return snapshot
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a") as f:
        f.write(json.dumps(snapshot) + "\n")
    REPORT_PATH.write_text(report)
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fire", action="store_true", help="trace the anchors (spends Atlas credits) and record")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_weekly_check(fire=args.fire)


if __name__ == "__main__":
    main()
