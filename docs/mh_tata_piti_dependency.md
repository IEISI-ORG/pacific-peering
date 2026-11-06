# Marshall Islands: every measured path in crosses one Tata router at Piti, Guam

Finding, 2026-11-06 (owner asked for the write-up). Source: the cached RIPE Atlas
traceroutes behind `outputs/reports/convergence.txt`, RIS upstream data in
`data/analysis/fishbowl.json`, and the Submarine Cable Map API. Report-only: no finding
in `findings.db` was changed.

## Summary

- **120 traceroutes** toward NTA (AS24439, the Marshall Islands National Telecommunications
  Authority), from **15 economies**, 2026-09-14 to 2026-11-05.
- **115 of them cross Tata Communications (AS6453) at Piti, Guam**:
  `if-bundle-3-2.qhar1.pv4-piti.as6453.net` (180.87.180.33), and on some paths `qhar2`.
  The other 5 end before Piti, and none shows another way in (see Exceptions).
- **RIS shows Tata as NTA's only upstream**: AS24439 -> AS6453, 1,646 of 1,646 observations.
- **The cable matches.** The Submarine Cable Map lists one in-service cable to the Marshall
  Islands: HANTRU-1, ready for service March 2010, landing at Piti (Guam), Kwajalein, Majuro
  and Pohnpei. Its owners include the Marshall Islands Telecommunications Authority. IOKWE
  (owner MINTA, Majuro) is listed as planned for 2029.

A failure of the Piti router, Tata's service at Piti, or HANTRU-1 would cut every path into
NTA that these measurements saw. In the convergence report this is the strongest dependency:
the always-crossed section marks 9 economy pairs as a "dependency" on `qhar1.pv4-piti`.

## Evidence by source economy

"Tata site before Piti" is the Tata router immediately before Piti on the trace. RTT is the
lowest round-trip time at the Piti hop.

| From | Traces | Via Piti | Probes | Source ASNs | Min RTT at Piti | Tata site before Piti | Dates | Measurements |
|---|---|---|---|---|---|---|---|---|
| CK | 5 | 5 | 1 | AS10131 | 227.5 ms | Los Angeles 5 | 09-20..11-04 | 211741326, 213457703, 221439948, 224427927, 232463064 |
| FJ | 1 | 1 | 1 | AS141695 | 230.6 ms | Los Angeles 1 | 09-27 | 216155814 |
| FM | 6 | 6 | 3 | AS14593, AS139759 | 81.2 ms | Tokyo 6 | 10-18..11-05 | 224430995, 233090273 |
| GU | 21 | 19 | 6 | AS3605, AS7131, AS17456, AS152735 | 62.1 ms | Tokyo 16, Los Angeles 3 | 09-14..11-04 | 211465536, 211567329, 212241945, 213456457, 216153949, 218707426, 221439391, 224427421, 232461446 |
| MH | 1 | 1 | 1 | AS14593 (Starlink) | 84.6 ms | Tokyo 1 | 09-23 | 214563597 |
| MP | 7 | 6 | 1 | AS7131 | 79.1 ms | Los Angeles 4, Tokyo 1 | 09-16..11-03 | 211567329, 212243973, 213512592, 216154230, 221439246, 224427233, 231754543 |
| NC | 15 | 15 | 3 | AS45345 | 242.9 ms | Tokyo 15 | 10-04..11-04 | 212128886, 218709542, 221441118, 224428889, 232466844 |
| NR | 1 | 1 | 1 | AS55722 | 258.4 ms | Los Angeles 1 | 10-08 | 220505886 |
| NU | 2 | 2 | 1 | AS55885 | 235.2 ms | Los Angeles 2 | 10-26 | 212141129, 227790057 |
| PF | 24 | 24 | 5 | AS9471 | 207.8 ms | Los Angeles 24 | 09-16..11-04 | 211683854, 212244006, 213456758, 216153941, 218707947, 221439546, 224427563, 232461444 |
| PG | 7 | 7 | 1 | AS17828 | 277.7 ms | Tokyo 5, Los Angeles 2 | 09-20..11-04 | 211965108, 213458236, 216155110, 218708291, 221440483, 224428409, 232464693 |
| PW | 6 | 6 | 1 | AS17893 | 78.4 ms | Tokyo 6 | 09-27..11-05 | 212015972, 216155909, 218709389, 221441124, 224429035, 233083410 |
| TO | 7 | 5 | 2 | AS24390, AS38198 | 176.6 ms | Tokyo 5 | 10-04..11-05 | 212094707, 218709564, 218709584, 218709972, 221441129, 224429036, 233083415 |
| TV | 6 | 6 | 1 | AS23917 | 220.3 ms | Los Angeles 6 | 09-27..11-04 | 212059716, 216156386, 218709561, 221441303, 224429034, 232466940 |
| VU | 11 | 11 | 2 | AS9249 | 216.7 ms | Los Angeles 11 | 09-16..11-03 | 211627606, 212237413, 213455350, 216152930, 218706874, 221438706, 224426761, 231753313 |

