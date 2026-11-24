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
- resolved: 2026-10-07 -- first trace of a newly tracked probe, not a change at the site (owner asked to resolve). The "earlier metadata change" was `tracked False -> True` on 2026-10-05 (6923 added by PROBE_ECONOMY_OVERRIDES, d2706e6) while the anchor was Disconnected, so the trace waited for it to reconnect. 219060211 (source 103.151.64.31, AS140627): gateway 103.151.64.30 0.3ms -> 103.151.64.7 `gu-gnc-rt1-----Vlan780.au-gssyd-rt1.oneqode.net` 70.4ms -> EdgeIX Sydney 202.77.88.76 71.1ms -> Cloudflare 1.1.1.1 70.9ms. Native OneQode path, no proxy; the anchor is physically in Guam (Guam Exchange probe 7385 reached it at 0.66ms, 218411496). The ROV valid trace 219592602 (2026-10-07) repeats the same Sydney exit. OneQode carries this traffic Guam -> Sydney on its own backbone; that's ordinary for an AU-registered carrier and not a corridor result. The probe stays a GU vantage for AS140627.

## Probe 23039 (GU, AS17456) -- metadata changed
- reason: probe watch (atlas/probe_watch.py)
- detail: asn_v4 9246 -> 17456; egress trace: AS17456 (measurement 219585601)
- action: owner review -- check the path before trusting this probe's next results, or changing any exclusion
- flagged: 2026-10-06T15:00:38.914706+00:00
- resolved: 2026-10-07 -- the probe's default uplink moved to PDS; path unchanged, still local (owner asked to resolve). Atlas derives asn_v4 from the probe's source address, now 199.127.237.2 (199.127.236.0/22, AS17456) where 10-05 had 114.142.217.210 (AS9246). Egress trace 219585601 to 1.1.1.1 matches 217919756 hop for hop: 199.127.237.1 0.5ms -> 103.212.24.73/.90 (AS17456) 0.9ms -> 202.128.10.206 (AS3605) 1.3ms -> JPNAP Tokyo 210.173.176.127 31.0ms -> Cloudflare 30.4ms. No proxy. asn_v4 now matches the measured first hop, so no PROBE_ASN_OVERRIDES entry; Sunday's registry rebuild moves 23039 from AS9246 (its only probe) to AS17456. Destination-based GTA egress (seen 10-03 toward OneQode, #272) not re-checked; corridor results take the vantage ASN from each probe's own chain (fec96da), so a GTA-routed trace stays labelled correctly.

