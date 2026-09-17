"""Registry of IXP LAN subnets, tagged in-fishbowl vs. out-of-fishbowl.

Per the project owner: an IXP hit in a traceroute isn't just "confirmed
peering" — whether the exchange sits inside or outside the study region
is the actual signal. An in-region hit (e.g. Fiji-IXP) is a clean marker
of local peering working as intended; an out-of-region hit (e.g. Equinix
Sydney, MegaIX Sydney — Australia is explicitly out of scope) is a
marker of the out-of-region-detour pattern this project exists to
document.

Governance rule, also per the project owner: **newly discovered IXPs are
never auto-classified.** Whether an exchange counts as in- or
out-of-fishbowl is a load-bearing distinction for the whole project's
thesis, not something to let a country-code lookup silently decide.
Every IXP new to this registry (not already in the persisted file on
disk) is written with `in_fishbowl = "TBA"`; rebuilding the registry
never overwrites an already-confirmed classification, only refreshes
that exchange's name/city/prefixes. Use `confirm_ixp_region` once a
classification has actually been discussed and agreed.
"""

from __future__ import annotations

import ipaddress
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from pacific_peering.analysis.fishbowl import DEFAULT_SUMMARY_PATH
from pacific_peering.discovery.economies import ECONOMIES
from pacific_peering.discovery.peeringdb import (
    fetch_ix_info,
    fetch_ixp_by_country,
    fetch_ixp_members,
    fetch_ixp_prefixes,
)
from pacific_peering.discovery.registry import DEFAULT_OUTPUT_PATH as ASN_REGISTRY_PATH

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_PATH = Path("data/analysis/ixp_lan_registry.json")
TBA = "TBA"


@dataclass(frozen=True)
class IxpLanEntry:
    """One IXP's known LAN prefixes, tagged by whether it's in-scope for this project.

    `in_fishbowl` is `True`, `False`, or the literal string `"TBA"`
    (`ixp_lan_registry.TBA`) when not yet confirmed by the project owner.
    """

    ix_id: int
    name: str
    city: str
    country: str
    in_fishbowl: bool | str
    prefixes: tuple[str, ...]


def _collect_known_ixps(fishbowl_path: Path) -> dict[int, dict]:
    """Collect every distinct IXP referenced in the fishbowl dataset's IXP memberships.

    One of two discovery paths merged by `build_ixp_lan_registry` — this
    one only finds an exchange if one of this project's already-tracked
    ASNs happens to be a member of it. See `_collect_ixps_by_country`
    for the second, independent path.
    """
    fishbowl = json.loads(fishbowl_path.read_text())
    ixps: dict[int, dict] = {}
    for entry in fishbowl.values():
        for ix in entry.get("ixp_memberships", []):
            ixps.setdefault(
                ix["ix_id"], {"name": ix["name"], "city": ix["city"], "country": ix["country"]}
            )
    return ixps


def _collect_ixps_by_country() -> dict[int, dict]:
    """Collect every IXP PeeringDB lists directly under one of the 20 in-scope economies.

    The second discovery path: finds an exchange purely from PeeringDB's
    own country tag, independent of whether any tracked ASN is a member
    — catching a real exchange this project doesn't yet see via
    `_collect_known_ixps`. Verified once already (see task_plan.md):
    running this directly found zero exchanges beyond what the
    membership-based path had already surfaced, an exact match against
    the confirmed in-fishbowl set — this path exists to keep that true
    as PeeringDB's own data changes, not because a gap was found.
    """
    by_country = fetch_ixp_by_country([economy.cc for economy in ECONOMIES])
    ixps: dict[int, dict] = {}
    for cc, records in by_country.items():
        for record in records:
            ixps.setdefault(
                record["id"],
                {"name": record["name"], "city": record["city"], "country": cc},
            )
    return ixps


