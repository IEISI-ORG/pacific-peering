"""The uv-script replacement for LLM-driven per-corridor classification.

Per the project owner's explicit direction (move off LLM processing, get uv
scripts doing all of the work): this pulls the next candidate off the
corridor backlog, fires a traceroute, triangulates it against RIS, classifies
it via fixed mechanical rules, files a SQLite finding (new or extending an
existing one), marks the corridor tested, and regenerates every derived
artifact -- the same sequence this project's tranches performed by hand,
all session, now scripted end-to-end. An LLM/human is only back in the loop
for a genuine escalation (see `_Escalation`, `escalations.md`) -- everything
else is fully automatic.

Classification rules, in priority order, per probe:

1. **Loop check** (`has_routing_loop`, called with the real target IP --
   omitting it silently defeats the target-reached exemption, a bug this
   project hit once already). A loop at an address `known_anomalies.py`
   already recognizes is routine, logged but not blocking; a loop at a new
   address is a genuine escalation.
2. **IXP crossing.** If the traceroute crosses a *classified*
   (`in_fishbowl` is `True`/`False`, never `"TBA"`) out-of-fishbowl exchange
   at a hub this project has coordinates for
   (`economy_coordinates.EXTERNAL_HUB_LATLON`), that's a Confirmed Detour --
   `"TBA"` exchanges and unmapped hubs escalate instead of guessing.
3. **RIS+Atlas agreement on the immediate upstream of the target**
   (Validation Rule 1). If the confirmed upstream ASN is itself a fishbowl
   ASN (`data/asn_registry.json`), that's Confirmed Local Transit. If it's
   external and step 2 didn't already resolve a hub, that ambiguity
   escalates rather than being filed as a locationless detour.
4. **Real signal, RIS disagrees** (Validation Rule 4): a resolved,
   contiguous upstream that RIS's neighbor list doesn't independently
   confirm -- Candidate Peering.
5. **Nothing real reached** -- retry once against the target ASN's next
   cached prefix (a dead end can be a property of one destination address,
   not the whole ASN -- confirmed concretely earlier this project). Still
   dark after the retry -- Inconclusive: marked tested, no finding filed.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import math
import sqlite3
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pacific_peering.analysis import known_anomalies
from pacific_peering.analysis import store as _store
from pacific_peering.analysis.corridor_backlog import (
    CorridorCandidate,
    enumerate_candidate_corridors,
    mark_corridor_tested,
    pick_next_corridor,
)
from pacific_peering.analysis.ixp_lan_registry import (
    DEFAULT_REGISTRY_PATH as IXP_REGISTRY_PATH,
    load_ixp_lan_registry,
)
from pacific_peering.analysis.traceroute_topology import (
    DEFAULT_ATLAS_PARSED_DIR,
    analyze_measurement,
)
from pacific_peering.atlas.asn_probes import (
    DEFAULT_REGISTRY_PATH as ASN_PROBE_REGISTRY_PATH,
    load_asn_probe_registry,
)
from pacific_peering.atlas.smoketest import run_smoketest
from pacific_peering.atlas.targets import has_routing_loop, list_target_ips
from pacific_peering.discovery import cloudflare_radar
from pacific_peering.discovery.bgp_tools import fetch_asn_names
from pacific_peering.discovery.economies import ECONOMIES_BY_CC
from pacific_peering.discovery.economy_coordinates import EXTERNAL_HUB_LATLON

logger = logging.getLogger(__name__)

DEFAULT_ASN_REGISTRY_PATH = Path("data/asn_registry.json")
DEFAULT_ESCALATIONS_PATH = Path("escalations.md")
DEFAULT_REVERIFY_QUEUE_PATH = Path("data/analysis/reverify_queue.json")
_PROBE_COUNT = 3
_MAX_TARGET_IP_ATTEMPTS = 2  # primary + one alternate prefix, per the retry-on-deadend feedback
_REVERIFY_FRACTION = 0.25  # oldest quarter each week -> full rotation roughly every 4 weeks
_ASPA_RECHECK_MAX_AGE_DAYS = 30  # project owner's own cadence choice

# A hop crossing a *local* (in_fishbowl=True) IXP should show fiber-propagation-
# scale RTT, not international-detour-scale RTT -- per the project owner, real
# fiber runs ~10 microseconds/km round-trip (2x the ~4.9us/km one-way speed of
# light in standard single-mode fiber), so even Fiji's largest inter-island
# span (a few hundred km) has a theoretical floor of a few ms, while any real
# Sydney/Auckland/LA/Tokyo detour is tens to a hundred-plus ms -- an order-of-
# magnitude physical separation, not a fitted statistical threshold (this
# project has zero recorded genuinely-local-IXP RTT samples yet to fit one).
# 10ms is a physically-grounded engineering margin for now, confirmed fiber
# (not microwave/satellite) end to end; expect to push it down once real
# local-IXP-crossing RTT data accumulates.
LOCAL_IXP_LATENCY_THRESHOLD_MS = 10.0


@dataclass
class _Escalation:
    """Something the mechanical rules couldn't confidently resolve -- surfaced
    to a human/LLM rather than silently guessed at or dropped."""

    candidate: CorridorCandidate
    measurement_id: int
    reason: str
    detail: str


@dataclass
class ClassifyResult:
    candidate: CorridorCandidate
    outcome: str  # "confirmed_detour" | "confirmed_local_transit" | "candidate_peering" | "inconclusive" | "escalated"
    finding_id: int | None = None
    escalations: list[_Escalation] = field(default_factory=list)


def _asn_holder_name(asn: int, cache: dict[int, str]) -> str:
    if asn not in cache:
        info = fetch_asn_names([asn]).get(asn)
        cache[asn] = info.name if info else f"AS{asn}"
    return cache[asn]


def _load_asn_to_cc(path: Path = DEFAULT_ASN_REGISTRY_PATH) -> dict[int, str]:
    registry = json.loads(path.read_text())
    return {asn: cc for cc, entry in registry.items() for asn in entry["asns"]}


def _first_looping_address(hops: list[dict]) -> str | None:
    """The first address that recurs across hops -- good enough to identify
    *which* known (or unknown) location a loop sits in; `has_routing_loop`
    already did the real work of deciding whether it's a genuine loop."""
    seen: list[str] = []
    window = 3
    for hop in hops:
        addresses = hop.get("addresses") or []
        if len(addresses) != 1:
            continue
        addr = addresses[0]
        if addr in seen:
            return addr
        seen.append(addr)
        if len(seen) > window:
            seen.pop(0)
    return None


