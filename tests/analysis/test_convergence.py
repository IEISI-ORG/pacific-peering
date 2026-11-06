"""convergence: off-region routers that many Pacific corridors share (report-only)."""

from __future__ import annotations

import json
from pathlib import Path

from pacific_peering.analysis import convergence as conv

FIXTURE = Path(__file__).parent / "fixtures" / "convergence_231754538.json"

# In-scope ASNs -> economy, as fishbowl.json supplies them.
IN_SCOPE = {3605: "GU", 9751: "AS", 4638: "FJ", 9471: "PF", 17893: "PW", 24390: "FJ", 9249: "VU", 45879: "TO"}


def _trace(probe_id, target, *addresses, measurement_id=1):
    return {"measurement_id": measurement_id, "probe_id": probe_id, "target": target,
            "hops": [{"hop": i, "addresses": [a], "min_rtt_ms": float(i)} for i, a in enumerate(addresses, 1)]}


# --- device_key ---------------------------------------------------------------

def test_device_key_drops_the_interface_label():
    assert conv.device_key("154.54.164.22", "be2378.ccr51.pdx02.atlas.cogentco.com") == "ccr51.pdx02.atlas.cogentco.com"
    assert conv.device_key("154.54.46.162", "be2467.ccr51.pdx02.atlas.cogentco.com") == "ccr51.pdx02.atlas.cogentco.com"
    assert conv.device_key("184.104.194.221", "port-channel4.core2.hnl1.he.net") == "core2.hnl1.he.net"
    assert conv.device_key("1.2.3.4", "100ge0-0-0-4.core3.syd1.he.net") == "core3.syd1.he.net"
    assert conv.device_key("113.197.15.213", "xe-0-0-0.pe1.a.suv.aarnet.net.au") == "pe1.a.suv.aarnet.net.au"
    assert conv.device_key("202.84.222.185", "i-90.sydo-core03.telstraglobal.net") == "sydo-core03.telstraglobal.net"
    assert conv.device_key("202.158.204.194", "fastethernet0-0.aarnie.usp.ac.fj") == "aarnie.usp.ac.fj"


def test_device_key_keeps_a_hostname_that_names_the_router_itself():
    assert conv.device_key("1.2.3.4", "cr8-lax2.ip4.gtt.net") == "cr8-lax2.ip4.gtt.net"
    assert conv.device_key("58.138.88.226", "sea002bb00.IIJ.Net.") == "sea002bb00.iij.net"
    assert conv.device_key("206.72.210.64", "aarnet.as7575.any2ix.coresite.com") == "aarnet.as7575.any2ix.coresite.com"


def test_device_key_falls_back_to_the_address():
    assert conv.device_key("38.142.108.162", None) == "38.142.108.162"
    # A hostname built from the address says nothing about which router it is.
    assert conv.device_key("103.43.212.161", "103-43-212-161.static.rise.net.ph") == "103.43.212.161"


# --- longest-prefix origin lookup ---------------------------------------------

def test_prefix_origins_takes_the_longest_match():
    lines = [
        json.dumps({"CIDR": "10.0.0.0/8", "ASN": 1, "Hits": 9}),
        json.dumps({"CIDR": "10.1.2.0/24", "ASN": 2, "Hits": 9}),
        json.dumps({"CIDR": "2001:db8::/32", "ASN": 3, "Hits": 9}),
        "",
    ]
    got = conv.prefix_origins(lines, ["10.1.2.3", "10.9.9.9", "11.0.0.1", "2001:db8::1"])
    assert got == {"10.1.2.3": 2, "10.9.9.9": 1, "2001:db8::1": 3}


# --- collect + categorise ------------------------------------------------------

PTR = {"9.9.9.1": "be1.core1.hub.example.net", "9.9.9.2": "be2.core1.hub.example.net"}.get


def _asn_of(table):
    return lambda ip: table.get(ip)


