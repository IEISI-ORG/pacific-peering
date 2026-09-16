# Escalations

Corridors `auto_classify.py`'s mechanical rules couldn't confidently resolve on their own -- a routing loop at an address never seen before, an IXP crossing PeeringDB/`ixp_lan_registry.json` hasn't been told is in- or out-of-fishbowl, an external upstream at a hub with no known coordinates. Each needs a human/LLM look before it's added to `known_anomalies.py`, `ixp_lan_registry.json`, or `economy_coordinates.EXTERNAL_HUB_LATLON` and reprocessed.

## AS3605 (GU) -> AS38198 (TO)
- measurement: 212242269
- reason: unrecognized routing loop
- detail: probe 60689: loop involving address 184.104.192.252, not in known_anomalies.py
- flagged: 2026-09-16T15:24:56.963480+00:00

## AS7131 (MP) -> AS24439 (MH)
- measurement: 212243973
- reason: unrecognized routing loop
- detail: probe 65653: loop involving address 103.57.234.1, not in known_anomalies.py
- flagged: 2026-09-16T15:27:30.180206+00:00

## AS3605 (GU) -> AS45879 (WF)
- measurement: 212244021
- reason: unrecognized routing loop
- detail: probe 60689: loop involving address 184.104.192.136, not in known_anomalies.py
- flagged: 2026-09-16T15:28:00.107072+00:00

## AS7131 (MP) -> AS55943 (PF)
- measurement: 212246887
- reason: unrecognized routing loop
- detail: probe 65653: loop involving address 209.120.142.174, not in known_anomalies.py
- flagged: 2026-09-16T15:42:51.207314+00:00