def _fire_measurement(candidate: CorridorCandidate, target_ip: str) -> int:
    return run_smoketest(
        target_asn=candidate.target_asn,
        target_cc=candidate.target_cc,
        probe_count=_PROBE_COUNT,
        source_cc=candidate.source_cc,
    )


def classify_corridor(
    candidate: CorridorCandidate,
    lock: threading.Lock | None = None,
    regenerate: bool = True,
) -> ClassifyResult:
    """Fire, triangulate, and classify one corridor. Files a finding (or an
    escalation) and always marks the corridor tested, any outcome.

    Args:
        lock: when given (batch mode -- see `run_batch`), every local
            write (SQLite, `tested_pairs.json`, `escalations.md`) is
            serialized under this lock so concurrent workers testing
            *different* corridors can't race each other's read-modify-write
            file updates. The slow part -- firing the measurement and
            waiting for Atlas -- happens *before* this section, unlocked,
            which is the whole point of running workers concurrently in
            the first place.
        regenerate: whether to regenerate every derived artifact after
            this one corridor. `run_batch` passes `False` and regenerates
            once at the end instead -- doing it after every corridor in a
            tight time-boxed batch would spend most of the budget on
            subprocess overhead rather than actual testing.
    """
    asn_to_cc = _load_asn_to_cc()
    ixp_registry = load_ixp_lan_registry(IXP_REGISTRY_PATH)
    name_cache: dict[int, str] = {}
    escalations: list[_Escalation] = []

    target_ips = list_target_ips(candidate.target_asn)
    measurement_id: int | None = None
    triangulation: dict | None = None
    parsed: list[dict] = []

    for attempt, target_ip in enumerate(target_ips[:_MAX_TARGET_IP_ATTEMPTS]):
        measurement_id = _fire_measurement(candidate, target_ip)
        triangulation = analyze_measurement(measurement_id, candidate.target_asn)
        parsed_path = DEFAULT_ATLAS_PARSED_DIR / f"{measurement_id}.json"
        parsed = json.loads(parsed_path.read_text())

        any_signal = any(
            p.get("traceroute_upstream_asn") is not None for p in triangulation["probes"]
        )
        if any_signal or attempt == len(target_ips[:_MAX_TARGET_IP_ATTEMPTS]) - 1:
            break
        logger.info(
            "AS%d -> AS%d: %s was fully dark, retrying against %s (%s)",
            candidate.source_asn, candidate.target_asn, target_ip,
            target_ips[attempt + 1], "alternate cached prefix",
        )

    assert measurement_id is not None and triangulation is not None
    hops_by_probe = {p["probe_id"]: p["hops"] for p in parsed}

    # Loop check, per probe -- always with the real target IP for this attempt.
    loop_notes: dict[int, str] = {}
    for probe in triangulation["probes"]:
        hops = hops_by_probe.get(probe["probe_id"], [])
        if not has_routing_loop(hops, target=target_ip):
            continue
        looping_addr = _first_looping_address(hops)
        known = known_anomalies.classify_loop_address(looping_addr) if looping_addr else None
        if known is not None:
            loop_notes[probe["probe_id"]] = f"loop at {looping_addr} ({known.description[:80]}...)"
        else:
            escalations.append(
                _Escalation(
                    candidate=candidate,
                    measurement_id=measurement_id,
                    reason="unrecognized routing loop",
                    detail=(
                        f"probe {probe['probe_id']}: loop involving address "
                        f"{looping_addr or '(unresolved)'}, not in known_anomalies.py"
                    ),
                )
            )

    detour_pick: tuple[dict, str, str] | None = None  # (crossing, ix_name, hub_city)
    local_transit_pick: dict | None = None
    candidate_picks: list[dict] = []
    tba_ixp_hit = False
    high_latency_local_crossings: list[dict] = []

    for probe in triangulation["probes"]:
        for crossing in probe.get("ixp_crossings", []):
            in_fishbowl = crossing.get("in_fishbowl")
            if in_fishbowl == "TBA":
                tba_ixp_hit = True
                continue
            if in_fishbowl is False:
                entry = ixp_registry.get(crossing.get("ix_id"))
                hub_city = entry.city if entry else None
                if hub_city in EXTERNAL_HUB_LATLON:
                    detour_pick = detour_pick or (crossing, crossing.get("name", "?"), hub_city)
            elif in_fishbowl is True:
                rtt = crossing.get("min_rtt_ms")
                if rtt is not None and rtt > LOCAL_IXP_LATENCY_THRESHOLD_MS:
                    high_latency_local_crossings.append({**crossing, "probe_id": probe["probe_id"]})

        upstream_asn = probe.get("traceroute_upstream_asn")
        if upstream_asn is None:
            continue
        if probe.get("ris_agrees") and probe.get("contiguous", True):
            if upstream_asn in asn_to_cc:
                local_transit_pick = local_transit_pick or probe
        elif not probe.get("ris_agrees"):
            candidate_picks.append(probe)

    if tba_ixp_hit and detour_pick is None:
        escalations.append(
            _Escalation(
                candidate=candidate,
                measurement_id=measurement_id,
                reason="unclassified (TBA) IXP crossing",
                detail="traceroute crosses an exchange ixp_lan_registry.json has not yet "
                "been told is in- or out-of-fishbowl; needs a human call, not a guess",
            )
        )

    for crossing in high_latency_local_crossings:
        escalations.append(
            _Escalation(
                candidate=candidate,
                measurement_id=measurement_id,
                reason="local IXP crossing with implausibly high latency",
                detail=(
                    f"probe {crossing['probe_id']}: hop {crossing['hop']} crosses "
                    f"{crossing.get('name', '?')} (in-fishbowl) at {crossing['min_rtt_ms']}ms, "
                    f"above the {LOCAL_IXP_LATENCY_THRESHOLD_MS}ms local-fiber threshold -- "
                    "either this hop isn't genuinely local despite the registry, or there's "
                    "an unexpected detour/backhaul before reaching it; needs a human look, "
                    "not a guess"
                ),
            )
        )

    def _finalize() -> ClassifyResult:
        conn = _store.connect()
        try:
            if detour_pick is not None:
                _, ix_name, hub_city = detour_pick
                finding = _store.find_existing_detour(conn, candidate.source_cc, candidate.target_asn)
                if finding is None:
                    finding_id = _store.create_finding(
                        conn,
                        kind=_store.KIND_CONFIRMED_DETOUR,
                        source_cc=candidate.source_cc,
                        source_asn=candidate.source_asn,
                        source_name=candidate.source_name,
                        target_cc=candidate.target_cc,
                        target_asn=candidate.target_asn,
                        target_name=_asn_holder_name(candidate.target_asn, name_cache),
                        detour_ix_name=ix_name,
                        detour_hub=hub_city,
                    )
                else:
                    finding_id = finding.id
                for probe in triangulation["probes"]:
                    chain = " -> ".join(f"AS{e['asn']}" for e in probe.get("as_sequence", []))
                    _store.add_corroboration(
                        conn,
                        finding_id=finding_id,
                        measurement_id=measurement_id,
                        vantage_point_cc=candidate.source_cc,
                        vantage_point_asn=candidate.source_asn,
                        chain=chain or None,
                        ris_observation_count=probe.get("ris_observation_count"),
                        ris_agrees=probe.get("ris_agrees"),
                        has_loop=probe["probe_id"] in loop_notes,
                        loop_note=loop_notes.get(probe["probe_id"]),
                    )
                mark_corridor_tested(candidate.source_asn, candidate.target_asn)
                if regenerate:
                    _regenerate_artifacts()
                if escalations:
                    _write_escalations(escalations)
                return ClassifyResult(candidate, "confirmed_detour", finding_id, escalations)

            if local_transit_pick is not None:
                upstream_asn = local_transit_pick["traceroute_upstream_asn"]
                finding = _store.find_existing(
                    conn, _store.KIND_CONFIRMED_LOCAL_TRANSIT, upstream_asn, candidate.target_asn
                )
                if finding is None:
                    finding_id = _store.create_finding(
                        conn,
                        kind=_store.KIND_CONFIRMED_LOCAL_TRANSIT,
                        source_cc=asn_to_cc.get(upstream_asn, "??"),
                        source_asn=upstream_asn,
                        source_name=_asn_holder_name(upstream_asn, name_cache),
                        target_cc=candidate.target_cc,
                        target_asn=candidate.target_asn,
                        target_name=_asn_holder_name(candidate.target_asn, name_cache),
                    )
                else:
                    finding_id = finding.id
                for probe in triangulation["probes"]:
                    chain = " -> ".join(f"AS{e['asn']}" for e in probe.get("as_sequence", []))
                    _store.add_corroboration(
                        conn,
                        finding_id=finding_id,
                        measurement_id=measurement_id,
                        vantage_point_cc=candidate.source_cc,
                        vantage_point_asn=candidate.source_asn,
                        chain=chain or None,
                        ris_observation_count=probe.get("ris_observation_count"),
                        ris_agrees=probe.get("ris_agrees"),
                        has_loop=probe["probe_id"] in loop_notes,
                        loop_note=loop_notes.get(probe["probe_id"]),
                    )
                mark_corridor_tested(candidate.source_asn, candidate.target_asn)
                if regenerate:
                    _regenerate_artifacts()
                if escalations:
                    _write_escalations(escalations)
                return ClassifyResult(candidate, "confirmed_local_transit", finding_id, escalations)

            if candidate_picks:
                upstream_asn = candidate_picks[0]["traceroute_upstream_asn"]
                agree_count = sum(
                    1 for p in candidate_picks if p["traceroute_upstream_asn"] == upstream_asn
                )
                finding = _store.find_existing(
                    conn, _store.KIND_CANDIDATE_PEERING, upstream_asn, candidate.target_asn
                )
                if finding is None:
                    finding_id = _store.create_finding(
                        conn,
                        kind=_store.KIND_CANDIDATE_PEERING,
                        source_cc=asn_to_cc.get(upstream_asn, "??"),
                        source_asn=upstream_asn,
                        source_name=_asn_holder_name(upstream_asn, name_cache),
                        target_cc=candidate.target_cc,
                        target_asn=candidate.target_asn,
                        target_name=_asn_holder_name(candidate.target_asn, name_cache),
                        probe_agreement=f"{agree_count}/{len(triangulation['probes'])} probes",
                    )
                else:
                    finding_id = finding.id
                for probe in triangulation["probes"]:
                    chain = " -> ".join(f"AS{e['asn']}" for e in probe.get("as_sequence", []))
                    _store.add_corroboration(
                        conn,
                        finding_id=finding_id,
                        measurement_id=measurement_id,
                        vantage_point_cc=candidate.source_cc,
                        vantage_point_asn=candidate.source_asn,
                        chain=chain or None,
                        ris_observation_count=probe.get("ris_observation_count"),
                        ris_agrees=probe.get("ris_agrees"),
                        has_loop=probe["probe_id"] in loop_notes,
                        loop_note=loop_notes.get(probe["probe_id"]),
                    )
                mark_corridor_tested(candidate.source_asn, candidate.target_asn)
                if regenerate:
                    _regenerate_artifacts()
                if escalations:
                    _write_escalations(escalations)
                return ClassifyResult(candidate, "candidate_peering", finding_id, escalations)
        finally:
            conn.close()

        mark_corridor_tested(candidate.source_asn, candidate.target_asn)
        if escalations:
            _write_escalations(escalations)
            return ClassifyResult(candidate, "escalated", None, escalations)
        logger.info(
            "AS%d -> AS%d: inconclusive, no real signal after %d attempt(s); marked tested",
            candidate.source_asn, candidate.target_asn, len(target_ips[:_MAX_TARGET_IP_ATTEMPTS]),
        )
        return ClassifyResult(candidate, "inconclusive", None, escalations)

    with lock if lock is not None else contextlib.nullcontext():
        return _finalize()
    return ClassifyResult(candidate, "inconclusive", None, escalations)


