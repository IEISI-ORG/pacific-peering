"""Report-only: off-region routers that many Pacific corridors converge on.

Per the project owner (2026-11-06): find single routers on transit providers
that carry 3 or more of the region's corridors, where one outage would cut
paths between economies that share no carrier. Changes nothing in the
findings store; writes `outputs/reports/convergence.txt`. Weekly, from the
discovery refresh. No Atlas credits: it reads the cached parsed traces.

Each off-region hop of every cached trace is recorded against the trace's
economy pair (probe economy -> target economy). A hop counts when its address
is global, resolves to an ASN, and that ASN is not in scope (fishbowl.json).
Interfaces are grouped into routers by PTR name with the interface label
removed (`be2378.ccr51.pdx02...` and `be2467.ccr51.pdx02...` are one router).
A router with no PTR, or a PTR built from its own address, stays its address.

Categories (thresholds per the owner, 2026-11-06):
- shared transit: >= 3 source economies and >= 3 target economies. The
  finding this report exists for.
- target access: >= 3 sources, < 3 targets. Usually just a target's
  single-homed upstream, which RIS already shows at AS level.
- source-side: < 3 sources, >= 3 targets. A probe's own first upstream;
  reflects probe placement, so only counted.

Limits, stated in the report too: counts measure path diversity among tested
corridors, not traffic; MPLS cores hide routers (AARNet's LA -> Sydney leg),
so convergence there is undercounted; PTR grouping misses routers with no
or address-style names; the probe economy is the listing's label.

ASN resolution: the project's IP-resolution cache, then `PREFIX_ASN_OVERRIDES`,
then a longest-prefix match on the cached bgp.tools table (secondary source;
fine for labelling transit routers in a report, never used to file a finding).
"""

from __future__ import annotations

import ipaddress
import json
import logging
import re
from collections import defaultdict
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pacific_peering.analysis.feasibility import DEFAULT_ATLAS_PARSED_DIR
from pacific_peering.analysis.fishbowl import DEFAULT_SUMMARY_PATH
from pacific_peering.analysis.ip_resolution_cache import IpResolutionCache
from pacific_peering.analysis.router_location import PtrResolver, reverse_dns
from pacific_peering.analysis.ris_upstreams import (  # noqa: F401 -- re-exported for callers and tests
    DEPENDENCY,
    PREFERRED_PATH,
    SINGLE_UPSTREAM,
    UNKNOWN,
    ris_verdict,
    upstream_chain,
)
from pacific_peering.discovery import bgp_tools
from pacific_peering.discovery.prefix_asn_overrides import find_prefix_override
from pacific_peering.reports.data import LEGAL_NOTICE

logger = logging.getLogger(__name__)

REPORT_PATH = Path("outputs/reports/convergence.txt")
DEFAULT_ATLAS_RAW_DIR = Path("data/atlas/raw")
DEFAULT_PROBE_LISTING = Path("data/atlas/probe_listing.json")
PTR_CACHE_PATH = Path("data/analysis/ptr_cache.json")  # gitignored with the rest of data/
PTR_CACHE_MAX_AGE_DAYS = 30

MIN_SOURCE_ECONOMIES = 3
MIN_TARGET_ECONOMIES = 3

SHARED_TRANSIT = "shared_transit"
TARGET_ACCESS = "target_access"
SOURCE_SIDE = "source_side"

AsnLookup = Callable[[str], "int | None"]

