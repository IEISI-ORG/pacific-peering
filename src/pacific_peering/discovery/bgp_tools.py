"""bgp.tools: a secondary, corroboration-only data source.

Per the project owner, explicitly framed as *secondary* — same "lead,
not ground truth" status this project already gives PeeringDB, never
used alone to confirm a finding (see task_plan.md's Validation Rules).
Two things bgp.tools offers that the project's primary sources don't:

1. **ASN name + class + country** (`/asns.csv`): a `class` field
   (e.g. "Eyeball", "Transit", "Unknown") this project's other sources
   lack — useful for a quick independent sanity check on whether an
   ASN looks like a real local access network versus a hosting/transit
   shell (exactly the question that came up when a cross-RIR ASN audit
   surfaced several Marshall-Islands-registered ASNs that turned out to
   be generic hosting companies, not real Pacific ISPs).
2. **A live BGP table dump with visibility counts** (`/table.jsonl`):
   an independent-vantage-point cross-check on prefix origination,
   separate from RIPEstat/RIS.
3. **Community tags** (`/tags.txt` for the tag list, `/tags/<tag>.csv`
   per tag): crowdsourced network-type labels (`uni`, `gov`, `mobile`,
   `satnet`, `vpsh`/`vpn` for hosting/VPN providers, etc.) — another
   independent signal for the same "is this a real local network"
   question, orthogonal to the `class` field. Already caught one real
   corroboration: AS14593 (SpaceX Starlink, seen as a transit hop in
   this project's FM->Kiribati traceroute) carries the `satnet` tag.

**Required by bgp.tools's own terms**: a real, identifying User-Agent
on every request — a generic one risks being blocked outright (their
own docs say so explicitly). Per the project owner, this project's
contact is its own GitHub repo, not a personal email.

**Caching, per bgp.tools's own posted guidance**: `/table.jsonl` is a
large (~70MB+) full global routing table that updates every ~30 minutes
at the earliest and they ask callers not to fetch it more than that
often, suggesting ~2 hours of caching in practice; `/asns.csv` (~5MB)
changes far less often — they suggest a 24-hour cache. Both are cached
to local files under `data/bgp_tools/` and only re-fetched once stale.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

USER_AGENT = "pacific-peering bgp.tools - github.com/IEISI-ORG/pacific-peering"
_DEFAULT_TIMEOUT = 60.0

DEFAULT_ASN_NAMES_CACHE = Path("data/bgp_tools/asns.csv")
DEFAULT_TABLE_CACHE = Path("data/bgp_tools/table.jsonl")
DEFAULT_TAG_CACHE_DIR = Path("data/bgp_tools/tags")
_ASN_NAMES_MAX_AGE_SECONDS = 24 * 60 * 60  # bgp.tools' own suggested cache window
_TABLE_MAX_AGE_SECONDS = 2 * 60 * 60  # bgp.tools' own suggested cache window
_TAG_MAX_AGE_SECONDS = 24 * 60 * 60  # tag membership changes slowly, same window as asns.csv


@dataclass(frozen=True)
class BgpToolsAsnInfo:
    """One ASN's bgp.tools-reported name, class, and country."""

    asn: int
    name: str
    network_class: str
    cc: str


def _is_stale(path: Path, max_age_seconds: float) -> bool:
    return not path.exists() or (time.time() - path.stat().st_mtime) > max_age_seconds


def _download(url: str, dest: Path, timeout: float = _DEFAULT_TIMEOUT) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, stream=True)
    response.raise_for_status()
    with dest.open("wb") as f:
        for chunk in response.iter_content(chunk_size=1 << 20):
            f.write(chunk)


def fetch_asn_names(
    asns: list[int] | None = None,
    cache_path: Path = DEFAULT_ASN_NAMES_CACHE,
    refresh: bool = False,
) -> dict[int, BgpToolsAsnInfo]:
    """Fetch bgp.tools' ASN name/class/country export, cached locally.

    Args:
        asns: If given, only return these ASNs (still downloads/reads
            the full file — filtering is just for the returned dict).
            None returns everything (~122k entries as of this writing).
        cache_path: Local cache file.
        refresh: Force a re-download even if the cache isn't stale yet.

    Returns:
        Mapping of ASN to its `BgpToolsAsnInfo`. An ASN bgp.tools has
        never seen is simply absent, not an error.
    """
    if refresh or _is_stale(cache_path, _ASN_NAMES_MAX_AGE_SECONDS):
        logger.info("Fetching fresh bgp.tools ASN name export to %s", cache_path)
        _download("https://bgp.tools/asns.csv", cache_path)

    wanted = set(asns) if asns is not None else None
    result: dict[int, BgpToolsAsnInfo] = {}
    with cache_path.open(encoding="utf-8") as f:
        next(f)  # header: asn,name,class,cc
        for line in f:
            parts = line.rstrip("\n").split(",")
            if len(parts) < 4:
                continue
            asn_field, name, network_class, cc = parts[0], parts[1], parts[2], parts[3]
            if not asn_field.startswith("AS"):
                continue
            asn = int(asn_field[2:])
            if wanted is not None and asn not in wanted:
                continue
            result[asn] = BgpToolsAsnInfo(
                asn=asn, name=name.strip('"'), network_class=network_class, cc=cc
            )
    return result


