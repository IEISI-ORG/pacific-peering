"""Systematic corridor backlog: a maintained todo list, not a fresh judgment call each tranche.

Per the project owner's explicit ask: generate a todo list of untested
corridors, work one item per `/loop` firing, refresh the list periodically
(every ~8 hours, via a separate `CronCreate` job), and treat new Atlas
probes / new RIS-observed neighbor relationships as a standing signal for
what to test next -- rather than re-deriving the candidate space from
memory each hourly tranche, which is how every prior tranche this session
actually worked (and which doesn't scale as the project's own history
grows).

Two persisted pieces of state, both under `data/analysis/` (generated,
gitignored -- same convention as the rest of this project's derived data):
- `tested_pairs.json`: every `(source_asn, target_asn)` this project has
  ever deliberately fired a traceroute between, *any* outcome. The
  authoritative "don't re-test this" record. Needed because the finding
  dataclasses alone don't capture inconclusive/candidate results, and
  `ConfirmedDetour` doesn't even store a source ASN (only `source_cc`) --
  see task_plan.md's NC->GU Superloop case, which is real, logged, and
  genuinely untested-again-worthy of exclusion despite not living in any
  dataclass.
- `corridor_backlog_snapshot.json`: the probe registry + RIS neighbor sets
  as of the last backlog regeneration, diffed against the current state
  each time `build_corridor_backlog()` runs, to surface what's *new* since
  last time (a probe that just came online, a RIS relationship that just
  appeared) as high-priority candidates rather than treating the whole
  164-ASN space as equally fresh forever.

One committed, human-readable artifact: `corridor_backlog.md` at the repo
root, alongside `task_plan.md`/`CHANGELOG.md` -- regenerated, not hand-
edited, but git-tracked so its history is visible the same way the rest
of this project's durable record is.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pacific_peering.analysis import store as _store
from pacific_peering.analysis.fishbowl import DEFAULT_SUMMARY_PATH
from pacific_peering.atlas.asn_probes import DEFAULT_REGISTRY_PATH, load_asn_probe_registry
from pacific_peering.atlas.probes import DEFAULT_LISTING_PATH, load_probe_listing
from pacific_peering.discovery.economies import ECONOMIES_BY_CC

# Loaded from the SQLite store (analysis/store.py), not the legacy
# confirmed_detours.py/confirmed_local_transit.py/candidate_peering.py
# modules directly -- those are frozen historical snapshots as of the
# SQLite migration. Loading here, not at call time, so a single backlog
# regeneration sees one consistent snapshot even if findings are being
# written concurrently (matches the previous module-level-constant
# behavior exactly).
_conn = _store.connect()
CONFIRMED_DETOURS = _store.load_confirmed_detours(_conn)
CONFIRMED_LOCAL_TRANSIT = _store.load_confirmed_local_transit(_conn)
CANDIDATE_PEERING = _store.load_candidate_peering(_conn)
_conn.close()

logger = logging.getLogger(__name__)

DEFAULT_TESTED_PAIRS_PATH = Path("data/analysis/tested_pairs.json")
DEFAULT_SNAPSHOT_PATH = Path("data/analysis/corridor_backlog_snapshot.json")
DEFAULT_BACKLOG_MD_PATH = Path("corridor_backlog.md")

# ASNs excluded as both source and target -- either not a real
# Pacific-region candidate at all (external carriers/proxies incidentally
# surfaced by country-based probe selection or transit paths), or a real
# Pacific ASN whose only connected probe's data is permanently unusable
# for path analysis regardless of geography. Extend this as more turn up
# (matches the exclusions already applied by hand across many tranches
# this session -- see task_plan.md).
EXTERNAL_NON_CANDIDATE_ASNS = frozenset(
    {
        2200,  # Renater (France)
        14593,  # SpaceX Starlink
        53813,  # Zscaler (proxy artifact)
        141695,  # Pacific Community -- real Fiji presence, but its only connected
        # probe (60575) still egresses through Zscaler (AS53813 as the first
        # resolved hop on every 2026-09-19 measurement fired from it) despite
        # its LAN-level ASN metadata correctly reading Fiji -- the ASN/geo
        # reclassification (reclassified_asns.py) fixed the economy label, not
        # the underlying path corruption. Confirmed on 6 separate FJ-domestic
        # measurements (findings 197-202, retracted) all showing AS53813 as
        # the first hop, and on the original finding 25 (also retracted).
        # Excluded here as a source *and* target until a probe on one of
        # Fiji's actual commercial ISPs (Vodafone/AS38442, Telecom Fiji/
        # AS4638 or AS45349, Digicel/AS45355, FINTEL/AS9241) comes online.
    }
)

# Economies explicitly opted into domestic (same-economy) corridor testing --
# an intentional exception to the cross-economy-only scope below. Per the
# project owner: this project's whole point is measuring local peering
# effectiveness, and a same-economy pair that tromboned through an external
# hub (e.g. two Fiji ASNs routing via Sydney) is arguably the single most
# important finding category -- yet it had never once been checked for
# automatically, anywhere, because the cross-economy filter excluded every
# domestic pair by construction. Opt-in per economy (not a blanket flip)
# to avoid combinatorial blowup on large in-scope ASN lists (e.g. PG's 38
# ASNs) where only a handful of pairs are actually reachable from a
# connected probe.
#
# Scoped to every economy with a real, same-country IXP on PeeringDB (per
# `probe_gap_report.py`'s Local IXP Presence section) -- per the project
# owner: "schedule all CC [with] an IXP next". A domestic detour is most
# interesting precisely where a local exchange exists to *not* be used;
# an economy with no local IXP at all has a different, less specific
# question ("is there any real local peering fabric here"), not this
# one. Recompute via the same query as `_compute_local_ixps` before
# adding an economy here -- don't hand-guess which ones qualify.
DOMESTIC_TEST_ECONOMIES: frozenset[str] = frozenset({"FJ", "GU", "NC", "PG", "VU"})

# Economy pairs already known to have a real result on record from before
# this backlog system existed, but only in task_plan.md prose (not
# recoverable from any dataclass) -- a one-time seed so the backlog
# doesn't immediately propose re-testing something already covered.
# Every pair tested *after* this system's introduction gets recorded via
# `mark_corridor_tested` instead; this list should never need to grow.
SEED_TESTED_ECONOMY_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        tuple(sorted(pair))  # type: ignore[misc]
        for pair in [
            ("GU", "PG"),
            ("NC", "FJ"),
            ("GU", "PW"),
            ("FJ", "VU"),
            ("PF", "NU"),
            ("FJ", "TV"),
            ("PF", "CK"),
            ("MP", "GU"),
            ("FM", "PW"),
            ("NC", "GU"),  # Superloop case: real signal, not RIS-confirmed
            ("NC", "VU"),
            ("PG", "VU"),
            ("FM", "KI"),  # Starlink transit chain, real color, inconclusive
            ("VU", "FM"),  # AS9249->AS38875 reverse test, inconclusive
        ]
    }
)


def _probe_live_cc_by_asn(
    probe_registry: dict[int, list[int]], listing_path: Path = DEFAULT_LISTING_PATH
) -> dict[int, set[str]]:
    """For each ASN with a connected probe, which economies its probes are *actually* live in.

    Per the project owner: trust each probe's own Atlas-reported
    country_code over this project's ASN-level registry classification --
    a probe's own live location is ground truth (confirmed independently
    from two probes' own `description` fields: 60575 reads "Pacific
    Community, Suva, Fiji", 11691 reads "USP Tonga Campus", both matching
    their live country_code exactly), whereas the ASN registry answers a
    different question (who legally operates the network, per WHOIS/
    APNIC), not where a specific measurement physically originates.

    A single ASN can map to more than one live economy when its
    connected probes sit in different countries -- e.g. AS7131 (Docomo
    Pacific): two probes live in Guam, one in the Northern Mariana
    Islands. Each becomes its own independent, correctly-labeled source.
    """
    listing = load_probe_listing(listing_path)
    live_cc_by_probe = {
        p["id"]: cc for cc, probes in listing.items() for p in probes if p["status"] == "Connected"
    }
    result: dict[int, set[str]] = {}
    for asn, probe_ids in probe_registry.items():
        ccs = {live_cc_by_probe[pid] for pid in probe_ids if pid in live_cc_by_probe}
        if ccs:
            result[asn] = ccs
    return result


@dataclass(frozen=True)
class CorridorCandidate:
    """One untested (source ASN, target ASN) pair worth firing a traceroute at."""

    source_asn: int
    source_cc: str
    source_name: str
    target_asn: int
    target_cc: str
    target_name: str
    rationale: str
    is_new_probe: bool = False
    is_new_ris_relationship: bool = False


def _load_tested_pairs(path: Path = DEFAULT_TESTED_PAIRS_PATH) -> set[tuple[int, int]]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text())
    return {tuple(pair) for pair in data.get("pairs", [])}  # type: ignore[misc]


def _save_tested_pairs(pairs: set[tuple[int, int]], path: Path = DEFAULT_TESTED_PAIRS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pairs": sorted(list(p) for p in pairs)}, indent=2) + "\n")


def mark_corridor_tested(
    source_asn: int, target_asn: int, path: Path = DEFAULT_TESTED_PAIRS_PATH
) -> None:
    """Record that this ASN pair has been deliberately traceroute-tested, any outcome.

    Call this from every tranche that fires a measurement, regardless of
    whether it ends up confirmed, candidate, or just real-signal-but-
    inconclusive -- this is the record that keeps the backlog from
    proposing the same pair twice, which the finding dataclasses alone
    can't do (they only record successes, and `ConfirmedDetour` doesn't
    even store a source ASN).
    """
    pairs = _load_tested_pairs(path)
    pairs.add((source_asn, target_asn))
    _save_tested_pairs(pairs, path)


def _tested_pairs_from_findings() -> set[tuple[int, int]]:
    """Exact ASN pairs recoverable from the two dataclasses that store both ends."""
    pairs: set[tuple[int, int]] = set()
    for entry in CONFIRMED_LOCAL_TRANSIT:
        pairs.add((entry.provider_asn, entry.customer_asn))
    for entry in CANDIDATE_PEERING:
        pairs.add((entry.upstream_asn, entry.target_asn))
    return pairs


def _tested_economy_pairs_from_findings() -> set[tuple[str, str]]:
    """Economy-level pairs, including from `ConfirmedDetour`, which only stores `source_cc`."""
    pairs: set[tuple[str, str]] = set(SEED_TESTED_ECONOMY_PAIRS)
    for entry in CONFIRMED_DETOURS:
        pairs.add(tuple(sorted((entry.source_cc, entry.target_cc))))  # type: ignore[misc]
    for entry in CONFIRMED_LOCAL_TRANSIT:
        pairs.add(tuple(sorted((entry.provider_cc, entry.customer_cc))))  # type: ignore[misc]
    for entry in CANDIDATE_PEERING:
        pairs.add(tuple(sorted((entry.upstream_cc, entry.target_cc))))  # type: ignore[misc]
    return pairs


def _load_snapshot(path: Path = DEFAULT_SNAPSHOT_PATH) -> dict:
    if not path.exists():
        return {"probe_asns": [], "fishbowl_neighbors": {}}
    return json.loads(path.read_text())


def _save_snapshot(
    probe_registry: dict[int, list[int]], fishbowl: dict, path: Path = DEFAULT_SNAPSHOT_PATH
) -> None:
    neighbors = {asn: sorted(e.get("neighbors", {}).keys()) for asn, e in fishbowl.items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "probe_asns": sorted(int(a) for a in probe_registry),
                "fishbowl_neighbors": neighbors,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
        + "\n"
    )


def detect_new_probes(previous: dict, current_registry: dict[int, list[int]]) -> set[int]:
    """ASNs that gained their first connected probe since the last snapshot."""
    prev_asns = set(previous.get("probe_asns", []))
    curr_asns = {int(a) for a in current_registry}
    return curr_asns - prev_asns


def detect_new_ris_neighbors(previous: dict, current_fishbowl: dict) -> set[tuple[int, int]]:
    """`(asn, neighbor_asn)` pairs that appeared in RIS data since the last snapshot."""
    new_pairs: set[tuple[int, int]] = set()
    prev_neighbors = previous.get("fishbowl_neighbors", {})
    for asn_str, entry in current_fishbowl.items():
        prev_set = {int(n) for n in prev_neighbors.get(asn_str, [])}
        curr_set = {int(n) for n in entry.get("neighbors", {})}
        for neighbor in curr_set - prev_set:
            new_pairs.add((int(asn_str), neighbor))
    return new_pairs


def enumerate_candidate_corridors(
    probe_registry_path: Path = DEFAULT_REGISTRY_PATH,
    fishbowl_path: Path = DEFAULT_SUMMARY_PATH,
    tested_pairs_path: Path = DEFAULT_TESTED_PAIRS_PATH,
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
    probe_listing_path: Path = DEFAULT_LISTING_PATH,
) -> list[CorridorCandidate]:
    """Build the ranked list of untested (source ASN, source economy, target ASN) pairs.

    Scope, deliberately: sources are every (ASN, live economy) pair with a
    connected Atlas probe -- per the project owner, each probe's own live
    `country_code` is ground truth for where a measurement actually fires
    from, trusted over this project's ASN-level registry classification
    (`_probe_live_cc_by_asn`; confirmed against two probes' own Atlas
    `description` fields, which independently corroborate their live
    location). A single ASN can therefore appear as a source for more than
    one economy if its different connected probes physically sit in
    different countries (e.g. AS7131/Docomo Pacific: Guam and the
    Northern Mariana Islands), and an ASN whose registry economy doesn't
    match any of its own probes' live locations (e.g. AS24390/University
    of the South Pacific, tracked as Fiji but its only probe live in
    Tonga) is simply a source for whichever economy its probe is actually
    in, not excluded. Targets are every in-scope ASN with cached RIS
    prefix data (anything in `fishbowl.json`, which mirrors the same RIS
    fetch `pick_target_ip` relies on) -- unlike sources, target economy is
    correctly the registry classification (who operates the network),
    since there's no specific probe location question on that side.
    Cross-economy pairs are always proposed -- domestic pairs only for
    economies in `DOMESTIC_TEST_ECONOMIES` (see that constant's docstring
    for why domestic testing is opt-in, not blanket).

    Excludes: external/proxy ASNs (`EXTERNAL_NON_CANDIDATE_ASNS`), any
    exact ASN pair already tested (`tested_pairs.json` + the two
    dataclasses that store both ends), and for cross-economy pairs only,
    any economy pair already covered by *any* finding or seeded prior
    result -- matching how this project has actually reasoned about "next
    unknown corridor" (move to a new economy pair once one is
    well-established, rather than exhaustively testing every ASN
    combination within it). That "one result closes out the whole economy
    pair" logic deliberately does *not* apply to opted-in domestic pairs --
    the goal there is exactly the opposite, checking many ASN pairs within
    one economy, since each domestic pair is its own independent
    local-peering-or-detour question.
    """
    probe_registry = load_asn_probe_registry(probe_registry_path)
    fishbowl = json.loads(fishbowl_path.read_text())
    tested_pairs = _load_tested_pairs(tested_pairs_path) | _tested_pairs_from_findings()
    tested_economy_pairs = _tested_economy_pairs_from_findings()
    snapshot = _load_snapshot(snapshot_path)
    new_probe_asns = detect_new_probes(snapshot, probe_registry)
    new_ris_pairs = detect_new_ris_neighbors(snapshot, fishbowl)

    asn_cc: dict[int, str] = {}
    for asn_str, entry in fishbowl.items():
        asn = int(asn_str)
        asn_cc[asn] = entry.get("economy", {}).get("cc", "??")

    probe_live_cc = _probe_live_cc_by_asn(probe_registry, probe_listing_path)
    source_pairs = sorted(
        (asn, cc)
        for asn, ccs in probe_live_cc.items()
        if asn not in EXTERNAL_NON_CANDIDATE_ASNS
        for cc in ccs
    )
    target_asns = sorted(
        a
        for a, entry in ((int(k), v) for k, v in fishbowl.items())
        if a not in EXTERNAL_NON_CANDIDATE_ASNS and entry.get("num_distinct_prefixes", 0) > 0
    )
    target_name: dict[int, str] = {
        int(k): v.get("economy", {}).get("name", "??") for k, v in fishbowl.items()
    }

    candidates: list[CorridorCandidate] = []
    for source_asn, source_cc in source_pairs:
        source_name = ECONOMIES_BY_CC[source_cc].name if source_cc in ECONOMIES_BY_CC else "??"
        for target_asn in target_asns:
            if source_asn == target_asn:
                continue
            target_cc = asn_cc.get(target_asn)
            if target_cc is None:
                continue
            is_domestic = target_cc == source_cc
            if is_domestic and source_cc not in DOMESTIC_TEST_ECONOMIES:
                continue
            pair = (source_asn, target_asn)
            reverse_pair = (target_asn, source_asn)
            if pair in tested_pairs or reverse_pair in tested_pairs:
                continue
            if not is_domestic:
                economy_pair = tuple(sorted((source_cc, target_cc)))
                if economy_pair in tested_economy_pairs:
                    continue
            is_new_probe = source_asn in new_probe_asns
            is_new_ris = pair in new_ris_pairs or reverse_pair in new_ris_pairs
            if is_domestic:
                rationale = (
                    "untested domestic pair in an economy opted into local-peering "
                    "checks (DOMESTIC_TEST_ECONOMIES) -- could reveal a same-economy "
                    "detour through an external hub"
                )
            elif is_new_probe:
                rationale = "source ASN just gained a connected probe since last regeneration"
            elif is_new_ris:
                rationale = "RIS just started observing this exact adjacency since last regeneration"
            else:
                rationale = "untested cross-economy pair, source has a connected probe"
            candidates.append(
                CorridorCandidate(
                    source_asn=source_asn,
                    source_cc=source_cc,
                    source_name=source_name,
                    target_asn=target_asn,
                    target_cc=target_cc,
                    target_name=target_name.get(target_asn, "?"),
                    rationale=rationale,
                    is_new_probe=is_new_probe,
                    is_new_ris_relationship=is_new_ris,
                )
            )

    candidates.sort(
        key=lambda c: (
            not c.is_new_probe,
            not c.is_new_ris_relationship,
            c.source_asn,
            c.target_asn,
        )
    )
    return candidates


_MAX_DISPLAYED = 100


def _render_backlog_markdown(
    candidates: list[CorridorCandidate], new_probe_count: int, new_ris_count: int
) -> str:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Corridor Backlog",
        "",
        "Auto-generated by `pacific-peering-corridor-backlog` "
        "(`analysis.corridor_backlog.build_corridor_backlog`). Regenerated roughly every "
        "8 hours by a standing `/loop` job; each hourly tranche pulls the next item here "
        "instead of re-deriving the candidate space from scratch. Not hand-edited -- "
        "see `task_plan.md` for the narrative record of what each tested corridor found.",
        "",
        f"Last regenerated: {now}",
        f"Candidates: {len(candidates)} | New probes since last run: {new_probe_count} | "
        f"New RIS relationships since last run: {new_ris_count}",
        "",
        "## Pending",
        "",
    ]
    if not candidates:
        lines.append(
            "*(none -- every untested cross-economy ASN pair this project can "
            "currently reach has been tried; wait for new probes/RIS data, or "
            "revisit the same-economy / external-ASN scope this list deliberately excludes.)*"
        )
    displayed = candidates[:_MAX_DISPLAYED]
    for c in displayed:
        flags = []
        if c.is_new_probe:
            flags.append("NEW PROBE")
        if c.is_new_ris_relationship:
            flags.append("NEW RIS RELATIONSHIP")
        flag_str = f" **[{', '.join(flags)}]**" if flags else ""
        lines.append(
            f"- [ ] AS{c.source_asn} ({c.source_name}, {c.source_cc}) -> "
            f"AS{c.target_asn} ({c.target_name}, {c.target_cc}) -- {c.rationale}{flag_str}"
        )
    if len(candidates) > _MAX_DISPLAYED:
        lines.append("")
        lines.append(
            f"*(showing the top {_MAX_DISPLAYED} of {len(candidates)} by priority -- "
            "new-probe and new-RIS-relationship candidates always sort first; the rest "
            "are exact untested cross-economy ASN pairs, complete but not all listed "
            "here for readability. Full set is always recomputable live via "
            "`pick_next_corridor`/`enumerate_candidate_corridors`, not just from this file.)*"
        )
    lines.append("")
    return "\n".join(lines)


def build_corridor_backlog(
    probe_registry_path: Path = DEFAULT_REGISTRY_PATH,
    fishbowl_path: Path = DEFAULT_SUMMARY_PATH,
    tested_pairs_path: Path = DEFAULT_TESTED_PAIRS_PATH,
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
    output_path: Path = DEFAULT_BACKLOG_MD_PATH,
) -> list[CorridorCandidate]:
    """Regenerate `corridor_backlog.md` and the change-detection snapshot.

    The standing "every ~8 hours" refresh: re-derives the full candidate
    list, flags anything new (a probe that just came online, a RIS
    relationship that just appeared) as high priority, writes the
    human-readable backlog, and saves the current state as the new
    snapshot baseline for next time.
    """
    probe_registry = load_asn_probe_registry(probe_registry_path)
    fishbowl = json.loads(fishbowl_path.read_text())
    snapshot = _load_snapshot(snapshot_path)
    new_probe_asns = detect_new_probes(snapshot, probe_registry)
    new_ris_pairs = detect_new_ris_neighbors(snapshot, fishbowl)

    candidates = enumerate_candidate_corridors(
        probe_registry_path, fishbowl_path, tested_pairs_path, snapshot_path
    )
    output_path.write_text(
        _render_backlog_markdown(candidates, len(new_probe_asns), len(new_ris_pairs))
    )
    _save_snapshot(probe_registry, fishbowl, snapshot_path)
    logger.info(
        "Corridor backlog regenerated: %d candidates (%d new-probe, %d new-RIS-relationship)",
        len(candidates),
        sum(1 for c in candidates if c.is_new_probe),
        sum(1 for c in candidates if c.is_new_ris_relationship),
    )
    return candidates


def pick_next_corridor(
    probe_registry_path: Path = DEFAULT_REGISTRY_PATH,
    fishbowl_path: Path = DEFAULT_SUMMARY_PATH,
    tested_pairs_path: Path = DEFAULT_TESTED_PAIRS_PATH,
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
) -> CorridorCandidate | None:
    """Return the single highest-priority untested corridor, or `None` if the backlog is empty.

    Doesn't require `corridor_backlog.md` to exist or be current -- always
    recomputes live from the underlying registries, so a `/loop` tranche
    can call this directly without depending on the 8-hourly regeneration
    having just run.
    """
    candidates = enumerate_candidate_corridors(
        probe_registry_path, fishbowl_path, tested_pairs_path, snapshot_path
    )
    return candidates[0] if candidates else None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    candidates = build_corridor_backlog()
    for c in candidates[:10]:
        logger.info(
            "AS%d (%s, %s) -> AS%d (%s, %s) -- %s",
            c.source_asn, c.source_name, c.source_cc,
            c.target_asn, c.target_name, c.target_cc,
            c.rationale,
        )


if __name__ == "__main__":
    main()