def _write_escalations(escalations: list[_Escalation], path: Path = DEFAULT_ESCALATIONS_PATH) -> None:
    now = datetime.now(timezone.utc).isoformat()
    lines = []
    if not path.exists():
        lines.append("# Escalations")
        lines.append("")
        lines.append(
            "Corridors `auto_classify.py`'s mechanical rules couldn't confidently "
            "resolve on their own -- a routing loop at an address never seen before, "
            "an IXP crossing PeeringDB/`ixp_lan_registry.json` hasn't been told is "
            "in- or out-of-fishbowl, an external upstream at a hub with no known "
            "coordinates. Each needs a human/LLM look before it's added to "
            "`known_anomalies.py`, `ixp_lan_registry.json`, or "
            "`economy_coordinates.EXTERNAL_HUB_LATLON` and reprocessed."
        )
        lines.append("")
    for esc in escalations:
        c = esc.candidate
        lines.append(f"## AS{c.source_asn} ({c.source_cc}) -> AS{c.target_asn} ({c.target_cc})")
        lines.append(f"- measurement: {esc.measurement_id}")
        lines.append(f"- reason: {esc.reason}")
        lines.append(f"- detail: {esc.detail}")
        lines.append(f"- flagged: {now}")
        lines.append("")
    with path.open("a") as f:
        f.write("\n".join(lines) + "\n")
    logger.warning("Wrote %d escalation(s) to %s", len(escalations), path)