def test_router_shared_by_three_sources_and_three_targets_is_shared_transit():
    probe_cc = {1: "GU", 2: "PF", 3: "FJ"}
    asn = {"9.9.9.1": 6939, "9.9.9.2": 6939, "t.as": 9751, "t.pw": 17893, "t.vu": 9249}
    traces = [
        (_trace(1, "t.as", "9.9.9.1"), "2026-10-01"),
        (_trace(2, "t.pw", "9.9.9.2"), "2026-10-20"),
        (_trace(3, "t.vu", "9.9.9.1"), "2026-11-03"),
    ]
    routers = conv.collect(traces, probe_cc, _asn_of(asn), IN_SCOPE, PTR)
    assert len(routers) == 1
    r = routers[0]
    assert r.key == "core1.hub.example.net"
    assert r.addresses == frozenset({"9.9.9.1", "9.9.9.2"})
    assert r.sources == {"GU", "PF", "FJ"} and r.targets == {"AS", "PW", "VU"}
    assert (r.first_seen, r.last_seen) == ("2026-10-01", "2026-11-03")
    assert conv.category(r) == conv.SHARED_TRANSIT


def test_router_with_one_target_economy_is_target_access():
    probe_cc = {1: "GU", 2: "PF", 3: "FJ"}
    asn = {"9.9.9.1": 11404, "t.as": 9751}
    traces = [(_trace(p, "t.as", "9.9.9.1"), None) for p in (1, 2, 3)]
    (r,) = conv.collect(traces, probe_cc, _asn_of(asn), IN_SCOPE, PTR)
    assert conv.category(r) == conv.TARGET_ACCESS


def test_router_with_one_source_economy_is_source_side():
    asn = {"9.9.9.1": 4826, "t.as": 9751, "t.pw": 17893, "t.vu": 9249}
    traces = [(_trace(1, t, "9.9.9.1"), None) for t in ("t.as", "t.pw", "t.vu")]
    (r,) = conv.collect(traces, {1: "PG"}, _asn_of(asn), IN_SCOPE, PTR)
    assert conv.category(r) == conv.SOURCE_SIDE


def test_router_under_both_thresholds_has_no_category():
    asn = {"9.9.9.1": 6939, "t.as": 9751, "t.pw": 17893}
    traces = [(_trace(1, "t.as", "9.9.9.1"), None), (_trace(2, "t.pw", "9.9.9.1"), None)]
    (r,) = conv.collect(traces, {1: "GU", 2: "PF"}, _asn_of(asn), IN_SCOPE, PTR)
    assert conv.category(r) is None


def test_in_scope_unresolved_and_private_hops_are_not_routers():
    asn = {"202.128.5.149": 3605, "t.as": 9751}  # 8.8.4.4 deliberately unresolved
    trace = _trace(1, "t.as", "192.168.1.1", "202.128.5.149", "8.8.4.4")
    assert conv.collect([(trace, None)], {1: "GU"}, _asn_of(asn), IN_SCOPE, PTR) == []


def test_trace_with_unknown_probe_or_out_of_scope_target_is_skipped():
    asn = {"9.9.9.1": 6939, "t.as": 9751, "1.1.1.1": 13335}
    traces = [(_trace(99, "t.as", "9.9.9.1"), None), (_trace(1, "1.1.1.1", "9.9.9.1"), None)]
    assert conv.collect(traces, {1: "GU"}, _asn_of(asn), IN_SCOPE, PTR) == []


# --- frozen real trace: 231754538 (GU -> AS9751), owner-reviewed 2026-11-06 -----

