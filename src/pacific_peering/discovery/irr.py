"""Resolve IRR AS-SET objects: a network's own declared peering/transit intentions.

Per the project owner: a PeeringDB `net` record's `irr_as_set` field
(see `discovery.peeringdb.fetch_irr_as_set_names`) names an Internet
Routing Registry AS-SET object — a network's own declared list of who
it intends to peer with or provide transit for. This is a fourth kind
of lead alongside RIS-observed AS-paths, PeeringDB IXP/facility
membership, and Atlas traceroutes: a declared *intention*, not an
observed fact — same "lead, not ground truth" caveat this project
already applies to PeeringDB.

**APNIC-sourced objects only, by explicit project owner instruction**:
other IRR sources (RADB's own self-registered objects, other RIRs'
databases mirrored into a shared server, etc.) are known to carry
invalid or stale entries and are not trusted here. Concretely, this
means:
1. Querying APNIC's own WHOIS server (`whois.apnic.net`) directly,
   never a third-party aggregator/mirror like RADB's — confirmed
   empirically to serve the identical objects.
2. Every response's `source:` field is checked and must read exactly
   `APNIC` — an object that doesn't carry that (or doesn't have the
   field at all) is treated as unresolved, not silently trusted.

Uses the plain WHOIS protocol (RFC 3912, port 43) — no API key, no
scraping, this is the standard, designed way to query IRR data.
"""

from __future__ import annotations

import logging
import socket

logger = logging.getLogger(__name__)

APNIC_WHOIS_SERVER = "whois.apnic.net"
TRUSTED_SOURCE = "APNIC"
_DEFAULT_TIMEOUT = 15.0


def _whois_query(query: str, server: str = APNIC_WHOIS_SERVER, timeout: float = _DEFAULT_TIMEOUT) -> str:
    """Send one plain WHOIS protocol query and return the raw response text."""
    with socket.create_connection((server, 43), timeout=timeout) as sock:
        sock.sendall(f"{query}\r\n".encode())
        chunks: list[bytes] = []
        while True:
            data = sock.recv(4096)
            if not data:
                break
            chunks.append(data)
    return b"".join(chunks).decode("utf-8", errors="replace")


def resolve_as_set(as_set_name: str, server: str = APNIC_WHOIS_SERVER) -> dict[str, list]:
    """Resolve one APNIC-sourced IRR AS-SET's `members:` line into ASNs and nested as-sets.

    Deliberately does *not* recursively expand nested as-sets (e.g.
    `AS-132528-PEERS` can declare `AS-45355-PEERS` as one of its own
    members) — real-world AS-SET expansion can be deep, and this
    project only needs a first-pass lead, not a full IRR toolchain.
    Both kinds of entry are returned so a caller can tell them apart and
    decide whether to resolve a nested one too.

    Args:
        as_set_name: e.g. "AS-132528-PEERS".
        server: IRR WHOIS server to query — defaults to APNIC's own,
            never a third-party mirror (see module docstring).

    Returns:
        `{"asns": [int, ...], "nested_as_sets": [str, ...]}` — both
        empty if the as-set has no `members:` line, wasn't found, *or*
        its `source:` field isn't exactly `APNIC` (an object from an
        untrusted source is treated as unresolved, not used).
    """
    try:
        response = _whois_query(as_set_name, server=server)
    except OSError as exc:
        logger.warning("IRR WHOIS query for %s failed: %s", as_set_name, exc)
        return {"asns": [], "nested_as_sets": []}

    lines = response.splitlines()
    source = next(
        (line.partition(":")[2].strip() for line in lines if line.lower().startswith("source:")),
        None,
    )
    if source != TRUSTED_SOURCE:
        logger.warning(
            "IRR object %s has source=%r, not %r -- treating as untrusted, not resolving",
            as_set_name,
            source,
            TRUSTED_SOURCE,
        )
        return {"asns": [], "nested_as_sets": []}

    asns: list[int] = []
    nested: list[str] = []
    for line in lines:
        if not line.lower().startswith("members:"):
            continue
        _, _, value = line.partition(":")
        for token in value.split(","):
            token = token.strip()
            if not token:
                continue
            if token.upper().startswith("AS-"):
                nested.append(token)
            elif token[:2].upper() == "AS" and token[2:].isdigit():
                asns.append(int(token[2:]))
    return {"asns": asns, "nested_as_sets": nested}
