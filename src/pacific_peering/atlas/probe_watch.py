"""Watch the probe fleet for metadata changes, and regression-test egress.

Per the project owner (2026-09-29): SPC are expected to take probe 60575
(AS141695, Suva) off its Zscaler VPN link, so be on the lookout for changes
on our probes. A metadata change alone proves nothing -- 60575's ASN moved
53813 -> 141695 on 2026-09-17 while its egress stayed on Zscaler (see
task_plan.md, 2026-09-19) -- so a change triggers a real traceroute, and the
probes known to egress via a proxy are traced weekly whether or not their
metadata moved, since the fix may not show in Atlas's metadata at all.

Every night, from `scripts/nightly_corridor_testing.sh`, before the batch:

1. Diff each Connected/Disconnected probe's economy, IPv4/IPv6 ASN and status
   against last night's snapshot (free; reads tonight's probe listing).
2. Egress traceroute to 1.1.1.1 (fallback 1.0.0.1), one measurement, from
   every Connected probe whose economy or ASN changed, plus -- with
   `--weekly`, which the nightly script passes on its local-time Wednesday --
   every Connected probe on an `EGRESS_WATCH_ASNS` network. Records the first
   resolved ASN on the path.
3. Escalate economy/ASN changes, every changed probe's egress result, and any
   watched probe whose first-hop ASN differs from its last egress check.
   Nothing is ever un-excluded automatically; that stays the owner's call
   after reading the path. A `BOLO_PROBES` probe returning to the listing is
   always escalated, with its egress trace once it can be fired.

Writes `outputs/reports/probe_watch_snapshot.json` (git-tracked, so the
baseline survives a fresh checkout), appends egress checks to
`probe_watch_history.jsonl`, and writes `probe_watch.txt`. Without `--fire`
nothing is fired or written.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

from pacific_peering.analysis.auto_classify import KNOWN_PROXY_ASNS, NON_LOCAL_FIRST_HOP_ASNS
from pacific_peering.analysis.traceroute_topology import extract_as_sequence, resolve_traceroute_hops
from pacific_peering.atlas.probes import load_probe_listing
from pacific_peering.atlas.smoketest import refetch_parsed
from pacific_peering.atlas.starlink_anchors import PUBLIC_DNS_ANCHORS_V4, run_starlink_anchor_traces

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = Path("outputs/reports/probe_watch_snapshot.json")
HISTORY_PATH = Path("outputs/reports/probe_watch_history.jsonl")
REPORT_PATH = Path("outputs/reports/probe_watch.txt")
ESCALATIONS_PATH = Path("escalations.md")
MEASUREMENT_LABEL = "probe-watch-egress"

# Networks whose probes are known to egress via a proxy/VPN: traced weekly so
# a fix shows up even if Atlas's metadata never changes.
EGRESS_WATCH_ASNS: dict[int, str] = {
    141695: "Pacific Community (SPC) -- egresses via Zscaler since 2026-09-19",
    **KNOWN_PROXY_ASNS,
}
# Be-on-the-lookout: Abandoned probes we want back. Any return to the listing
# is escalated whatever its egress, since a local path is the good news here.
BOLO_PROBES: dict[int, str] = {
    51448: "TCC (AS38201, Tonga) hardware probe, live 2019-09-18..25 only -- possibly still cabled but unpowered (PacNOG, 2026-10-02)",
    21626: "TCC (AS38201, Tonga) hardware probe, live 2019-12-11..12 only -- possibly still cabled but unpowered (PacNOG, 2026-10-02)",
}
_TRACKED_STATUSES = ("Connected", "Disconnected")
_METADATA_FIELDS = ("cc", "asn_v4", "asn_v6")
# An IPv4 egress trace can only speak to these; Atlas clears `asn_v6` whenever
# a probe loses IPv6, so v6 changes are reported but never traced or escalated.
_TRACE_FIELDS = ("cc", "asn_v4")


def probe_state(listing: dict[str, list[dict]]) -> dict[str, dict]:
    """Probe id (as str, for JSON) -> economy, ASNs and status, for live probes only."""
    return {
        str(p["id"]): {"cc": cc, "asn_v4": p.get("asn_v4"), "asn_v6": p.get("asn_v6"), "status": p["status"]}
        for cc, probes in listing.items()
        for p in probes
        if p["status"] in _TRACKED_STATUSES
    }


def diff_states(previous: dict[str, dict], current: dict[str, dict]) -> list[dict]:
    """Every field change, plus probes that appeared or left the tracked statuses."""
    changes = []
    for pid in sorted(set(previous) | set(current), key=int):
        old, new = previous.get(pid), current.get(pid)
        if old is None or new is None:
            changes.append({"probe": int(pid), "field": "tracked", "old": old is not None, "new": new is not None})
            continue
        for field in (*_METADATA_FIELDS, "status"):
            if old.get(field) != new.get(field):
                changes.append({"probe": int(pid), "field": field, "old": old.get(field), "new": new.get(field)})
    return changes


def metadata_changed_probes(changes: list[dict]) -> set[int]:
    """Probes whose economy or IPv4 ASN changed: each needs an egress trace."""
    return {c["probe"] for c in changes if c["field"] in _TRACE_FIELDS}


def newly_tracked_probes(changes: list[dict]) -> set[int]:
    return {c["probe"] for c in changes if c["field"] == "tracked" and c["new"]}


def egress_watch_probes(current: dict[str, dict]) -> set[int]:
    return {int(pid) for pid, s in current.items() if s["status"] == "Connected" and s["asn_v4"] in EGRESS_WATCH_ASNS}


def first_egress_asn(trace: dict) -> int | None:
    """First resolved public ASN on the path (private hops are skipped by the resolver)."""
    sequence = extract_as_sequence(resolve_traceroute_hops(trace["hops"]))
    return sequence[0].asn if sequence else None


def describe_egress(asn: int | None) -> str:
    if asn is None:
        return "no resolvable public hop"
    if asn in NON_LOCAL_FIRST_HOP_ASNS:
        return f"AS{asn} ({NON_LOCAL_FIRST_HOP_ASNS[asn]}) -- non-local egress"
    return f"AS{asn}"


def last_egress(path: Path | None = None) -> dict[str, int]:
    """Each probe's most recent resolved first-hop ASN (unresolved results are never recorded)."""
    path = path or HISTORY_PATH
    result: dict[str, int] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                result.update({k: v for k, v in json.loads(line)["egress"].items() if v is not None})
    return result