# A leading label that names an interface, not a router: be2378, ae-15, xe-0-0-0,
# et-1-0-2, port-channel4, 100ge0-0-0-4, ve101, i-90, fastethernet0-0, ...
_INTERFACE_LABEL = re.compile(
    r"^(?:if-|ix-)?(?:\d+ge|ae|be|bu|bundle-ether|bundle|xe|et|ge|gi|gigabitethernet|te|tengige|tengigabitethernet|"
    r"hu|hundredgige|fastethernet|fa|eth|ethernet|port-channel|po|ve|vl|vlan|irb|lo|i)[-\d./_:]*\d$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Router:
    """One off-region router and the corridors whose traces crossed it."""

    key: str
    asn: int
    addresses: frozenset[str]
    pairs: frozenset[tuple[str, str]]  # (source economy, target economy)
    probes: frozenset[int]
    first_seen: str | None  # ISO date of the earliest trace, None if no timestamp was known
    last_seen: str | None

    @property
    def sources(self) -> set[str]:
        return {s for s, _ in self.pairs}

    @property
    def targets(self) -> set[str]:
        return {t for _, t in self.pairs}


def device_key(address: str, hostname: str | None) -> str:
    """Name the router behind `address`: its PTR minus any interface label, else the address."""
    if not hostname:
        return address
    name = hostname.rstrip(".").lower()
    octets = re.split(r"[.:]", address)
    if len(octets) >= 4 and any(sep.join(octets[:4]) in name for sep in ("-", ".")):
        return address  # e.g. 103-43-212-161.static.rise.net.ph
    first, _, rest = name.partition(".")
    if rest.count(".") >= 1 and _INTERFACE_LABEL.match(first):
        return rest
    return name


def prefix_origins(table_lines: Iterable[str], addresses: Iterable[str]) -> dict[str, int]:
    """Longest-prefix origin ASN for each address, from bgp.tools `table.jsonl` lines.

    One pass over the table: every wanted address is indexed under each of its
    covering prefixes, so each table row is a dict lookup.
    """
    index: dict[tuple[int, int, int], list[str]] = defaultdict(list)
    for a in addresses:
        try:
            ip = ipaddress.ip_address(a)
        except ValueError:
            continue
        bits = ip.max_prefixlen
        n = int(ip)
        for plen in range(0, bits + 1):
            index[(ip.version, plen, n >> (bits - plen) << (bits - plen))].append(a)
    best: dict[str, tuple[int, int]] = {}
    for line in table_lines:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        net = ipaddress.ip_network(row["CIDR"], strict=False)
        for a in index.get((net.version, net.prefixlen, int(net.network_address)), ()):
            if a not in best or net.prefixlen > best[a][0]:
                best[a] = (net.prefixlen, row["ASN"])
    return {a: asn for a, (_, asn) in best.items()}


def _is_global(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False


def _name_filter(traces: list[tuple[dict, str | None]], ptr: PtrResolver) -> PtrResolver:
    """`ptr`, but returning None for placeholder PTRs.

    A raw PTR that more than one address carries is a placeholder
    (`unknown.telstraglobal.net`, `ip4.gtt.net`), not a router name: real
    interfaces get their own names. Those addresses stay separate.
    """
    holders: dict[str, set[str]] = defaultdict(set)
    for trace, _ in traces:
        for hop in trace.get("hops", []):
            for address in hop.get("addresses", []):
                if _is_global(address) and (name := ptr(address)):
                    holders[name.rstrip(".").lower()].add(address)
    placeholders = {name for name, addrs in holders.items() if len(addrs) > 1}

    def name_of(address: str) -> str | None:
        name = ptr(address)
        return None if name and name.rstrip(".").lower() in placeholders else name

    return name_of


def _routers_on(trace: dict, asn_of: AsnLookup, in_scope: dict[int, str], name_of: PtrResolver):
    """Yield (asn, router key, address) for each off-region hop of one trace."""
    for hop in trace.get("hops", []):
        for address in hop.get("addresses", []):
            if not _is_global(address):
                continue
            asn = asn_of(address)
            if asn is None or asn in in_scope:
                continue
            yield asn, device_key(address, name_of(address)), address


def collect(
    traces: Iterable[tuple[dict, str | None]],
    probe_cc: dict[int, str],
    asn_of: AsnLookup,
    in_scope: dict[int, str],
    ptr: PtrResolver,
) -> list[Router]:
    """Group the off-region hops of `(trace, iso_date)` pairs into routers."""
    traces = list(traces)
    name_of = _name_filter(traces, ptr)
    acc: dict[tuple[int, str], dict] = {}
    for trace, day in traces:
        source = probe_cc.get(trace["probe_id"])
        target = in_scope.get(asn_of(trace["target"]))
        if not source or not target:
            continue
        for asn, key, address in _routers_on(trace, asn_of, in_scope, name_of):
            r = acc.setdefault((asn, key), {"addresses": set(), "pairs": set(), "probes": set(), "days": set()})
            r["addresses"].add(address)
            r["pairs"].add((source, target))
            r["probes"].add(trace["probe_id"])
            if day:
                r["days"].add(day)
    return [
        Router(key=key, asn=asn, addresses=frozenset(r["addresses"]), pairs=frozenset(r["pairs"]),
               probes=frozenset(r["probes"]), first_seen=min(r["days"], default=None),
               last_seen=max(r["days"], default=None))
        for (asn, key), r in acc.items()
    ]


# --- Always-crossed routers and the RIS upstream check (owner, 2026-11-06) ------
#
# A router every trace of an economy pair crossed is a dependency only if BGP
# has no way around it. RIS `neighbors` (fishbowl.json) say which networks
# routes to the source or target are learned through -- the inbound
# direction -- while a trace shows the outbound path, so a single upstream
# that isn't the router's own network is information, not a contradiction
# (NU AS55885 -> AS55943 -> GTT only in RIS, yet NU traces cross HE hnl1).

MIN_PAIR_TRACES = 3
MIN_ALWAYS_PAIRS = 3  # routers listed in the always-crossed section


@dataclass(frozen=True)
class AlwaysCrossed:
    """One router that every trace of one economy pair crossed, with the RIS reading."""

    key: str
    asn: int
    pair: tuple[str, str]
    traces: int
    probes: int
    verdict: str
    detail: str


def always_crossed(
    traces: Iterable[tuple[dict, str | None]],
    probes: dict[int, tuple[str, int | None]],
    asn_of: AsnLookup,
    in_scope: dict[int, str],
    ptr: PtrResolver,
    fishbowl: dict,
) -> list[AlwaysCrossed]:
    """Routers on every trace of an economy pair with >= MIN_PAIR_TRACES traces.

    `probes` maps probe id -> (economy, ASN). Domestic pairs count too: an
    off-region router on every trace between two networks in one economy
    is the same-country detour this project looks for.
    """
    traces = list(traces)
    name_of = _name_filter(traces, ptr)
    per_pair: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"n": 0, "probes": set(), "src": set(), "tgt": set(), "routers": defaultdict(int)})
    for trace, _ in traces:
        source, source_asn = probes.get(trace["probe_id"], (None, None))
        target_asn = asn_of(trace["target"])
        target = in_scope.get(target_asn)
        if not source or not target:
            continue
        p = per_pair[(source, target)]
        p["n"] += 1
        p["probes"].add(trace["probe_id"])
        if source_asn:
            p["src"].add(source_asn)
        p["tgt"].add(target_asn)
        for asn, key in {(a, k) for a, k, _ in _routers_on(trace, asn_of, in_scope, name_of)}:
            p["routers"][(asn, key)] += 1
    out = []
    for pair, p in sorted(per_pair.items()):
        if p["n"] < MIN_PAIR_TRACES:
            continue
        for (asn, key), seen in sorted(p["routers"].items(), key=lambda kv: kv[0][1]):
            if seen == p["n"]:
                verdict, detail = ris_verdict(asn, p["src"], p["tgt"], fishbowl)
                out.append(AlwaysCrossed(key=key, asn=asn, pair=pair, traces=p["n"], probes=len(p["probes"]),
                                         verdict=verdict, detail=detail))
    return out


