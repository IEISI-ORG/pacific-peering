"""Second chances for ASNs the offshore check couldn't judge because nothing answered.

Owner's request (2026-10-01). The ping physics test in `atlas.offshore_check`
can only judge an address that replies, and the 2026-09-24 full run got no
reply at all from 48 of 123 testable ASNs -- including AS131995 (XLPM), later
found hosted in Brisbane. Two fixes, both free of Atlas credits:

1. Better addresses. A silent `.1` isn't a silent network (AS45495's `.1`
   never answered; 21 hosts in the same /24 did). `alternate_addresses` looks
   for addresses inside the ASN's prefixes that answered in cached Atlas
   traceroutes, then falls back to an nmap ping sweep from this host, which
   also records reverse DNS for every responder. The caller pings up to
   `MAX_ALTERNATES_PER_ASN` of them through Atlas and judges them as usual.
2. RIS upstream screen. `upstream_screen` flags a still-silent ASN whose RIS
   upstreams are all foreign and include nothing recognisably ordinary (a
   Tier 1 per bgp.tools, or a known regional transit, satellite or research
   network) -- the XLPM (Servers Australia) and AS154410 (GSL) pattern. A
   lead for a latency test, never a verdict.
"""

from __future__ import annotations

import csv
import ipaddress
import json
import logging
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

PARSED_DIR = Path("data/atlas/parsed")
BGP_TOOLS_CSV = Path("data/bgp_tools/asns.csv")
MAX_ALTERNATES_PER_ASN = 3
SWEEP_MAX_PREFIXLEN = 22  # sweep at most a /22 (1,024 addresses) per prefix
SWEEP_TIMEOUT_S = 900

# Foreign upstreams that are ordinary for a Pacific network: regional transit
# carriers bgp.tools doesn't class as T1, satellite providers, and research
# networks. Anything classed T1 by bgp.tools counts as ordinary too.
ORDINARY_UPSTREAMS: dict[int, str] = {
    4637: "Telstra International (transit)",
    1221: "Telstra (transit)",
    6939: "Hurricane Electric (transit)",
    4826: "Vocus (transit)",
    4648: "Spark New Zealand (transit)",
    9901: "Pacific Internet (transit)",
    7473: "Singtel (transit)",
    4775: "Globe Telecom (transit)",
    9304: "HGC Global (transit)",
    135409: "Kacific (satellite)",
    14593: "Starlink (satellite)",
    7575: "AARNet (research)",
    6360: "University of Hawaii (research)",
    38022: "REANNZ (research)",
}


def _in_any(address: str, networks: list[ipaddress.IPv4Network]) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(ip in n for n in networks)


def cached_responders(prefixes: list[str], parsed_dir: Path = PARSED_DIR) -> list[str]:
    """Addresses inside `prefixes` that answered as a hop (or as the target) in
    any cached Atlas traceroute, most-seen first."""
    networks = [ipaddress.ip_network(p, strict=False) for p in prefixes if ":" not in p]
    if not networks or not parsed_dir.exists():
        return []
    seen: dict[str, int] = {}
    for path in parsed_dir.glob("*.json"):
        try:
            records = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        for record in records if isinstance(records, list) else []:
            for hop in record.get("hops", []):
                for address in hop.get("addresses") or []:
                    if _in_any(address, networks):
                        seen[address] = seen.get(address, 0) + 1
    return sorted(seen, key=lambda a: (-seen[a], ipaddress.ip_address(a)))


def sweep_targets(prefixes: list[str]) -> list[str]:
    """What to sweep: each IPv4 prefix, or its first /22 if larger."""
    out = []
    for p in prefixes:
        if ":" in p:
            continue
        net = ipaddress.ip_network(p, strict=False)
        if net.prefixlen < SWEEP_MAX_PREFIXLEN:
            net = next(net.subnets(new_prefix=SWEEP_MAX_PREFIXLEN))
        out.append(str(net))
    return out


_NMAP_UP = re.compile(r"^Host: (\S+) \(([^)]*)\)\s+Status: Up", re.M)


def parse_nmap_grepable(text: str) -> dict[str, str]:
    """{address: reverse DNS name or ""} for every host nmap reported up."""
    return {m.group(1): m.group(2) for m in _NMAP_UP.finditer(text)}


def nmap_sweep(prefixes: list[str]) -> dict[str, str]:
    """ICMP echo sweep of `prefixes` from this host, with reverse DNS. Empty if
    nmap isn't installed or the sweep fails (logged, never fatal)."""
    targets = sweep_targets(prefixes)
    if not targets:
        return {}
    if shutil.which("nmap") is None:
        logger.warning("nmap not installed; skipping ping sweep of %d prefix(es)", len(targets))
        return {}
    try:
        result = subprocess.run(
            ["nmap", "-sn", "-PE", "--max-retries", "1", "-T3", "-oG", "-", *targets],
            capture_output=True, text=True, timeout=SWEEP_TIMEOUT_S, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("nmap sweep of %s failed: %s", ", ".join(targets), exc)
        return {}
    return parse_nmap_grepable(result.stdout)


def alternate_addresses(prefixes: list[str], exclude: set[str], sweep: bool = True) -> tuple[list[str], dict[str, str]]:
    """(up to MAX_ALTERNATES_PER_ASN addresses to ping, {responder: rDNS} from the sweep).

    Cached traceroute responders first (free, already known to answer), then
    sweep responders, skipping anything in `exclude` (the addresses already
    tried). The sweep only runs if the cache didn't supply enough.
    """
    picked = [a for a in cached_responders(prefixes) if a not in exclude][:MAX_ALTERNATES_PER_ASN]
    swept: dict[str, str] = {}
    if sweep and len(picked) < MAX_ALTERNATES_PER_ASN:
        swept = nmap_sweep(prefixes)
        for address in sorted(swept, key=ipaddress.ip_address):
            if len(picked) >= MAX_ALTERNATES_PER_ASN:
                break
            if address not in exclude and address not in picked:
                picked.append(address)
    return picked, swept


def load_upstream_classes(path: Path = BGP_TOOLS_CSV) -> dict[int, tuple[str, str]]:
    """{asn: (name, bgp.tools class)} from the cached bgp.tools export."""
    out: dict[int, tuple[str, str]] = {}
    if not path.exists():
        return out
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            asn = row.get("asn", "")
            if asn.startswith("AS") and asn[2:].isdigit():
                out[int(asn[2:])] = (row.get("name", ""), row.get("class", ""))
    return out


def upstream_screen(
    asn: int,
    fishbowl: dict,
    in_scope: set[int],
    classes: dict[int, tuple[str, str]],
) -> dict | None:
    """A lead if every RIS upstream of `asn` is foreign and none is ordinary; else None.

    Returns {"upstreams": [{"asn", "name", "class", "observations"}]} so the
    report and escalation can show exactly what the screen saw.
    """
    neighbours = fishbowl.get(str(asn), {}).get("neighbors", {})
    if not neighbours:
        return None
    foreign = {int(n): count for n, count in neighbours.items() if int(n) not in in_scope}
    if len(foreign) != len(neighbours):
        return None  # at least one in-region upstream: not this pattern
    if any(n in ORDINARY_UPSTREAMS or classes.get(n, ("", ""))[1] == "T1" for n in foreign):
        return None
    return {"upstreams": [
        {"asn": n, "name": classes.get(n, ("?", ""))[0], "class": classes.get(n, ("", "?"))[1], "observations": c}
        for n, c in sorted(foreign.items(), key=lambda kv: -kv[1])
    ]}
