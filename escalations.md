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

## AS3605 (GU) -> AS9246 (GU)
- measurement: 213204603
- reason: local IXP crossing with implausibly high latency
- detail: probe 64953: hop 6 crosses MARIIX (in-fishbowl) at 15.741ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-09-19T01:35:21.666521+00:00

## AS152735 (GU) -> AS9246 (GU)
- measurement: 213205466
- reason: local IXP crossing with implausibly high latency
- detail: probe 64953: hop 6 crosses MARIIX (in-fishbowl) at 11.111ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-09-19T01:38:25.504223+00:00

## AS7131 (GU) -> AS56200 (GU)
- measurement: 213209039
- reason: unrecognized routing loop
- detail: probe 60689: loop involving address 154.18.76.1, not in known_anomalies.py
- flagged: 2026-09-19T01:47:43.630954+00:00

## AS152735 (GU) -> AS395400 (GU)
- measurement: 213209268
- reason: local IXP crossing with implausibly high latency
- detail: probe 62689: hop 5 crosses MARIIX (in-fishbowl) at 24.484ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-09-19T01:50:51.628050+00:00

## AS17456 (GU) -> AS395400 (GU)
- measurement: 213209280
- reason: local IXP crossing with implausibly high latency
- detail: probe 60689: hop 8 crosses MARIIX (in-fishbowl) at 23.234ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-09-19T01:51:00.839704+00:00


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

## AS10131 (CK) -> AS17828 (PG)
- measurement: 216153814
- reason: no probe data returned
- detail: Atlas returned zero probe results for this measurement -- most likely a transient results-fetch race (status went terminal moments before results were indexed) rather than a real network outcome; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-09-27T15:09:58.132290+00:00

## AS7131 (MP) -> AS24390 (FJ)
- measurement: 216153943
- reason: unrecognized routing loop
- detail: probe 65653: loop involving address 103.112.0.226, not in known_anomalies.py
- flagged: 2026-09-27T15:12:26.023585+00:00

## AS10131 (CK) -> AS24390 (FJ)
- measurement: 216153954
- reason: no probe data returned
- detail: Atlas returned zero probe results for this measurement -- most likely a transient results-fetch race (status went terminal moments before results were indexed) rather than a real network outcome; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-09-27T15:13:20.097674+00:00

## AS3605 (GU) -> AS38198 (TO)
- measurement: 216154286
- reason: unrecognized routing loop
- detail: probe 60689: loop involving address 202.43.12.5, not in known_anomalies.py
- flagged: 2026-09-27T15:15:44.219904+00:00

## AS10131 (CK) -> AS24439 (MH)
- measurement: 216154414
- reason: no probe data returned
- detail: Atlas returned zero probe results for this measurement -- most likely a transient results-fetch race (status went terminal moments before results were indexed) rather than a real network outcome; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-09-27T15:16:43.235106+00:00

## AS10131 (CK) -> AS45193 (FM)
- measurement: 216154556
- reason: no probe data returned
- detail: Atlas returned zero probe results for this measurement -- most likely a transient results-fetch race (status went terminal moments before results were indexed) rather than a real network outcome; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-09-27T15:20:12.803614+00:00

## AS10131 (CK) -> AS45879 (WF)
- measurement: 216154870
- reason: no probe data returned
- detail: Atlas returned zero probe results for this measurement -- most likely a transient results-fetch race (status went terminal moments before results were indexed) rather than a real network outcome; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-09-27T15:23:34.901267+00:00

## AS10131 (CK) -> AS140504 (NR)
- measurement: 216155432
- reason: no probe data returned
- detail: Atlas returned zero probe results for this measurement -- most likely a transient results-fetch race (status went terminal moments before results were indexed) rather than a real network outcome; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-09-27T15:26:56.500873+00:00

## AS24390 (FJ) -> AS9751 (AS)
- measurement: 216155552
- reason: all probes proxy-corrupted
- detail: every probe in this measurement resolved a known corporate proxy/VPN ASN as its first hop (probe 60575 via Zscaler) -- this source's own probe currently can't produce a real path; needs a human look (a different source, or wait for the proxy egress to genuinely change), not a target-IP retry
- flagged: 2026-09-27T15:28:10.838773+00:00

## AS24390 (FJ) -> AS24439 (MH)
- measurement: 216155814
- reason: all probes proxy-corrupted
- detail: every probe in this measurement resolved a known corporate proxy/VPN ASN as its first hop (probe 60575 via Zscaler) -- this source's own probe currently can't produce a real path; needs a human look (a different source, or wait for the proxy egress to genuinely change), not a target-IP retry
- flagged: 2026-09-27T15:33:10.817887+00:00

## AS17456 (GU) -> AS9246 (GU)
- measurement: 216991839
- reason: local IXP crossing with implausibly high latency
- detail: probe 64953: hop 6 crosses MARIIX (in-fishbowl) at 10.636ms, above the 10.0ms local-fiber threshold -- either this hop isn't genuinely local despite the registry, or there's an unexpected detour/backhaul before reaching it; needs a human look, not a guess
- flagged: 2026-09-29T15:06:59.886272+00:00

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
## AS7131 (MP) -> AS38198 (TO)
- measurement: 218277100
- reason: no probe data returned
- detail: Atlas returned zero probe results (status=Scheduled) -- the source probe never ran this measurement, so check that probe (it can read as Connected in the probe list while still not taking measurements) before re-firing from it; not marked tested so it retries on its own, not a signal about this corridor itself
- flagged: 2026-10-02T15:10:28.250480+00:00

