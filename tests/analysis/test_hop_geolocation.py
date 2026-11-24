"""Tests for hop_geolocation.resolve_hostname: a router's location from its own PTR name.

OneQode names an interface `<router at the far end>-----<VLAN>.<router it is on>`.
The two ends of Vlan780, one link between Guam and Sydney, show it (PTRs as of
2026-11-06): 103.151.64.6 is `au-gssyd-rt1-----Vlan780.gu-gnc-rt1` and 103.151.64.7
is `gu-gnc-rt1-----Vlan780.au-gssyd-rt1`. Guam probes reach .7 at ~70ms, one hop
after OneQode Guam at 0.2-0.5ms, and the next hop is an EdgeIX Sydney or IX Australia
NSW LAN address within 1ms (223636622, 213458029). Owner, 2026-11-16: locate these
names by the router after the dot, not the first token.
"""

from __future__ import annotations

from pacific_peering.analysis.hop_geolocation import resolve_hostname

GUAM_END = "au-gssyd-rt1-----Vlan780.gu-gnc-rt1.oneqode.net"  # 103.151.64.6
SYDNEY_END = "gu-gnc-rt1-----Vlan780.au-gssyd-rt1.oneqode.net"  # 103.151.64.7


def test_oneqode_interface_is_located_by_the_router_it_is_on():
    loc = resolve_hostname(SYDNEY_END)
    assert loc is not None
    assert (loc.city, loc.economy_cc) == ("Sydney", None)


def test_the_guam_end_of_the_same_link_stays_in_guam():
    loc = resolve_hostname(GUAM_END)
    assert loc is not None
    assert (loc.city, loc.economy_cc) == ("Guam", "GU")


def test_oneqode_hong_kong_interface_facing_guam_is_hong_kong():
    # 103.151.64.207 on 211527961: 45-52ms from Saipan, one hop after OneQode Guam
    # (103.112.0.226, 2-10ms), then Telstra Global hkth (Hong Kong).
    loc = resolve_hostname("gu-gnc-rt1-----Vlan756.hk-mgi-rt1.oneqode.net")
    assert loc is not None
    assert loc.city == "Hong Kong"


def test_the_far_end_token_alone_never_locates_an_interface():
    # jp-cc1 and us-la2 have no confirmed pattern yet: unknown, not Guam.
    assert resolve_hostname("gu-gnc-rt1-----Vlan750.jp-cc1-rt2.oneqode.net") is None
    assert resolve_hostname("gu-gnc-rt1-----Vlan769.us-la2-rt1.oneqode.net") is None


def test_plain_router_names_are_unchanged():
    assert resolve_hostname("hk-mgi-rt1.oneqode.net").city == "Hong Kong"
    assert resolve_hostname("gu-gnc-rt1.oneqode.net").economy_cc == "GU"
    assert resolve_hostname("ix-xe-2-1-4-0.tcore2.lvw-losangeles.as6453.net").city == "Los Angeles"


# Telstra Global (AS4637) names its routers by four-letter site code, not IATA code, and
# 'syd' alone doesn't match 'sydo'/'sydp' at a segment boundary. Real names, each next to
# a router whose city is not in doubt (2026-11-17):
#   sydo/sydp: PG probe 50365 reaches them at ~39ms, 0.1-0.4ms after Telstra's
#     oxf-gw30.sydney.telstra.net (211789443, 224429318).
#   hkck: GU probe 65337 at 58.626ms, 0.1ms after telstra4-lacp-100g.hkix.net (212458784).
#   hkth/hkmi: VU probe 1008536/64783 on 213187876, hkth12 165.6ms, hkmi01 166.3ms,
#     hkck 166.8ms, then iij3-10g.hkix.net 171.6ms.
TELSTRA_SYDNEY = (
    "bundle-ether1.sydo-core04.telstraglobal.net",
    "i-91.sydo10.telstraglobal.net",
    "i-91.sydp10.telstraglobal.net",
    "i-10201.sydp-core04.telstraglobal.net",
    "Bundle-Ether10157.sydp-core03.sydney.telstraglobal.net",
)
TELSTRA_HONG_KONG = (
    "i-91.hkth-core02.telstraglobal.net",
    "i-0-5-0-5.hkth12.telstraglobal.net",
    "i-96.hkck-core01.telstraglobal.net",
    "i-92.hkmi01.telstraglobal.net",
)


def test_telstra_global_sydney_site_codes():
    for name in TELSTRA_SYDNEY:
        loc = resolve_hostname(name)
        assert loc is not None, name
        assert (loc.city, loc.economy_cc) == ("Sydney", None), name


def test_telstra_global_hong_kong_site_codes():
    for name in TELSTRA_HONG_KONG:
        loc = resolve_hostname(name)
        assert loc is not None, name
        assert (loc.city, loc.economy_cc) == ("Hong Kong", None), name


def test_telstra_site_codes_only_count_on_telstra_global_names():
    assert resolve_hostname("sydo-core04.example.net") is None
    assert resolve_hostname("i-91.hkth-core02.example.net") is None


# Telstra's domestic network puts the city in the name (`<if>.<site>-<role>.sydney.telstra.net`).
# Every Sydney name in the PTR cache sits within ~1ms of a router already placed in Sydney
# (2026-11-17): VU probe 64783 on 211648499, i-91.sydp-core04 51.6ms then pad-gw30 50.9ms;
# PG probe 50365 on 221438711, hay-core30 38.3ms then sydo-core04 39.7ms; TO probe 11691
# on 212106578, AARNet bdr1.mcqd.nsw 109.9ms then chw-edge903 109.3ms.
TELSTRA_DOMESTIC_SYDNEY = (
    "bundle-ether2.oxf-gw30.sydney.telstra.net",
    "bundle-ether1.pad-gw30.sydney.telstra.net",
    "ae19.alx-edge411.sydney.telstra.net",
    "Bundle-Ether1111-567.chw-edge903.sydney.telstra.net",
    "bundle-ether50.hay-core30.sydney.telstra.net",
)

