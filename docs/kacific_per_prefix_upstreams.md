# Kacific (AS135409): each prefix enters through one regional upstream group

Finding, 2026-11-16 (owner asked for the write-up; scope: Kacific only). Sources: RIPEstat
`asn-neighbours`, `announced-prefixes`, `bgp-state` and `as-overview` (RIS, queried
2026-11-16), PeeringDB `net` for AS135409, two RIPE Atlas traceroutes from 2026-11-15, and
public gateway announcements and an FCC filing (listed at the end). Report-only: no finding in
`findings.db` was changed and the classifier is unchanged.

## Summary

- Kacific Broadband Satellites (AS135409, one GEO satellite, Kacific-1) has **22 RIS
  neighbours**: 11 upstreams, 10 customers and 1 RIPEstat marks uncertain (AS131111, Mora's
  Cepatnet, 7 IPv4 peers). PeeringDB lists 4 facilities (Equinix SY1/SY2
  Sydney, STTGDC SIN5 Singapore, VITRO Makati 2, XLSmart Surabaya) and no IXPs.
- **153 IPv4 prefixes checked** (Kacific's own 26, plus 127 originated by its 10 RIS
  customers). **45 reach the internet through Kacific.**
- **Each of the 45 enters Kacific through one upstream group**, and the groups follow the
  gateway regions: Australia, the Philippines, Indonesia, Singapore and Pakistan. Only one
  prefix, 103.70.66.0/23, is split between two regions.
- So a path into a Kacific-served network depends on **which prefix the target is in**, not on
  AS135409 as a whole. A Papua New Guinea customer enters through Indonesia; Niue and Tonga
  customers enter through Sydney.
- Kacific carries **no IPv6** in RIS: it announces no IPv6 prefix and every neighbour shows 0
  IPv6 peers.

## Method

For each prefix, every RIS path from `bgp-state` was taken, AS prepends collapsed, and the AS
immediately before AS135409 recorded. A share is that upstream's count over all paths that
contain AS135409. Paths that don't contain AS135409 at all (the customer's other upstreams)
are counted separately.

## Upstream groups

Shares are rounded per prefix; where a group's prefixes differ by a point or two, the typical
value is given.

| Upstream group (RIS share) | Likely gateway | Kacific's own prefixes | Customer prefixes through Kacific |
|---|---|---|---|
| AS7594 OneQode, 100% | Australia (Sydney hand-off; Broken Hill gateway in the FCC filing) | 14.137.32.0/19, 14.137.47.0/24, 14.137.48.0/24, 14.137.49.0/24, 14.137.50.0/24, 103.103.61.0/24, 182.54.145.0/24 | NU: IUSN Foundation AS10025, all 5 (202.59.4.0/22, 202.59.4-7.0/24). TO: Tonga Communications AS38201, 2 of 19 (202.134.29.0/24, 103.239.162.0/23). NZ: Gravity Internet AS131202 (103.133.117.0/24), Wireless Nation AS132449, 1 of 7 (43.249.197.0/24). SB: Solomon Telekom AS45891, 1 of 28 (202.1.172.0/24) |
| AS9299 PLDT ~84%, AS9304 HGC ~14%, AS137996 HGC Philippines <1% | Philippines (ABS teleport, Subic Bay) | 203.21.140.0/22, 203.21.140.0/24, 182.54.144.0/24, 182.54.146.0/23, 182.255.28.0/22, 203.24.104.0/22, 203.27.97.0/24, 103.103.63.0/24 | PH: AZ Communications AS38463, all 4 (203.189.8/9/11/14.0/24). iOne Resources AS133198, 1 of 3 (103.38.174.0/24). Globalreach AS17895, 1 of 56 (202.124.159.0/24, which also has non-Kacific paths: 102 of 387) |
| AS23947 Mora ~81%, AS4761 Indosat ~18%, AS136888 Petro One and AS131111 Cepatnet <1% | Indonesia (Petro1, East Java) | 202.5.112.0/20, 203.8.206.0/23, 203.8.206.0/24, 203.2.130.0/23, 203.27.96.0/24, 103.103.62.0/24 | PG: LOTIC Bige AS152477, both (103.213.10.0/24, 103.213.11.0/24) |
| AS4761 Indosat ~86%, AS17922 Indosat ~8%, AS136888 Petro One ~5% | Indonesia | 202.5.114.0/24, 103.106.175.0/24 | — |
| AS24482 SG.GS, 100% | Singapore | 103.103.60.0/24 | — |
| AS17557 PTCL 70-91%, AS17563 Nexlinx 8-29% | Pakistan | 103.70.65.0/24 | PK: Pak Datacom AS154022, 1 of 2 (165.101.131.0/24) |
| Split: AS4761 Indosat 68%, AS7594 OneQode 23%, AS17922 Indosat 7% | Indonesia and Australia | 103.70.66.0/23 | — |

