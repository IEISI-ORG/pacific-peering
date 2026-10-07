# Escalations

Corridors `auto_classify.py`'s mechanical rules couldn't confidently resolve on their own -- a routing loop at an address never seen before, an IXP crossing PeeringDB/`ixp_lan_registry.json` hasn't been told is in- or out-of-fishbowl, an external upstream at a hub with no known coordinates. Each needs a human/LLM look before it's added to `known_anomalies.py`, `ixp_lan_registry.json`, or `economy_coordinates.EXTERNAL_HUB_LATLON` and reprocessed.
## AS9249 (VU) -> AS23959 (VU)
- measurement: 213187876
- reason: unrecognized routing loop
- detail: probe 1008536: loop involving address 202.84.222.81, not in known_anomalies.py
- flagged: 2026-09-19T00:45:51.475813+00:00
- resolved: 2026-09-24 -- AS23959 excluded as offshore-hosted (space served from Tokyo, sole upstream AS4785 xTom JP); see discovery/excluded_asns.py. Its findings were removed.

## AS9249 (VU) -> AS23959 (VU)
- measurement: 213187876
- reason: unrecognized routing loop
- detail: probe 64783: loop involving address 202.84.222.81, not in known_anomalies.py
- flagged: 2026-09-19T00:45:51.475813+00:00
- resolved: 2026-09-24 -- AS23959 excluded as offshore-hosted (space served from Tokyo, sole upstream AS4785 xTom JP); see discovery/excluded_asns.py. Its findings were removed.

## AS17828 (PG) -> AS55792 (PG)
- measurement: 213188745
- reason: unrecognized routing loop
- detail: probe 50365: loop involving address 202.95.200.36, not in known_anomalies.py
- flagged: 2026-09-19T00:47:28.039833+00:00
- resolved: 2026-10-05 -- target-side loop (owner): both looping addresses, 202.95.200.36/.35, are inside AS55792 (the target), alternating for 29 hops at +20ms per cycle after a clean AS17828 -> AS55792 handoff at hop 3->4; the confirmed_local_transit finding stands on that handoff. Alternate-prefix retry from the same probe (218785315, to 202.95.195.1) goes dark after AS17828's 202.165.194.4 with no loop, so the loop is specific to 103.3.168.1, most likely an unassigned address. Not seen in any other trace.

## AS3605 (GU) -> AS9246 (GU)
- measurement: 213204603
- reason: local IXP crossing with implausibly high latency
- detail: probe 64953: hop 6 crosses MARIIX (in-fishbowl) at 15.741ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-09-19T01:35:21.666521+00:00
- resolved: 2026-10-05 -- ordinary (owner): the hop after MARIIX answers faster than the MARIIX hop itself (15.7ms vs 9.8ms at 114.142.196.90), so the extra time is the exchange router generating its ICMP reply, not path. Probe 64953 already sits 9-13ms out before any IXP (202.128.2.86 / 202.128.28.32). The 10ms check uses absolute RTT; queued to compare against the later hops' minimum.

## AS152735 (GU) -> AS9246 (GU)
- measurement: 213205466
- reason: local IXP crossing with implausibly high latency
- detail: probe 64953: hop 6 crosses MARIIX (in-fishbowl) at 11.111ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-09-19T01:38:25.504223+00:00
- resolved: 2026-10-05 -- ordinary (owner): the hop after MARIIX answers faster than the MARIIX hop itself (11.1ms vs 10.2ms at 114.142.196.90), so the extra time is the exchange router generating its ICMP reply, not path. Probe 64953 already sits 9-13ms out before any IXP (202.128.2.86 / 202.128.28.32). The 10ms check uses absolute RTT; queued to compare against the later hops' minimum.

## AS7131 (GU) -> AS56200 (GU)
- measurement: 213209039
- reason: unrecognized routing loop
- detail: probe 60689: loop involving address 154.18.76.1, not in known_anomalies.py
- flagged: 2026-09-19T01:47:43.630954+00:00
- resolved: 2026-10-05 -- not a loop (owner): 154.18.76.1 (AS7131) answers at hop 8 with TTL-exceeded, then at hop 11 with ICMP host-unreachable (err H) for 203.215.52.1 -- the router reporting the target unreachable. Ordinary AS7131 space, consistent with finding #231's note. Queued: the loop check should ignore repeats that carry an ICMP error.

