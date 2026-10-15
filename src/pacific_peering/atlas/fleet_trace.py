"""Queued fleet traceroutes: one target, every connected in-scope probe.

Per the project owner (2026-10-16, "retest FNU from the fleet in tomorrow's
run"): some questions need one address traced from the whole fleet at once,
not a corridor test from one source economy. The USP check that day
(measurements 223634394 and 223636622) was the first; FNU is the next.

`--enqueue` adds a target to `data/analysis/fleet_trace_queue.json` (free).
The nightly run (`scripts/nightly_corridor_testing.sh`) calls `--run-queued`
after the corridor batch: for each queued target it fires one traceroute
from every Connected probe in tonight's probe listing (one measurement,
real Atlas credits), re-fetches the results so late probes aren't lost, and
writes the newest section to the top of `outputs/reports/fleet_traces.txt`
(git-tracked via `outputs/reports`). A target leaves the queue only once
its measurement exists; a refused fire stays queued for the next night.

Report only: nothing here files findings. The owner reviews the report and
decides what, if anything, becomes a finding.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

from pacific_peering.atlas.probes import load_probe_listing
from pacific_peering.atlas.smoketest import _fire_and_persist, refetch_parsed

logger = logging.getLogger(__name__)

QUEUE_PATH = Path("data/analysis/fleet_trace_queue.json")
REPORT_PATH = Path("outputs/reports/fleet_traces.txt")


def load_queue(path: Path = QUEUE_PATH) -> list[dict]:
    return json.loads(path.read_text()) if path.exists() else []


def _save_queue(queue: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(queue, indent=2) + "\n")


def enqueue(target_ip: str, target_asn: int, reason: str, path: Path = QUEUE_PATH) -> list[dict]:
    """Queue `target_ip` for the next nightly run; a target already queued isn't added twice."""
    queue = load_queue(path)
    if any(entry["target_ip"] == target_ip for entry in queue):
        logger.info("%s is already queued", target_ip)
        return queue
    queue.append({"target_ip": target_ip, "target_asn": target_asn, "reason": reason,
                  "queued_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    _save_queue(queue, path)
    return queue


def connected_probes(listing: dict[str, list[dict]]) -> dict[int, tuple[str, int | None]]:
    """Every Connected probe in the listing: {probe_id: (economy, asn_v4)}."""
    return {p["id"]: (cc, p.get("asn_v4")) for cc, probes in listing.items()
            for p in probes if p["status"] == "Connected"}


def _summarize(trace: dict | None, target_ip: str) -> str:
    if trace is None:
        return "no result"
    answered = [h for h in trace["hops"] if h["addresses"]]
    reached = next((h for h in answered if target_ip in h["addresses"]), None)
    if reached is not None:
        return f"reached {reached['min_rtt_ms']:.1f} ms (hop {reached['hop']})"
    if not answered:
        return "dark from hop 1"
    last = answered[-1]
    return f"dark after {last['addresses'][0]} ({last['min_rtt_ms']} ms, hop {last['hop']})"


def render_section(entry: dict, measurement_id: int, probes: dict[int, tuple[str, int | None]],
                   traces: list[dict], now: datetime) -> str:
    by_probe = {t["probe_id"]: t for t in traces}
    reached = sum(1 for pid in probes if _summarize(by_probe.get(pid), entry["target_ip"]).startswith("reached"))
    lines = [f"== {entry['target_ip']} (AS{entry['target_asn']}) -- {now.date().isoformat()}, "
             f"measurement {measurement_id}",
             f"Reason: {entry['reason']}",
             f"{len(probes)} probes, {len(by_probe)} reported, {reached} reached the target", ""]
    for pid, (cc, asn) in sorted(probes.items(), key=lambda kv: (kv[1][0], kv[0])):
        lines.append(f"  {cc}  {pid:>8}  AS{asn or '?':<7}  {_summarize(by_probe.get(pid), entry['target_ip'])}")
    return "\n".join(lines) + "\n"


def _prepend_report(section: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = path.read_text() if path.exists() else ""
    path.write_text(section + ("\n" + previous if previous else ""))


def run_queued(queue_path: Path = QUEUE_PATH, report_path: Path = REPORT_PATH,
               now: datetime | None = None) -> list[int]:
    """Fire every queued target from the whole fleet and report it. Returns the measurement IDs."""
    queue = load_queue(queue_path)
    if not queue:
        logger.info("Fleet trace queue is empty")
        return []
    now = now or datetime.now(timezone.utc)
    probes = connected_probes(load_probe_listing())
    probe_value = ",".join(str(p) for p in sorted(probes))
    fired: list[int] = []
    remaining: list[dict] = []
    for entry in queue:
        description = (f"pacific-peering fleet-trace {len(probes)} connected in-scope probes "
                       f"to AS{entry['target_asn']} {entry['target_ip']}")
        try:
            measurement_id = _fire_and_persist("probes", probe_value, entry["target_ip"], description, len(probes))
        except (requests.RequestException, ValueError) as exc:
            logger.error("Fleet trace to %s not fired, kept queued: %s", entry["target_ip"], exc)
            remaining.append(entry)
            continue
        fired.append(measurement_id)
        traces = refetch_parsed([measurement_id])
        _prepend_report(render_section(entry, measurement_id, probes, traces, now), report_path)
        logger.info("Fleet trace to %s: measurement %d", entry["target_ip"], measurement_id)
    _save_queue(remaining, queue_path)
    return fired


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--enqueue", metavar="IP", help="queue IP for the next nightly run (free)")
    group.add_argument("--run-queued", action="store_true", help="fire every queued target (spends Atlas credits)")
    parser.add_argument("--asn", type=int, help="target ASN (with --enqueue)")
    parser.add_argument("--reason", default="", help="why this target is queued (with --enqueue)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.enqueue:
        if args.asn is None:
            parser.error("--enqueue needs --asn")
        for entry in enqueue(args.enqueue, args.asn, args.reason):
            logger.info("queued: %s (AS%d) -- %s", entry["target_ip"], entry["target_asn"], entry["reason"])
    else:
        run_queued()


if __name__ == "__main__":
    main()
