# Escalations

Corridors `auto_classify.py`'s mechanical rules couldn't confidently resolve on their own -- a routing loop at an address never seen before, an IXP crossing PeeringDB/`ixp_lan_registry.json` hasn't been told is in- or out-of-fishbowl, an external upstream at a hub with no known coordinates. Each needs a human/LLM look before it's added to `known_anomalies.py`, `ixp_lan_registry.json`, or `economy_coordinates.EXTERNAL_HUB_LATLON` and reprocessed.
## AS9249 (VU) -> AS23959 (VU)
- measurement: 213187876
- reason: unrecognized routing loop
- detail: probe 1008536: loop involving address 202.84.222.81, not in known_anomalies.py
- flagged: 2026-09-19T00:45:51.475813+00:00

## AS9249 (VU) -> AS23959 (VU)
- measurement: 213187876
- reason: unrecognized routing loop
- detail: probe 64783: loop involving address 202.84.222.81, not in known_anomalies.py
- flagged: 2026-09-19T00:45:51.475813+00:00

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

## AS23959 (VU) -- possible offshore-hosted address space
- reason: offshore-hosting check (atlas/offshore_check.py)
- detail: 194.127.166.1: probe 1014094 11.19ms < 66.6ms minimum (measurement 215225380)
- action: owner review; if confirmed, add to discovery/excluded_asns.py (offshore_hosted)
- flagged: 2026-09-24T11:49:55.550669+00:00

## AS58932 (PW) -- possible offshore-hosted address space
- reason: offshore-hosting check (atlas/offshore_check.py)
- detail: 103.30.248.1: probe 1000112 48.72ms < 110.9ms minimum (measurement 215228529)
- action: owner review; if confirmed, add to discovery/excluded_asns.py (offshore_hosted)
- flagged: 2026-09-24T11:49:55.550669+00:00

## AS132468 (SB) -- possible offshore-hosted address space
- reason: offshore-hosting check (atlas/offshore_check.py)
- detail: 103.188.182.1: probe 1011722 11.1ms < 28.5ms minimum (measurement 215228678)
- action: owner review; if confirmed, add to discovery/excluded_asns.py (offshore_hosted)
- flagged: 2026-09-24T11:49:55.550669+00:00
