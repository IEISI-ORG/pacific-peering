# Escalations

Corridors `auto_classify.py`'s mechanical rules couldn't confidently resolve on their own -- a routing loop at an address never seen before, an IXP crossing PeeringDB/`ixp_lan_registry.json` hasn't been told is in- or out-of-fishbowl, an external upstream at a hub with no known coordinates. Each needs a human/LLM look before it's added to `known_anomalies.py`, `ixp_lan_registry.json`, or `economy_coordinates.EXTERNAL_HUB_LATLON` and reprocessed.