def _regenerate_artifacts() -> None:
    """Re-run every derived-artifact command as a subprocess, mirroring how
    this project's tranches have always regenerated reports by hand.
    Subprocesses, not in-process calls, because `reports/data.py` and
    `corridor_backlog.py` read their SQLite-backed constants at import
    time -- a long-lived classifier process can't just re-import them."""
    commands = [
        ["findings-export", "pacific_peering.analysis.store"],
        ["corridor-backlog", "pacific_peering.analysis.corridor_backlog"],
        ["report-ascii", "pacific_peering.reports.ascii_report"],
        ["report-html", "pacific_peering.reports.html_report"],
        ["viz-detours", "pacific_peering.viz.geographic"],
    ]
    for label, module in commands:
        result = subprocess.run(
            [sys.executable, "-m", module], capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.error("Artifact regeneration step %s failed:\n%s", label, result.stderr)


def classify_next(max_corridors: int = 1) -> list[ClassifyResult]:
    """Pull up to `max_corridors` candidates off the backlog and classify each."""
    results: list[ClassifyResult] = []
    for _ in range(max_corridors):
        candidate = pick_next_corridor()
        if candidate is None:
            logger.info("Corridor backlog is empty; nothing to classify")
            break
        logger.info(
            "Classifying AS%d (%s) -> AS%d (%s): %s",
            candidate.source_asn, candidate.source_cc,
            candidate.target_asn, candidate.target_cc, candidate.rationale,
        )
        results.append(classify_corridor(candidate))
    return results


def _last_verified(conn: sqlite3.Connection, finding: _store.Finding) -> str:
    """The most recent corroboration's timestamp for this finding, or its
    own creation time if it's never been re-corroborated since filing."""
    corrobs = _store.get_corroborations(conn, finding.id)
    if not corrobs:
        return finding.created_at
    return max(c.created_at for c in corrobs)


def select_reverification_batch(fraction: float = _REVERIFY_FRACTION) -> list[int]:
    """IDs of the oldest-verified `fraction` of all findings, by their most
    recent corroboration -- the ones due for a fresh look, not the ones
    already checked in on recently."""
    conn = _store.connect()
    try:
        findings = _store.all_findings(conn)
        ranked = sorted(findings, key=lambda f: _last_verified(conn, f))
    finally:
        conn.close()
    n = math.ceil(len(ranked) * fraction)
    return [f.id for f in ranked[:n]]


def write_reverification_queue(
    path: Path = DEFAULT_REVERIFY_QUEUE_PATH, fraction: float = _REVERIFY_FRACTION
) -> int:
    """Stage the oldest-verified quarter of findings for this week's nightly
    runs to re-test. Per the project owner: a rolling reverification (the
    oldest quarter, every week) rather than one giant periodic re-check --
    it never has to compete with new-corridor testing for a whole night's
    budget, and every finding gets a fresh look roughly every 4 weeks.
    Overwrites any prior queue contents -- this is "this week's ration,"
    not an ever-growing backlog; whatever the nightly runs didn't get to
    this week is superseded, not lost (it'll be near the front again once
    its turn comes back around, since it's still among the oldest-verified).
    """
    finding_ids = select_reverification_batch(fraction)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"finding_ids": finding_ids, "enqueued_at": datetime.now(timezone.utc).isoformat()},
            indent=2,
        )
        + "\n"
    )
    logger.info("Staged %d finding(s) for reverification this week", len(finding_ids))
    return len(finding_ids)