def _always_section(rows: Iterable[AlwaysCrossed], asn_names: dict[int, str]) -> list[str]:
    by_router: dict[tuple[int, str], list[AlwaysCrossed]] = defaultdict(list)
    for r in rows:
        by_router[(r.asn, r.key)].append(r)
    listed = sorted(((k, v) for k, v in by_router.items() if len(v) >= MIN_ALWAYS_PAIRS),
                    key=lambda kv: (-len(kv[1]), kv[0][1]))
    out = [
        f"ALWAYS-CROSSED ROUTERS: {len(listed)}",
        f"(every trace of an economy pair with >= {MIN_PAIR_TRACES} traces crossed the router; routers with",
        f">= {MIN_ALWAYS_PAIRS} such pairs. 'Every trace' means no other path was observed, not that none",
        "exists. RIS check: dependency = a side's only upstream in RIS is the router's network;",
        "single upstream = a side has one upstream in RIS, but a different network; preferred path = both",
        "sides multi-homed in RIS, so BGP has alternatives. RIS shows how routes reach a network",
        "(inbound); a trace shows the outbound path.)",
        "",
    ]
    for (asn, key), rs in listed:
        out.append(f"  {key}  [{_owner(asn, asn_names)}]  {len(rs)} pairs")
        for r in sorted(rs, key=lambda r: r.pair):
            out.append(f"      {r.pair[0]}>{r.pair[1]:3} {r.traces:3d} traces/{r.probes} probe(s)  "
                       f"{r.verdict.replace('_', ' ')}: {r.detail}")
    out.append("")
    return out