def build_ixp_lan_registry(
    fishbowl_path: Path = DEFAULT_SUMMARY_PATH,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> dict[int, IxpLanEntry]:
    """Build/refresh the IXP LAN subnet registry from two merged discovery paths.

    Discovers exchanges two independent ways: (1) every IXP one of this
    project's tracked ASNs is a member of, per `fishbowl.json`
    (`_collect_known_ixps` — can only find an exchange indirectly,
    through membership); (2) every IXP PeeringDB lists directly under
    one of the 20 in-scope economies' own country codes
    (`_collect_ixps_by_country` — finds an exchange whether or not any
    tracked ASN belongs to it). Verified once already that these agree
    exactly for this project's confirmed in-fishbowl set — kept as two
    paths so a real gap (a new exchange PeeringDB adds that none of our
    ASNs are members of yet) still gets caught by path (2) even if path
    (1) would miss it.

    Any exchange already present in the on-disk registry keeps its
    existing `in_fishbowl` value untouched (whatever a human previously
    set it to, including `"TBA"`) — only its name/city/country/prefixes
    are refreshed. An exchange new to the registry is written as `"TBA"`,
    never auto-classified — including one found only via its own country
    code, which might seem safe to auto-confirm but is exactly the kind
    of inference this project's governance rule exists to prevent.
    Exchanges already in the registry but *not* derived from either
    discovery path (e.g. added via `add_or_confirm_ixp` — GOREX was the
    first case, a real exchange not yet linked to any known ASN) are
    preserved untouched, never dropped by a rebuild.

    Args:
        fishbowl_path: Path to Phase 1a's `fishbowl.json`.
        registry_path: Where to load the existing registry from (if any)
            and persist the rebuilt one.

    Returns:
        Mapping of ix_id to its `IxpLanEntry`.
    """
    existing = load_ixp_lan_registry(registry_path) if registry_path.exists() else {}
    from_membership = _collect_known_ixps(fishbowl_path)
    from_country = _collect_ixps_by_country()
    known_ixps = {**from_country, **from_membership}  # membership data wins on overlap (has more fields)
    new_ix_ids = [ix_id for ix_id in known_ixps if ix_id not in existing]
    country_only = set(from_country) - set(from_membership)

    logger.info(
        "Found %d distinct IXPs (%d via tracked-ASN membership, %d via direct per-economy "
        "search only, %d already in registry, %d new -> TBA); fetching LAN prefixes",
        len(known_ixps),
        len(from_membership),
        len(country_only),
        len(known_ixps) - len(new_ix_ids),
        len(new_ix_ids),
    )
    prefixes_by_ix = fetch_ixp_prefixes(list(known_ixps))

    registry: dict[int, IxpLanEntry] = dict(existing)  # preserve entries not sourced from fishbowl.json
    for ix_id, meta in known_ixps.items():
        in_fishbowl = existing[ix_id].in_fishbowl if ix_id in existing else TBA
        fetched_prefixes = prefixes_by_ix.get(ix_id, [])
        if not fetched_prefixes and ix_id in existing and existing[ix_id].prefixes:
            # An empty refetch can't be told apart from a failed one here
            # (both look like []) — discovered as a real bug: a PeeringDB
            # rate limit during a routine rebuild silently wiped out 3
            # exchanges' already-known-good prefixes, including GU-IX's,
            # which actually matters for the classifier. Once we've
            # successfully fetched prefixes for an exchange, never let a
            # later empty result erase them.
            logger.warning(
                "ix_id=%d refetch returned no prefixes; keeping %d already on record "
                "(likely a transient fetch failure, not a real change)",
                ix_id,
                len(existing[ix_id].prefixes),
            )
            fetched_prefixes = list(existing[ix_id].prefixes)
        registry[ix_id] = IxpLanEntry(
            ix_id=ix_id,
            name=meta["name"],
            city=meta["city"],
            country=meta["country"],
            in_fishbowl=in_fishbowl,
            prefixes=tuple(fetched_prefixes),
        )

    _save_registry(registry, registry_path)

    in_count = sum(1 for e in registry.values() if e.in_fishbowl is True)
    out_count = sum(1 for e in registry.values() if e.in_fishbowl is False)
    tba_count = sum(1 for e in registry.values() if e.in_fishbowl == TBA)
    logger.info(
        "Wrote IXP LAN registry: %d exchanges (%d in-fishbowl, %d out-of-fishbowl, %d TBA)",
        len(registry),
        in_count,
        out_count,
        tba_count,
    )
    return registry


def _save_registry(registry: dict[int, IxpLanEntry], registry_path: Path) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        str(ix_id): {
            "name": entry.name,
            "city": entry.city,
            "country": entry.country,
            "in_fishbowl": entry.in_fishbowl,
            "prefixes": list(entry.prefixes),
        }
        for ix_id, entry in registry.items()
    }
    registry_path.write_text(json.dumps(payload, indent=2) + "\n")