def recheck_aspa_candidates(
    max_age_days: int = _ASPA_RECHECK_MAX_AGE_DAYS, regenerate: bool = True
) -> dict[str, int]:
    """Re-check every `candidate_peering` finding not ASPA-checked in the
    last `max_age_days` against Cloudflare Radar's current ASPA snapshot,
    promoting any whose upstream is now an ASPA-authorized provider of the
    target ASN to `confirmed_local_transit` -- see
    `store.mark_aspa_checked`/`discovery.cloudflare_radar`.

    Cheap and local (one cached snapshot fetch, then in-memory lookups),
    unlike Atlas-backed reverification -- there's no reason to ration this
    across nightly runs the way `select_reverification_batch` does.
    `max_age_days` exists only so a routine weekly call doesn't redundantly
    re-touch findings checked a few days ago, not to spread out real cost.
    """
    conn = _store.connect()
    try:
        due = _store.find_candidates_due_for_aspa_recheck(conn, max_age_days=max_age_days)
        if not due:
            logger.info("No candidate_peering findings due for an ASPA recheck")
            return {"checked": 0, "promoted": 0}
        checked_at = datetime.now(timezone.utc).isoformat()
        promoted = 0
        for finding in due:
            providers = cloudflare_radar.get_aspa_providers(finding.target_asn)
            confirmed = providers is not None and finding.source_asn in providers
            note = None
            if confirmed:
                note = (
                    "\n\n---\n\n"
                    f"**ASPA-confirmed {checked_at}**: AS{finding.target_asn}'s own "
                    f"published ASPA record (RFC 9582, via Cloudflare Radar) lists "
                    f"AS{finding.source_asn} among its authorized providers "
                    f"{providers} -- a cryptographically-signed statement from the "
                    f"target itself, promoted from candidate_peering on that basis "
                    f"rather than RIS agreement."
                )
            did_promote = _store.mark_aspa_checked(
                conn, finding.id, confirmed=confirmed, checked_at=checked_at, promotion_note=note,
            )
            if did_promote:
                promoted += 1
                logger.info(
                    "AS%d -> AS%d: ASPA-confirmed, promoted candidate_peering -> confirmed_local_transit",
                    finding.source_asn, finding.target_asn,
                )
            elif confirmed:
                logger.warning(
                    "AS%d -> AS%d: ASPA confirms this upstream but an existing "
                    "confirmed_local_transit finding already occupies this "
                    "(source_asn, target_asn) pair -- left as candidate_peering, "
                    "needs a human look",
                    finding.source_asn, finding.target_asn,
                )
        logger.info("ASPA recheck: %d checked, %d promoted", len(due), promoted)
    finally:
        conn.close()
    if regenerate:
        # Always re-export, even with zero promotions -- every checked
        # finding's aspa_checked_at moved, and that has to reach the
        # committed JSONL (the source of truth) or it's lost the next
        # time the local, gitignored findings.db gets rebuilt from it,
        # defeating the whole point of the 30-day gate.
        _regenerate_artifacts()
    return {"checked": len(due), "promoted": promoted}