## AS152735 (GU) -> AS395400 (GU)
- measurement: 213209268
- reason: local IXP crossing with implausibly high latency
- detail: probe 62689: hop 5 crosses MARIIX (in-fishbowl) at 24.484ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-09-19T01:50:51.628050+00:00
- resolved: 2026-10-05 -- ordinary (owner): the hop after MARIIX answers faster than the MARIIX hop itself (24.5ms vs 3.0ms at 168.123.136.7), so the extra time is the exchange router generating its ICMP reply, not path. The 10ms check uses absolute RTT; queued to compare against the later hops' minimum.

## AS17456 (GU) -> AS395400 (GU)
- measurement: 213209280
- reason: local IXP crossing with implausibly high latency
- detail: probe 60689: hop 8 crosses MARIIX (in-fishbowl) at 23.234ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-09-19T01:51:00.839704+00:00
- resolved: 2026-10-05 -- ordinary (owner): the hop after MARIIX answers faster than the MARIIX hop itself (23.2ms vs 9.4ms at 168.123.136.7), so the extra time is the exchange router generating its ICMP reply, not path. The 10ms check uses absolute RTT; queued to compare against the later hops' minimum.


## AS10131 (CK) -- possible offshore-hosted address space
- reason: offshore-hosting check (atlas/offshore_check.py)
- detail: 202.65.33.1: probe 1004726 4.3ms < 50.4ms minimum (measurement 215224841)
- action: owner review; if confirmed, add to discovery/excluded_asns.py (offshore_hosted)
- flagged: 2026-09-24T11:49:55.550669+00:00
- resolved: 2026-09-25 -- prefix-level, not ASN-level: 202.65.33.0/24 is Sydney-hosted and is excluded as a traceroute target (atlas/targets.py EXCLUDED_TARGET_PREFIXES); AS10131's 202.65.32.0/24 tests local, so the ASN stays in scope. The monthly offshore check keeps pinging the block.

## AS23959 (VU) -- possible offshore-hosted address space
- reason: offshore-hosting check (atlas/offshore_check.py)
- detail: 194.127.166.1: probe 1014094 11.19ms < 66.6ms minimum (measurement 215225380)
- action: owner review; if confirmed, add to discovery/excluded_asns.py (offshore_hosted)
- flagged: 2026-09-24T11:49:55.550669+00:00
- resolved: 2026-09-24 -- AS23959 excluded as offshore-hosted (space served from Tokyo, sole upstream AS4785 xTom JP); see discovery/excluded_asns.py. Its findings were removed.

