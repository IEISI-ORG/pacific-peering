"""Does a raw Atlas traceroute hide routers just before the hop that answered for the target?

Per the project owner (2026-10-09): a lack of real hop data is just
inconclusive every time. Dark or unresolved hops are already visible as a
gap in the AS sequence (`traceroute_topology.extract_as_sequence`); this
module covers the two cases where every hop answered but routers are still
out of view:

1. **Forward TTL reset.** Atlas adds `ittl` to a reply when the probe
   packet quoted in it arrived with a TTL other than 1, so something on
   the way reset or skipped TTL decrements (an MPLS tunnel without TTL
   propagation, for instance). Finding #273 (218712900): ittl=240 on every
   target reply, about 15 routers hidden.
2. **Return-TTL jump.** A reply's TTL counts down from the responder's
   initial TTL (32/64/128/255), so `initial - ttl` is how many routers the
   reply crossed on its way back. If the target's return path is longer than
   the last responding hop's by clearly more than the forward step between
   them, routers sit in between that the forward trace never showed.
   Finding #291 (220522848): OneQode's Sydney router answered 4 hops back,
   the SISCC target 11 hops back, one forward hop later.

Threshold (`TTL_EXCESS_THRESHOLD`), calibrated 2026-10-09 against all 616
final segments in data/atlas/raw: 568 sit at -1..+1 excess hops (ordinary
return-path asymmetry). Everything at 5 or above came with a one-hop RTT
jump the cable distance can't explain: the Tonga probe 1018023 TTL-reset
traces (8-13), OneQode NR->FJ/SB (6), and Guam probe 329's 1.9ms -> 128ms
step (5). At 4 the hits include traces with no RTT jump at all (Hurricane
Electric, Google IPv6), so 5 is the cut.
"""

from __future__ import annotations

_INITIAL_TTLS = (32, 64, 128, 255)
TTL_EXCESS_THRESHOLD = 5


def _return_hops(ttl: int) -> int:
    """Routers a reply crossed back to the probe, from the smallest standard initial TTL >= `ttl`."""
    return next(initial for initial in _INITIAL_TTLS if initial >= ttl) - ttl


def _replies(hop: dict) -> list[dict]:
    return [r for r in hop.get("result", []) if "from" in r and r.get("ttl") is not None]


def hidden_hops_reason(raw_result: dict, target_hop: int) -> str | None:
    """Why routers are out of view just before `target_hop`, or None if nothing shows they are.

    Args:
        raw_result: one probe's raw Atlas traceroute result (with `result`
            holding each hop's replies, including `ttl` and any `ittl`).
        target_hop: the hop number of the first reply from the target ASN.
    """
    hops = {h.get("hop"): h for h in raw_result.get("result", [])}
    target_replies = _replies(hops.get(target_hop, {}))
    if not target_replies:
        return None

    ittls = sorted({r["ittl"] for r in target_replies if r.get("ittl") not in (None, 1)})
    if ittls:
        return (
            f"hop {target_hop} replies carry ittl={ittls[0]}: the forward TTL was "
            "reset on the way, so routers before it are out of view"
        )

    previous = [
        (hop_no, _replies(hop))
        for hop_no, hop in hops.items()
        if isinstance(hop_no, int) and hop_no < target_hop and _replies(hop)
    ]
    if not previous:
        return None
    prev_hop, prev_replies = max(previous, key=lambda item: item[0])
    return_step = min(_return_hops(r["ttl"]) for r in target_replies) - min(
        _return_hops(r["ttl"]) for r in prev_replies
    )
    excess = return_step - (target_hop - prev_hop)
    if excess < TTL_EXCESS_THRESHOLD:
        return None
    return (
        f"return-TTL jump: hop {target_hop}'s reply crossed {return_step} more routers "
        f"back than hop {prev_hop}'s, {excess} more than the {target_hop - prev_hop}-hop "
        "forward step, so about that many routers are out of view"
    )
