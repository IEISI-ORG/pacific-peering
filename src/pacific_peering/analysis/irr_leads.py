"""Registry of PeeringDB-declared IRR AS-SET peering/transit intentions (APNIC-only).

Per the project owner: a fourth kind of lead alongside RIS-observed
AS-paths, PeeringDB IXP/facility membership, and Atlas traceroutes — a
network's own declared list of who it intends to peer with or provide
transit for. First done as a one-off cross-reference against four
ASNs already in play; the project owner then asked for it to become a
proper, persisted, monthly-refreshed data asset like the other
recurring registries, not a throwaway script.

**APNIC-sourced objects only** (explicit project owner instruction —
other IRRs are known to carry invalid/stale entries): every
`resolve_as_set` call already enforces this at the WHOIS layer; this
module inherits that guarantee rather than re-implementing it.

Refreshed monthly via `pipeline.run_pipeline`, alongside discovery/
fishbowl/ixp_lan_registry — same free-API-only cadence as the rest of
the recurring pipeline, no Atlas credits involved.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from pacific_peering.discovery.irr import resolve_as_set
from pacific_peering.discovery.peeringdb import fetch_irr_as_set_names
from pacific_peering.discovery.registry import DEFAULT_OUTPUT_PATH as DEFAULT_ASN_REGISTRY_PATH

logger = logging.getLogger(__name__)

DEFAULT_IRR_LEADS_PATH = Path("data/analysis/irr_as_sets.json")
_QUERY_DELAY_SECONDS = 0.3


@dataclass(frozen=True)
class ResolvedAsSet:
    """One AS-SET's resolved membership (APNIC-sourced, or empty if untrusted/not found)."""

    name: str
    asns: tuple[int, ...]
    nested_as_sets: tuple[str, ...]


@dataclass(frozen=True)
class IrrLead:
    """One in-scope ASN's declared IRR AS-SET(s) and what they resolved to."""

    asn: int
    declared_field: str  # raw PeeringDB irr_as_set value — can hold >1 space-separated name
    resolved: tuple[ResolvedAsSet, ...]


def _all_in_scope_asns(registry_path: Path) -> list[int]:
    registry = json.loads(registry_path.read_text())
    return sorted({asn for entry in registry.values() for asn in entry["asns"]})


def build_irr_leads(
    registry_path: Path = DEFAULT_ASN_REGISTRY_PATH,
    output_path: Path = DEFAULT_IRR_LEADS_PATH,
) -> dict[int, IrrLead]:
    """Fetch and resolve every in-scope ASN's declared IRR AS-SET, and persist the result.

    Handles two real-world wrinkles PeeringDB's raw `irr_as_set` field
    can carry: (1) more than one space-separated as-set name in a single
    field, and (2) an explicit `SOURCE::` prefix (e.g.
    `APNIC::AS132228:AS-ALL`) that APNIC's own WHOIS server rejects
    unless stripped first (confirmed directly: the prefixed form returns
    `%ERROR:101: no entries found`).

    Paced with a small delay between WHOIS queries — the same restraint
    already learned the hard way with PeeringDB's rate limits.

    Preserves already-persisted leads for any ASN a rate-limited chunk
    causes `fetch_irr_as_set_names` to skip this run — the same "never
    let a transient upstream failure silently discard already-confirmed
    data" fix already applied to `ixp_lan_registry` twice (once for
    `in_fishbowl`, once for `prefixes`). Without this, a rebuild that
    happens to catch PeeringDB mid-rate-limit would quietly drop real,
    previously-resolved leads — confirmed this actually happened, not
    just theoretical: a live rebuild silently dropped 3 of 36 entries
    (AS152735, AS153053, AS154410) the first time this ran without the
    guard.

    Args:
        registry_path: Path to the Phase 0b ASN registry (which ASNs
            are in scope).
        output_path: Where to persist the resolved leads.

    Returns:
        Mapping of ASN to its `IrrLead` (only ASNs with a non-empty
        `irr_as_set` field, current or previously-persisted, are
        included).
    """
    asns = _all_in_scope_asns(registry_path)
    as_set_fields = fetch_irr_as_set_names(asns)
    existing = load_irr_leads(output_path) if output_path.exists() else {}

    missing = set(asns) & set(existing) - set(as_set_fields)
    for asn in missing:
        logger.warning(
            "AS%d had a declared AS-SET on record but this run's PeeringDB fetch "
            "didn't return it (likely rate-limited, not a real change) -- keeping "
            "the existing entry",
            asn,
        )

    leads: dict[int, IrrLead] = {asn: existing[asn] for asn in missing}
    for asn, raw_field in as_set_fields.items():
        resolved: list[ResolvedAsSet] = []
        for name in raw_field.split():
            clean_name = name.split("::", 1)[1] if "::" in name else name
            result = resolve_as_set(clean_name)
            resolved.append(
                ResolvedAsSet(
                    name=clean_name,
                    asns=tuple(result["asns"]),
                    nested_as_sets=tuple(result["nested_as_sets"]),
                )
            )
            time.sleep(_QUERY_DELAY_SECONDS)
        leads[asn] = IrrLead(asn=asn, declared_field=raw_field, resolved=tuple(resolved))

    _save_leads(leads, output_path)
    resolved_count = sum(
        1 for lead in leads.values() if any(r.asns or r.nested_as_sets for r in lead.resolved)
    )
    logger.info(
        "IRR sweep: %d/%d in-scope ASNs declare an AS-SET, %d resolved to trusted (APNIC) data",
        len(leads),
        len(asns),
        resolved_count,
    )
    return leads


def _save_leads(leads: dict[int, IrrLead], output_path: Path) -> None:
    payload = {
        str(asn): {
            "declared_field": lead.declared_field,
            "resolved": [
                {"name": r.name, "asns": list(r.asns), "nested_as_sets": list(r.nested_as_sets)}
                for r in lead.resolved
            ],
        }
        for asn, lead in leads.items()
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n")


def load_irr_leads(path: Path = DEFAULT_IRR_LEADS_PATH) -> dict[int, IrrLead]:
    """Load a previously-built IRR leads registry from disk."""
    payload = json.loads(path.read_text())
    return {
        int(asn): IrrLead(
            asn=int(asn),
            declared_field=v["declared_field"],
            resolved=tuple(
                ResolvedAsSet(
                    name=r["name"],
                    asns=tuple(r["asns"]),
                    nested_as_sets=tuple(r["nested_as_sets"]),
                )
                for r in v["resolved"]
            ),
        )
        for asn, v in payload.items()
    }


def find_in_scope_relationships(
    leads: dict[int, IrrLead], registry_path: Path = DEFAULT_ASN_REGISTRY_PATH
) -> list[tuple[int, int, str]]:
    """Return every (source_asn, target_asn, as_set_name) triple where both ASNs are in-scope.

    A cheap, in-memory join — not persisted separately, since it's
    trivial to recompute from `leads` plus the ASN registry.
    """
    registry = json.loads(registry_path.read_text())
    asn_to_cc = {asn: cc for cc, entry in registry.items() for asn in entry["asns"]}
    relationships: list[tuple[int, int, str]] = []
    for asn, lead in leads.items():
        for r in lead.resolved:
            for target in r.asns:
                if target != asn and target in asn_to_cc:
                    relationships.append((asn, target, r.name))
    return relationships


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    leads = build_irr_leads()
    relationships = find_in_scope_relationships(leads)
    logger.info("Found %d in-scope-to-in-scope declared relationship(s)", len(relationships))
    for source, target, name in relationships:
        logger.info("  AS%d -> AS%d (via %s)", source, target, name)


if __name__ == "__main__":
    main()