The Pakistan pair is a market Kacific serves, not stray transit: a Pakistani customer's prefix
and one of Kacific's own leave through the same two Pakistani networks.

## Niue: the two replies from one address

Two 2026-11-15 traceroutes toward 202.59.4.1 (IUSN, Niue) enter Kacific at OneQode in Sydney.
The hop before the OneQode handoff reverse-resolves to
`gu-gnc-rt1-----Vlan780.au-gssyd-rt1.oneqode.net`, OneQode's Global Switch Sydney router.

| Measurement | Probe | OneQode hop 120.88.74.158 | First reply from 202.59.4.1 | Second reply from 202.59.4.1 |
|---|---|---|---|---|
| 238217921 | 65653 (MP) | 78.8 ms | 111.6 ms (hop 16) | 639.6 ms (hop 19) |
| 238217237 | 7588 (TV) | 56.5 ms | 75.1 ms (hop 11) | 616.7 ms (hop 13) |

In both, the first reply comes about 19 ms after Sydney, and the second about 520-540 ms after
the first. 520-540 ms is the size of one round trip through a geostationary satellite, so the
second reply is most likely the host in Niue. A fibre round trip from Sydney to Broken Hill is
roughly 12-15 ms, so the first reply fits ground equipment at an inland gateway answering for
the address. This is an inference: the FCC filing names Broken Hill as the gateway for the
Northern Mariana Islands, not for Niue, and no hop between Sydney and the first reply has a
public address. A vantage point inside AS10025 would settle it.

## What this means for corridor measurements

- **The RTT of a Kacific-served target depends on which reply is used.** Taking the first reply
  makes the target look about 500 ms closer than it is. Findings #326, #327 and #328 (toward
  AS10025) are affected; the owner decides which reply counts.
- **The hidden hops after OneQode are Kacific's gateway path.** RIS shows no other way into
  AS10025, which supports reading #328 as AS7594 -> AS135409 -> AS10025, not a direct AS7594
  adjacency.
- **The target prefix decides the route.** A test toward a Kacific-served network shows the
  gateway region of that prefix only. Tonga (AS38201) and Solomon Telekom (AS45891) use Kacific
  for a few blocks; most of their space has other upstreams.

## Limits

- RIS shows only the paths its collectors receive. A backup gateway announced only on failure,
  or not exported to collectors, would not appear here.
- This covers the inbound direction only, which is what a traceroute toward the target follows.
  A terminal is fixed to one beam and gateway, so the outbound path most likely uses the same
  gateway, but that wasn't measured.
- Gateway locations come from each upstream's country and the 2019-2021 announcements and FCC
  filing below, not from hop locations. Kacific may have added or moved gateways since.
- Only IPv4. Single snapshot (2026-11-16).

## Sources

- RIPEstat data API: `asn-neighbours`, `announced-prefixes`, `bgp-state`, `as-overview`
  (https://stat.ripe.net/docs/data_api), queried 2026-11-16.
- PeeringDB network record for AS135409 (https://www.peeringdb.com/asn/135409), last updated
  2026-08-31.
- Kacific selects the ABS Subic Bay teleport (SatNews, 2019-08-26):
  https://satnews.com/2019/08/26/kacific-selects-the-abs-subic-bay-teleport-for-their-kacific1-satellite-first-level-ground-support/
- Kacific brings in PT Petro One Indonesia for ground infrastructure (SatNews, 2019-10-28):
  https://satnews.com/2019/10/28/kacific-brings-pt-petro-one-indonesia-in-to-handle-ground-infrastructure-services-for-their-new-satellite/
- FCC filing SES-LFS-20210521-00824 (Broken Hill gateway for the Northern Mariana Islands):
  https://fcc.report/IBFS/SES-LFS-20210521-00824/7971794.pdf
- Kratos to build gateways for Kacific (Via Satellite, 2018-09-07):
  https://www.satellitetoday.com/ground-systems/2018/09/07/kratos-to-build-gateways-for-kacifics-new-hts-network/
