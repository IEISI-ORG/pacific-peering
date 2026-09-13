"""Persistent cache for IP -> ASN resolution results.

Traceroute analysis re-resolves the same handful of backbone/IXP-fabric
addresses over and over (the same transit ASNs and exchange points show
up across many different measurements). Without a cache, each new
analysis re-queries RIPEstat and PeeringDB for addresses already known
from a previous run — wasteful, and part of why PeeringDB rate-limited
this project during loop tranche 4. This cache makes resolution
idempotent across runs, not just within one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CACHE_PATH = Path("data/analysis/ip_resolution_cache.json")


@dataclass
class IpResolutionCache:
    """In-memory IP -> (asn, source) cache, backed by a JSON file.

    `asn` is `None` for addresses confirmed unresolvable (e.g. private/
    CGNAT addresses) — caching the negative result matters too, since
    otherwise every unresolved hop gets re-queried on every run forever.
    """

    path: Path
    entries: dict[str, dict]

    @classmethod
    def load(cls, path: Path = DEFAULT_CACHE_PATH) -> "IpResolutionCache":
        """Load a cache from `path`, or start empty if it doesn't exist yet."""
        entries = json.loads(path.read_text()) if path.exists() else {}
        return cls(path=path, entries=entries)

    def get(self, ip: str) -> tuple[int | None, str | None, dict | None] | None:
        """Return (asn, source, ixp_context) if `ip` is cached, else None (not yet looked up).

        `ixp_context` (added after the cache's initial version — absent
        on older entries, which `.get` on the raw dict handles safely)
        is set when `asn` is None but the address is still known to fall
        within a registered IXP LAN prefix: `{"ix_id", "name", "in_fishbowl"}`.
        """
        entry = self.entries.get(ip)
        if entry is None:
            return None
        return entry["asn"], entry["source"], entry.get("ixp_context")

    def set(
        self, ip: str, asn: int | None, source: str | None, ixp_context: dict | None = None
    ) -> None:
        """Record a resolution result for `ip` (call `.save()` to persist it)."""
        self.entries[ip] = {"asn": asn, "source": source, "ixp_context": ixp_context}

    def save(self) -> None:
        """Write all cached entries back to this cache's file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries, indent=2) + "\n")