def load_ixp_lan_registry(registry_path: Path = DEFAULT_REGISTRY_PATH) -> dict[int, IxpLanEntry]:
    """Load a previously-built registry from disk."""
    payload = json.loads(registry_path.read_text())
    return {
        int(ix_id): IxpLanEntry(
            ix_id=int(ix_id),
            name=v["name"],
            city=v["city"],
            country=v["country"],
            in_fishbowl=v["in_fishbowl"],
            prefixes=tuple(v["prefixes"]),
        )
        for ix_id, v in payload.items()
    }


def confirm_ixp_region(
    ix_id: int, in_fishbowl: bool, registry_path: Path = DEFAULT_REGISTRY_PATH
) -> None:
    """Record a human-confirmed in/out-of-fishbowl decision for one exchange.

    The only intended way a `"TBA"` entry should ever change — never done
    automatically by `build_ixp_lan_registry`.
    """
    registry = load_ixp_lan_registry(registry_path)
    if ix_id not in registry:
        raise KeyError(f"ix_id {ix_id} not in registry at {registry_path}")
    entry = registry[ix_id]
    registry[ix_id] = IxpLanEntry(
        ix_id=entry.ix_id,
        name=entry.name,
        city=entry.city,
        country=entry.country,
        in_fishbowl=in_fishbowl,
        prefixes=entry.prefixes,
    )
    _save_registry(registry, registry_path)
    logger.info("Confirmed ix_id %d (%s) as in_fishbowl=%s", ix_id, entry.name, in_fishbowl)


def add_or_confirm_ixp(
    ix_id: int, in_fishbowl: bool, registry_path: Path = DEFAULT_REGISTRY_PATH
) -> IxpLanEntry:
    """Add an IXP the project owner has pointed at directly, or confirm one already present.

    Unlike `build_ixp_lan_registry` (which only discovers exchanges
    already linked to a known ASN via `fishbowl.json`), this fetches the
    exchange's own metadata and prefixes directly from PeeringDB — for
    cases like GOREX (Piti, Guam), a real exchange not yet linked to any
    in-scope ASN this project has seen, so it never surfaces from the
    fishbowl-seeded build alone.

    Args:
        ix_id: PeeringDB exchange ID.
        in_fishbowl: Human-confirmed in/out-of-region classification —
            never inferred here, matching `build_ixp_lan_registry`'s rule.
        registry_path: Registry file to update.

    Returns:
        The added/updated `IxpLanEntry`.
    """
    registry = load_ixp_lan_registry(registry_path) if registry_path.exists() else {}
    ix_info = fetch_ix_info([ix_id]).get(ix_id, {})
    prefixes = fetch_ixp_prefixes([ix_id]).get(ix_id, [])

    entry = IxpLanEntry(
        ix_id=ix_id,
        name=ix_info.get("name", f"ix-{ix_id}"),
        city=ix_info.get("city", ""),
        country=ix_info.get("country", ""),
        in_fishbowl=in_fishbowl,
        prefixes=tuple(prefixes),
    )
    registry[ix_id] = entry
    _save_registry(registry, registry_path)
    logger.info(
        "Added/confirmed ix_id=%d %s (%s, %s) as in_fishbowl=%s, %d prefix(es)",
        ix_id,
        entry.name,
        entry.city,
        entry.country,
        in_fishbowl,
        len(entry.prefixes),
    )
    return entry