def test_231754538_both_guam_probes_converge_on_one_cogent_pdx02_router():
    """Probe 329 enters Cogent via sea08/pdx01, probe 64953 via sfo01/pdx01; both then hit
    ccr51.pdx02 on different interfaces (154.54.164.22 / 154.54.46.162), which is one router."""
    traces = [(t, "2026-11-03") for t in json.loads(FIXTURE.read_text())]
    asn = {"38.101.165.1": 9751}
    for t in traces:
        for h in t[0]["hops"]:
            for a in h["addresses"]:
                if a.startswith("154.54.") or a.startswith("38.142."):
                    asn[a] = 174
    ptr = {"154.54.164.22": "be2378.ccr51.pdx02.atlas.cogentco.com",
           "154.54.46.162": "be2467.ccr51.pdx02.atlas.cogentco.com"}.get
    routers = {r.key: r for r in conv.collect(traces, {329: "GU", 64953: "GU"}, _asn_of(asn), IN_SCOPE, ptr)}
    pdx02 = routers["ccr51.pdx02.atlas.cogentco.com"]
    assert pdx02.addresses == frozenset({"154.54.164.22", "154.54.46.162"})
    assert pdx02.probes == {329, 64953}
    assert routers["38.142.108.162"].probes == {329, 64953}


# --- render --------------------------------------------------------------------

def test_render_lists_shared_and_target_access_but_only_counts_source_side():
    shared = conv.Router(key="core1.lax2.he.net", asn=6939, addresses=frozenset({"a", "b"}),
                         pairs=frozenset({("GU", "AS"), ("PF", "PW"), ("CK", "VU")}),
                         probes=frozenset({1, 2, 3}), first_seen="2026-09-16", last_seen="2026-11-05")
    access = conv.Router(key="cr1-fdcp.bb.as11404.net", asn=11404, addresses=frozenset({"c"}),
                         pairs=frozenset({("GU", "AS"), ("PF", "AS"), ("CK", "AS")}),
                         probes=frozenset({1, 2, 3}), first_seen=None, last_seen=None)
    source = conv.Router(key="202.137.111.77", asn=4826, addresses=frozenset({"d"}),
                         pairs=frozenset({("PG", "AS"), ("PG", "FJ"), ("PG", "VU")}),
                         probes=frozenset({4}), first_seen=None, last_seen=None)
    text = conv.render([shared, access, source], {6939: "Hurricane Electric", 11404: "Wave"}, traces_read=10)
    assert "core1.lax2.he.net" in text and "AS6939 Hurricane Electric" in text
    assert "2026-09-16..2026-11-05" in text
    assert "cr1-fdcp.bb.as11404.net" in text
    assert "202.137.111.77" not in text
    assert "Source-side routers (not listed): 1" in text
    assert text.index("core1.lax2.he.net") < text.index("cr1-fdcp.bb.as11404.net")


def test_render_ends_with_the_shared_legal_notice():
    from pacific_peering.reports.data import LEGAL_NOTICE

    text = conv.render([], {}, traces_read=0)
    assert "LEGAL NOTICE" in text
    for heading, body in LEGAL_NOTICE:
        assert f"{heading}. {body}" in text


def test_device_key_drops_tata_if_and_ix_interface_labels():
    assert conv.device_key("1.2.3.4", "if-ae-15-2.tcore3.lvw-losangeles.as6453.net") == "tcore3.lvw-losangeles.as6453.net"
    assert conv.device_key("1.2.3.4", "if-bundle-12-2.qhar1.pv4-piti.as6453.net") == "qhar1.pv4-piti.as6453.net"
    assert conv.device_key("1.2.3.4", "ix-xe-2-1-4-0.tcore2.lvw-losangeles.as6453.net") == "tcore2.lvw-losangeles.as6453.net"


def test_a_ptr_shared_by_several_addresses_is_a_placeholder_not_a_router():
    """unknown.telstraglobal.net and ip4.gtt.net sit on many unrelated routers (2026-11-06)."""
    asn = {"202.84.222.93": 4637, "202.40.149.30": 4637, "t.as": 9751, "t.pw": 17893, "t.vu": 9249}
    ptr = {"202.84.222.93": "unknown.telstraglobal.net", "202.40.149.30": "unknown.telstraglobal.net."}.get
    traces = [(_trace(1, "t.as", "202.84.222.93"), None), (_trace(2, "t.pw", "202.40.149.30"), None)]
    keys = {r.key for r in conv.collect(traces, {1: "GU", 2: "PF"}, _asn_of(asn), IN_SCOPE, ptr)}
    assert keys == {"202.84.222.93", "202.40.149.30"}