def _any_probe_asn_for_cc(cc: str) -> int | None:
    """Any currently-connected probe ASN for this economy -- used only as a
    firing-bookkeeping fallback when a finding's original vantage-point ASN
    wasn't recorded (every finding migrated from the legacy dataclasses
    only ever tracked the vantage *economy*, never a literal ASN). Firing
    itself is always country-based (`run_smoketest`'s `source_cc`), so this
    doesn't need to be the *exact* original probe -- any connected ASN in
    the same economy fires from the same country selector."""
    registry = load_asn_probe_registry(ASN_PROBE_REGISTRY_PATH)
    asn_to_cc = _load_asn_to_cc()
    candidates = sorted(a for a in registry if asn_to_cc.get(a) == cc)
    return candidates[0] if candidates else None


def _candidate_from_finding(conn: sqlite3.Connection, finding_id: int) -> CorridorCandidate | None:
    """Rebuild a firable `CorridorCandidate` from an existing finding, using
    its most recent corroboration's vantage point as the source -- this
    re-runs the exact test that originally produced the finding, rather
    than searching for something new. Returns `None` if the finding has
    since vanished, has no corroboration to derive a vantage point from, or
    its vantage economy no longer has any connected probe at all."""
    finding = next((f for f in _store.all_findings(conn) if f.id == finding_id), None)
    if finding is None:
        return None
    corrobs = _store.get_corroborations(conn, finding_id)
    if not corrobs:
        return None
    latest = max(corrobs, key=lambda c: c.created_at)
    source_cc = latest.vantage_point_cc
    source_asn = latest.vantage_point_asn or _any_probe_asn_for_cc(source_cc)
    if source_asn is None:
        return None
    source_economy = ECONOMIES_BY_CC.get(source_cc)
    target_economy = ECONOMIES_BY_CC.get(finding.target_cc)
    return CorridorCandidate(
        source_asn=source_asn,
        source_cc=source_cc,
        source_name=source_economy.name if source_economy else source_cc,
        target_asn=finding.target_asn,
        target_cc=finding.target_cc,
        target_name=target_economy.name if target_economy else finding.target_cc,
        rationale=(
            f"scheduled reverification of finding #{finding.id} "
            f"(kind={finding.kind}, last verified {latest.created_at})"
        ),
    )


