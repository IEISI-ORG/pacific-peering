"""Text report and week-on-week diff for the Globalping SB corridor traces (`sb_corridors`)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from pacific_peering.analysis.satellite_operators import SATELLITE_OPERATORS

SB = "SB"


FINISHED = "finished"


def load_last_snapshot(path: Path) -> dict | None:
    """The newest snapshot that has traces (an empty run is never a baseline)."""
    if not path.exists():
        return None
    for line in reversed(path.read_text().splitlines()):
        if line.strip():
            snapshot = json.loads(line)
            if snapshot.get("traces"):
                return snapshot
    return None


def _outcomes(snapshot: dict) -> dict[tuple, list[tuple]]:
    """{(src_cc, src_asn, src_city, target_asn, target_ip): distinct [(reached, as_path)]}.

    Only finished traces count: an offline or unfinished probe is not a path
    change. Duplicate probes on one network share a key, and only their
    distinct outcomes are compared, so one of two probes being offline isn't a change.
    """
    out: dict[tuple, set[tuple]] = defaultdict(set)
    for t in snapshot["traces"]:
        if t.get("status", FINISHED) != FINISHED:
            continue
        key = (t["src_cc"], t["src_asn"], t["src_city"], t["target_asn"], t["target_ip"])
        out[key].add((t["reached"], tuple(t["as_path"])))
    return {k: sorted(v) for k, v in out.items()}


def _group_key(label: str) -> str:
    """'GU AS152735 Guam Exchange (Dededo Village) x1' -> 'GU AS152735'."""
    return " ".join(label.split()[:2])


def diff_snapshots(previous: dict | None, current: dict) -> list[str]:
    """Probe groups gained, lost or changed, and corridors whose reachability or AS path changed."""
    if previous is None:
        return ["first run"]
    old = {_group_key(g): g for g in previous["probe_groups"]}
    new = {_group_key(g): g for g in current["probe_groups"]}
    changes = [f"probe group gone: {old[k]}" for k in old if k not in new]
    changes += [f"probe group new: {new[k]}" for k in new if k not in old]
    changes += [f"probe group changed: {old[k]} => {new[k]}" for k in old if k in new and old[k] != new[k]]
    before, after = _outcomes(previous), _outcomes(current)
    for key in sorted(before.keys() & after.keys()):
        if before[key] != after[key]:
            cc, asn, city, target, _ip = key
            changes.append(f"AS{asn} {city} ({cc}) -> AS{target}: {_brief(before[key])} => {_brief(after[key])}")
    return changes


def _brief(outcomes: list[tuple]) -> str:
    return "; ".join(f"{'reached' if r else 'not reached'} [{' '.join(f'AS{a}' for a in path) or '-'}]"
                     for r, path in outcomes)


def _ixp(crossing: dict) -> str:
    text = f" | IX {crossing['name']}"
    if not crossing["in_fishbowl"]:
        text += " (out of region)"
    if crossing["rtt_ms"] is not None:
        text += f" {crossing['rtt_ms']:.1f} ms"
    return text


def _satellites(trace: dict) -> str:
    """' | satellite <operator> (<orbit>)' for each satellite operator on the AS path, in path order."""
    seen = dict.fromkeys(a for a in trace["as_path"] if a in SATELLITE_OPERATORS)
    return "".join(f" | satellite {SATELLITE_OPERATORS[a].name} ({SATELLITE_OPERATORS[a].orbit})" for a in seen)


def _path(trace: dict, asn_to_cc: dict[int, str]) -> str:
    """AS path with in-scope ASNs labelled by economy (unlabelled = outside the region),
    then IXP crossings, then any satellite operator on the path."""
    asns = " ".join(f"AS{a}({asn_to_cc[a]})" if a in asn_to_cc else f"AS{a}" for a in trace["as_path"])
    return (asns or "-") + "".join(_ixp(x) for x in trace["ixps"]) + _satellites(trace)


def _status(trace: dict) -> str:
    status = trace.get("status", FINISHED)
    if status != FINISHED:
        return f"probe result {status}"
    if trace["reached"]:
        return "reached (no RTT)" if trace["rtt_ms"] is None else f"reached {trace['rtt_ms']:.1f} ms"
    if trace["last_address"] is None:
        return "dark from hop 1"
    rtt = trace["last_rtt_ms"]
    return f"dark after {trace['last_address']}" + ("" if rtt is None else f" ({rtt:.1f} ms)")


def _line(trace: dict, asn_to_cc: dict[int, str]) -> str:
    return (f"  {trace['src_cc']} AS{trace['src_asn']:<7} {trace['src_city'][:14]:<14} -> "
            f"{trace['target_cc']} AS{trace['target_asn']:<7} {trace['target_ip']:<15} "
            f"{_status(trace):<36} {_path(trace, asn_to_cc)}")


def render_report(snapshot: dict, changes: list[str], asn_to_cc: dict[int, str]) -> str:
    traces = snapshot["traces"]
    sections = {
        "Domestic (SB -> SB)": [t for t in traces if t["src_cc"] == SB and t["target_cc"] == SB],
        "Inbound (other Pacific -> SB)": [t for t in traces if t["src_cc"] != SB],
        "Outbound (SB -> other Pacific economies)": [t for t in traces if t["src_cc"] == SB and t["target_cc"] != SB],
    }
    below = [t for t in traces if t["below_floor"]]
    reached = sum(t["reached"] for t in traces)
    unfinished = sum(t.get("status", FINISHED) != FINISHED for t in traces)
    lines = [
        f"Globalping Solomon Islands corridors -- {snapshot['date']}",
        "Auto-generated weekly (Wednesday) by `pacific-peering-globalping-sb` (globalping/sb_corridors.py).",
        "Report only: Globalping traces are not RIPE Atlas findings and file nothing. Probe locations are",
        "Globalping's IP geolocation; Globalping probes have no stable IDs, so each is named by network and city.",
        "\"satellite ... (GEO)\" marks a path through a geostationary operator: that hop alone adds about 0.5 s.",
        f"{len(snapshot['measurement_ids'])} measurements, {snapshot['tests']} Globalping tests, "
        f"{len(traces)} traces, {reached} reached the target, {unfinished} probe results not finished.",
        "",
        "Probe groups (economy, network, city, probe count):",
        *[f"  {g}" for g in snapshot["probe_groups"]],
        *[f"  skipped: {g}" for g in snapshot["skipped_probes"]],
        "",
        "Changes since last run:",
        *([f"  - {c}" for c in changes] or ["  (none)"]),
        "",
        "Faster than fibre allows (the probe or the target is not where it is labelled):",
        *([f"{_line(t, asn_to_cc)}  floor {t['floor_ms']:.1f} ms" for t in below] or ["  (none)"]),
    ]
    for title, rows in sections.items():
        lines += ["", f"{title}: {len(rows)} traces"]
        lines += [_line(t, asn_to_cc) for t in sorted(rows, key=lambda t: (t["target_cc"], t["target_asn"],
                                                                           t["src_cc"], t["src_asn"]))]
    if snapshot["unmeasured"]:
        lines += ["", "Not measured this run:", *[f"  {u}" for u in snapshot["unmeasured"]]]
    lines += ["", f"Globalping measurement IDs (public, kept about six months): "
                  f"{', '.join(snapshot['measurement_ids']) or 'none'}"]
    return "\n".join(lines) + "\n"