def trace_egress(probe_ids: list[int]) -> tuple[list[int], dict[str, int | None]]:
    measurement_ids = run_starlink_anchor_traces(
        probe_ids, anchors=PUBLIC_DNS_ANCHORS_V4[:1], af=4, label=MEASUREMENT_LABEL
    )
    egress: dict[str, int | None] = {}
    if measurement_ids:
        for trace in refetch_parsed(measurement_ids):
            egress[str(trace["probe_id"])] = first_egress_asn(trace)
    return measurement_ids, egress


def _block(pid: str, s: dict, title: str, reason: str, detail: str, action: str, now: datetime) -> str:
    return (
        f"\n## Probe {pid} ({s.get('cc', '?')}, AS{s.get('asn_v4')}) -- {title}\n"
        f"- reason: {reason} (atlas/probe_watch.py)\n- detail: {detail}\n- action: {action}\n"
        f"- flagged: {now.isoformat()}\n"
    )


_REVIEW_PATH = "owner review -- check the path before trusting this probe's next results, or changing any exclusion"


def escalation_blocks(
    changes: list[dict],
    current: dict[str, dict],
    deferred: set[int],
    egress: dict[str, int | None],
    previous_egress: dict[str, int],
    measurement_ids: list[int],
    now: datetime,
) -> list[str]:
    """One block per economy/IPv4-ASN change (with its trace, or why it's still
    pending); per deferred trace that finally resolved; per new probe that
    egresses non-locally; per watched probe whose resolved first hop moved."""
    blocks = []
    msm = ", ".join(str(m) for m in measurement_ids) or "none fired"
    changed = metadata_changed_probes(changes)
    for pid in sorted(changed):
        moved = "; ".join(f"{c['field']} {c['old']} -> {c['new']}" for c in changes
                          if c["probe"] == pid and c["field"] in _TRACE_FIELDS)
        asn = egress.get(str(pid))
        result = (f"{describe_egress(asn)} (measurement {msm})" if asn is not None
                  else "not traced yet (not Connected, or no resolvable result) -- retried nightly until it resolves")
        blocks.append(_block(str(pid), current.get(str(pid), {}), "metadata changed", "probe watch",
                             f"{moved}; egress trace: {result}", _REVIEW_PATH, now))
    new = newly_tracked_probes(changes)
    for pid in sorted(new & set(BOLO_PROBES)):
        s = current.get(str(pid), {})
        asn = egress.get(str(pid))
        result = (f"{describe_egress(asn)} (measurement {msm})" if asn is not None
                  else "not traced yet (not Connected, or no resolvable result) -- retried nightly until it resolves")
        blocks.append(_block(str(pid), s, "BOLO probe back online", "probe watch BOLO",
                             f"{BOLO_PROBES[pid]}; status {s.get('status')}; egress trace: {result}",
                             "owner review -- thank the host, check the path, then let discovery pick it up", now))
    for pid, asn in sorted(egress.items(), key=lambda kv: int(kv[0])):
        s = current.get(pid, {})
        if asn is None or int(pid) in changed or int(pid) in BOLO_PROBES and int(pid) in new:
            continue
        if int(pid) in deferred:
            blocks.append(_block(pid, s, "deferred regression trace", "probe watch",
                                 f"egress trace after an earlier metadata change: {describe_egress(asn)} "
                                 f"(measurement {msm})", _REVIEW_PATH, now))
            continue
        if int(pid) in new:
            if asn in NON_LOCAL_FIRST_HOP_ASNS:
                blocks.append(_block(pid, s, "new probe egresses non-locally", "probe watch",
                                     f"first hop {describe_egress(asn)} (measurement {msm})", _REVIEW_PATH, now))
            continue
        if pid in previous_egress:
            if previous_egress[pid] == asn:
                continue
            before = describe_egress(previous_egress[pid])
        elif asn in NON_LOCAL_FIRST_HOP_ASNS:
            continue  # first check, still proxied: that's the expected baseline
        else:
            before = "no earlier check (watched as proxy-egressing)"
        blocks.append(_block(
            pid, s, "egress changed", "probe watch weekly egress check",
            f"first-hop {before} -> {describe_egress(asn)} (measurement {msm})",
            "owner review; if the proxy is really gone, regression-test real corridors before removing "
            "its ASN from corridor_backlog.EXTERNAL_NON_CANDIDATE_ASNS", now,
        ))
    return blocks