def _pop_reverify_candidate(
    exclude_source_asns: set[int], path: Path = DEFAULT_REVERIFY_QUEUE_PATH
) -> CorridorCandidate | None:
    """Must be called with `run_batch`'s write lock held -- reads, mutates,
    and rewrites the queue file, so two workers popping concurrently would
    otherwise race each other's read-modify-write. Pops the first queued
    finding whose vantage-point ASN isn't already in flight; a finding
    that's vanished (or lost every connected probe in its vantage economy)
    is dropped permanently, not left to jam the queue forever. Leaves
    everything else queued -- including any entry blocked only by
    `exclude_source_asns` right now -- for a later attempt."""
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    finding_ids: list[int] = list(data.get("finding_ids", []))
    if not finding_ids:
        return None
    conn = _store.connect()
    try:
        remaining = list(finding_ids)
        picked: CorridorCandidate | None = None
        for finding_id in finding_ids:
            candidate = _candidate_from_finding(conn, finding_id)
            if candidate is None:
                remaining.remove(finding_id)
                continue
            if candidate.source_asn in exclude_source_asns:
                continue
            remaining.remove(finding_id)
            picked = candidate
            break
    finally:
        conn.close()
    if remaining != finding_ids:
        data["finding_ids"] = remaining
        path.write_text(json.dumps(data, indent=2) + "\n")
    return picked


def _pick_next_for_batch(exclude_source_asns: set[int]) -> CorridorCandidate | None:
    """Like `pick_next_corridor`, but skips any candidate whose source ASN
    is currently in flight in another worker. Atlas serializes measurements
    per source probe regardless of how fast we submit to it, so two workers
    racing the same source ASN would just queue behind each other for zero
    throughput gain -- the actual lever is running *different* source ASNs
    concurrently, not more work against one."""
    for candidate in enumerate_candidate_corridors():
        if candidate.source_asn not in exclude_source_asns:
            return candidate
    return None