## AS140627 (OneQode, no economy) -> AS9241/AS45349 (FJ), AS139609/AS142279 (SB) -- from new NR probe 1018134
- measurement: 220501321, 220508737, 220522848, 220526456
- reason: unattended daily check -- four new candidate_peering findings (#286, #288, #291, #294) credit OneQode (AU-registered, source_cc "??") with a direct adjacency to FJ/SB targets, but each rests on hidden hops after OneQode's Sydney router
- detail: all four from probe 1018134 (CenpacNet AS55722, Nauru, first connected 2026-10-08; Atlas geometry 166.91E 0.54S, so the NR vantage label is right). Every trace goes 203.98.224.7 (0.4-0.7ms) -> 202.123.138.210 / 103.112.0.226 (AS7131, ~36ms) -> 103.151.64.7 (OneQode, ~106ms) -> target at 236-254ms. 103.151.64.7 is the Sydney-side router seen from Guam probe 6923 at 70ms right before EdgeIX Sydney (219060211, see the probe 6923 entry above), so these NR -> FJ/SB paths go Nauru -> Guam -> Sydney. After it: 220501321 (-> FINTEL) hops 6-9 dark, then the known 202.170.33.17/.11 loop at 240ms; 220508737 (-> TFL 202.137.176.1) hops 6-9 dark, target at 253.5ms; 220526456 (-> Solitech 103.166.98.1) hop 6 dark, target at 236.1ms; 220522848 (-> SISCC 103.142.98.1) target at hop 6 directly, 235.9ms, but its reply TTL is 244 (about 11 hops back) against 60 for the OneQode hop (about 4 back), so at least ~6 routers are out of view. Sydney -> Suva/Honiara on cable should add tens of ms, not +130-147ms. RIPEstat asn-neighbours (2026-10-08): AS140627 is not a neighbour of AS9241, AS45349, AS139609 or AS142279; AS142279's sole neighbour is AS139609 (SISCC, domestic), so not offshore hosting. These are the first four "??"-source rows in findings_export.jsonl. The night's eight confirmed_local_transit rows (#180, #249, #282, #287, #289, #290, #292, #293) all have RIS agreeing (329-1066 observations); the other candidate_peering corroborations (#2, #15, #17, #19) are older findings with RIS disagreeing and weren't re-examined here. Confidence: high that no OneQode -> target adjacency is visible; high that the path exits via Sydney; low on what the hidden middle is.
- proposed correction: hold #286/#288/#291/#294 out of the tallies (as #273 was, via HELD_FINDINGS) or drop them. Decide how an NR -> FJ/SB corridor that transits Sydney with no IXP crossing should be recorded (the detour check didn't fire because no IX was crossed). Consider not filing candidate_peering when the upstream ASN has no economy ("??") or when dark hops / a TTL jump sit between the upstream and the target.
- flagged: 2026-10-08T21:32:49Z
- resolved: 2026-10-09 -- held, not dropped (owner): all four added to `discovery/quarantined_asns.HELD_FINDINGS`, so they stay in findings.db and the export but leave the report tallies, the map and reverification until a trace shows the adjacency with no hidden hops, or RIS lists it. Report pathways 259 -> 255. No classifier guard added for "??" upstreams or TTL jumps yet. Owner's read: +130-147ms past OneQode's Sydney router is an around-the-world or scenic Pacific-rim leg in the hidden hops, not a OneQode handoff; recorded in each hold's note.

## known_anomalies.py: 202.170.33.0/24 loop credited to AS174 (Cogent), but it's FINTEL (AS9241) space
- measurement: 220501321, 219062598
- reason: unattended daily check -- the known-loop registry entry's text and asn don't match the address owner, and the wrong text is on the public report
- detail: src/pacific_peering/analysis/known_anomalies.py:76-84 describes the .11/.17 alternating loop as "inside AS174's (Cogent) own network" with asn=174. RIPEstat network-info (2026-10-08T21:31Z) for 202.170.33.17: prefix 202.170.32.0/20, origin AS9241. task_plan.md (lines ~1980, ~2164) and CHANGELOG.md (~1448, ~1697) already say both addresses are AS9241 itself. The loop itself is genuine (220501321: .17/.11 alternate from hop 10 to hop 32, nothing new after), so the has_loop flag on #286 is right; only the attribution is wrong. The Cogent wording shows on outputs/reports/report.txt/report.html for 220501321 (NR) and 219062598 (FJ).
- proposed correction: change the entry to asn=9241 and reword it as FINTEL's own edge; regenerate reports so the loop notes on both findings read correctly.
- flagged: 2026-10-08T21:32:49Z
- resolved: 2026-10-09 -- entry changed to asn=9241 and reworded as FINTEL's own edge; the stored loop notes on corroborations for #21, #275 and #286 rewritten to the new text; export and reports regenerated, no Cogent wording left. Owner: Cogent has no Pacific presence, so a Cogent attribution on a Pacific edge was never plausible.

## Probe 22761 (CK, AS10131) back to Connected -- CK corridors still untested
- measurement: 216153502, 216153814, 216153954, 216154414, 216154556, 216154870, 216155432 (the 2026-09-27 Failed set)
- reason: unattended daily check -- CK's only usable probe reconnected 2026-10-08, but nothing has re-run the seven CK corridors that failed while it was down, and the probe has read Connected while failing to run measurements before
- detail: probe_watch (2026-10-09T15:00Z nightly) logged "probe 22761: status Disconnected -> Connected" but traced no egress (status-only change); that night's batch tested 0 corridors. Atlas probe API (2026-10-10T21:3xZ): status Connected since 2026-10-08T21:26:09Z, last_connected ~2026-10-10T21:31Z, asn_v4 10131, prefix 202.65.48.0/20, geometry 159.79W 18.87S (Aitutaki, so the CK label is right), tags IPv4 Works / IPv4 RFC1918. The weekly refresh (2026-10-10T15:02Z) regenerated the backlog at 0 candidates ("0 new-probe" -- 22761 isn't new), so the 2026-09-27 corridors CK -> AS9751 (AS), AS17828 (PG), AS24390 (FJ), AS24439 (MH), AS45193 (FM), AS45879 (WF), AS140504 (NR) aren't queued. probe_gaps.txt now lists CK as FRAGILE (1 connected) instead of zero. task_plan.md (~3263-3265, 2026-09-28/29) notes 22761 "still reads Connected while failing to start measurements", so Connected alone doesn't show it works. Tonight's reverify ration (64 finding IDs, enqueued 2026-10-10T15:02Z) may include some of the 14 CK-vantage corroborations; not checked, since the export carries no finding IDs and this check doesn't query findings.db.
- proposed correction: none to the data. Owner's call whether to fire a single regression trace from 22761 first (per the regression-test-on-probe-change rule) and, if it runs, re-queue the seven CK corridors; and whether probe_watch should trace egress on a Disconnected -> Connected change for a sole-probe economy.
- flagged: 2026-10-10T21:40:00Z
- resolved: 2026-10-12 -- probe 22761 runs measurements again (owner asked to resolve). The 2026-10-11T15:00Z nightly batch's reverify ration re-ran all seven CK corridors from 22761: AS45193 (FM) confirmed_local_transit (221440229) and AS140504 (NR) confirmed_detour (221440864) came back with real hop data; AS9751, AS17828, AS24390, AS24439 and AS45879 were inconclusive with no real signal after 1-2 attempts (221439245, 221439382, 221439545, 221439948, 221440468). No separate regression trace needed, since two real results show the probe isn't stuck in the Connected-but-failing state. probe_watch egress-tracing on reconnect for sole-probe economies not added.

## AS9471 (PF) -> AS45879 (WF)
- measurement: 221440472
- reason: unrecognized routing loop
- detail: probe 30712: loop involving address 117.20.32.11, not in known_anomalies.py
- flagged: 2026-10-11T15:22:26.215108+00:00
- resolved: 2026-10-12 -- added 117.20.32.0/24 (AS45879, Orange Wallis & Futuna) to known_anomalies.py (owner). Raw hops: all three probes (30712, 52614, 53098) cross Opentransit (AS5511), then .11 answers every other hop to TTL 32, constant reply TTL, target 117.20.34.1 never reached -- a loop at the destination's own edge, same pattern as FINTEL.

## AS9471 (PF) -> AS45879 (WF)
- measurement: 221440472
- reason: unrecognized routing loop
- detail: probe 53098: loop involving address 117.20.32.11, not in known_anomalies.py
- flagged: 2026-10-11T15:22:26.215108+00:00
- resolved: 2026-10-12 -- added 117.20.32.0/24 (AS45879, Orange Wallis & Futuna) to known_anomalies.py (owner). Raw hops: all three probes (30712, 52614, 53098) cross Opentransit (AS5511), then .11 answers every other hop to TTL 32, constant reply TTL, target 117.20.34.1 never reached -- a loop at the destination's own edge, same pattern as FINTEL.

## AS7131 (MP) -> AS38198 (TO)
- measurement: 221439393
- reason: unrecognized routing loop
- detail: probe 65653: loop involving address 202.43.12.5, not in known_anomalies.py
- flagged: 2026-10-11T15:50:27.312831+00:00
- resolved: 2026-10-12 -- added 202.43.12.0/23 (AS38198, Digicel Tonga) to known_anomalies.py (owner). Raw hops: Telstra Global (AS4637) -> Digicel Fiji (AS45355) -> .5 answers at hops 18-19 then dark to the end, target 202.43.12.1 never reached -- a double-answer inside the destination's own network.

## AS3605 (GU) -> AS9751 (AS)
- measurement: 224427229
- reason: router in a hub city with no coordinates
- detail: probe 64953: router hub: hop 13 154.54.43.9 be3669.ccr21.sfo01.atlas.cogentco.com -> San Francisco, 141.218ms (no hub coordinates, unmapped)
- flagged: 2026-10-18T15:07:55.285055+00:00
- resolved: 2026-10-21 -- San Francisco added to EXTERNAL_HUB_LATLON (owner; reverses the 2026-10-12 decision to leave SF unmapped). Re-run offline on the cached trace: hop 13 sfo01 at 141.218ms vs floor 92.95ms from GU -> ok. The reverification of finding #33 (confirmed_detour, Tokyo) had already succeeded in this measurement (corroborations 618 via Portland and 619), so nothing was reclassified; corroboration 619's note keeps its original 'unmapped' text. Future Cogent sfo01 hops classify instead of escalating.


## Probe 62046 (FM, AS14593) -- metadata changed
- reason: probe watch (atlas/probe_watch.py)
- detail: asn_v4 139759 -> 14593; egress trace: AS14593 (Starlink (satellite egress)) -- non-local egress (measurement 225316709)
- action: owner review -- check the path before trusting this probe's next results, or changing any exclusion
- flagged: 2026-10-20T15:00:44.087554+00:00
- resolved: 2026-10-21 -- option (a), guarded (owner): SPC Pohnpei's dual-uplink site now egresses via Starlink. All three traces on 10-20 (egress 225316709; ROV 225320704/225321906) go 10.10.15.50 -> 14.1.90.1 (AS14593, ~54ms) -> Cloudflare, versus AS139759 at <2ms in the 33 cached traces of 09-16..24 and the 10-02 egress check. FSM Telecom itself is fine (FM 7448/50897 traced normally the same night), so this is the site's path choice, not an outage. PROBE_ASN_OVERRIDES (62046 -> AS139759) and rule 0 (NON_LOCAL_FIRST_HOP_ASNS) left as-is: any corridor trace starting in AS14593 is dropped, so 62046 contributes nothing to FM corridors while on Starlink and resumes automatically if the site switches back. No findings affected; SPC not contacted.
## AS141695 (FJ) -> AS154229 (FJ)
- measurement: 227408126
- reason: unrecognized routing loop
- detail: probe 60575: loop involving address 202.62.124.42, not in known_anomalies.py
- flagged: 2026-10-25T15:13:16.786786+00:00
- resolved: 2026-10-27 -- not a loop: TFL's (AS4638) last link before FNPF answering again at a filtered edge. Fleet trace to the alternate address 203.55.68.254 (measurement 228090126) gave the same `.41 .42 * .42` tail from 17 of the 23 probes that reached .42, from 12 economies, with no router ever after .42. 202.62.124.40/30 added to known_anomalies.py at the owner's direction, with a regression test frozen from 227408126.


## AS9246 (GU) -- possible offshore-hosted address space
- reason: offshore-hosting check (atlas/offshore_check.py)
- detail: 114.142.196.155: probe 1012863 0.37ms < 25.1ms minimum (measurement 227417811)
- action: owner review; if confirmed, add to discovery/excluded_asns.py (offshore_hosted)
- flagged: 2026-10-25T15:42:08.178346+00:00
- resolved: 2026-10-27 -- operator router, not hosted space; AS9246 stays in scope, no exclusion. 114.142.196.155 is 114-142-196-155.core.static.teleguam.net in GTA's core block (.145-.170 all core.static). It answers at Tokyo distance from Japan (Atlas JP 0.37ms on AS141995/AS17511; Brisbane trace reaches it at 112ms, the same as the Tokyo hop before it, while .164 is +28ms on, i.e. Guam; Radar: .155 JP, .164/.166 GU). From inside the region it behaves as a Guam hop: in all 140 appearances across 52 of our measurements (FM probes 7448/50897/62046, GU probe 23039) its RTT equals the previous hop's (median step-in -0.2..-0.4ms, step-out +1.2ms), so it answers at both ends of the Tokyo link (shared loopback or MPLS behaviour) and has distorted no classification. Corridor tests target 114.142.192.1, never .155, so no target exclusion is needed. The offshore check will not re-escalate it (already offshore in its history).

## AS132462 (SB) -- possible offshore-hosted address space
- reason: offshore-hosting check (atlas/offshore_check.py)
- detail: 103.21.248.1: probe 1017873 2.51ms < 61.1ms minimum (measurement 227412138)
- action: owner review; if confirmed, add to discovery/excluded_asns.py (offshore_hosted)
- flagged: 2026-10-25T15:42:08.178346+00:00

## AS152655 (PG) -- possible offshore-hosted address space
- reason: offshore-hosting check (atlas/offshore_check.py)
- detail: 14.192.75.1: probe 1013222 11.19ms < 27.3ms minimum (measurement 227413970)
- action: owner review; if confirmed, add to discovery/excluded_asns.py (offshore_hosted)
- flagged: 2026-10-25T15:42:08.178346+00:00
- resolved: 2026-10-27 -- confirmed offshore: sole prefix 14.192.75.0/24 terminates in AU behind SES (AS12684 only upstream; 24 live hosts at 21-22ms from Brisbane, traceroute Megaport IX -> SES 148.253.23.174 -> target, Radar geolocates AU). Excluded as offshore_hosted in discovery/excluded_asns.py at the owner's direction; no findings to remove; AS58460 stays in scope.

## AS151398 (PG) -- silent ASN with only foreign hosting-type upstreams
- reason: offshore check upstream screen (atlas/offshore_alternates.py)
- detail: no address answered (including 0 sweep responder(s) retried); RIS upstream(s): AS13335 Cloudflare, Inc. (614 RIS obs)
- action: traceroute the prefix from AU and home-economy probes and judge where it ends; then owner review (acknowledge in SCREEN_ACKNOWLEDGED, quarantine, or exclude)
- flagged: 2026-10-25T15:42:08.178346+00:00
- resolved: 2026-10-27 -- in PNG behind Cloudflare Magic Transit (Kina Bank pattern). Fleet trace to live host 103.215.93.76 (measurement 228089158) went dark at each probe's nearest Cloudflare PoP; TCP 443 on .76/.205 connects in 54ms from Brisbane vs 1.4ms to local Cloudflare, with no Cloudflare certificate or headers, so the origin sits beyond the tunnel. Added to SCREEN_ACKNOWLEDGED at the owner's direction.

## AS132462 (SB) -- WHOIS and routing diverge: Bemobile SI space announced from HK via Bangladesh
- measurement: 227412138
- reason: interactive daily check -- follow-up to the 2026-10-25 offshore flag; registry says Honiara, routing says Hong Kong
- detail: WHOIS (APNIC): AS132462 + 103.21.248.0/22 = Bemobile Solomon Islands Ltd, Point Cruz, Honiara, SB; inetnum/aut-num last-modified 2020-07-15; IRT contact devan.kula@bmobile.com.sb marked "is invalid" by APNIC; no ROA (RPKI unknown). bmobile.com.sb registry expiry 2025-12-03, SERVFAIL; bmobile.com.pg expiry 2025-11-08. Legit route objects: APNIC (origin AS132462, 2014) and RADB proxy object origin AS38456 Speedcast AU (MAINT-AS4637, 2023-11-13).
- detail: routing (RIPEstat): the SISCC-transited (AS139609) /24s were last seen 2026-10-07 (same day ex-Bemobile PNG AS133137 went dark). A /22 aggregate appeared 2026-08-08 via AS140889 Impex Bd Net (BD), switched 2026-09-18 to AS45904 Banglalion WiMAX (BD); all 317 RIS paths now end `3356|3491|... 38008 45904 132462`. AS38008 = Aperture Science Ltd, HK (export: announce AS-APERNET).
- detail: IRR cover: AS-APERNET -> AS-APERNET-CUSTOMER-MACROS -> AS-OPTIONS (ALTDB, MAINT-AS10241, Options & Choices Inc, Cheyenne WY), which lists AS132462, AS45904 and AS152706; last changed by dblaney@ociwyo.com 2026-08-08 -- the day the /22 first appeared.
- detail: latency: 103.21.248.1 answers 2.51ms from probe 1017873 (Alibaba HK) and from 4 networks (AS16276, AS3491, AS45102, AS59253) vs a 61.1ms physical floor to Honiara.
- proposed correction: treat AS132462 as not-in-SB (offshore_hosted exclusion) pending owner decision; report to APNIC (Dave Phelan) as a probable squat/hijack of an abandoned resource -- draft prepared in terry@ieisi.org for owner approval.
- flagged: 2026-10-27T04:57:01Z
- detail: Cloudflare Radar (2026-10-27T05:03Z): IP entity 103.21.248.1 geolocates to Hong Kong (ASN location SB) -- independent of our Atlas latency; pfx2as single origin AS132462, 72/78 peers, RPKI Unknown; no MOAS; only relationship AS45904 (provider and peer, aspa_validated false); no ASPA object; upstream share AS139609 1.00 to 08-06, intermittent to 10-07, 0 since, 'OTHER' 1.00 from 08-08; no hijack or leak events in 52w (origin unchanged, so origin-based detection misses it).
- detail: press search (2026-10-27): no public announcement of a bmobile SI sale, closure or network exit. Latest found: KCH expression-of-interest sale notice (Island Sun, 2020-11-11, no buyer or outcome reported); PNG Telikom/bmobile merger into Telikom Ltd (2021-22, SI unit's fate not reported); SATSOL interconnection with bmobile SI (May 2025); a 2026 travel guide still lists bmobile as one of two SB mobile operators (weak evidence). So the retail operation may still exist -- the routing evidence says its AS132462/103.21.248.0/22 has been taken over, not that the company has gone.
- reported: 2026-10-27T05:00:58Z to APNIC (Dave Phelan, dave.phelan@apnic.net) from terry@ieisi.org, thread 1a17bb8c4babafa5; awaiting reply
- detail: 2026-10-28 23:40Z Dave Phelan acknowledged ("I will have a dig and chat with the services team"); nothing since as of 2026-11-24. RIPEstat 2026-11-23: 103.21.248.0/22 still origin AS132462, 321/322 RIS peers, all 326 bgp-state paths end `38008 45904 132462`; 103.36.150.0/23 RIB paths all via AS6453 (forged path still not winning). Owner decisions on AS132462 exclusion and finding #15 don't depend on APNIC's answer.

## AS152706 (NR) -- intermittent forged-origin path via AS38008/AS45904 for Neotel's 103.36.150.0/23
- reason: interactive daily check -- AS152706 sits in the same ALTDB AS-OPTIONS set as AS132462
- detail: WHOIS is healthy: TNC-NR / Neotel, contacts validated 2026-05-23, route object 2025-01-22, ROA valid (AS152706, maxLength 23). Announced continuously since 2025-01-19; all 317 current RIS RIB paths are via AS6453 Tata (matches our findings #170-174).
- detail: RIPEstat neighbour history adds AS140889 (2026-08-08 to 09-18) and AS45904 (2026-09-18 onward), the same pattern and start date as AS132462. bgp-updates 2026-10-01..26: `38008 45904 152706` announced on 25 of 26 days, seen at 17 RRCs (last 2026-10-26T03:12Z), but never wins best path in the RIB snapshot. Forged origin, so ROV passes it.
- detail: earlier trace FJ -> AS152706 died after AS38008 via AS3491 (task_plan.md: logged inconclusive) -- likely followed the forged path.
- proposed correction: no change to findings (all Neotel corroborations are via AS6453 and RIS-agreed); include in the APNIC report as a live, ROA-covered victim; owner may want to tell Neotel (admin@neotel.nr).
- flagged: 2026-10-27T04:57:01Z
- detail: Cloudflare Radar (2026-10-27T05:03Z): Neotel publishes ASPA (customer AS152706, providers [AS6453] only), so `... 45904 152706` is ASPA-invalid -- the likely reason the forged path churns in updates but never wins in RIB snapshots. Radar lists 6453->152706 provider-customer aspa_validated true and 45904->152706 provider-customer aspa_validated false; pfx2as RPKI Valid, 71/78 peers; no MOAS; no hijack events in 52w.
- reported: 2026-10-27T05:00:58Z to APNIC (Dave Phelan, dave.phelan@apnic.net) from terry@ieisi.org, thread 1a17bb8c4babafa5; awaiting reply
- detail: 2026-10-28 23:40Z Dave Phelan acknowledged ("I will have a dig and chat with the services team"); nothing since as of 2026-11-24. RIPEstat 2026-11-23: 103.21.248.0/22 still origin AS132462, 321/322 RIS peers, all 326 bgp-state paths end `38008 45904 132462`; 103.36.150.0/23 RIB paths all via AS6453 (forged path still not winning). Owner decisions on AS132462 exclusion and finding #15 don't depend on APNIC's answer.

## Finding #15 (PG AS38008 -> SB AS132462) -- AS38008 mislabelled as Telikom PNG
- measurement: 212143004, 212158110, 213459523, 220513022
- reason: interactive daily check -- APNIC RDAP: AS38008 is APERTURE-AS-AP, Aperture Science Ltd, HK (registered 2020-06-15), not "Telikom PNG Satellite Tier 1 AS" (that is AS38009)
- detail: label hand-entered in the 2026-09-16 bulk clear-out (candidate_peering.py:695 and :774). The pair is the HK transit hop of the AS132462 hijack path above, not a PG->SB peering.
- proposed correction: retire #15 (or relabel upstream_cc HK / Aperture) once the owner decides on AS132462.
- flagged: 2026-10-27T04:57:01Z
## AS139759 (FM) -> AS17893 (PW)
- measurement: 228276160
- reason: local IXP crossing with implausibly high latency
- detail: probe 50897: hop 7 crosses Guam IX (in-fishbowl) at 40.186ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-10-27T15:10:27.516298+00:00
- resolved: 2026-11-02 -- ordinary (owner): FM probe reaches Guam at ~21ms (119.252.112.181/.169), then PNCC's Guam IX port 103.142.153.18 at 40.2ms and the PW target at 40.7ms: FM->Guam plus Guam->Palau cable legs. Same remote-port reading as the GU->PW flags (measurement 228736794).

## AS17893 (PW) -> AS3605 (GU)
- measurement: 228276691
- reason: local IXP crossing with implausibly high latency
- detail: probe 7455: hop 3 crosses GU-IX (in-fishbowl) at 19.174ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-10-27T15:13:13.434029+00:00
- resolved: 2026-11-02 -- ordinary (owner): 202.128.12.10 is docomo.gw8.gu-ix.net; 19.2ms from Palau is the Palau->Guam cable leg (PNCC hops before it at 0.2-0.3ms), target 19.9ms.

## AS55885 (NU) -> AS154100 (KI)
- measurement: 228277577
- reason: unrecognized routing loop
- detail: probe 64391: loop involving address 180.87.60.189, not in known_anomalies.py
- flagged: 2026-10-27T15:16:20.038283+00:00
- resolved: 2026-11-02 -- not a loop (owner): 180.87.60.189 (Tata, after Piti 180.87.60.178) answers at hop 10, then again at hop 14 with ICMP host-unreachable (err H) -- the router reporting the target unreachable, as in 213209039. Inconclusive dead end.

## AS17893 (PW) -> AS55722 (NR)
- measurement: 228277632
- reason: local IXP crossing with implausibly high latency
- detail: probe 7455: hop 3 crosses Guam IX (in-fishbowl) at 54.533ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-10-27T15:16:30.067296+00:00
- resolved: 2026-11-19T09:18+10:00 -- ordinary: remote member port, not a detour (temp/escalation_reviews_2026-11-19/review_ixp_latency.md 4.4). 103.142.153.24 is CenPac AS55722's Guam IX port on a router in Nauru (cr1/cr2.core.cenpac.net.nr 0.03ms behind it); Koror-Guam 19ms + Guam-Nauru 35.5ms = 54.5ms. The check now allows both cable legs (fbbb5e8) and clears it.

## AS55885 (NU) -> AS55885 (NU)
- measurement: 228278355
- reason: unrecognized routing loop
- detail: probe 64391: loop involving address 49.156.51.245, not in known_anomalies.py
- flagged: 2026-10-27T15:19:26.473434+00:00
- resolved: 2026-11-02 -- reverify bug, fixed (owner): a retest of #182 (PF AS9471 -> NU AS55885), whose only corroboration came from Niue's own probe, rebuilt as 55885 -> 55885 and traced Niue to itself. The 49.156.51.245/.246 alternation is a real loop inside Telecom Niue toward 49.156.48.1 (probably an unassigned address, like AS55792 on 2026-10-05), but it says nothing about #182. Retests now fire from the finding's upstream (`d7de623`).

## AS45345 (NC) -> AS4638 (FJ)
- measurement: 228735988
- reason: local IXP crossing with implausibly high latency
- detail: probe 33674: hop 8 crosses Fiji-IXP (in-fishbowl) at 40.32ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-10-28T15:03:59.475869+00:00
- detail: 2026-11-02 -- still open: TFL's Fiji-IXP port .30 and core 202.137.178.55 sit ~23ms above FINTEL's 16ms cable hop, while Digicel's .20 on the same forward path adds <1ms. Hypothesis: TFL's return path to OPT-NC space is the long one. Reverse trace 230608167 (SPC 60575 -> Nautile 103.2.187.254, 17.5ms) left via Digicel Fiji (202.129.230.121, AS45355), not TFL, so TFL's return path is untested; it needs a probe on AS4638 (the TFL anchor, or a software probe meanwhile). The new latency rule (`820480f`) still flags it (+22.5-23.0ms).
- detail: 2026-11-24 -- kept as the single open item for this corridor (owner: collapse the duplicates). Measurements so far: 228735988 (10-28), 235633070 (11-10), 242767108 (11-23), each on probes 33674/63050/7018, always hop 8 at Fiji-IXP +22.5-23.3ms over the hop before. Explained by the 2026-11-19 review: forward path is local (FINTEL cable hop, then Fiji-IXP), TFL's return path to OPT-NC space goes via Sydney (anchoring 31472919). The leg-aware check (`fbbb5e8`, 10ms + cable leg in + remote-port allowance, 13.2-14.1ms here) still flags it, so each reverification of this pair adds 3 more entries; resolve them against this one. Remaining action: a probe on AS4638 (TFL anchor, or a software probe meanwhile) to measure the return path directly.

## AS45345 (NC) -> AS4638 (FJ)
- measurement: 228735988
- reason: local IXP crossing with implausibly high latency
- detail: probe 63050: hop 8 crosses Fiji-IXP (in-fishbowl) at 39.95ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-10-28T15:03:59.475869+00:00
- detail: 2026-11-02 -- still open: TFL's Fiji-IXP port .30 and core 202.137.178.55 sit ~23ms above FINTEL's 16ms cable hop, while Digicel's .20 on the same forward path adds <1ms. Hypothesis: TFL's return path to OPT-NC space is the long one. Reverse trace 230608167 (SPC 60575 -> Nautile 103.2.187.254, 17.5ms) left via Digicel Fiji (202.129.230.121, AS45355), not TFL, so TFL's return path is untested; it needs a probe on AS4638 (the TFL anchor, or a software probe meanwhile). The new latency rule (`820480f`) still flags it (+22.5-23.0ms).
- resolved: 2026-11-24 -- duplicate (owner: collapse the duplicates); tracked in the open AS45345 -> AS4638 entry for measurement 228735988 / probe 33674. Cause per the 2026-11-19 review: local forward path, return via Sydney.

## AS45345 (NC) -> AS4638 (FJ)
- measurement: 228735988
- reason: local IXP crossing with implausibly high latency
- detail: probe 7018: hop 8 crosses Fiji-IXP (in-fishbowl) at 39.082ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-10-28T15:03:59.475869+00:00
- detail: 2026-11-02 -- still open: TFL's Fiji-IXP port .30 and core 202.137.178.55 sit ~23ms above FINTEL's 16ms cable hop, while Digicel's .20 on the same forward path adds <1ms. Hypothesis: TFL's return path to OPT-NC space is the long one. Reverse trace 230608167 (SPC 60575 -> Nautile 103.2.187.254, 17.5ms) left via Digicel Fiji (202.129.230.121, AS45355), not TFL, so TFL's return path is untested; it needs a probe on AS4638 (the TFL anchor, or a software probe meanwhile). The new latency rule (`820480f`) still flags it (+22.5-23.0ms).
- resolved: 2026-11-24 -- duplicate (owner: collapse the duplicates); tracked in the open AS45345 -> AS4638 entry for measurement 228735988 / probe 33674. Cause per the 2026-11-19 review: local forward path, return via Sydney.

## AS152735 (GU) -> AS17893 (PW)
- measurement: 228736794
- reason: local IXP crossing with implausibly high latency
- detail: probe 1012513: hop 2 crosses Guam IX (in-fishbowl) at 19.126ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-10-28T15:07:06.213468+00:00
- resolved: 2026-11-02 -- ordinary (owner): 103.142.153.18 is PNCC AS17893's Guam IX port (PeeringDB netixlan). From probes in Guam it answers at ~19ms with PNCC's target 0.2ms behind it, so the router on that port answers from ~19ms away (a remote port, router most likely in Koror); traffic still crosses the Guam IX fabric in-region. The 10ms check uses absolute RTT, which a cross-economy or remote-port crossing always exceeds. Probe 1012513: 19.1ms, then dark.

## AS152735 (GU) -> AS17893 (PW)
- measurement: 228736794
- reason: local IXP crossing with implausibly high latency
- detail: probe 60703: hop 3 crosses Guam IX (in-fishbowl) at 19.629ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-10-28T15:07:06.213468+00:00
- resolved: 2026-11-02 -- ordinary (owner): 103.142.153.18 is PNCC AS17893's Guam IX port (PeeringDB netixlan). From probes in Guam it answers at ~19ms with PNCC's target 0.2ms behind it, so the router on that port answers from ~19ms away (a remote port, router most likely in Koror); traffic still crosses the Guam IX fabric in-region. The 10ms check uses absolute RTT, which a cross-economy or remote-port crossing always exceeds. Probe 60703: 19.6ms, target 19.8ms.

## AS152735 (GU) -> AS17893 (PW)
- measurement: 228736794
- reason: local IXP crossing with implausibly high latency
- detail: probe 7385: hop 2 crosses Guam IX (in-fishbowl) at 19.128ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-10-28T15:07:06.213468+00:00
- resolved: 2026-11-02 -- ordinary (owner): 103.142.153.18 is PNCC AS17893's Guam IX port (PeeringDB netixlan). From probes in Guam it answers at ~19ms with PNCC's target 0.2ms behind it, so the router on that port answers from ~19ms away (a remote port, router most likely in Koror); traffic still crosses the Guam IX fabric in-region. The 10ms check uses absolute RTT, which a cross-economy or remote-port crossing always exceeds. Probe 7385: 19.1ms, target 19.3ms.

## AS45345 (NC) -> AS45355 (FJ)
- measurement: 228736784
- reason: local IXP crossing with implausibly high latency
- detail: probe 33674: hop 8 crosses Fiji-IXP (in-fishbowl) at 16.537ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-10-28T15:07:09.293064+00:00
- resolved: 2026-11-02 -- ordinary (owner): FINTEL 202.170.33.250 at 15.9ms (the NC-Fiji cable), Fiji-IXP .20 at 16.5ms, target 17.9ms.

## AS45345 (NC) -> AS45355 (FJ)
- measurement: 228736784
- reason: local IXP crossing with implausibly high latency
- detail: probe 63050: hop 8 crosses Fiji-IXP (in-fishbowl) at 17.238ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-10-28T15:07:09.293064+00:00
- resolved: 2026-11-02 -- ordinary (owner): FINTEL 202.170.33.250 at 17.1ms (the NC-Fiji cable), Fiji-IXP .20 at 17.2ms, target 18.8ms.

## AS45345 (NC) -> AS45355 (FJ)
- measurement: 228736784
- reason: local IXP crossing with implausibly high latency
- detail: probe 7018: hop 8 crosses Fiji-IXP (in-fishbowl) at 16.45ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-10-28T15:07:09.293064+00:00
- resolved: 2026-11-02 -- ordinary (owner): FINTEL 202.170.33.250 at 16.0ms (the NC-Fiji cable), Fiji-IXP .20 at 16.4ms, target 18.0ms.

## AS3605 (GU) -> AS17993 (WS)
- measurement: 228737735
- reason: router hubs in several cities
- detail: probe 329: router hub: hop 11 154.54.28.189 be9852.ccr22.pdx01.atlas.cogentco.com -> Portland, 116.318ms (floor 90.97ms, ok); probe 64953: router hub: hop 13 154.54.43.13 be3670.ccr22.sfo01.atlas.cogentco.com -> San Francisco, 141.1ms (floor 92.95ms, ok) -- probes leave the region through different cities; needs a human read, not a detour
- flagged: 2026-10-28T15:10:19.176715+00:00
- resolved: 2026-11-02 -- ordinary (owner): both probes go Guam -> IIJ Tokyo -> IIJ Seattle (sea002bb00) -> Cogent pdx01/sfo01 -> pdx02 -> syd01 (250ms) -> Samoa (~300ms). Portland and San Francisco are only where each probe enters Cogent; the paths converge, and the last off-region hub is Sydney, so finding #58's Sydney hub stands (the pre-Sydney leg now runs via Seattle/Portland).

## AS7131 (GU) -> AS17456 (GU)
- measurement: 229249301
- reason: local IXP crossing with implausibly high latency
- detail: probe 60689: hop 8 crosses MARIIX (in-fishbowl) at 10.067ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-10-29T15:07:32.078050+00:00
- resolved: 2026-11-02 -- ordinary (owner): MARIIX hop 103.115.193.13 (pds.ix.mariix.net) at 10.07ms vs the 10.0ms limit; probe 60689 already sits 9-11ms out before any IXP (hops 3-6), as on 2026-10-05.

## AS7131 (GU) -> AS395400 (GU)
- measurement: 229251973
- reason: unrecognized routing loop
- detail: probe 60689: loop involving address 168.123.136.7, not in known_anomalies.py
- flagged: 2026-10-29T15:17:13.068192+00:00
- resolved: 2026-11-02 -- not a loop (owner): 168.123.136.7 (the hop after MARIIX .5) repeats at hops 8-9 at the tail with no new router after it, then dark -- the 216154286 pattern. Inconclusive dead end.

## AS9249 (VU) -> AS17993 (WS) -- parked measurement retried 3 nights against a Failed Atlas measurement
- measurement: 228276817
- reason: unattended daily check -- the parked-measurement retry treated an Atlas-Failed measurement as a classify error and spent all 3 attempts on it
- detail: Atlas reports 228276817 (probe 64783, National University of Vanuatu, to 110.5.112.1) as status Failed (id 7), created 2026-10-27T15:10:29Z, stopped 2026-10-27T15:16:00Z, participant_count 1, results endpoint returns []. No data/atlas/raw or data/atlas/parsed file was ever written for it, so the 10-28, 10-29 and 10-30 nightly runs each raised `[Errno 2] No such file or directory: 'data/atlas/parsed/228276817.json'` (with traceback) and re-parked it; the 10-30 run dropped it after attempt 3. The corridor is left untested and will be fired fresh. Probe 64783 is Connected again since 2026-10-29T03:43:59Z, so the failure was most likely a probe outage, not a corridor property.
- proposed correction: when collecting a parked measurement, check its Atlas status first; on Failed/Stopped with zero results, drop it at once (or record it as no-data) instead of re-parking it and logging a traceback for three nights. Code change for the owner to decide; no data change needed.
- flagged: 2026-10-29T21:31:32Z
- resolved: 2026-11-02 -- fixed (owner): a parked measurement Atlas reports Failed or "No suitable probes" with no results is now dropped at collection and its retest stamped lost (`7bbce26`).


## AS9249 (VU) -- 103.16.15.0/24 leased or foreign-registered space
- reason: leasing-marker check (discovery/leasing_check.py)
- detail: registered_abroad: RIR record country AU, not VU
- action: sweep the prefix for live hosts and ping them from AU and home-economy probes; then owner review (acknowledge, exclude the prefix as a target, or exclude the ASN)
- flagged: 2026-10-31T15:04:13.201328+00:00
- resolved: 2026-11-02 -- recorded, no action (owner): not leased or foreign-registered. 103.16.15.0/24 was assigned (VU, 2013-01-30) to SPIM (inetnum SPIM-AP, org ORG-SA1-AP, BP 5036 Vila Mall / Khumul Highway, Port Vila; IRT-SPIM-VU), which also held AS132548 (SPIM-AS-AP, 2013-01-08; opaque-id A9144A25). APNIC WHOWAS (rdap.apnic.net/history) shows both objects deleted on 2026-04-26 while the ORG-SA1-AP object remains, so the resources were reclaimed, not the organisation removed; the delegated files show it from 2026-04-28, and the /24 is now `reserved`. AS9249 Telecom Vanuatu has originated it since 2013-03-16 (RIPEstat routing-history, ~323 RIS peers, last seen 2026-11-01), so TVL carried this customer's space, and still announces it after the holder's resources were returned. AS132548 never originated anything in RIS. RPKI unknown (no ROA). The check's 'RIR record country AU' came from RDAP returning APNIC's 103/8 parent block once the inetnum was gone; it should report 'no delegation record' instead. Added to leasing_check.ACKNOWLEDGED. Evidence: delegated-apnic(-extended) archives 2013-03-01 .. 2026-11-02.

## AS56017 (PF) -- 38.51.136.0/22 leased or foreign-registered space
- reason: leasing-marker check (discovery/leasing_check.py)
- detail: foreign_registry: held by ARIN; registered_abroad: RIR record country US, not PF
- action: sweep the prefix for live hosts and ping them from AU and home-economy probes; then owner review (acknowledge, exclude the prefix as a target, or exclude the ASN)
- flagged: 2026-10-31T15:04:13.201328+00:00
- resolved: 2026-11-02 -- acknowledged (owner): same Cogent provider-assigned ARIN assignment as the 38.51.136.0/24 and .139.0/24 acknowledged 2026-10-01; ora.pf/geofeed.csv lists 38.51.136.0/22 as PF, Papeete. Added to leasing_check.ACKNOWLEDGED.

## AS56017 (PF) -- 38.51.137.0/24 leased or foreign-registered space
- reason: leasing-marker check (discovery/leasing_check.py)
- detail: foreign_registry: held by ARIN; registered_abroad: RIR record country US, not PF
- action: sweep the prefix for live hosts and ping them from AU and home-economy probes; then owner review (acknowledge, exclude the prefix as a target, or exclude the ASN)
- flagged: 2026-10-31T15:04:13.201328+00:00
- resolved: 2026-11-02 -- acknowledged (owner): same Cogent provider-assigned ARIN assignment as the 38.51.136.0/24 and .139.0/24 acknowledged 2026-10-01; ora.pf/geofeed.csv lists 38.51.136.0/22 as PF, Papeete. Added to leasing_check.ACKNOWLEDGED.

## AS56017 (PF) -- 38.51.138.0/24 leased or foreign-registered space
- reason: leasing-marker check (discovery/leasing_check.py)
- detail: foreign_registry: held by ARIN; registered_abroad: RIR record country US, not PF
- action: sweep the prefix for live hosts and ping them from AU and home-economy probes; then owner review (acknowledge, exclude the prefix as a target, or exclude the ASN)
- flagged: 2026-10-31T15:04:13.201328+00:00
- resolved: 2026-11-02 -- acknowledged (owner): same Cogent provider-assigned ARIN assignment as the 38.51.136.0/24 and .139.0/24 acknowledged 2026-10-01; ora.pf/geofeed.csv lists 38.51.136.0/22 as PF, Papeete. Added to leasing_check.ACKNOWLEDGED.

## AS132831 (TO) -- 103.36.146.0/24 leased or foreign-registered space
- reason: leasing-marker check (discovery/leasing_check.py)
- detail: registered_abroad: RIR record country AU, not TO
- action: sweep the prefix for live hosts and ping them from AU and home-economy probes; then owner review (acknowledge, exclude the prefix as a target, or exclude the ASN)
- flagged: 2026-10-31T15:04:13.201328+00:00
- resolved: 2026-11-02 -- excluded as a target prefix (owner): 103.36.146.0/24 added to atlas.targets.EXCLUDED_TARGET_PREFIXES (Vultr Sydney, offshore on 3 networks, measurement 230614528) and leasing_check.ACKNOWLEDGED; AS132831 stays in scope (103.134.118.0/24 local). The monthly offshore check keeps pinging the block (include_excluded).
- detail: 2026-11-02 sweep (owner asked): nmap from Brisbane (unprivileged, so TCP ping) found 11 hosts up (.20 .30 .35 .40 .50 .60-.63 .100 .101), no rDNS. ICMP is filtered: Atlas pings 230611754-230611792 (18 probes incl. TO 11691/1018023, VU 64783) and local ping all time out.
- detail: TCP: every host answers 443 and 80 in 12.7ms from Brisbane (same as Cloudflare Sydney 104.17.124.41); .200 and a bogon time out. TLS cert CN=au.wantok.cloud (Let's Encrypt), nginx. RIS looking-glass: all paths end `... 20473 132831` -- AS20473 Vultr is the only upstream.
- detail: Atlas TCP/443 traceroute 230614528 to 103.36.146.20: Sydney 1013676 (AS133120) 0.7ms, Melbourne 1018013 (AS31898) 12.5ms, Adelaide 65955 (AS139623) 20.0ms -- three independent networks under the Tonga floor (35.8/42.3/47.4ms) -> offshore by the two-network rule; SPC Tonga 1018023 51.5ms, NUV Vanuatu 64783 50.6ms (cable legs to Sydney). Reading: WanTok's AU-registered 'Cloud IPV4 Mixed' block hosts WanTok cloud servers at Vultr Sydney, originated by AS132831 TokoWireless (TO).
- detail: Impact: no finding involves AS132831; 103.36.146.1 is its third target address (alternate only); its main 103.134.118.0/24 tested consistent with Tonga 2026-10-25. Proposed (owner's call): add 103.36.146.0/24 to atlas.targets.EXCLUDED_TARGET_PREFIXES (Sydney-hosted, like AS10131's 202.65.33.0/24); AS132831 stays in scope.
## AS7131 (GU) -> AS9246 (GU)
- measurement: 230524076
- reason: unrecognized routing loop
- detail: probe 60689: loop involving address 114.142.196.81, not in known_anomalies.py
- flagged: 2026-11-01T15:04:09.869171+00:00
- resolved: 2026-11-02 -- not a loop (owner): 114.142.196.81 answers at hop 10, then at hop 11 with ICMP host-unreachable (err H) -- the router reporting the target unreachable. Inconclusive dead end.

## AS7131 (GU) -> AS24390 (FJ)
- measurement: 231753360
- reason: unrecognized routing loop
- detail: probe 60689: loop involving address 113.197.15.213, not in known_anomalies.py
- flagged: 2026-11-03T15:13:31.780878+00:00
- detail: 2026-11-04 recheck 232195299 (owner asked), probe 60689 reproduces it: 113.197.15.213 xe-0-0-0.pe1.a.suv.aarnet.net.au (10) -> 202.158.204.194 fastethernet0-0.aarnie.usp.ac.fj (11) -> 113.197.15.136 et-3-0-2.pe1.alxd.nsw.aarnet.net.au (12) -> 113.197.15.213 again (13, 210ms), then dark. A real loop: AARNet Suva PE -> USP border -> back via AARNet Sydney. Probe 62689 and all other traces to 144.120.0.1 stop after .194. Likely reading: 144.120.0.1 unused inside USP, USP default-routes back to AARNet. Query sent 2026-11-04 to noc@aarnet.edu.au, Cc Warrick Mitchell (AARNet) and Edwin Sandys (USP); ticket NOC-150312.
- detail: 2026-11-05 AARNet reply (Fernando de Souza): fij-suva-pe1 routes 144.120.0.0/16 straight to USP (202.158.204.194, MED 100); fij-suva-pe2 prefers pe1 (next hop 113.197.15.192 via ae1.0) over its own USP link 202.158.204.198 (MED 101); their Sydney/Brisbane traces die after .194; 'no looping on the AARNet side'. RIS: AARNet is AS24390's only upstream.
- detail: 2026-11-05 recheck 232787436, probe 60689: .194 at hop 11 (115ms) and again at 14 (208ms) -- loop persists, 3-hop cycle, +93ms each time, Sydney->Suva step (+38ms) matches AARNet's 36ms. Reading: USP hands the packet back (likely to pe2 on .198) and pe2->pe1 runs via Alexandria. Reply sent 2026-11-05 asking AARNet where pe2's ae1.0 goes and asking USP (Edwin) about a discard route -- awaiting answers.
- detail: 2026-11-05 14:12Z AARNet second reply (Fernando): 113.197.15.192 is fij-suva-pe1 itself; pe2's own trace goes 113.197.15.192 -> .194 in under 1ms, so pe2->pe1 stays in Suva (our Alexandria reading was wrong). PTR correction: 113.197.15.136 is et-1-0-2.pe1.mcqp.nsw.aarnet.net.au (Macquarie Park, Sydney), not alxd; AARNet fixed the PTR (dig confirms 2026-11-06). Still Sydney, so the `nsw` geolocation pattern and the PW->FJ finding (212013476) are unaffected. AARNet's reading: USP has no discard route for 144.120.0.0/16, so unused addresses follow USP's default back to AARNet. Open gap: if the returned packet entered pe1/pe2 via inet.0 it would go straight back to .194 in Suva; the observed .194 -> mcqp (Sydney) -> pe1.a.suv cycle implies USP's default (or the AARNet side it lands on) reaches Sydney first. Edwin (USP) has not answered; the discard route is USP's fix.
- detail: 2026-11-06 MPLS read (owner: "AARNet are using MPLS"). In 232195299, hop 12 (113.197.15.136, mcqp) quotes an RFC 4950 label stack: label 830, S=1, TTL=1. Fernando's own Sydney trace shows the same label 830 at ae425.pe1.mcqp, with pe1.a.suv as the next hop. So the packet USP sent back was inside AARNet's Sydney->Suva LSP at Macquarie Park, and the hops between USP and mcqp are hidden by MPLS. On the forward pass the probe enters AARNet at EdgeIX Sydney (202.77.88.26, as7575.syd.edgeix, hop 9) and the next visible hop is pe1.a.suv, so that Sydney->Suva leg is hidden too. This contradicts "any loop would stay within Fiji": wherever USP's default enters AARNet, it is carried to Sydney before coming back to Suva. Open question for AARNet: what FEC/service label 830 is, and which PE, interface and routing instance (inet.0 or a VRF) traffic from USP on .194/.198 enters.
- detail: 2026-11-06 01:13Z follow-up sent on NOC-150312 (tcsweetser -> noc@aarnet.edu.au): label 830 evidence, asked Fernando what label 830 on pe1.mcqp maps to and which PE/interface/routing instance USP's returned traffic enters. Edwin (USP) discard-route question still open. Awaiting answers.
- detail: 2026-11-23 00:06Z AARNet closed NOC-150312 (Fernando): 144.120.0.0/16 routed correctly on their side, no AARNet changes in the period, USP is sending the packets back, fix is a discard (null) route for the /16 on USP's border; follow up with USP directly. Edwin Sandys (USP, Cc'd on the ticket) has not answered. Open for the owner: write to USP directly, add .213/.194 to known_anomalies, or leave open.

## AS3605 (GU) -> AS9751 (AS)
- measurement: 231754538
- reason: router hubs in several cities
- detail: probe 329: router hub: hop 11 154.54.26.165 be9851.ccr21.pdx01.atlas.cogentco.com -> Portland, 121.894ms (floor 90.97ms, ok); probe 64953: router hub: hop 13 154.54.43.13 be3670.ccr22.sfo01.atlas.cogentco.com -> San Francisco, 139.985ms (floor 92.95ms, ok) -- probes leave the region through different cities; needs a human read, not a detour
- flagged: 2026-11-03T15:16:41.134610+00:00
- resolved: 2026-11-06 -- ordinary (owner): both probes go Guam -> 210.173.173.81 (~31-39ms, Japan) -> IIJ, then split inside IIJ: probe 329 via sea002bb00 (118ms) -> Cogent sea08 -> pdx01, probe 64953 via sjc002bb00 (139ms) -> Cogent sfo01 -> pdx01. Both then reach Cogent pdx02 (154.54.164.22 / 154.54.46.162, 122/139ms) and the same Cogent customer address 38.142.108.162 (COGENT-A, 207/235ms), then go dark. Portland and San Francisco are only where each probe enters Cogent. The paths meet at pdx02, and the last off-region hub is Portland, about +85ms before the AS9751 handoff, consistent with an Oregon -> Pago Pago cable leg. Same IIJ/Cogent shape as finding #33 (corroboration 224427229, 2026-10-18: pdx01 / sfo01). #33's detour_hub relabelled Tokyo -> Portland (owner, 2026-11-06): the last off-region hub, same rule as #58 (Sydney) on 2026-11-02.

## AS9471 (PF) -> AS24390 (FJ)
- measurement: 231756512
- reason: router hubs in several cities
- detail: probe 30712: router hub: hop 6 184.104.194.220 be5.core1.lax2.he.net -> Los Angeles, 104.855ms (floor 49.31ms, ok); probe 52614: router hub: hop 10 113.197.15.136 et-3-0-2.pe1.alxd.nsw.aarnet.net.au -> Sydney, 237.607ms (floor 44.23ms, ok); probe 53098: router hub: hop 8 113.197.15.136 et-3-0-2.pe1.alxd.nsw.aarnet.net.au -> Sydney, 233.257ms (floor 44.23ms, ok) -- probes leave the region through different cities; needs a human read, not a detour
- flagged: 2026-11-03T15:19:37.858045+00:00
- resolved: 2026-11-06 -- ordinary (owner): all three probes hand off to AARNet at the same Any2 LA address, 206.72.210.64 (aarnet.as7575.any2ix.coresite.com, 101-104ms). Probes 30712 and 53098 get there via HE hnl1 -> lax2. Probe 52614's HE leg is dark (private 172.18.0.84 at 53ms, then *). After LA all three go 113.197.15.136 (now et-1-0-2.pe1.mcqp.nsw, Sydney, 233-238ms) -> pe1.a.suv (270-274ms) -> USP 202.158.204.194, then dark (the unused 144.120.0.1, see NOC-150312). The "Sydney" hub on 52614/53098 is AARNet's own LA -> Sydney -> Suva backhaul after the handoff, the same path rather than a different exit city. The picker chose Sydney only because those probes' lax2 hop didn't answer. Finding #70 (Any2West, Los Angeles) stands. The LA -> Sydney leg is MPLS-hidden inside AS7575 (no hops between Any2 LA and mcqp).

## AS139759 (FM) -> AS38800 (WS)
- measurement: 233692457
- reason: unrecognized routing loop
- detail: probe 50897: loop involving address 202.87.208.244, not in known_anomalies.py
- flagged: 2026-11-06T15:17:04.619079+00:00
- resolved: 2026-11-19T09:18+10:00 -- transient (temp/escalation_reviews_2026-11-19/review_routing_loops.md 3): a real two-router loop inside Digicel Samoa (AS38800), 202.87.208.244 (gi0-0-0.rgwict01.digicelsamoa.ws) <-> .246, hops 16-32, flat RTT, all three FM probes on one shared path, seen once. It has cleared: 234378989 (11-08), 235636840 (11-10) and 236866386 (11-12) pass .246 -> 182.50.169.217 and reach the target. Not added to known_anomalies.py, so a recurrence escalates again.

## AS139759 (FM) -> AS38800 (WS)
- measurement: 233692457
- reason: unrecognized routing loop
- detail: probe 62046: loop involving address 202.87.208.244, not in known_anomalies.py
- flagged: 2026-11-06T15:17:04.619079+00:00
- resolved: 2026-11-19T09:18+10:00 -- transient (temp/escalation_reviews_2026-11-19/review_routing_loops.md 3): a real two-router loop inside Digicel Samoa (AS38800), 202.87.208.244 (gi0-0-0.rgwict01.digicelsamoa.ws) <-> .246, hops 16-32, flat RTT, all three FM probes on one shared path, seen once. It has cleared: 234378989 (11-08), 235636840 (11-10) and 236866386 (11-12) pass .246 -> 182.50.169.217 and reach the target. Not added to known_anomalies.py, so a recurrence escalates again.

## AS139759 (FM) -> AS38800 (WS)
- measurement: 233692457
- reason: unrecognized routing loop
- detail: probe 7448: loop involving address 202.87.208.244, not in known_anomalies.py
- flagged: 2026-11-06T15:17:04.619079+00:00
- resolved: 2026-11-19T09:18+10:00 -- transient (temp/escalation_reviews_2026-11-19/review_routing_loops.md 3): a real two-router loop inside Digicel Samoa (AS38800), 202.87.208.244 (gi0-0-0.rgwict01.digicelsamoa.ws) <-> .246, hops 16-32, flat RTT, all three FM probes on one shared path, seen once. It has cleared: 234378989 (11-08), 235636840 (11-10) and 236866386 (11-12) pass .246 -> 182.50.169.217 and reach the target. Not added to known_anomalies.py, so a recurrence escalates again.

## AS17893 (PW) -> AS3605 (GU)
- measurement: 234920970
- reason: local IXP crossing with implausibly high latency
- detail: probe 7455: hop 3 crosses GU-IX (in-fishbowl) at 19.28ms, 19.0ms more than the hop before it (minimum over it and later hops), above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-09T15:04:19.669371+00:00
- resolved: 2026-11-19T09:18+10:00 -- ordinary: the PW -> GU-IX cable leg (temp/escalation_reviews_2026-11-19/review_ixp_latency.md 4.1). PNCC's Koror border router hands straight to docomo.gw8.gu-ix.net; the 19.0ms step is the Palau-Guam cable (floor 12.9ms), as in 228276691 (resolved 2026-11-02). The check now allows the probe's cable leg (fbbb5e8) and clears it.

## AS139759 (FM) -> AS17893 (PW)
- measurement: 234926407
- reason: local IXP crossing with implausibly high latency
- detail: probe 50897: hop 7 crosses Guam IX (in-fishbowl) at 40.258ms, 18.6ms more than the hop before it (minimum over it and later hops), above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-09T15:10:58.793229+00:00
- resolved: 2026-11-19T09:18+10:00 -- ordinary: FM -> Guam cable leg, then PNCC's remote Guam IX port .18 in Koror (temp/escalation_reviews_2026-11-19/review_ixp_latency.md 4.3; anchoring mesh 86005050 shows the same 19.7 + 18.9ms). Same as 228276160 (resolved 2026-11-02). The check now allows the remote member's cable leg (fbbb5e8) and clears it.

## AS139759 (FM) -> AS17893 (PW)
- measurement: 234926407
- reason: local IXP crossing with implausibly high latency
- detail: probe 62046: hop 8 crosses Guam IX (in-fishbowl) at 40.626ms, 18.1ms more than the hop before it (minimum over it and later hops), above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-09T15:10:58.793229+00:00
- resolved: 2026-11-19T09:18+10:00 -- ordinary: FM -> Guam cable leg, then PNCC's remote Guam IX port .18 in Koror (temp/escalation_reviews_2026-11-19/review_ixp_latency.md 4.3; anchoring mesh 86005050 shows the same 19.7 + 18.9ms). Same as 228276160 (resolved 2026-11-02). The check now allows the remote member's cable leg (fbbb5e8) and clears it.

## AS139759 (FM) -> AS17893 (PW)
- measurement: 234926407
- reason: local IXP crossing with implausibly high latency
- detail: probe 7448: hop 5 crosses Guam IX (in-fishbowl) at 38.649ms, 18.8ms more than the hop before it (minimum over it and later hops), above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-09T15:10:58.793229+00:00
- resolved: 2026-11-19T09:18+10:00 -- ordinary: FM -> Guam cable leg, then PNCC's remote Guam IX port .18 in Koror (temp/escalation_reviews_2026-11-19/review_ixp_latency.md 4.3; anchoring mesh 86005050 shows the same 19.7 + 18.9ms). Same as 228276160 (resolved 2026-11-02). The check now allows the remote member's cable leg (fbbb5e8) and clears it.

## AS17893 (PW) -> AS55722 (NR)
- measurement: 234928910
- reason: local IXP crossing with implausibly high latency
- detail: probe 7455: hop 3 crosses Guam IX (in-fishbowl) at 54.483ms, 54.3ms more than the hop before it (minimum over it and later hops), above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-09T15:13:44.994601+00:00
- resolved: 2026-11-19T09:18+10:00 -- ordinary: remote member port, not a detour (temp/escalation_reviews_2026-11-19/review_ixp_latency.md 4.4). 103.142.153.24 is CenPac AS55722's Guam IX port on a router in Nauru (cr1/cr2.core.cenpac.net.nr 0.03ms behind it); Koror-Guam 19ms + Guam-Nauru 35.5ms = 54.5ms. The check now allows both cable legs (fbbb5e8) and clears it.

## AS45345 (NC) -> AS4638 (FJ)
- measurement: 235633070
- reason: local IXP crossing with implausibly high latency
- detail: probe 33674: hop 8 crosses Fiji-IXP (in-fishbowl) at 39.306ms, 22.5ms more than the hop before it (minimum over it and later hops), above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-10T15:07:14.259301+00:00
- resolved: 2026-11-24 -- duplicate (owner: collapse the duplicates); tracked in the open AS45345 -> AS4638 entry for measurement 228735988 / probe 33674. Cause per the 2026-11-19 review: local forward path, return via Sydney.

## AS45345 (NC) -> AS4638 (FJ)
- measurement: 235633070
- reason: local IXP crossing with implausibly high latency
- detail: probe 63050: hop 8 crosses Fiji-IXP (in-fishbowl) at 40.359ms, 22.6ms more than the hop before it (minimum over it and later hops), above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-10T15:07:14.259301+00:00
- resolved: 2026-11-24 -- duplicate (owner: collapse the duplicates); tracked in the open AS45345 -> AS4638 entry for measurement 228735988 / probe 33674. Cause per the 2026-11-19 review: local forward path, return via Sydney.

## AS45345 (NC) -> AS4638 (FJ)
- measurement: 235633070
- reason: local IXP crossing with implausibly high latency
- detail: probe 7018: hop 8 crosses Fiji-IXP (in-fishbowl) at 39.157ms, 22.5ms more than the hop before it (minimum over it and later hops), above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-10T15:07:14.259301+00:00
- resolved: 2026-11-24 -- duplicate (owner: collapse the duplicates); tracked in the open AS45345 -> AS4638 entry for measurement 228735988 / probe 33674. Cause per the 2026-11-19 review: local forward path, return via Sydney.

## AS152735 (GU) -> AS17893 (PW)
- measurement: 235634536
- reason: local IXP crossing with implausibly high latency
- detail: probe 1012513: hop 2 crosses Guam IX (in-fishbowl) at 18.961ms, 18.9ms more than the hop before it (minimum over it and later hops), above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-10T15:10:09.990299+00:00
- resolved: 2026-11-19T09:18+10:00 -- ordinary: remote member port, not a detour (temp/escalation_reviews_2026-11-19/review_ixp_latency.md 4.2-4.3). 103.142.153.18 is PNCC AS17893's Guam IX port on a router in Koror, reached over an L2 circuit on the Palau-Guam cable; anchoring mesh 86005050 / 79954801 put the whole Guam-Koror round trip (19.1ms) on .18. The check now allows a remote member's cable leg (fbbb5e8) and clears it.

## AS152735 (GU) -> AS17893 (PW)
- measurement: 235634536
- reason: local IXP crossing with implausibly high latency
- detail: probe 60703: hop 3 crosses Guam IX (in-fishbowl) at 19.494ms, 18.9ms more than the hop before it (minimum over it and later hops), above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-10T15:10:09.990299+00:00
- resolved: 2026-11-19T09:18+10:00 -- ordinary: remote member port, not a detour (temp/escalation_reviews_2026-11-19/review_ixp_latency.md 4.2-4.3). 103.142.153.18 is PNCC AS17893's Guam IX port on a router in Koror, reached over an L2 circuit on the Palau-Guam cable; anchoring mesh 86005050 / 79954801 put the whole Guam-Koror round trip (19.1ms) on .18. The check now allows a remote member's cable leg (fbbb5e8) and clears it.

## AS152735 (GU) -> AS17893 (PW)
- measurement: 235634536
- reason: local IXP crossing with implausibly high latency
- detail: probe 7385: hop 2 crosses Guam IX (in-fishbowl) at 19.05ms, 18.7ms more than the hop before it (minimum over it and later hops), above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-10T15:10:09.990299+00:00
- resolved: 2026-11-19T09:18+10:00 -- ordinary: remote member port, not a detour (temp/escalation_reviews_2026-11-19/review_ixp_latency.md 4.2-4.3). 103.142.153.18 is PNCC AS17893's Guam IX port on a router in Koror, reached over an L2 circuit on the Palau-Guam cable; anchoring mesh 86005050 / 79954801 put the whole Guam-Koror round trip (19.1ms) on .18. The check now allows a remote member's cable leg (fbbb5e8) and clears it.

## AS152735 (GU) -> AS17893 (PW)
- measurement: 235635618
- reason: local IXP crossing with implausibly high latency
- detail: probe 1012513: hop 2 crosses Guam IX (in-fishbowl) at 18.98ms, 18.9ms more than the hop before it (minimum over it and later hops), above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-10T15:13:28.582639+00:00
- resolved: 2026-11-19T09:18+10:00 -- ordinary: remote member port, not a detour (temp/escalation_reviews_2026-11-19/review_ixp_latency.md 4.2-4.3). 103.142.153.18 is PNCC AS17893's Guam IX port on a router in Koror, reached over an L2 circuit on the Palau-Guam cable; anchoring mesh 86005050 / 79954801 put the whole Guam-Koror round trip (19.1ms) on .18. The check now allows a remote member's cable leg (fbbb5e8) and clears it. Duplicate run of 235634536 (#54's retest).

## AS152735 (GU) -> AS17893 (PW)
- measurement: 235635618
- reason: local IXP crossing with implausibly high latency
- detail: probe 60703: hop 3 crosses Guam IX (in-fishbowl) at 19.515ms, 18.8ms more than the hop before it (minimum over it and later hops), above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-10T15:13:28.582639+00:00
- resolved: 2026-11-19T09:18+10:00 -- ordinary: remote member port, not a detour (temp/escalation_reviews_2026-11-19/review_ixp_latency.md 4.2-4.3). 103.142.153.18 is PNCC AS17893's Guam IX port on a router in Koror, reached over an L2 circuit on the Palau-Guam cable; anchoring mesh 86005050 / 79954801 put the whole Guam-Koror round trip (19.1ms) on .18. The check now allows a remote member's cable leg (fbbb5e8) and clears it. Duplicate run of 235634536 (#54's retest).

## AS152735 (GU) -> AS17893 (PW)
- measurement: 235635618
- reason: local IXP crossing with implausibly high latency
- detail: probe 7385: hop 2 crosses Guam IX (in-fishbowl) at 18.944ms, 18.8ms more than the hop before it (minimum over it and later hops), above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-10T15:13:28.582639+00:00
- resolved: 2026-11-19T09:18+10:00 -- ordinary: remote member port, not a detour (temp/escalation_reviews_2026-11-19/review_ixp_latency.md 4.2-4.3). 103.142.153.18 is PNCC AS17893's Guam IX port on a router in Koror, reached over an L2 circuit on the Palau-Guam cable; anchoring mesh 86005050 / 79954801 put the whole Guam-Koror round trip (19.1ms) on .18. The check now allows a remote member's cable leg (fbbb5e8) and clears it. Duplicate run of 235634536 (#54's retest).

## AS3605 (GU) -> AS17993 (WS)
- measurement: 235635673
- reason: router hubs in several cities
- detail: probe 329: router hub: hop 11 154.54.28.189 be9852.ccr22.pdx01.atlas.cogentco.com -> Portland, 116.416ms (floor 90.97ms, ok); probe 64953: router hub: hop 13 154.54.43.13 be3670.ccr22.sfo01.atlas.cogentco.com -> San Francisco, 142.284ms (floor 92.95ms, ok) -- probes leave the region through different cities; needs a human read, not a detour
- flagged: 2026-11-10T15:13:42.455940+00:00
- resolved: 2026-11-19T15:05+10:00 -- duplicate of the 228737735 entry the owner resolved on 11-02 (owner ruling 2026-11-19; temp/escalation_reviews_2026-11-19/review_remaining.md 2.2). Portland and San Francisco are only where each probe enters Cogent: probe 329 goes IIJ Seattle -> Cogent sea08 -> pdx01 -> pdx02, probe 64953 IIJ San Jose -> Cogent sfo01 -> pdx01 -> pdx02; both then cross to ccr71.syd01 -> agr51.syd01 (249-273ms) -> 154.18.97.50 -> Vodafone Samoa and reach 110.5.112.1. With current code (last-city rule) find_router_hub returns be3578.agr51.syd01.atlas.cogentco.com, Sydney, on both probes (250.6 and 271.5ms, floor 52.62ms), one city, matching #58's filed hub. No retest needed.


## Probe 62046 (FM, AS139759) -- metadata changed
- reason: probe watch (atlas/probe_watch.py)
- detail: asn_v4 14593 -> 139759; egress trace: AS139759 (measurement 236238083)
- action: owner review -- check the path before trusting this probe's next results, or changing any exclusion
- flagged: 2026-11-11T15:00:57.052535+00:00
- resolved: 2026-11-13 -- back on AS139759 (FSM Telecom) after leaving via Starlink since 2026-10-20; egress trace 236238083 and the 2026-11-12 ROV traces leave via AS139759. Per the owner's 2026-10-21 decision (option a), `PROBE_ASN_OVERRIDES` and rule 0 stay as they are and the probe rejoins FM corridors.

## Probe 64391 (NU, AS14593) -- metadata changed
- reason: probe watch (atlas/probe_watch.py)
- detail: asn_v4 55885 -> 14593; egress trace: AS55885 (measurement 236238083)
- action: owner review -- check the path before trusting this probe's next results, or changing any exclusion
- flagged: 2026-11-11T15:00:57.052535+00:00
- resolved: 2026-11-13 -- real Starlink failover, and the egress line above is wrong: the trace left via Starlink. Atlas connection events show 64391 connecting from Starlink 14.1.76.0/23 on 2026-11-11 06:10-17:35Z, then Telecom Niue again. 236238083 went 49.156.50.254 (the site's own gateway, AS55885) -> 14.1.76.1 (Starlink, 50ms) -> Cloudflare; the probe sits on public Telecom Niue space, so its gateway was read as the egress. No corridor or ROV trace ran from it in the window (92 of 93 cached traces left from 49.156.50.5 via Telecom Niue). Rule 0, probe watch and the feasibility sweep now see past a probe's own public LAN (`auto_classify.egress_guard_asn`).

## Probe 64391 (NU, AS55885) -- metadata changed
- reason: probe watch (atlas/probe_watch.py)
- detail: asn_v4 14593 -> 55885; egress trace: AS55885 (measurement 236862652)
- action: owner review -- check the path before trusting this probe's next results, or changing any exclusion
- flagged: 2026-11-12T15:00:57.602446+00:00
- resolved: 2026-11-13 -- back on Telecom Niue since 2026-11-11T17:35Z (Atlas connection events); this egress trace and the 2026-11-12 ROV traces leave via AS55885. See the entry above.

## Public site -- Workers build failed for 7ab16b9 (nightly batch 2026-11-13)
- reason: unattended daily check -- site deploy failed, so the public site did not get the 2026-11-13 nightly batch
- detail: Workers build 843efabf-8e8e-4594-9bb1-a14137440875 (2026-11-13T15:26:40Z, commit 7ab16b9) ran `python3 src/pacific_peering/reports/site.py` successfully (index.html, 2 charts, 5 text reports) and uploaded 3 assets, then `npx wrangler deploy` (wrangler 4.161.0) failed at 15:27:54Z: "A request to the Cloudflare API (/accounts/.../workers/scripts/pacific-peering/versions) failed. An unknown error has occurred. [code: 10013]". The two builds before it (889db4a, ad7dc2d, 2026-11-12) succeeded. The site answers 200 and still shows generated 2026-11-12T15:35:32Z.
- proposed correction: none in the repo. Code 10013 is a Cloudflare-side unknown error and the build step itself passed, so it looks transient: retry the build in the dashboard, or let the next push rebuild. If the next build fails the same way, look at the wrangler version (npx pulled 4.161.0 unpinned).
- flagged: 2026-11-13T21:30:00+00:00
- resolved: 2026-11-14 -- transient. The next push (5ba306c) rebuilt and deployed at 21:31:32Z with wrangler 4.162.0; the live site now shows generated 2026-11-13T15:26:34Z, the 7ab16b9 batch. No repo change. Pin wrangler only if a 10013 failure recurs.

## AS45411 (PG) -- 210.79.16.0/21 leased or foreign-registered space
- reason: leasing-marker check (discovery/leasing_check.py)
- detail: registered_abroad: RIR record country AU, not PG
- action: sweep the prefix for live hosts and ping them from AU and home-economy probes; then owner review (acknowledge, exclude the prefix as a target, or exclude the ASN)
- flagged: 2026-11-14T15:04:31.867025+00:00
- resolved: 2026-11-19T15:05+10:00 -- acknowledged (owner ruling 2026-11-19; temp/escalation_reviews_2026-11-19/review_remaining.md 2.3). The /21 sits inside 210.79.16.0/20, netname APCSNET, country AU (RIPEstat WHOIS 11-19), which the owner put in atlas.targets.EXCLUDED_TARGET_PREFIXES on 2026-11-09 when adding AS45411 (it spans PNG and Sydney). leasing_check.ACKNOWLEDGED now holds (45411, "210.79.16.0/20"), and an entry covers its more-specifics for the same ASN (0c38ccf), so the other prefixes AS45411 announces inside the /20 will not escalate one by one.

## AS45411 (PG) -- 210.79.16.0/24 leased or foreign-registered space
- reason: leasing-marker check (discovery/leasing_check.py)
- detail: registered_abroad: RIR record country AU, not PG
- action: sweep the prefix for live hosts and ping them from AU and home-economy probes; then owner review (acknowledge, exclude the prefix as a target, or exclude the ASN)
- flagged: 2026-11-14T15:04:31.867025+00:00
- resolved: 2026-11-19T15:05+10:00 -- acknowledged with the /21 above (owner ruling 2026-11-19; temp/escalation_reviews_2026-11-19/review_remaining.md 2.3): inside APCSNET 210.79.16.0/20 (AU), target-excluded since 2026-11-09; covered by the (45411, "210.79.16.0/20") entry in leasing_check.ACKNOWLEDGED (0c38ccf).

## Finding #328 (AS7594 "??" -> NU AS10025) -- candidate_peering rests on private hops; target 202.59.4.1 answers twice
- measurement: 238217921, 238217237, 238217136
- reason: unattended daily check -- new candidate_peering AS7594 -> AS10025 (IUSN, Niue) has source_cc "??", RIS disagrees, and the hops between AS7594 and the target are RFC 1918; the same target also replies at both terrestrial and satellite latency
- detail: 238217921 (MP probe 65653): 103.151.64.7 78.8 ms -> 120.88.74.158 78.8 ms (the AS7594 hop) -> 10.25.15.243 97.3 ms -> 172.18.0.5 97.9 ms -> 172.25.131.22 97.6 ms -> 202.59.4.1 111.6 ms (hop 16), two dark hops, then 202.59.4.1 again at 639.6 ms (hop 19). 238217237 (TV probe 7588, finding #327, same night): the same 120.88.74.158 56.5 ms -> 103.103.61.19 57.0 ms -> three dark hops -> 202.59.4.1 75.1 ms (hop 11), then again at 616.7 ms (hop 13); that chain was resolved as AS7594 -> AS135409 -> AS10025. RIPEstat asn-neighbours for AS10025 (2026-11-15): one neighbour only, AS135409 (left, 1621 v4 peers). So the private hops in 238217921 most likely sit inside AS135409 (Kacific) and #328 is the same corridor as #326/#327 with the middle AS unresolved, not a direct AS7594 adjacency (fairly confident). Separately, 202.59.4.1 answering at +19 ms past the 120.88.74.158 hub and again at ~620-640 ms in both traces suggests something on the near side of the satellite link answers for the address before the real host does (less sure; hub location not checked, no rDNS in this run). Same shape as the 2026-10-08 OneQode "??" escalation (#286/#288/#291/#294).
- proposed correction: hold or drop #328 (no evidence of a direct AS7594-AS10025 adjacency). Owner to say whether the short-RTT reply from 202.59.4.1 counts as reaching Niue for #326/#327, or whether the corridor's RTT should be taken from the ~620 ms reply. Worth a look before the IUSN probe comes online, since it will show the Niue side directly.
- flagged: 2026-11-15T21:36:00Z
- note (2026-11-16, owner session): RIS per-prefix upstreams show all of AS10025's space (202.59.4.0/22 + /24s) enters Kacific only via AS7594 OneQode (Sydney), so the private hops after 120.88.74.158 are Kacific's Sydney/Broken Hill-side gateway path. The first 202.59.4.1 reply lands ~19 ms past the Sydney hop in both traces, which fits a gateway roughly Broken Hill's distance away answering for the address; the ~620 ms reply is the GEO round trip to Niue (inference, see task_plan.md 2026-11-16).
- resolved: 2026-11-19T15:05+10:00 -- explained (owner ruling 2026-11-19; temp/escalation_reviews_2026-11-19/review_remaining.md 2.4). The short "202.59.4.1" reply (76-byte replies at 75-112ms, TTL 51-53) is an ICMP time-exceeded message from a router 2-3 hops before the host, not the target answering: the probes sent 48-byte echo requests, and the echo reply from the host comes back at 48 bytes, one GEO round trip later, at 617-640ms (TTL 48-51, two to three hops further). Across all cached raw files no other destination ever replied at size 76. #328 is the #326/#327 corridor (AS7594 -> Kacific AS135409 -> AS10025) with Kacific hidden behind RFC 1918 hops, not a direct AS7594-AS10025 adjacency; the corridor RTT is the echo reply. The owner's hold/drop decision on finding #328 is still open; finding #328 is unchanged.

## Finding #51 (MP AS7131 -> PG AS17828) -- late-collected trace that dies inside AS6939 was counted as a confirmed_detour corroboration
- measurement: 238217235
- reason: unattended daily check -- parked measurement collected at the end of the 2026-11-15 batch was filed as confirmed_detour (hub Sydney), but the trace never leaves Hurricane Electric
- detail: probe 65653 -> 103.20.76.1: 8.3.127.1 8.4 ms -> 64.71.131.185 9.6 ms -> three dark hops -> 184.104.189.163 237.9 ms -> two dark -> 184.104.194.234 246.2 ms -> five dark hops, then the hop-255 terminator. Resolved chain is "AS7131 -> AS6939" only; no hop in AS17828 or any PG network. cron.log 2026-11-16 01:35:11: "collected parked measurement 238217235 (Stopped)" then "confirmed_detour (parked measurement 238217235)". On 2026-09-17 the on-time path for the same corridor retried an alternate prefix (202.165.192.1) after a dark result and ended inconclusive; the parked-collection path does not appear to have retried. The 238-246 ms HE hops are also a poor fit for Sydney from this probe (it reached a hub at ~79 ms in 238217921 the same night), but HE hop locations were not checked (no rDNS in this run). Fairly confident this is a dead end, not a corroboration; less sure why the classifier accepted it.
- proposed correction: treat 238217235 as inconclusive (dark gap before the target) and remove it as a corroboration of #51; check whether collecting a parked measurement skips the dead-end / alternate-prefix retry that the on-time path applies.
- flagged: 2026-11-15T21:36:00Z
- note (2026-11-16, owner session): not the parked path. RIS agrees AS7131 -> AS6939, so the probe was decisive and no retry would run on time either. Rule 2 found HE Los Angeles (be48.core3.lax1.he.net, 237.9 ms) and `_finalize` corroborated #51 (Sydney) without comparing hubs; 231073937 (HE Portland, 11-02) did the same. Fixed going forward (mismatch escalates; dead-end router hub is inconclusive). The two existing #51 rows (231073937, 238217235) stay until the owner rules on the 113 mismatched rows; see task_plan.md 2026-11-16.
- resolved: 2026-11-19T15:05+10:00 -- fixed going forward (owner ruling 2026-11-19; temp/escalation_reviews_2026-11-19/review_remaining.md 2.5). The cause, a router hub accepted on a trace that never reaches the target and no comparison with the filed hub, was fixed in c05e089: such a trace is now inconclusive and a cross-city run escalates. Both disputed runs (231073937, 238217235) end at HE core3.syd1 and then go dark, with no AS17828 hop. Corroboration rows 918 and 1343 stay, pending the owner's 113-row decision; #51's real evidence is 211552535 (09-16) and 218707446 (10-04).

## Probe 23039 (GU, AS9246) -- metadata changed
- reason: probe watch (atlas/probe_watch.py)
- detail: asn_v4 17456 -> 9246; egress trace: AS9246 (measurement 238724161)
- action: owner review -- check the path before trusting this probe's next results, or changing any exclusion
- flagged: 2026-11-16T15:00:58.730720+00:00
- resolved: 2026-11-19T15:05+10:00 -- ordinary uplink change, path local (owner ruling 2026-11-19; temp/escalation_reviews_2026-11-19/review_remaining.md 2.6). The dual-homed site's default uplink moved from PDS (AS17456) back to GTA (AS9246) between 11-15 15:07Z (corridor run 238216216 still left via PDS 199.127.237.13) and 11-16 00:02Z (Atlas: Connected since 00:02:06Z, 114.142.217.210). Egress 238724161 runs GTA core <1ms -> GTA Tokyo 114.142.196.28/.155 29.4ms -> BBIX Tokyo -> Cloudflare -> 1.1.1.1 at 29.6ms; no PDS hop, no proxy. The probe's Cloudflare ROV label follows the uplink (rov_cloudflare_history.jsonl: filtered whenever the invalid trace left via PDS, 09-24, 09-29 and 10-20 to 11-12; not filtered when it left via GTA, 10-06's invalid trace, 10-13 and 11-17), so the 11-17 Guam ROV change is the uplink, not a policy change. AS17456 now has no connected probe.
## AS10131 (CK) -> AS140504 (NR)
- measurement: 238725343
- reason: detour hub differs from the filed finding
- detail: finding #159 is filed via Los Angeles; this run left the region via Tokyo (JPNAP Tokyo) -- not corroborated; relabel, keep, or retest is the owner's call
- flagged: 2026-11-16T15:07:11.845403+00:00

## AS23917 (TV) -> AS9246 (GU)
- measurement: 238725340
- reason: detour hub differs from the filed finding
- detail: finding #24 is filed via Los Angeles; this run left the region via Tokyo (BBIX Tokyo) -- not corroborated; relabel, keep, or retest is the owner's call
- flagged: 2026-11-16T15:07:14.071346+00:00
- resolved: 2026-11-24 -- keep Los Angeles (owner, per the 2026-11-19 hub-mismatch review): Hurricane Electric carries TV -> GU via LA on some runs and via Tokyo on others (231751014 11-03 and 221440874 10-11 corroborated LA); a single Tokyo run is HE variation, not a path change. No data changed.

## AS55722 (NR) -> AS137890 (FJ)
- measurement: 238726884
- reason: router in a hub city with no coordinates
- detail: probe 1018134: router hub: hop 5 103.151.64.207 gu-gnc-rt1-----Vlan756.hk-mgi-rt1.oneqode.net -> Hong Kong, 79.213ms (no hub coordinates, unmapped)
- flagged: 2026-11-16T15:10:22.530066+00:00
- resolved: 2026-11-19T15:05+10:00 -- cleared by e0e4e1f (owner ruling 2026-11-19; temp/escalation_reviews_2026-11-19/review_remaining.md 2.7): the 11-17 Hong Kong coordinates and Telstra Global sydp/hkck patterns. With current code find_router_hub picks i-90.sydp10.telstraglobal.net, Sydney, 250.7ms (floor 40.39ms, ok); Hong Kong is an intermediate city, Sydney the last off-region one, and the target 103.116.156.1 is reached. The run corroborated #290 (local transit), which stands; a new NR -> FJ AS137890 detour via Sydney is expected on #290's next reverification from Nauru.

## AS7131 (GU) -> AS24390 (FJ)
- measurement: 238730380
- reason: unrecognized routing loop
- detail: probe 60689: loop involving address 113.197.15.213, not in known_anomalies.py
- flagged: 2026-11-16T15:13:41.188875+00:00
- resolved: 2026-11-19T09:18+10:00 -- duplicate of the 2026-11-03 entry for this corridor (NOC-150312), which stays open (temp/escalation_reviews_2026-11-19/review_routing_loops.md 2.4). Same loop, unchanged: .213 (10) -> .194 (11) -> 113.197.15.136 label 830 (12) -> .213 (13) -> .194 (14), then dark; 6 of 6 second-pass replies.

## AS55722 (NR) -> AS142245 (FJ)
- measurement: 239432778
- reason: detour hub differs from the filed finding
- detail: finding #321 is filed via Los Angeles; this run left the region via Sydney (100ge0-0-0-4.core3.syd1.he.net (router in Sydney, no IXP crossing)) -- not corroborated; relabel, keep, or retest is the owner's call
- flagged: 2026-11-17T15:07:08.515069+00:00
- resolved: 2026-11-19T09:18+10:00 -- relabelled: finding #321's detour_hub is now Sydney (temp/escalation_reviews_2026-11-19/review_hub_mismatch.md 2.3). The Los Angeles label was the first off-region router, from before the 11-16 last-city fix. All three runs (231754568, 239432778, 239434797) end at core3.syd1.he.net (274-317ms, floor 40.39ms) and reach 198.15.17.1. Rehearsed on a DB copy: with Sydney all three corroborate, with Los Angeles all three escalate.

## AS55722 (NR) -> AS142245 (FJ)
- measurement: 239434797
- reason: detour hub differs from the filed finding
- detail: finding #321 is filed via Los Angeles; this run left the region via Sydney (100ge0-0-0-4.core3.syd1.he.net (router in Sydney, no IXP crossing)) -- not corroborated; relabel, keep, or retest is the owner's call
- flagged: 2026-11-17T15:10:13.667050+00:00
- resolved: 2026-11-19T09:18+10:00 -- relabelled: finding #321's detour_hub is now Sydney (temp/escalation_reviews_2026-11-19/review_hub_mismatch.md 2.3). The Los Angeles label was the first off-region router, from before the 11-16 last-city fix. All three runs (231754568, 239432778, 239434797) end at core3.syd1.he.net (274-317ms, floor 40.39ms) and reach 198.15.17.1. Rehearsed on a DB copy: with Sydney all three corroborate, with Los Angeles all three escalate.

## AS45345 (NC) -> AS45193 (FM)
- measurement: 240073513
- reason: router address has no single BGP owner
- detail: probe 33674: router hub: hop 7 103.200.13.168 HundredGigE0-0-1-2.921.bdr01-ipt-624sgran-lax.us.as38195.net -> Los Angeles, 211.915ms (floor 96.77ms, no_owner) -- BGP gives no single origin for the address (lookup failed, unannounced, or multi-origin), so the hostname can't be checked against its network; needs a human look, not a detour
- flagged: 2026-11-18T15:10:19.547097+00:00
- resolved: 2026-11-19T15:05+10:00 -- ordinary (owner ruling 2026-11-19; temp/escalation_reviews_2026-11-19/review_remaining.md 2.8). 103.200.13.168 (HundredGigE0-0-1-2.921.bdr01-ipt-624sgran-lax.us.as38195.net) is Superloop's Los Angeles border router at 624 S Grand Ave, in Superloop's allocated but unannounced 103.200.13.0/24 (WHOIS SUPERLOOP-AU inside 103.200.12.0/22; RADB route object origin AS38195; RIS: AS38195 originated it 2016-10-02 to 2021-05-20, 0 of 320 peers see it today). Its 190-213ms clears the 96.77ms floor; the next hop is the Any2West LAN (206.72.210.133) in the same building, the hop before it Superloop Sydney. Path and hub agree with #110 (Los Angeles, Any2West). The prefix override 103.200.13.0/24 -> AS38195 (F1) is pending: its rehearsal over the 48 cached corridor runs through 103.200.13.x found a change beyond clearing these flags (NC AS45345 -> GU AS3605, 211259107, would file a new detour via Los Angeles, and with no router hub a candidate_peering AS38195 -> AS3605), so it was not committed and goes back to the owner (patch in temp/escalation_reviews_2026-11-19/f1_superloop_override.patch). Until then NC runs through this router will keep raising this escalation.

## AS45345 (NC) -> AS45193 (FM)
- measurement: 240073513
- reason: router address has no single BGP owner
- detail: probe 63050: router hub: hop 7 103.200.13.168 HundredGigE0-0-1-2.921.bdr01-ipt-624sgran-lax.us.as38195.net -> Los Angeles, 212.842ms (floor 96.77ms, no_owner) -- BGP gives no single origin for the address (lookup failed, unannounced, or multi-origin), so the hostname can't be checked against its network; needs a human look, not a detour
- flagged: 2026-11-18T15:10:19.547097+00:00
- resolved: 2026-11-19T15:05+10:00 -- ordinary (owner ruling 2026-11-19; temp/escalation_reviews_2026-11-19/review_remaining.md 2.8). 103.200.13.168 (HundredGigE0-0-1-2.921.bdr01-ipt-624sgran-lax.us.as38195.net) is Superloop's Los Angeles border router at 624 S Grand Ave, in Superloop's allocated but unannounced 103.200.13.0/24 (WHOIS SUPERLOOP-AU inside 103.200.12.0/22; RADB route object origin AS38195; RIS: AS38195 originated it 2016-10-02 to 2021-05-20, 0 of 320 peers see it today). Its 190-213ms clears the 96.77ms floor; the next hop is the Any2West LAN (206.72.210.133) in the same building, the hop before it Superloop Sydney. Path and hub agree with #110 (Los Angeles, Any2West). The prefix override 103.200.13.0/24 -> AS38195 (F1) is pending: its rehearsal over the 48 cached corridor runs through 103.200.13.x found a change beyond clearing these flags (NC AS45345 -> GU AS3605, 211259107, would file a new detour via Los Angeles, and with no router hub a candidate_peering AS38195 -> AS3605), so it was not committed and goes back to the owner (patch in temp/escalation_reviews_2026-11-19/f1_superloop_override.patch). Until then NC runs through this router will keep raising this escalation.

## AS45345 (NC) -> AS45193 (FM)
- measurement: 240073513
- reason: router address has no single BGP owner
- detail: probe 7018: router hub: hop 7 103.200.13.168 HundredGigE0-0-1-2.921.bdr01-ipt-624sgran-lax.us.as38195.net -> Los Angeles, 190.441ms (floor 96.77ms, no_owner) -- BGP gives no single origin for the address (lookup failed, unannounced, or multi-origin), so the hostname can't be checked against its network; needs a human look, not a detour
- flagged: 2026-11-18T15:10:19.547097+00:00
- resolved: 2026-11-19T15:05+10:00 -- ordinary (owner ruling 2026-11-19; temp/escalation_reviews_2026-11-19/review_remaining.md 2.8). 103.200.13.168 (HundredGigE0-0-1-2.921.bdr01-ipt-624sgran-lax.us.as38195.net) is Superloop's Los Angeles border router at 624 S Grand Ave, in Superloop's allocated but unannounced 103.200.13.0/24 (WHOIS SUPERLOOP-AU inside 103.200.12.0/22; RADB route object origin AS38195; RIS: AS38195 originated it 2016-10-02 to 2021-05-20, 0 of 320 peers see it today). Its 190-213ms clears the 96.77ms floor; the next hop is the Any2West LAN (206.72.210.133) in the same building, the hop before it Superloop Sydney. Path and hub agree with #110 (Los Angeles, Any2West). The prefix override 103.200.13.0/24 -> AS38195 (F1) is pending: its rehearsal over the 48 cached corridor runs through 103.200.13.x found a change beyond clearing these flags (NC AS45345 -> GU AS3605, 211259107, would file a new detour via Los Angeles, and with no router hub a candidate_peering AS38195 -> AS3605), so it was not committed and goes back to the owner (patch in temp/escalation_reviews_2026-11-19/f1_superloop_override.patch). Until then NC runs through this router will keep raising this escalation.

## AS45345 (NC) -> AS23657 (AS)
- measurement: 240078520
- reason: detour hub differs from the filed finding
- detail: finding #66 is filed via Sydney; this run left the region via Portland (be2378.ccr51.pdx02.atlas.cogentco.com (router in Portland, no IXP crossing)) -- not corroborated; relabel, keep, or retest is the owner's call
- flagged: 2026-11-18T15:16:47.531604+00:00
- resolved: 2026-11-19T13:26+10:00 -- relabelled: finding #66's detour_hub is now Portland (owner's ruling 2026-11-19: "relabel #66 and #65 to Portland, pin 38.134.236.1"; temp/as23657_routing_2026-11-19/report.md, temp/escalation_reviews_2026-11-19/review_hub_mismatch.md 2.4). Routing into AS23657 is fixed per prefix: 202.4.47.0/24 (traced 09-16 and 10-18) enters at Sydney via Vodafone Samoa (AS17993), and Blue Sky's own space, including 38.134.236.0/22, enters at Portland. Every 38.134.236.1 run (233087028, 240078520, 240298607, 240318863) exits via Cogent pdx02 -> 67.218.63.217, ~192ms against a 99.33ms floor (probe 63050 is dark after Sydney on 233087028). Rehearsed on a DB copy: with Portland this run corroborates on all 3 probes, with Sydney it escalates. Reverification is now pinned to 38.134.236.1 (6ef8ec3).

## AS9471 (PF) -> AS17893 (PW)
- measurement: 240372348
- reason: detour hub differs from the filed finding
- detail: finding #55 is filed via Los Angeles; this run left the region via Tokyo (be15.core1.tyo1.he.net (router in Tokyo, no IXP crossing)) -- not corroborated; relabel, keep, or retest is the owner's call
- flagged: 2026-11-19T03:11:11.352121+00:00

## AS24390 (TO) -> AS140504 (NR)
- measurement: 240373634
- reason: detour hub differs from the filed finding
- detail: finding #303 is filed via Sydney; this run left the region via Los Angeles (et-0-0-0.bdr1.laxc.us.aarnet.net.au (router in Los Angeles, no IXP crossing)) -- not corroborated; relabel, keep, or retest is the owner's call
- flagged: 2026-11-19T03:14:28.207281+00:00

## AS45345 (NC) -> AS152706 (NR)
- measurement: 240684326
- reason: detour hub differs from the filed finding
- detail: finding #172 is filed via Los Angeles; this run left the region via Tokyo (if-ae-51-2.tcore1.tv2-tokyo.as6453.net (router in Tokyo, no IXP crossing)) -- not corroborated; relabel, keep, or retest is the owner's call
- flagged: 2026-11-19T15:13:29.119481+00:00

## AS139759 (FM) -> AS38201 (TO)
- measurement: 240687613
- reason: detour hub differs from the filed finding
- detail: finding #101 is filed via Sydney; this run left the region via Tokyo (BBIX Tokyo) -- not corroborated; relabel, keep, or retest is the owner's call
- flagged: 2026-11-19T15:20:21.785375+00:00
- detail: 2026-11-24 trace reading (cached raw, no new measurement). Not just a hub relabel: the whole path has changed. Filed via Kacific (legacy chain `AS139759 -> AS9246 -> AS4637 -> AS3356 -> AS7594 -> AS135409`, Sydney). All 3 probes (50897, 62046, 7448) now go GTA Guam -> 114.142.196.155 (GTA Tokyo-link core, Guam RTT ~49-51ms) -> BBIX Tokyo 101.203.88.74 (HE, 51-54ms) -> be1.core1.sea1.he.net (145-150ms) -> core1.pdx3.he.net (145-149ms) -> 216.218.213.73 (HE space, 241-244ms) -> 103.245.162.22 (AS132579 Tonga Cable, same RTT) -> 202.134.30.206 / 103.239.160.241 (AS38201, 284-288ms), then dark. Chain `AS139759 -> AS9246 -> AS6939 -> AS132579 -> AS38201`, RIS agrees (1508 observations); Kacific and Telstra no longer appear. 'Tokyo' is the IXP rule's first crossing; the last located off-region city is Portland (open first-crossing vs last-city question). The +95ms Portland -> HE/Tonga Cable handoff step is below the ~123ms Portland-Sydney fibre floor, so the handoff isn't in Sydney; not placed further. Owner's call, tied to first-crossing vs last-city.

## Probe 50365 (PG, AS17828) Disconnected -- PG reverifications fail with Atlas 400
- measurement: none created (both Atlas create calls returned 400)
- reason: unattended daily check -- the 2026-11-22T15:00Z nightly batch logged two tracebacks for AS17828 (PG) -> AS17993 (WS), reverifications of findings #302 (confirmed_detour) and #7 (candidate_peering)
- detail: Atlas shows probe 50365 (AS17828, Port Moresby, PG's only probe used in corridor tests) Disconnected since 2026-11-22T07:54:35Z, tagged "unstable-connection". With no connected PG probe, auto_classify fell back to "sourcing by country" (PG), and create_traceroute_measurement got `400 Client Error: Bad Request` from https://atlas.ripe.net/api/v2/measurements/ (logs/cron.log ~line 44155 and 44193). The corridor is left untested, so it will be retried, and probably fail the same way, each night until the probe reconnects. No credits were spent. No probe-watch escalation for 50365 exists yet.
- proposed correction: none to the data. When 50365 reconnects, fire one regression trace from it before trusting the PG corridors again (regression-test-on-probe-change rule). Code question for the owner: should the country-fallback path skip, or log one clean line, when the economy has no connected probe, instead of raising on Atlas's 400?
- flagged: 2026-11-22T21:40:00Z

## AS45345 (NC) -> AS4638 (FJ)
- measurement: 242767108
- reason: local IXP crossing with implausibly high latency
- detail: probe 33674: hop 8 crosses Fiji-IXP (in-fishbowl) at 39.16ms, 23.2ms more than the hop before it (minimum over it and later hops), above the 14.0ms allowed (10.0ms local fibre + 4.0ms cable leg in + 0.0ms to a confirmed remote port) -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-23T15:13:40.847413+00:00
- resolved: 2026-11-24 -- duplicate (owner: collapse the duplicates); tracked in the open AS45345 -> AS4638 entry for measurement 228735988 / probe 33674. Cause per the 2026-11-19 review: local forward path, return via Sydney.

## AS45345 (NC) -> AS4638 (FJ)
- measurement: 242767108
- reason: local IXP crossing with implausibly high latency
- detail: probe 63050: hop 8 crosses Fiji-IXP (in-fishbowl) at 39.986ms, 23.2ms more than the hop before it (minimum over it and later hops), above the 13.2ms allowed (10.0ms local fibre + 3.2ms cable leg in + 0.0ms to a confirmed remote port) -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-23T15:13:40.847413+00:00
- resolved: 2026-11-24 -- duplicate (owner: collapse the duplicates); tracked in the open AS45345 -> AS4638 entry for measurement 228735988 / probe 33674. Cause per the 2026-11-19 review: local forward path, return via Sydney.

## AS45345 (NC) -> AS4638 (FJ)
- measurement: 242767108
- reason: local IXP crossing with implausibly high latency
- detail: probe 7018: hop 8 crosses Fiji-IXP (in-fishbowl) at 39.219ms, 23.3ms more than the hop before it (minimum over it and later hops), above the 14.1ms allowed (10.0ms local fibre + 4.1ms cable leg in + 0.0ms to a confirmed remote port) -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-11-23T15:13:40.847413+00:00
- resolved: 2026-11-24 -- duplicate (owner: collapse the duplicates); tracked in the open AS45345 -> AS4638 entry for measurement 228735988 / probe 33674. Cause per the 2026-11-19 review: local forward path, return via Sydney.

