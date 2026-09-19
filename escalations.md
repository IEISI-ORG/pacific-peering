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