def run_batch(time_budget_seconds: float, max_concurrent: int = 5) -> list[ClassifyResult]:
    """Fit as many corridor tests as possible into `time_budget_seconds`,
    running concurrently across different source-economy probes.

    This is the parallel-across-probes insight from earlier in this
    project, applied for real: a single source ASN's connected probe
    serializes its own measurements no matter how fast we submit to it, so
    real throughput comes from running several *different* source ASNs at
    once, not from batching more work against one. Each worker thread only
    ever has one source ASN in flight at a time; picking the next candidate,
    filing a finding, and marking a corridor tested are all serialized
    under one lock (fast, local file/DB writes), while firing a measurement
    and waiting for Atlas -- the actually slow part -- happens unlocked, so
    that's where the concurrency gain is spent.

    Stops pulling *new* work once the deadline passes; corridors already in
    flight are allowed to finish (a fired Atlas measurement can't be
    un-fired). Regenerates every derived artifact once at the end, not per
    corridor -- spending a time-boxed budget on repeated subprocess
    overhead instead of actual testing would defeat the point.
    """
    deadline = time.monotonic() + time_budget_seconds
    write_lock = threading.Lock()
    in_flight: set[int] = set()
    results: list[ClassifyResult] = []
    results_lock = threading.Lock()

    def worker() -> None:
        while time.monotonic() < deadline:
            with write_lock:
                # Reverification queue first -- it's a fixed weekly ration
                # meant to finish within the week, whereas new corridors
                # just keep accumulating regardless of when they're tested.
                candidate = _pop_reverify_candidate(in_flight)
                if candidate is None:
                    candidate = _pick_next_for_batch(in_flight)
                if candidate is not None:
                    in_flight.add(candidate.source_asn)
                elif not in_flight:
                    return  # nothing left anywhere, and nothing else will free one up
            if candidate is None:
                time.sleep(2)  # everything left is behind a source ASN another worker holds
                continue
            logger.info(
                "Classifying AS%d (%s) -> AS%d (%s): %s",
                candidate.source_asn, candidate.source_cc,
                candidate.target_asn, candidate.target_cc, candidate.rationale,
            )
            try:
                result = classify_corridor(candidate, lock=write_lock, regenerate=False)
                with results_lock:
                    results.append(result)
                logger.info(
                    "AS%d -> AS%d: %s%s",
                    candidate.source_asn, candidate.target_asn, result.outcome,
                    f" ({len(result.escalations)} escalation(s))" if result.escalations else "",
                )
            except Exception:  # noqa: BLE001 - one corridor's failure must not sink the worker
                logger.exception(
                    "AS%d -> AS%d: classification failed, leaving untested for a future pull",
                    candidate.source_asn, candidate.target_asn,
                )
            finally:
                with write_lock:
                    in_flight.discard(candidate.source_asn)

    threads = [
        threading.Thread(target=worker, name=f"corridor-worker-{i}") for i in range(max_concurrent)
    ]
    started_at = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if results:
        _regenerate_artifacts()
    logger.info(
        "Batch done: %d corridor(s) tested in %.0fs (budget %.0fs)",
        len(results), time.monotonic() - started_at, time_budget_seconds,
    )
    return results


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    results = classify_next()
    for r in results:
        logger.info(
            "AS%d -> AS%d: %s%s",
            r.candidate.source_asn, r.candidate.target_asn, r.outcome,
            f" ({len(r.escalations)} escalation(s))" if r.escalations else "",
        )


def main_batch() -> None:
    """`uv run pacific-peering-auto-classify-batch [--hours H] [--max-concurrent N]`
    -- fit as many corridor tests as possible into a fixed wall-clock budget
    (default 2 hours), for unattended cron use. See `run_batch`."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Time-boxed batch corridor classification.")
    parser.add_argument(
        "--hours", type=float, default=2.0, help="time budget in hours (default: 2)"
    )
    parser.add_argument(
        "--max-concurrent", type=int, default=5,
        help="max concurrent source-ASN workers (default: 5)",
    )
    args = parser.parse_args()
    results = run_batch(args.hours * 3600, max_concurrent=args.max_concurrent)
    outcomes: dict[str, int] = {}
    for r in results:
        outcomes[r.outcome] = outcomes.get(r.outcome, 0) + 1
    logger.info("Outcomes: %s", outcomes)


def main_reverify_enqueue() -> None:
    """`uv run pacific-peering-reverify-enqueue [--fraction F]` -- stage the
    oldest-verified fraction of findings (default 1/4) for the nightly
    batches to re-test this week. Run from the weekly discovery refresh,
    right after the backlog regen -- see `write_reverification_queue`."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Stage findings for reverification.")
    parser.add_argument(
        "--fraction", type=float, default=_REVERIFY_FRACTION,
        help=f"fraction of findings to stage, oldest-verified first (default: {_REVERIFY_FRACTION})",
    )
    args = parser.parse_args()
    write_reverification_queue(fraction=args.fraction)


def main_aspa_recheck() -> None:
    """`uv run pacific-peering-aspa-recheck [--max-age-days N]` -- re-check
    `candidate_peering` findings against Cloudflare Radar's ASPA data,
    promoting any now-confirmed ones. Cheap and local (no Atlas credits) --
    run from the weekly discovery refresh, alongside the reverification
    enqueue step. See `recheck_aspa_candidates`."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Re-check candidate_peering findings against ASPA.")
    parser.add_argument(
        "--max-age-days", type=int, default=_ASPA_RECHECK_MAX_AGE_DAYS,
        help=(
            "only recheck findings not already checked within this many "
            f"days (default: {_ASPA_RECHECK_MAX_AGE_DAYS})"
        ),
    )
    args = parser.parse_args()
    result = recheck_aspa_candidates(max_age_days=args.max_age_days)
    logger.info(
        "ASPA recheck done: %d checked, %d promoted", result["checked"], result["promoted"]
    )


if __name__ == "__main__":
    main()