# --- PTR cache: a lookup that times out this run must not split a router -------

def test_cached_ptr_name_is_reused_when_the_live_lookup_fails():
    cache = {"9.9.9.1": {"name": "be1.core1.hub.example.net", "checked": "2026-11-01"}}
    names = conv.resolve_ptrs(["9.9.9.1"], lambda a: None, cache, today="2026-11-06")
    assert names == {"9.9.9.1": "be1.core1.hub.example.net"}


def test_fresh_cached_name_is_not_looked_up_again():
    cache = {"9.9.9.1": {"name": "be1.core1.hub.example.net", "checked": "2026-11-01"}}
    calls = []
    conv.resolve_ptrs(["9.9.9.1"], lambda a: calls.append(a), cache, today="2026-11-06")
    assert calls == []


def test_stale_or_missing_names_are_looked_up_and_cached():
    cache = {"9.9.9.1": {"name": "old.example.net", "checked": "2026-09-01"}}
    live = {"9.9.9.1": "be1.core1.hub.example.net", "9.9.9.2": "be2.core1.hub.example.net"}.get
    names = conv.resolve_ptrs(["9.9.9.1", "9.9.9.2"], live, cache, today="2026-11-06")
    assert names == {"9.9.9.1": "be1.core1.hub.example.net", "9.9.9.2": "be2.core1.hub.example.net"}
    assert cache["9.9.9.2"] == {"name": "be2.core1.hub.example.net", "checked": "2026-11-06"}


def test_a_miss_is_retried_once_in_the_same_run():
    answers = iter([None, "be1.core1.hub.example.net"])
    names = conv.resolve_ptrs(["9.9.9.1"], lambda a: next(answers), {}, today="2026-11-06")
    assert names == {"9.9.9.1": "be1.core1.hub.example.net"}


# --- always-crossed routers + RIS upstream check --------------------------------

FISHBOWL = {
    "55885": {"economy": {"cc": "NU"}, "neighbors": {"55943": 1646}},
    "55943": {"economy": {"cc": "PF"}, "neighbors": {"3257": 1644, "286": 5}},  # 286 is noise (<2%)
    "45879": {"economy": {"cc": "WF"}, "neighbors": {"5511": 1647}},
    "10131": {"economy": {"cc": "CK"}, "neighbors": {"55943": 1130, "45177": 259, "12684": 226}},
    "17993": {"economy": {"cc": "WS"}, "neighbors": {"174": 1111, "6939": 145, "35280": 11}},
    "9751": {"economy": {"cc": "AS"}, "neighbors": {}},
    "17480": {"economy": {"cc": "NC"}, "neighbors": {"18200": 1600}},
    "18200": {"economy": {"cc": "NC"}, "neighbors": {"5511": 900, "4637": 700}},
}


def test_upstream_chain_follows_single_upstreams_through_in_scope_networks():
    assert conv.upstream_chain(55885, FISHBOWL) == [55943, 3257]


def test_upstream_chain_is_empty_for_a_multi_homed_network():
    assert conv.upstream_chain(10131, FISHBOWL) == []
    assert conv.upstream_chain(17993, FISHBOWL) == []  # 35280 at 11/1267 is under 2%, 6939 isn't


def test_upstream_chain_is_none_without_ris_data():
    assert conv.upstream_chain(9751, FISHBOWL) is None
    assert conv.upstream_chain(64512, FISHBOWL) is None


def test_verdict_is_dependency_when_a_sides_only_upstream_is_the_routers_network():
    code, detail = conv.ris_verdict(5511, source_asns={10131}, target_asns={45879}, fishbowl=FISHBOWL)
    assert code == conv.DEPENDENCY
    assert "AS45879 -> AS5511" in detail