def fetch_prefix_visibility(
    asns: list[int],
    cache_path: Path = DEFAULT_TABLE_CACHE,
    refresh: bool = False,
) -> dict[int, list[dict]]:
    """Look up bgp.tools' visibility ("Hits") counts for specific ASNs' prefixes.

    Streams the cached table file line by line rather than loading the
    full ~1.5M-row global table into memory — this project only ever
    needs a handful of in-scope ASNs at a time.

    Args:
        asns: ASNs to filter for.
        cache_path: Local cache file for the full table dump.
        refresh: Force a re-download even if the cache isn't stale yet.

    Returns:
        Mapping of ASN to a list of `{"prefix": str, "hits": int}` —
        "hits" is bgp.tools' own visibility count for that origination,
        useful for filtering out low-visibility/noise announcements.
    """
    if refresh or _is_stale(cache_path, _TABLE_MAX_AGE_SECONDS):
        logger.info("Fetching fresh bgp.tools global table dump to %s (~70MB)", cache_path)
        _download("https://bgp.tools/table.jsonl", cache_path)

    wanted = set(asns)
    result: dict[int, list[dict]] = {asn: [] for asn in wanted}
    with cache_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            asn = record.get("ASN")
            if asn in wanted:
                result[asn].append({"prefix": record["CIDR"], "hits": record["Hits"]})
    return result


def is_prefix_routed_by_asn(
    asn: int, address: str, cache_path: Path = DEFAULT_TABLE_CACHE, refresh: bool = False
) -> bool | None:
    """Check whether `asn`'s bgp.tools-routed prefix set actually covers `address`.

    The concrete cross-check for a suspected-but-BGP-invisible attribution
    (e.g. a WHOIS `netname` pointing at a carrier, for a hop RIS shows zero
    visibility for): does that carrier route *any* prefix covering this
    exact address? A `False` here is itself informative — it means the
    suspected operator's allocation includes this space but deliberately
    doesn't announce it (the concrete Superloop case: AS38195 routes
    `103.200.14.0/24` and `103.200.15.0/24` but not the `.12`/`.13` /24s
    a hop address fell inside).

    Returns:
        `True`/`False` if `asn` appears in bgp.tools' table at all;
        `None` if `asn` originates nothing there (can't determine either
        way, not the same as "not routed").
    """
    visibility = fetch_prefix_visibility([asn], cache_path=cache_path, refresh=refresh)
    prefixes = visibility.get(asn, [])
    if not prefixes:
        return None
    target = ipaddress.ip_address(address)
    return any(target in ipaddress.ip_network(p["prefix"], strict=False) for p in prefixes)


def fetch_tag_list(refresh: bool = False) -> dict[str, int]:
    """Fetch bgp.tools' list of all community tags and how many ASNs carry each.

    Returns:
        Mapping of tag name (e.g. "uni", "satnet", "vpsh") to member count.
    """
    cache_path = DEFAULT_TAG_CACHE_DIR / "_tags.txt"
    if refresh or _is_stale(cache_path, _TAG_MAX_AGE_SECONDS):
        _download("https://bgp.tools/tags.txt", cache_path)
    tags: dict[str, int] = {}
    for line in cache_path.read_text().splitlines():
        name, _, count = line.partition(",")
        if name:
            tags[name] = int(count) if count.isdigit() else 0
    return tags


def fetch_tag_members(
    tag: str, cache_dir: Path = DEFAULT_TAG_CACHE_DIR, refresh: bool = False
) -> dict[int, str]:
    """Fetch every ASN bgp.tools' community has labeled with `tag`.

    Args:
        tag: A tag name from `fetch_tag_list` (e.g. "uni", "satnet",
            "vpsh" for VPS hosting providers, "vpn").
        cache_dir: Directory to cache each tag's CSV under.
        refresh: Force a re-download even if the cache isn't stale yet.

    Returns:
        Mapping of ASN to its bgp.tools-reported name, for every ASN
        carrying this tag. An unknown tag returns an empty dict rather
        than raising (bgp.tools serves an empty/404 body for one).
    """
    cache_path = cache_dir / f"{tag}.csv"
    if refresh or _is_stale(cache_path, _TAG_MAX_AGE_SECONDS):
        try:
            _download(f"https://bgp.tools/tags/{tag}.csv", cache_path)
        except requests.exceptions.HTTPError as exc:
            logger.warning("Could not fetch bgp.tools tag %r: %s", tag, exc)
            return {}

    members: dict[int, str] = {}
    for line in cache_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        asn_field, _, name = line.partition(",")
        if asn_field.startswith("AS"):
            members[int(asn_field[2:])] = name.strip('"')
    return members