# HKIX LAN names (`<member><n>-<port>.hkix.net`). GU probe 65337 on 212458784:
# telstra4-lacp-100g 58.7ms, then Telstra Global hkck-core01 58.6ms. VU probe 1008536 on
# 213187876: hkmi01 166.3ms, iij3-10g 171.6ms, then IIJ hkg002bb01 170.6ms.
HKIX = ("telstra4-lacp-100g.hkix.net", "iij3-10g.hkix.net")


def test_telstra_domestic_sydney_names():
    for name in TELSTRA_DOMESTIC_SYDNEY:
        loc = resolve_hostname(name)
        assert loc is not None, name
        assert (loc.city, loc.economy_cc) == ("Sydney", None), name


def test_hkix_lan_names_are_hong_kong():
    for name in HKIX:
        loc = resolve_hostname(name)
        assert loc is not None, name
        assert (loc.city, loc.economy_cc) == ("Hong Kong", None), name


def test_telstra_domestic_city_word_only_counts_on_telstra_net():
    # Customer link names carry no city; other cities have no hub coordinates yet.
    assert resolve_hostname("twi4246393.lnk.telstra.net") is None
    assert resolve_hostname("bundle-ether1.win-edge903.melbourne.telstra.net") is None
    assert resolve_hostname("core1.sydney.example.net") is None
    assert resolve_hostname("telstra4-lacp-100g.hkix.net.example.com") is None


# AARNet's Los Angeles border router is `bdr1.laxc.us`; the `lax\d*` pattern needs a segment
# boundary after the digits, so `laxc` never matched (owner, 2026-11-19). TO probe 11691 on
# 240076669: AARNet Sydney 46.7ms, `et-0-0-0.bdr1.laxc.us.aarnet.net.au` (113.197.15.137)
# 179.8ms, then the Any2West LAN address 206.72.210.133 at 179.7ms.
AARNET_LOS_ANGELES = "et-0-0-0.bdr1.laxc.us.aarnet.net.au"

# Hurricane Electric's Tokyo routers are `core<n>.tyo<n>.he.net` (owner, 2026-11-19). NR probe
# 1018134 reaches ve101.core2.tyo1 at 75ms, one hop after Guam at 36ms (231076198);
# be15.core1.tyo1 sits directly before the BBIX Tokyo (213456317) and JPNAP Tokyo (231751013)
# LAN addresses. All ten tyo1 names in the PTR cache (2026-11-19):
HE_TOKYO = (
    "ve101.core2.tyo1.he.net",
    "be15.core1.tyo1.he.net",
    "be3.core1.tyo1.he.net",
    "be47.core1.tyo1.he.net",
    "be48.core1.tyo1.he.net",
    "port-channel1.core3.tyo1.he.net",
    "port-channel9.core2.tyo1.he.net",
    "port-channel16.core2.tyo1.he.net",
    "gigabitethernet2-8.core1.tyo1.he.net",
    "port-channel10.core3.tyo1.he.net",
)


def test_aarnet_laxc_is_los_angeles():
    loc = resolve_hostname(AARNET_LOS_ANGELES)
    assert loc is not None
    assert (loc.city, loc.economy_cc) == ("Los Angeles", None)


def test_he_tyo_routers_are_tokyo():
    for name in HE_TOKYO:
        loc = resolve_hostname(name)
        assert loc is not None, name
        assert (loc.city, loc.economy_cc) == ("Tokyo", None), name


def test_laxc_and_tyo_only_count_on_their_own_carriers():
    # Other carriers' tyo names (Cogent tyo01, GTT cr4-tyo1) are not yet checked against a hop.
    assert resolve_hostname("be2915.ccr81.tyo01.atlas.cogentco.com") is None
    assert resolve_hostname("ae6.cr4-tyo1.ip4.gtt.net") is None
    assert resolve_hostname("core1.tyo1.he.net.example.com") is None
    assert resolve_hostname("xe-0.bdr1.laxc.example.net") is None
    assert resolve_hostname("et-0-0-0.bdr1.laxc.aarnet.net.au") is None


# Hurricane Electric's Honolulu routers are `core<n>.hnl<n>.he.net` (owner, 2026-11-24, on #309).
# Guam probe 60703 reaches 10ge0-5.core1.gum1 at 2ms, 100ge0-0-0-2.core1.hnl1 at 68ms (Guam-Honolulu
# floor ~61ms), then be5.core1.lax2 at 129ms (212241945); NU probe 64391 goes port-channel4.core2.hnl1
# 127ms -> 100ge0-36.core1.gum1 194ms (233688533). All three hnl1 names in the PTR cache (2026-11-24):
HE_HONOLULU = (
    "100ge0-0-0-2.core1.hnl1.he.net",
    "port-channel4.core2.hnl1.he.net",
    "be47.core1.hnl1.he.net",
)


def test_he_hnl_routers_are_honolulu():
    for name in HE_HONOLULU:
        loc = resolve_hostname(name)
        assert loc is not None, name
        assert (loc.city, loc.economy_cc) == ("Honolulu", None), name


def test_hnl_only_counts_on_hurricane_electric():
    # Level3's hnl1-ar3 (one measurement, 211510435) is not yet checked against a hop.
    assert resolve_hostname("hnl1-ar3-ae21-0.3549.level3.net") is None
    assert resolve_hostname("core1.hnl1.he.net.example.com") is None