## AS58932 (PW) -- possible offshore-hosted address space
- reason: offshore-hosting check (atlas/offshore_check.py)
- detail: 103.30.248.1: probe 1000112 48.72ms < 110.9ms minimum (measurement 215228529)
- action: owner review; if confirmed, add to discovery/excluded_asns.py (offshore_hosted)
- flagged: 2026-09-24T11:49:55.550669+00:00
- resolved: 2026-09-24 -- downgraded to `unconfirmed` by the two-network rule: the only probe that beat physics, 1000112, is registered as an "LA VM" but sits on AS3258 xTom Japan and answered at Tokyo-like RTT (48.7ms vs a Tokyo probe's 48.4ms) -- a probe-location error, not offshore hosting.

## AS132468 (SB) -- possible offshore-hosted address space
- reason: offshore-hosting check (atlas/offshore_check.py)
- detail: 103.188.182.1: probe 1011722 11.1ms < 28.5ms minimum (measurement 215228678)
- action: owner review; if confirmed, add to discovery/excluded_asns.py (offshore_hosted)
- flagged: 2026-09-24T11:49:55.550669+00:00
- resolved: 2026-09-25 -- prefix-level, not ASN-level: 103.188.182.0/23 (registered to XconX Pty Ltd, AU) is Sydney-hosted and is excluded as a traceroute target (atlas/targets.py EXCLUDED_TARGET_PREFIXES); AS132468's 103.115.80.0/24 tests local, so the ASN stays in scope.

## AS10131 (CK) -> AS9751 (AS)
- measurement: 216153502
- reason: no probe data returned
- detail: Atlas returned zero probe results for this measurement -- most likely a transient results-fetch race (status went terminal moments before results were indexed) rather than a real network outcome; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-09-27T15:06:36.944315+00:00
- resolved: 2026-10-03 -- not a fetch race (the detail above is wrong): all seven 2026-09-27 CK measurements (216153502, 216153814, 216153954, 216154414, 216154556, 216154870, 216155432) are Failed with zero results -- the source probe, 22761 (Telecom Aitutaki, AS10131, CK's only working probe), was assigned and didn't run. It has been Disconnected since 2026-10-01T08:27Z, so CK has no live vantage; tracked as one probe issue, not per corridor.

## AS10131 (CK) -> AS17828 (PG)
- measurement: 216153814
- reason: no probe data returned
- detail: Atlas returned zero probe results for this measurement -- most likely a transient results-fetch race (status went terminal moments before results were indexed) rather than a real network outcome; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-09-27T15:09:58.132290+00:00
- resolved: 2026-10-03 -- not a fetch race (the detail above is wrong): all seven 2026-09-27 CK measurements (216153502, 216153814, 216153954, 216154414, 216154556, 216154870, 216155432) are Failed with zero results -- the source probe, 22761 (Telecom Aitutaki, AS10131, CK's only working probe), was assigned and didn't run. It has been Disconnected since 2026-10-01T08:27Z, so CK has no live vantage; tracked as one probe issue, not per corridor.

## AS7131 (MP) -> AS24390 (FJ)
- measurement: 216153943
- reason: unrecognized routing loop
- detail: probe 65653: loop involving address 103.112.0.226, not in known_anomalies.py
- flagged: 2026-09-27T15:12:26.023585+00:00
- resolved: 2026-10-03 -- false loop: the 2026-10-01 re-check after the loop-test fix (commit 21480aa) found this measurement is repeat-then-progress (the trace reached new routers after the repeated address), which no longer flags.

## AS10131 (CK) -> AS24390 (FJ)
- measurement: 216153954
- reason: no probe data returned
- detail: Atlas returned zero probe results for this measurement -- most likely a transient results-fetch race (status went terminal moments before results were indexed) rather than a real network outcome; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-09-27T15:13:20.097674+00:00
- resolved: 2026-10-03 -- not a fetch race (the detail above is wrong): all seven 2026-09-27 CK measurements (216153502, 216153814, 216153954, 216154414, 216154556, 216154870, 216155432) are Failed with zero results -- the source probe, 22761 (Telecom Aitutaki, AS10131, CK's only working probe), was assigned and didn't run. It has been Disconnected since 2026-10-01T08:27Z, so CK has no live vantage; tracked as one probe issue, not per corridor.

## AS3605 (GU) -> AS38198 (TO)
- measurement: 216154286
- reason: unrecognized routing loop
- detail: probe 60689: loop involving address 202.43.12.5, not in known_anomalies.py
- flagged: 2026-09-27T15:15:44.219904+00:00
- resolved: 2026-10-05 -- not a loop (owner): 202.43.12.5 (AS38198 border, seen on ten prior detours) answers at hop 19, then once more at hop 20 with the same reply TTL (238); no router appears after it. A duplicate last-hop reply. Queued: the loop check should ignore a repeat at the tail with nothing new after it.

## AS10131 (CK) -> AS24439 (MH)
- measurement: 216154414
- reason: no probe data returned
- detail: Atlas returned zero probe results for this measurement -- most likely a transient results-fetch race (status went terminal moments before results were indexed) rather than a real network outcome; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-09-27T15:16:43.235106+00:00
- resolved: 2026-10-03 -- not a fetch race (the detail above is wrong): all seven 2026-09-27 CK measurements (216153502, 216153814, 216153954, 216154414, 216154556, 216154870, 216155432) are Failed with zero results -- the source probe, 22761 (Telecom Aitutaki, AS10131, CK's only working probe), was assigned and didn't run. It has been Disconnected since 2026-10-01T08:27Z, so CK has no live vantage; tracked as one probe issue, not per corridor.

## AS10131 (CK) -> AS45193 (FM)
- measurement: 216154556
- reason: no probe data returned
- detail: Atlas returned zero probe results for this measurement -- most likely a transient results-fetch race (status went terminal moments before results were indexed) rather than a real network outcome; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-09-27T15:20:12.803614+00:00
- resolved: 2026-10-03 -- not a fetch race (the detail above is wrong): all seven 2026-09-27 CK measurements (216153502, 216153814, 216153954, 216154414, 216154556, 216154870, 216155432) are Failed with zero results -- the source probe, 22761 (Telecom Aitutaki, AS10131, CK's only working probe), was assigned and didn't run. It has been Disconnected since 2026-10-01T08:27Z, so CK has no live vantage; tracked as one probe issue, not per corridor.

## AS10131 (CK) -> AS45879 (WF)
- measurement: 216154870
- reason: no probe data returned
- detail: Atlas returned zero probe results for this measurement -- most likely a transient results-fetch race (status went terminal moments before results were indexed) rather than a real network outcome; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-09-27T15:23:34.901267+00:00
- resolved: 2026-10-03 -- not a fetch race (the detail above is wrong): all seven 2026-09-27 CK measurements (216153502, 216153814, 216153954, 216154414, 216154556, 216154870, 216155432) are Failed with zero results -- the source probe, 22761 (Telecom Aitutaki, AS10131, CK's only working probe), was assigned and didn't run. It has been Disconnected since 2026-10-01T08:27Z, so CK has no live vantage; tracked as one probe issue, not per corridor.

## AS10131 (CK) -> AS140504 (NR)
- measurement: 216155432
- reason: no probe data returned
- detail: Atlas returned zero probe results for this measurement -- most likely a transient results-fetch race (status went terminal moments before results were indexed) rather than a real network outcome; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-09-27T15:26:56.500873+00:00
- resolved: 2026-10-03 -- not a fetch race (the detail above is wrong): all seven 2026-09-27 CK measurements (216153502, 216153814, 216153954, 216154414, 216154556, 216154870, 216155432) are Failed with zero results -- the source probe, 22761 (Telecom Aitutaki, AS10131, CK's only working probe), was assigned and didn't run. It has been Disconnected since 2026-10-01T08:27Z, so CK has no live vantage; tracked as one probe issue, not per corridor.

## AS24390 (FJ) -> AS9751 (AS)
- measurement: 216155552
- reason: all probes proxy-corrupted
- detail: every probe in this measurement resolved a known corporate proxy/VPN ASN as its first hop (probe 60575 via Zscaler) -- this source's own probe currently can't produce a real path; needs a human look (a different source, or wait for the proxy egress to genuinely change), not a target-IP retry
- flagged: 2026-09-27T15:28:10.838773+00:00
- resolved: 2026-10-05 -- stale: fired from 60575 while it egressed via Zscaler. Two later changes stop it recurring: corridor tests now pin to the source ASN's own probes (fec96da, so AS24390 fires from 11691), and 60575 now egresses natively via Telecom Fiji (218747738, ee94576).

## AS24390 (FJ) -> AS24439 (MH)
- measurement: 216155814
- reason: all probes proxy-corrupted
- detail: every probe in this measurement resolved a known corporate proxy/VPN ASN as its first hop (probe 60575 via Zscaler) -- this source's own probe currently can't produce a real path; needs a human look (a different source, or wait for the proxy egress to genuinely change), not a target-IP retry
- flagged: 2026-09-27T15:33:10.817887+00:00
- resolved: 2026-10-05 -- stale: fired from 60575 while it egressed via Zscaler. Two later changes stop it recurring: corridor tests now pin to the source ASN's own probes (fec96da, so AS24390 fires from 11691), and 60575 now egresses natively via Telecom Fiji (218747738, ee94576).

## AS17456 (GU) -> AS9246 (GU)
- measurement: 216991839
- reason: local IXP crossing with implausibly high latency
- detail: probe 64953: hop 6 crosses MARIIX (in-fishbowl) at 10.636ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-09-29T15:06:59.886272+00:00
- resolved: 2026-10-05 -- ordinary (owner): the hop after MARIIX answers faster than the MARIIX hop itself (10.6ms vs 10.3ms at 114.142.196.90), so the extra time is the exchange router generating its ICMP reply, not path. Probe 64953 already sits 9-13ms out before any IXP (202.128.2.86 / 202.128.28.32). The 10ms check uses absolute RTT; queued to compare against the later hops' minimum.

## AS45345/AS56089 (NC) -> AS131995 (NC)
- measurement: 217486797, 217486796
- reason: suspected offshore hosting
- detail: AS131995 (XLPM, registered NC) originates one prefix, 103.29.155.0/24 (tested 103.29.155.1, rDNS unknown-host.xlnet.au). All 4 NC probes go Noumea -> Equinix Sydney (~23ms) -> Superloop AS38195 Sydney, then Brisbane (bdr03-ipt-20wharfs-bne) -> 202.60.93.189 eth49-1.core01.br1.as9280.net.au (~38ms), then no replies. RIS: sole neighbour is AS9280 Servers Australia (AU, 350 obs locally, 273 live); every collector path ends "... 38195|58511 9280 131995". The filed confirmed_detour (finding #263, NC -> NC via Sydney) is most likely an Australia-hosted prefix, not a domestic peering failure -- same shape as AS23959 (resolved 2026-09-24). RIS disagreement ("0") is the last *resolved* ASN (AS38195) vs the target: AS9280's link address is unannounced so the chain stops one AS short.
- flagged: 2026-10-01
- resolved: 2026-10-01 -- AS131995 excluded as offshore-hosted (sole upstream AS9280 Servers Australia, space served from Brisbane); see discovery/excluded_asns.py. Finding #263 removed.

## Probe 23039 (GU, AS9246) -- metadata changed
- reason: probe watch (atlas/probe_watch.py)
- detail: asn_v4 17456 -> 9246; egress trace: AS17456 (measurement 217919756)
- action: owner review -- check the path before trusting this probe's next results, or changing any exclusion
- flagged: 2026-10-01T15:00:56.787975+00:00
- resolved: 2026-10-05 -- dual-homed, both local (owner): 23039 NATs to 114.142.217.210 (GTA) but egresses by destination -- 1.1.1.1 via AS17456 PDS -> AS3605 -> JPNAP Tokyo (217919756); OneQode via GTA throughout (218411496, #272, correctly labelled). No proxy. Three corroborations since 10-01 whose chains start at AS17456 were relabelled vantage 9246 -> 17456 (217920667, 217921610, 217929821; DB backed up first). Queued: take the vantage ASN from each trace's first public hop.

## Probe 61210 (NC, AS141197) -- metadata changed
- reason: probe watch (atlas/probe_watch.py)
- detail: asn_v4 56089 -> 141197; egress trace: AS141197 (measurement 217919756)
- action: owner review -- check the path before trusting this probe's next results, or changing any exclusion
- flagged: 2026-10-01T15:00:56.787975+00:00
- resolved: 2026-10-02 -- host-confirmed: SPC (Usaia Tawakevou, PacNOG thread, 2026-10-01) re-homed the Noumea probe onto SPC's own ASN. The path is native, not tunnelled: the 2026-10-01 nightly traces (e.g. measurements 217920678, 217925248) go 202.0.159.1 (AS141197) -> OPT AS18200 / CANL AS17480 within ~1-2ms. The probe stays in use as an NC vantage. Note: SPC's Fiji probe 60575 (AS141695) still egresses via Zscaler (measurement 218054280, 2026-10-02: 147.161.214.89 AS53813 at 37.7ms, handing to Cloudflare at Equinix Sydney), so AS141695 stays excluded.

## Probe 62046 (FM, AS139759) -- metadata changed
- reason: probe watch (atlas/probe_watch.py)
- detail: asn_v4 14593 -> 139759; egress trace: AS139759 (measurement 218274746, 218276868)
- action: owner review -- check the path before trusting this probe's next results, or changing any exclusion
- flagged: 2026-10-02T15:00:39.173272+00:00
- resolved: 2026-10-03 -- the expected fix: Atlas now reports the ASN the probe actually measures through (Starlink AS14593 -> AS139759), and the egress trace shows AS139759 first (measurements 218274746/218276868). auto_classify's hard-coded ASN override for 62046 is now redundant but harmless.

## AS7131 (MP) -> AS38198 (TO)
- measurement: 218277100
- reason: no probe data returned
- detail: Atlas returned zero probe results (status=Scheduled) -- the source probe never ran this measurement, so check that probe (it can read as Connected in the probe list while still not taking measurements) before re-firing from it; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-10-02T15:10:28.250480+00:00
- resolved: 2026-10-03 -- not a dead probe: 65653 ran at ~15:07Z and its result arrived after the 180s wait (measurement now Stopped, 1 participant). Path Saipan -> PTI (8.3.127.1, 103.57.234.1) -> HE Tokyo (core2.tyo1.he.net, 37.8ms), dark after. Re-test of finding #10; the corridor isn't marked tested, so it retries on its own.

## AS7131 (MP) -> AS24439 (MH)
- measurement: 218708330
- reason: no probe data returned
- detail: Atlas returned zero probe results (status=Scheduled) -- the source probe never ran this measurement, so check that probe (it can read as Connected in the probe list while still not taking measurements) before re-firing from it; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-10-04T15:19:47.907068+00:00
- resolved: 2026-10-05 -- not a dead probe, same as the 10-03 case: 65653's result arrived after the 180s wait (measurement now Stopped, 1 participant, checked against Atlas in an interactive session). Path Saipan -> PTI (8.3.127.1) -> HE (184.104.208.73, 46.9ms; 184.105.65.96, 156.9ms) -> 207.45.208.18 (159.3ms) -> 64.86.252.141 / 180.87.60.178 (~249ms), dark after. The corridor is already in tested_pairs from an earlier run.

## AS38198 (TO) -> AS140504 (NR)
- measurement: 218712900
- reason: unattended daily check -- candidate_peering finding #273 (direct AS38198 -> AS140504) rests on hidden hops, not a visible adjacency
- detail: probe 1018023 (Digicel Tonga) reaches 202.43.14.173 (AS38198) at hop 4, 9.8ms, reply TTL 252, then the target 103.49.173.1 answers at hop 5 at 339.7ms (+330ms in one hop). Reply TTL 238, and Atlas reports ittl=240 on all three target replies: the probe sent that packet with TTL 5, so something past hop 4 reset the forward TTL (tunnel ingress or similar), leaving about 15 routers out of view each way. RIS (RIPEstat asn-neighbours, 2026-10-04) shows one neighbour for AS140504: AS3605 (Guam), power 418, 1646 v4 peers. Last night's TV -> NR trace (218707166, finding #161) goes the same way: HE -> JPIX Tokyo -> 202.128.5.115 (AS3605, 321.7ms), then dark. Confidence: high that the trace doesn't show a direct adjacency; moderate on what's hidden (probably Digicel/Telstra backbone to AS3605 Guam, then the Nauru link).
- proposed correction: don't treat #273 as a TO<->NR peering; reclassify it as a detour through AS3605 Guam, or drop it until a trace shows the middle. Consider whether candidate_peering should be held back when the target's ittl shows the TTL was reset.
- flagged: 2026-10-04T21:45:00+00:00
- resolved: 2026-10-05 -- held, not reclassified (owner): #273 stays a candidate_peering row in findings.db and the export, but `discovery/quarantined_asns.HELD_FINDINGS` keeps it out of the report tallies, the map and reverification until latency and other evidence support it. A Guam detour wasn't recorded: the Guam leg is inferred, not seen, and Guam is in scope, not an external hub. AS38198 and AS140504 stay in scope; their other findings are unaffected.


## Probe 6923 (GU, AS140627) -- deferred regression trace
- reason: probe watch (atlas/probe_watch.py)
- detail: egress trace after an earlier metadata change: AS140627 (measurement 219060211)
- action: owner review -- check the path before trusting this probe's next results, or changing any exclusion
- flagged: 2026-10-05T15:00:58.678262+00:00

## Probe 23039 (GU, AS17456) -- metadata changed
- reason: probe watch (atlas/probe_watch.py)
- detail: asn_v4 9246 -> 17456; egress trace: AS17456 (measurement 219585601)
- action: owner review -- check the path before trusting this probe's next results, or changing any exclusion
- flagged: 2026-10-06T15:00:38.914706+00:00
- resolved: 2026-10-07 -- the probe's default uplink moved to PDS; path unchanged, still local (owner asked to resolve). Atlas derives asn_v4 from the probe's source address, now 199.127.237.2 (199.127.236.0/22, AS17456) where 10-05 had 114.142.217.210 (AS9246). Egress trace 219585601 to 1.1.1.1 matches 217919756 hop for hop: 199.127.237.1 0.5ms -> 103.212.24.73/.90 (AS17456) 0.9ms -> 202.128.10.206 (AS3605) 1.3ms -> JPNAP Tokyo 210.173.176.127 31.0ms -> Cloudflare 30.4ms. No proxy. asn_v4 now matches the measured first hop, so no PROBE_ASN_OVERRIDES entry; Sunday's registry rebuild moves 23039 from AS9246 (its only probe) to AS17456. Destination-based GTA egress (seen 10-03 toward OneQode, #272) not re-checked; corridor results take the vantage ASN from each probe's own chain (fec96da), so a GTA-routed trace stays labelled correctly.