def test_verdict_is_single_upstream_when_the_only_upstream_is_another_network():
    code, detail = conv.ris_verdict(6939, source_asns={55885}, target_asns={17993}, fishbowl=FISHBOWL)
    assert code == conv.SINGLE_UPSTREAM
    assert "AS55885 -> AS55943 -> AS3257" in detail


def test_verdict_is_preferred_path_when_both_sides_are_multi_homed():
    code, _ = conv.ris_verdict(6939, source_asns={10131}, target_asns={17993}, fishbowl=FISHBOWL)
    assert code == conv.PREFERRED_PATH


def test_verdict_is_unknown_without_ris_data_for_a_side():
    code, _ = conv.ris_verdict(6939, source_asns={10131}, target_asns={9751}, fishbowl=FISHBOWL)
    assert code == conv.UNKNOWN


def _ac_inputs():
    in_scope = {int(k): v["economy"]["cc"] for k, v in FISHBOWL.items()}
    asn = {"9.9.9.1": 5511, "9.9.9.2": 6939, "t.wf": 45879, "t.ws": 17993}
    probes = {1: ("CK", 10131), 2: ("CK", 10131), 3: ("CK", 10131)}
    return in_scope, asn, probes


def test_router_on_every_trace_of_a_pair_is_always_crossed():
    in_scope, asn, probes = _ac_inputs()
    traces = [(_trace(p, "t.wf", "9.9.9.1"), None) for p in (1, 2, 3)]
    (row,) = conv.always_crossed(traces, probes, _asn_of(asn), in_scope, PTR, FISHBOWL)
    assert (row.pair, row.key, row.asn, row.traces, row.probes) == (("CK", "WF"), "core1.hub.example.net", 5511, 3, 3)
    assert row.verdict == conv.DEPENDENCY


def test_a_pair_with_one_trace_avoiding_the_router_is_not_always_crossed():
    in_scope, asn, probes = _ac_inputs()
    traces = [(_trace(1, "t.ws", "9.9.9.2"), None), (_trace(2, "t.ws", "9.9.9.2"), None),
              (_trace(3, "t.ws", "8.8.8.8"), None)]
    asn["8.8.8.8"] = 15169
    assert conv.always_crossed(traces, probes, _asn_of(asn), in_scope, PTR, FISHBOWL) == []


def test_a_pair_needs_three_traces():
    in_scope, asn, probes = _ac_inputs()
    traces = [(_trace(p, "t.wf", "9.9.9.1"), None) for p in (1, 2)]
    assert conv.always_crossed(traces, probes, _asn_of(asn), in_scope, PTR, FISHBOWL) == []


def test_render_lists_always_crossed_routers_with_three_or_more_pairs():
    rows = [conv.AlwaysCrossed(key="core2.hnl1.he.net", asn=6939, pair=(s, t), traces=4, probes=1,
                               verdict=conv.PREFERRED_PATH, detail="both sides multi-homed in RIS")
            for s, t in (("CK", "KI"), ("NU", "GU"), ("PF", "WS"))]
    rows.append(conv.AlwaysCrossed(key="lonely.example.net", asn=1, pair=("FJ", "TO"), traces=3, probes=1,
                                   verdict=conv.UNKNOWN, detail="no RIS data"))
    text = conv.render([], {6939: "Hurricane Electric"}, traces_read=0, always=rows)
    assert "ALWAYS-CROSSED ROUTERS: 1" in text
    assert "core2.hnl1.he.net" in text and "CK>KI" in text and "preferred path" in text
    assert "lonely.example.net" not in text
    assert text.index("ALWAYS-CROSSED") < text.index("LEGAL NOTICE")


def test_one_in_region_upstream_that_is_multi_homed_is_a_preferred_path():
    """NC AS17480 -> OPT-NC AS18200 only, but OPT-NC has two off-region upstreams (2026-11-06)."""
    code, detail = conv.ris_verdict(6939, source_asns={10131}, target_asns={17480}, fishbowl=FISHBOWL)
    assert code == conv.PREFERRED_PATH
    assert "AS17480 -> AS18200" in detail