def prune_orphaned_entries(
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    asn_registry_path: Path = ASN_REGISTRY_PATH,
) -> list[int]:
    """Remove registry entries with zero current real Pacific ASN connection.

    The opposite of `build_ixp_lan_registry`'s own governance rule
    (existing entries are otherwise *never* dropped on a rebuild, since a
    human's in/out-of-fishbowl classification is load-bearing and must
    never silently vanish) -- this is a deliberate, explicit action, run
    only when asked, never as part of a routine rebuild. An entry only
    ever entered this registry via `_collect_known_ixps` (a tracked ASN
    was a real member there) or `_collect_ixps_by_country` (PeeringDB
    lists it directly under an in-scope economy's own country code). If
    neither is true any more -- checked live against PeeringDB, not the
    possibly-stale cached fishbowl.json -- the exchange has no remaining
    connection to this project's actual Pacific scope at all.

    Built for the concrete case that surfaced it: AS137064 (ISC F-root)
    and AS24013 (DNS.SB) -- both excluded as DNS anycast infrastructure,
    see `discovery.excluded_asns` -- were the *sole* in-scope-ASN
    connections to ABQIX and seven German exchanges (DE-CIX Dusseldorf/
    Frankfurt/Hamburg/Munich, LOCIX Dusseldorf/Frankfurt, MegaIX
    Dusseldorf) respectively. Once those two ASNs were excluded, none of
    those eight exchanges had any real Pacific member left, and none of
    them (US/Germany) can be found via the country-code path either.

    Returns:
        The ix_ids actually removed.
    """
    existing = load_ixp_lan_registry(registry_path)
    asn_registry = json.loads(asn_registry_path.read_text())
    in_scope_asns = {asn for entry in asn_registry.values() for asn in entry["asns"]}
    in_scope_ccs = set(asn_registry.keys())

    removed: list[int] = []
    for ix_id, entry in list(existing.items()):
        if entry.country in in_scope_ccs:
            continue  # still discoverable via the country path regardless of membership
        members = fetch_ixp_members(ix_id)
        if any(asn in in_scope_asns for asn in members):
            continue  # a real in-scope ASN is still a genuine member
        logger.warning(
            "Pruning orphaned IXP entry: %s (%s, %s) ix_id=%d -- zero remaining in-scope "
            "ASN members and not derivable from any in-scope economy's own country code",
            entry.name,
            entry.city,
            entry.country,
            ix_id,
        )
        del existing[ix_id]
        removed.append(ix_id)

    if removed:
        _save_registry(existing, registry_path)
        logger.info("Pruned %d orphaned IXP entries; %d remain", len(removed), len(existing))
    else:
        logger.info("No orphaned IXP entries found")
    return removed


def classify_ixp_fabric(ip: str, registry: dict[int, IxpLanEntry]) -> IxpLanEntry | None:
    """Return the IXP whose LAN prefix contains `ip`, if any.

    Args:
        ip: An IPv4 address to check.
        registry: Result of `build_ixp_lan_registry` / `load_ixp_lan_registry`.

    Returns:
        The matching `IxpLanEntry` (whose `in_fishbowl` may be `"TBA"` —
        callers must not assume it's a plain bool), or None if `ip` isn't
        in any known IXP's LAN prefix.
    """
    address = ipaddress.ip_address(ip)
    for entry in registry.values():
        for prefix in entry.prefixes:
            if address in ipaddress.ip_network(prefix):
                return entry
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    registry = build_ixp_lan_registry()
    tba = [e for e in registry.values() if e.in_fishbowl == TBA]
    if tba:
        logger.info("Awaiting region confirmation for %d exchange(s):", len(tba))
        for entry in sorted(tba, key=lambda e: e.name):
            logger.info("  ix_id=%d %s (%s, %s)", entry.ix_id, entry.name, entry.city, entry.country)


if __name__ == "__main__":
    main()