def category(router: Router) -> str | None:
    """SHARED_TRANSIT / TARGET_ACCESS / SOURCE_SIDE, or None under both thresholds."""
    many_sources = len(router.sources) >= MIN_SOURCE_ECONOMIES
    many_targets = len(router.targets) >= MIN_TARGET_ECONOMIES
    if many_sources and many_targets:
        return SHARED_TRANSIT
    if many_sources:
        return TARGET_ACCESS
    if many_targets:
        return SOURCE_SIDE
    return None


def _owner(asn: int, names: dict[int, str]) -> str:
    return f"AS{asn} {names.get(asn, '')}".rstrip()


def _line(r: Router, names: dict[int, str]) -> str:
    seen = f"{r.first_seen}..{r.last_seen}" if r.first_seen else "dates unknown"
    owner = _owner(r.asn, names)
    return (
        f"{len(r.pairs):4d} pairs  {r.key}  [{owner}]\n"
        f"      {len(r.sources)} sources: {','.join(sorted(r.sources))}   "
        f"{len(r.targets)} targets: {','.join(sorted(r.targets))}\n"
        f"      {len(r.addresses)} interface(s): {', '.join(sorted(r.addresses))}   "
        f"{len(r.probes)} probe(s)   seen {seen}"
    )


def render(
    routers: list[Router], asn_names: dict[int, str], traces_read: int,
    always: Iterable[AlwaysCrossed] = (),
) -> str:
    by_cat: dict[str | None, list[Router]] = defaultdict(list)
    for r in routers:
        by_cat[category(r)].append(r)
    for rs in by_cat.values():
        rs.sort(key=lambda r: (-len(r.pairs), r.key))
    out = [
        "Transit router convergence (report-only; nothing in findings.db changed)",
        "Routers on networks outside the project's scope (fishbowl.json), wherever they sit: some are",
        "physically in the region (Tata qhar1/qhar2.pv4-piti and HE core1.gum1 are in Guam).",
        # No run timestamp: an unchanged corpus must leave the file byte-identical (weekly cron commit).
        f"Latest trace: {max((r.last_seen for r in routers if r.last_seen), default='unknown')}. "
        f"Traces read: {traces_read}. Thresholds: >= {MIN_SOURCE_ECONOMIES} source economies, "
        f">= {MIN_TARGET_ECONOMIES} target economies.",
        "Counts are economy pairs (probe economy -> target economy) among tested corridors, not traffic.",
        "MPLS cores hide routers, so convergence inside them is undercounted. Interfaces are grouped",
        "into routers by PTR name; routers with no PTR, or an address-style PTR, stay separate addresses.",
        "",
        f"SHARED TRANSIT ROUTERS: {len(by_cat[SHARED_TRANSIT])}",
        "(one router carrying corridors between several unrelated Pacific economies)",
        "",
        *(_line(r, asn_names) for r in by_cat[SHARED_TRANSIT]),
        "",
        f"TARGET ACCESS ROUTERS: {len(by_cat[TARGET_ACCESS])}",
        f"(>= {MIN_SOURCE_ECONOMIES} sources but < {MIN_TARGET_ECONOMIES} target economies: "
        "mostly a target's own upstream)",
        "",
        *(_line(r, asn_names) for r in by_cat[TARGET_ACCESS]),
        "",
        f"Source-side routers (not listed): {len(by_cat[SOURCE_SIDE])}",
        "",
        *_always_section(always, asn_names),
        "LEGAL NOTICE",
        *(f"{heading}. {body}" for heading, body in LEGAL_NOTICE),
    ]
    return "\n".join(out) + "\n"