def render_report(
    now: datetime, changes: list[dict], egress: dict[str, int | None], current: dict[str, dict],
    measurement_ids: list[int], pending: list[int],
) -> str:
    lines = [
        "Probe watch (atlas/probe_watch.py) -- nightly metadata diff; egress traced on change "
        "and weekly for proxy-flagged networks.",
        f"Generated {now.isoformat(timespec='seconds')}; {len(current)} Connected/Disconnected probes tracked.",
        "",
        f"Changes since the previous snapshot: {len(changes) or 'none'}",
    ]
    lines += [f"  probe {c['probe']}: {c['field']} {c['old']} -> {c['new']}" for c in changes]
    lines += ["", f"Egress checks tonight: {len(egress) or 'none'} (measurement(s) {measurement_ids or '-'})"]
    for pid, asn in sorted(egress.items(), key=lambda kv: int(kv[0])):
        s = current.get(pid, {})
        lines.append(f"  probe {pid} ({s.get('cc', '?')}, AS{s.get('asn_v4')}): first hop {describe_egress(asn)}")
    lines += ["", f"Regression traces still pending: {pending or 'none'}"]
    return "\n".join(lines) + "\n"


def run_watch(fire: bool, weekly: bool = False, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    current = probe_state(load_probe_listing())
    snapshot = json.loads(SNAPSHOT_PATH.read_text()) if SNAPSHOT_PATH.exists() else None
    changes = diff_states(snapshot["probes"], current) if snapshot is not None else []
    # A change is only cleared once a trace resolves, so a probe that changed
    # while Disconnected (or returned nothing) is traced when it next can be.
    deferred = set(snapshot.get("pending_trace", [])) if snapshot is not None else set()
    needs_trace = deferred | metadata_changed_probes(changes) | newly_tracked_probes(changes)
    needs_trace = {pid for pid in needs_trace if str(pid) in current}
    connected = {int(pid) for pid, s in current.items() if s["status"] == "Connected"}
    to_trace = sorted((needs_trace & connected) | (egress_watch_probes(current) if weekly else set()))
    logger.info(
        "Probe watch: %s, %d change(s), tracing %s%s",
        "baseline (no previous snapshot)" if snapshot is None else "diffed", len(changes),
        to_trace or "nothing", " (weekly egress day)" if weekly else "",
    )
    if not fire:
        for c in changes:
            logger.info("  probe %d: %s %s -> %s", c["probe"], c["field"], c["old"], c["new"])
        logger.info("Dry run -- pass --fire to trace and record")
        return {"changes": changes, "to_trace": to_trace}

    previous_egress = last_egress()
    measurement_ids: list[int] = []
    egress: dict[str, int | None] = {}
    if to_trace:
        try:
            measurement_ids, egress = trace_egress(to_trace)
        except (requests.RequestException, OSError, ValueError, KeyError) as e:
            logger.error("Egress trace failed (%s); changed probes stay pending for tomorrow", e)
    for pid in to_trace:
        if egress.get(str(pid)) is None:
            logger.warning("Probe %d: no resolvable egress trace tonight", pid)
    pending = sorted(pid for pid in needs_trace if egress.get(str(pid)) is None)
    blocks = escalation_blocks(changes, current, deferred, egress, previous_egress, measurement_ids, now)
    resolved = {pid: asn for pid, asn in egress.items() if asn is not None}
    if resolved:
        with HISTORY_PATH.open("a") as f:
            f.write(json.dumps({"at": now.isoformat(), "measurements": measurement_ids, "egress": resolved}) + "\n")
    # Escalate before the snapshot: a crash in between re-files tomorrow rather than losing it.
    if blocks:
        with ESCALATIONS_PATH.open("a") as f:
            f.write("".join(blocks))
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(
        {"at": now.isoformat(), "pending_trace": pending, "probes": current}, indent=1, sort_keys=True
    ) + "\n")
    REPORT_PATH.write_text(render_report(now, changes, egress, current, measurement_ids, pending))
    return {"changes": changes, "to_trace": to_trace, "egress": egress, "escalations": len(blocks), "pending": pending}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fire", action="store_true", help="trace egress (spends Atlas credits) and record")
    parser.add_argument("--weekly", action="store_true", help="also trace every EGRESS_WATCH_ASNS probe")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_watch(fire=args.fire, weekly=args.weekly)


if __name__ == "__main__":
    main()
