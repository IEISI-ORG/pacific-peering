"""Cloudflare Radar's RPKI ASPA data -- a stronger corroboration source
than RIS neighbor-observation for confirming upstream-provider
relationships. An ASPA record (RFC 9582) is the AS holder's own
cryptographically-signed statement of which ASNs are its legitimate
providers, not something inferred from observed BGP paths the way this
project's existing RIS neighbor-list checks are -- absence from RIS just
means "never observed," but presence in a target's own ASPA record is a
direct declaration, and absence from it (once the target has published
one at all) is itself informative.

Project owner's own find (bgp.tools/aspa/<asn> pages, e.g.
bgp.tools/aspa/140504). Generalized here into a scriptable source rather
than one-off page checks: bgp.tools and rpki-client's own public ASPA
reports are HTML-only with no documented bulk export (checked both
directly), and RIPEstat has no ASPA endpoint at all. Cloudflare Radar's
REST API is the one that actually has a JSON endpoint for this
(`/radar/bgp/rpki/aspa/snapshot`).

Requires a Cloudflare API token scoped to Account > Radar > Read -- the
first authenticated third-party credential this project's discovery
pipeline depends on (every other source here needs either no auth at all,
or a read-only key already documented the same way -- see
`discovery/secrets.py`, `atlas/secrets.py`).

Same caching convention as `bgp_tools.py`: the raw API response is cached
to one local JSON file, refetched only when stale -- ASPA adoption is
still early and records don't change often enough to justify a live API
call per lookup.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests
import yaml

logger = logging.getLogger(__name__)

RADAR_API_BASE = "https://api.cloudflare.com/client/v4/radar"
DEFAULT_SECRETS_PATH = Path("secrets.yaml")
_SECRET_KEY_NAME = "cloudflar_radar_api"

DEFAULT_ASPA_CACHE = Path("data/cloudflare_radar/aspa_snapshot.json")
_ASPA_MAX_AGE_SECONDS = 24 * 60 * 60  # ASPA records change rarely; daily is plenty
_DEFAULT_TIMEOUT = 60.0


def load_cloudflare_api_token(path: Path = DEFAULT_SECRETS_PATH) -> str:
    """Load the Cloudflare API token.

    Mirrors `atlas.secrets.load_atlas_api_key` / `discovery.secrets.
    load_peeringdb_api_key` exactly: `secrets.yaml` is never committed
    (see `.gitignore`) and its contents are never logged or echoed
    anywhere in this codebase. The token must be scoped to
    Account > Radar > Read -- nothing here ever needs write access.

    Args:
        path: Path to the secrets file.

    Returns:
        The API token string.

    Raises:
        FileNotFoundError: If `path` doesn't exist.
        KeyError: If `path` exists but has no `cloudflar_radar_api` entry.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Expected a gitignored secrets.yaml with a "
            f"'{_SECRET_KEY_NAME}' entry holding a Cloudflare API token "
            f"scoped to Account > Radar > Read."
        )
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or _SECRET_KEY_NAME not in data:
        raise KeyError(f"{path} must contain a '{_SECRET_KEY_NAME}' entry")
    return data[_SECRET_KEY_NAME]


def _is_stale(path: Path, max_age_seconds: float) -> bool:
    return not path.exists() or (time.time() - path.stat().st_mtime) > max_age_seconds


def _fetch_snapshot_payload(api_token: str | None, timeout: float) -> dict:
    token = api_token or load_cloudflare_api_token()
    response = requests.get(
        f"{RADAR_API_BASE}/bgp/rpki/aspa/snapshot",
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success", False):
        raise RuntimeError(f"Cloudflare Radar API error: {payload.get('errors')}")
    return payload["result"]


def fetch_aspa_snapshot(
    cache_path: Path = DEFAULT_ASPA_CACHE,
    refresh: bool = False,
    api_token: str | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> dict[int, list[int]]:
    """Fetch Cloudflare Radar's current global ASPA snapshot, cached locally.

    Args:
        cache_path: Local cache file for the raw API response.
        refresh: Force a live re-fetch even if the cache isn't stale yet.
        api_token: Override the token loaded from `secrets.yaml` (mainly
            for tests).
        timeout: Request timeout in seconds, only used on a live fetch.

    Returns:
        Mapping of customer ASN -> its list of ASPA-authorized provider
        ASNs. An ASN absent from this mapping simply hasn't published an
        ASPA object -- most ASNs haven't yet, this is not an error.
    """
    if refresh or _is_stale(cache_path, _ASPA_MAX_AGE_SECONDS):
        logger.info("Fetching fresh Cloudflare Radar ASPA snapshot to %s", cache_path)
        result = _fetch_snapshot_payload(api_token, timeout)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(result))

    raw = json.loads(cache_path.read_text())
    # The live API returns camelCase field names (aspaObjects/customerAsn),
    # not the snake_case shown in Cloudflare's own API reference docs --
    # confirmed by inspecting a real response directly, not by guessing.
    return {
        obj["customerAsn"]: list(obj["providers"])
        for obj in raw.get("aspaObjects", [])
    }


def get_aspa_providers(
    customer_asn: int,
    cache_path: Path = DEFAULT_ASPA_CACHE,
    refresh: bool = False,
) -> list[int] | None:
    """Look up `customer_asn`'s ASPA-authorized providers, if it has any.

    `None` means this ASN has no published ASPA object -- absence of
    evidence, not evidence of absence, same posture this project already
    takes for RIS-invisible prefixes elsewhere (see `hop_investigation.py`).
    An empty list is different and real: the ASN has published an ASPA
    object explicitly declaring it has no upstream providers (a pure
    peering-only or stub network).
    """
    snapshot = fetch_aspa_snapshot(cache_path=cache_path, refresh=refresh)
    return snapshot.get(customer_asn)