def resolve_ptrs(
    addresses: Iterable[str], resolver: PtrResolver, cache: dict[str, dict], today: str, workers: int = 16
) -> dict[str, str | None]:
    """PTR names for `addresses`, reusing `cache` entries younger than `PTR_CACHE_MAX_AGE_DAYS`.

    Live lookups time out under load (2s cap), and a miss splits a router
    into separate addresses, so without the cache two runs over the same
    traces disagree (967 vs 1003 routers, 2026-11-06). Misses are retried
    once with fewer workers; a name found earlier is kept if the live lookup
    fails. Only names are cached: a miss is looked up again next run.
    `cache` is updated in place.
    """
    cutoff = (datetime.fromisoformat(today) - timedelta(days=PTR_CACHE_MAX_AGE_DAYS)).date().isoformat()
    addresses = list(addresses)
    names: dict[str, str | None] = {}
    due = [a for a in addresses if not (a in cache and cache[a]["checked"] >= cutoff)]
    for a in addresses:
        if a not in due:
            names[a] = cache[a]["name"]
    for pool_size, batch in ((workers, due), (max(1, workers // 4), None)):
        batch = batch if batch is not None else [a for a in due if not names.get(a)]
        if not batch:
            continue
        with ThreadPoolExecutor(max_workers=pool_size) as pool:
            for a, name in zip(batch, pool.map(resolver, batch)):
                if name:
                    names[a] = name
                    cache[a] = {"name": name, "checked": today}
                elif not names.get(a):
                    names[a] = cache.get(a, {}).get("name")
    return names


def _trace_dates(raw_dir: Path, measurement_id: int) -> dict[int, str]:
    """probe_id -> ISO date of that probe's result, from the raw Atlas file if cached."""
    path = raw_dir / f"{measurement_id}.json"
    if not path.exists():
        return {}
    out = {}
    for r in json.loads(path.read_text()):
        if "timestamp" in r and "prb_id" in r:
            out[r["prb_id"]] = datetime.fromtimestamp(r["timestamp"], timezone.utc).date().isoformat()
    return out


def load_traces(parsed_dir: Path, raw_dir: Path) -> list[tuple[dict, str | None]]:
    out = []
    for path in sorted(parsed_dir.glob("*.json")):
        traces = json.loads(path.read_text())
        dates = _trace_dates(raw_dir, int(path.stem)) if path.stem.isdigit() else {}
        out.extend((t, dates.get(t["probe_id"])) for t in traces)
    return out


def _all_addresses(traces: list[tuple[dict, str | None]]) -> set[str]:
    out = set()
    for t, _ in traces:
        out.add(t["target"])
        for h in t.get("hops", []):
            out.update(a for a in h.get("addresses", []) if _is_global(a))
    return out


def build_asn_lookup(addresses: set[str], cache: IpResolutionCache, table_path: Path) -> AsnLookup:
    """Cache, then prefix overrides, then the bgp.tools table for whatever is left."""
    resolved: dict[str, int] = {}
    for a in addresses:
        hit = cache.get(a)
        if hit and hit[0] is not None:
            resolved[a] = hit[0]
        elif (o := find_prefix_override(a)) is not None:
            resolved[a] = o.asn
    rest = addresses - resolved.keys()
    if rest:
        with table_path.open(encoding="utf-8") as f:
            resolved.update(prefix_origins(f, rest))
    return resolved.get


def main() -> None:
    """`uv run pacific-peering-convergence` -- rebuild outputs/reports/convergence.txt."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    traces = load_traces(DEFAULT_ATLAS_PARSED_DIR, DEFAULT_ATLAS_RAW_DIR)
    fishbowl = json.loads(DEFAULT_SUMMARY_PATH.read_text())
    in_scope = {int(k): v["economy"]["cc"] for k, v in fishbowl.items()}
    listing = json.loads(DEFAULT_PROBE_LISTING.read_text())
    probe_cc = {p["id"]: cc for cc, probes in listing.items() for p in probes}
    probe_info = {p["id"]: (cc, p.get("asn_v4")) for cc, probes in listing.items() for p in probes}

    bgp_tools.ensure_table()
    asn_of = build_asn_lookup(_all_addresses(traces), IpResolutionCache.load(), bgp_tools.DEFAULT_TABLE_CACHE)

    off_region = sorted({a for a in _all_addresses(traces) if (n := asn_of(a)) is not None and n not in in_scope})
    logger.info("%d traces, %d off-region addresses; looking up PTRs", len(traces), len(off_region))
    ptr_cache = json.loads(PTR_CACHE_PATH.read_text()) if PTR_CACHE_PATH.exists() else {}
    names = resolve_ptrs(off_region, reverse_dns, ptr_cache, today=datetime.now(timezone.utc).date().isoformat())
    PTR_CACHE_PATH.write_text(json.dumps(ptr_cache, indent=1, sort_keys=True))

    routers = collect(traces, probe_cc, asn_of, in_scope, names.get)
    always = always_crossed(traces, probe_info, asn_of, in_scope, names.get, fishbowl)
    asn_names = {i.asn: i.name for i in bgp_tools.fetch_asn_names().values()} if routers else {}
    REPORT_PATH.write_text(render(routers, asn_names, traces_read=len(traces), always=always))
    shared = sum(1 for r in routers if category(r) == SHARED_TRANSIT)
    logger.info("Wrote %s (%d routers, %d shared transit)", REPORT_PATH, len(routers), shared)


if __name__ == "__main__":
    main()