All dates are 2026. Some measurements carry traces from more than one probe.

## What the paths show

**Every path reaches Piti from Tokyo or Los Angeles, including the Guam ones.** No probe sees
the Piti router at a local RTT. The lowest is 62.1 ms, from Guam probe 329 (measurement
211465536), and Guam paths arrive from Tata Tokyo (16) or Tata Los Angeles (3). Example,
measurement 211567329, probe 62689 (AS7131):
Cogent `ccr81.tyo01` (144 ms) -> `tata.tyo01` -> Tata `tcore1.tv2-tokyo` (155 ms) -> Tata
`qhar1.pv4-piti` (155 ms). Traffic from Guam to the Marshall Islands goes to Japan and back to a
router a few kilometres from where it started, because no Guam network observed here meets
Tata at Piti locally.

**No hop inside AS24439 answers on any trace.** NTA's network is dark past Piti, so these
measurements can't show the Piti -> Majuro/Kwajalein leg or where NTA's own routers sit.

**The one Marshall Islands probe is on Starlink, not NTA.** Probe 64237 (AS14593) reaches NTA
via Starlink -> Tata Tokyo (85 ms) -> Piti (84.6 ms), measurement 214563597. That is a Starlink
user in the Marshall Islands reaching the national network through Japan and Guam, not NTA's
internal routing. There is no NTA-hosted probe.

## Exceptions (the 5 traces that don't cross Piti)

- 2 from Guam probe 23039 (AS17456; measurements 212241945, 216153949): dark after hop 1.
- 2 from Tonga probe 1018023 (AS38198; measurements 218709584, 218709972): end inside Digicel
  Tonga at hop 4.
- 1 from MP probe 65653 (AS7131; measurement 211567329): ends at Tata `tcore1.tv2-tokyo`, the
  hop immediately before Piti on the other paths.

None of the five shows a route into AS24439 that avoids Tata.

## Limits

- "Every measured path" means these 120 traces from these probes. Several economies have one
  probe, so a different source network could in principle take another route. RIS showing Tata
  as the only upstream (1,646 of 1,646) is the evidence that no such route is announced.
- RIS shows how routes to NTA are learned (inbound). A trace shows the outbound path. They agree
  here: both point at Tata.
- The router's location rests on its hostname (`pv4-piti`), the project's existing Piti pattern
  (`hop_geolocation`, confirmed via 211683854), and the Tata Piti Cable Landing Station entry in
  `regional_carrier_facilities.py`. No trace measures it at a Guam-local RTT, because none
  reaches it from Guam directly.
- Cable facts come from the Submarine Cable Map API (`/api/v3/cable/hantru1-cable-system.json`,
  `/api/v3/country/marshall-islands.json`, read 2026-11-06), not from the operators.

## For the owner

- **Hub labels on the existing MH findings.** Findings #73–84 (each source economy -> AS24439)
  are filed as detours via Tata. Piti is in the region, so under the last-off-region-hub rule
  (#58 on 2026-11-02, #33 on 2026-11-06) each hub is the Tata city before Piti. Two labels don't
  match the current traces: **#77 MP (Sydney)**, where MP traces reach Piti from Tata Los Angeles
  or Tokyo, and **#84 VU (Tokyo)**, where all 11 VU traces reach Piti from Tata Los Angeles.
  Not changed; owner's call.
- **FM -> NR also depends on Tata Piti** in the convergence report: target AS152706 -> AS6453
  only in RIS. AS152706 is the forged-path ASN in the open APNIC report (2026-10-27). Noted
  only.
- **IXP angle.** Guam networks reach the Marshall Islands' only cable through Tokyo or Los
  Angeles, not at Piti. Local interconnection with Tata at Piti, or Tata at a Guam exchange,
  would cut that hairpin. Logged as a business-case point in `task_plan.md`.
