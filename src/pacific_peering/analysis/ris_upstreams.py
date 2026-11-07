"""RIS upstream chains for in-scope networks, from fishbowl.json `neighbors`.

Split out of `convergence.py` (2026-11-06), which uses it to say whether a
router every trace of an economy pair crossed is a real dependency. RIS
`neighbors` say which networks routes to an origin are learned through --
the inbound direction -- while a traceroute shows the outbound path.
"""

from __future__ import annotations

MIN_UPSTREAM_SHARE = 0.02  # an upstream under 2% of RIS observations is collector noise

DEPENDENCY = "dependency"
SINGLE_UPSTREAM = "single_upstream"
PREFERRED_PATH = "preferred_path"
UNKNOWN = "unknown"


def _ris_upstreams(asn: int, fishbowl: dict) -> set[int] | None:
    entry = fishbowl.get(str(asn))
    if not entry or not entry.get("neighbors"):
        return None
    counts = {int(k): v for k, v in entry["neighbors"].items()}
    total = sum(counts.values())
    return {a for a, n in counts.items() if n >= MIN_UPSTREAM_SHARE * total}


def upstream_chain(asn: int, fishbowl: dict) -> list[int] | None:
    """The run of only-upstreams above `asn` in RIS: [] if it is multi-homed, None if RIS has no data.

    The walk continues through in-scope networks (NU AS55885 -> AS55943) and
    stops at the first one outside the scope, or at a multi-homed one.
    """
    ups = _ris_upstreams(asn, fishbowl)
    if ups is None:
        return None
    chain: list[int] = []
    while ups is not None and len(ups) == 1:
        (up,) = ups
        if up in chain or up == asn:
            break
        chain.append(up)
        ups = _ris_upstreams(up, fishbowl)
    return chain


def _chain_text(asn: int, chain: list[int]) -> str:
    return " -> ".join(f"AS{a}" for a in (asn, *chain))


def _off_region_exit(chain: list[int], fishbowl: dict) -> int | None:
    """The single out-of-scope network a chain leaves the region through, if it has one.

    None when the chain stops at an in-scope network that is multi-homed (or
    has no RIS data): NC AS17480 -> OPT-NC AS18200 has one upstream, but OPT-NC
    reaches several off-region networks, so BGP has alternatives.
    """
    return chain[-1] if chain and str(chain[-1]) not in fishbowl else None


def ris_verdict(router_asn: int, source_asns: set[int], target_asns: set[int], fishbowl: dict) -> tuple[str, str]:
    """DEPENDENCY > SINGLE_UPSTREAM > UNKNOWN > PREFERRED_PATH, with a one-line reason.

    Judged on each side's single off-region exit in RIS (`_off_region_exit`):
    DEPENDENCY when every network on one side leaves the region only through
    the router's network, SINGLE_UPSTREAM when only through one other network.
    """
    sides = {"source": {a: upstream_chain(a, fishbowl) for a in source_asns},
             "target": {a: upstream_chain(a, fishbowl) for a in target_asns}}
    exits = {side: {a: (_off_region_exit(c, fishbowl) if c else None) for a, c in chains.items()}
             for side, chains in sides.items()}
    for side, chains in sides.items():
        if chains and all(exits[side][a] == router_asn for a in chains):
            return DEPENDENCY, "; ".join(f"{side} {_chain_text(a, c or [])} only in RIS" for a, c in chains.items())
    single = [f"{side} {_chain_text(a, c or [])} only in RIS, not AS{router_asn}"
              for side, chains in sides.items() if chains and all(exits[side][a] for a in chains)
              for a, c in chains.items()]
    if single:
        return SINGLE_UPSTREAM, "; ".join(single)
    missing = [f"AS{a}" for chains in sides.values() for a, c in chains.items() if c is None]
    if missing:
        return UNKNOWN, f"no RIS upstream data for {', '.join(missing)}"
    in_region = [f"{side} {_chain_text(a, c)}, then multi-homed"
                 for side, chains in sides.items() for a, c in chains.items() if c]
    return PREFERRED_PATH, "; ".join(["both sides multi-homed in RIS", *in_region])
