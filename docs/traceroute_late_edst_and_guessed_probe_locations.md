# Late and misdirected traceroute replies, and probes with guessed locations

*Method note, 2026-10-22. Prompted by a review of RIPE NCC's ixp-country-jedi
(github.com/emileaben/ixp-country-jedi), which handles both issues and which
this project did not.*

## Summary

1. **RIPE Atlas traceroute replies marked `late` or `edst` do not belong to the
   hop they are filed under.** Until today `atlas.client.parse_traceroute_results`
   kept them. In the local cache that touched 86 hops in 28 measurements
   (13 probes), and changed the AS sequence that 23 probe traces resolve to.
   Three effects: false AS loops, false trailing ASNs, and real carriers hidden
   behind an ambiguous two-ASN hop. No finding's conclusion changes. Two stored
   corroboration chains (#87, #89) carry the artefact in their text.
2. **Some Atlas probes have a country that Atlas guessed from GeoIP**
   (`system-auto-geoip-country`), because the host never set a location. Two
   connected probes in scope have this tag: 1012513 (GU, AS152735) and 1008625
   (NC, AS45345). Both sit at their economy's centroid. Source selection
   trusted their country. Neither has produced a finding or corroboration.

Both are fixed: the parser drops `late` and `edst` replies, and corridor source
selection skips probes with a guessed country.

## 1. `late` and `edst` replies

### What the fields mean

Atlas sends several packets per TTL and logs every reply it receives while a
hop is open.

- **`late: N`** marks a reply to a packet sent N packets earlier. It has no
  `rtt`. The router that sent it answered an *earlier* hop's packet, so its
  address is not evidence about this hop.
- **`edst: <address>`** marks an ICMP error whose quoted packet was addressed
  to `<address>`, not to the traceroute's target. It answers some other
  packet the probe sent, and it carries an RTT of its own.

ixp-country-jedi removes `edst` replies before analysis (`filter_cruft` in
`get-measurements.py`) and skips `late` replies when building hop address
sets (`libixpcountryjedi.py`).

### Two real cases

**Stale `late` reply, measurement 211495010, probe 64953 (GU, AS3605 Guam
Cablevision, target 49.156.48.1 in Niue).** Hop 4's router answered after
3.9 s. A second copy of that reply was logged at hop 8, next to hop 8's own
router:

```json
{"hop": 4, "result": [{"x": "*"},
  {"late": 1, "from": "202.128.2.86", "ttl": 252, "size": 28},
  {"from": "202.128.2.86", "ttl": 252, "size": 28, "rtt": 3928.808}, {"x": "*"}]}
{"hop": 8, "result": [
  {"from": "198.81.233.25", "ttl": 248, "size": 28, "rtt": 119.644},
  {"from": "198.81.233.25", "ttl": 248, "size": 28, "rtt": 122.277},
  {"late": 12, "from": "202.128.2.86", "ttl": 252, "size": 28},
  {"from": "198.81.233.25", "ttl": 248, "size": 28, "rtt": 124.072}]}
```

Old parse: hop 8 = `198.81.233.25, 202.128.2.86`. New parse: `198.81.233.25`.

**Misdirected `edst` replies, measurement 218710339, probe 1018023 (SPC
container on Digicel Tonga, target 103.235.110.1).** Every reply at hops 5 and
6 quotes a packet to 193.0.0.164 (RIPE NCC), not to the target:

```json
{"hop": 6, "result": [
  {"from": "10.8.3.1", "ttl": 64, "size": 68, "rtt": 0.071, "edst": "193.0.0.164"},
  {"from": "10.8.3.1", "ttl": 64, "size": 68, "rtt": 0.082, "edst": "193.0.0.164"},
  {"late": 14, "from": "10.1.85.1", "ttl": 63, "size": 68, "edst": "193.0.0.164"}, {"x": "*"}]}
```

Old parse: hop 6 = `10.1.85.1, 10.8.3.1`, min RTT 0.071 ms, a value that
belongs to the probe's own traffic to RIPE NCC. New parse: hop 6 is dark.

### How much of the cache it touched

Across 4,756 cached traces (1,006 measurements), re-parsing changed 86 hops in
28 measurements:

| Change | Hops |
|---|---|
| Hop had only `late`/`edst` replies and is now dark | 68 |
| Hop lost a second, stale address | 18 |
| Hop's min RTT changed (all `edst`, probe 1018023) | 5 |

Two sources produce almost all of it:

- **Guam Cablevision's first routers.** Probes 329 and 64953 (both AS3605)
  account for 56 of the 86 hops. Their early routers 202.128.5.149 and
  202.128.2.86 answer seconds late, and the late copies land at hops further
  along the path.
- **Starlink routers near the end of a trace.** Late replies from AS14593
  addresses (206.224.64.0/20, 149.19.108.0/23) appear at hops 8-26, mostly
  after the trace has otherwise gone dark, on probes 65337, 63050, 7018, 33674, 61210,
  50897, 62046, 7448 and 1008229. They made a dark tail look answered, which
  matters for this project's rule that a dark gap before the target is
  inconclusive.

### Effect on AS paths

`traceroute_topology.extract_as_sequence` turns hops into AS paths, and a hop
that resolves to two ASNs is skipped as ambiguous. Resolving all 28
measurements with the old and the new parse, 23 probe traces changed:

- **False loops removed.** 212242269, probe 64953: `3605 3356 3605 3356 4637
  45355 38198` became `3605 3356 4637 45355 38198`. The second AS3605 was
  hop 4's router again.
- **False trailing ASNs removed.** 212236336, probe 65337: the path ended
  `... 4637 14593`. The final AS14593 was the probe's own Starlink router
  answering late. The path now ends at AS4637.
- **Hidden carriers revealed.** 211520771, probe 64953: `3605 6453 152706`
  became `3605 2497 6453 152706`. A hop holding the stale AS3605 address and an
  IIJ address (58.138.112.110) resolved to two ASNs and was skipped, which hid
  IIJ. The same happened with Lumen (AS3356) in 212240634.

### Effect on findings

18 corroborations and 2 legacy finding notes cite one of the 28 measurements.
Each was checked against the new AS sequences.

- **No finding's conclusion changes.** Finding 58 (GU -> WS, AS17993) already
  names AS3356 in its detour description, and finding 171 (GU -> NR,
  AS152706) already names AS2497. The analyst read past the artefact.
- **Two stored chains carried it, now corrected** (finding 58, measurement
  212240634, owner-approved 2026-10-22). Both now read
  `AS3605 -> AS3356 -> AS174 -> AS17993`, as the project's own chain builder
  gives on the re-parsed trace. Each row's `note_extra` records the old chain
  and the cause:
  - #87 (probe 329) read `AS3605 -> AS3356 -> AS3605 -> AS174 -> AS17993`.
    Hop 1's router 202.128.5.149 only ever answered late, and one copy landed
    at hop 7, between Lumen (hop 6) and Cogent (hop 8). It was not a loop;
    `has_loop` was never set.
  - #89 (probe 64953) read `AS3605 -> AS174 -> AS17993`. Hop 4's router
    202.128.2.86 answered late and was logged at hop 9 beside Lumen's
    4.14.44.25, so that hop resolved to two ASNs and AS3356 was skipped.
  - #88 (probe 60689, `AS7131 -> AS6939 -> AS17993`) was unaffected.
  The database was backed up first, and `findings_export.jsonl` was
  regenerated (one line changed). No report prints these chains.
- Every other citation either uses a probe whose sequence did not change or
  changes only a contiguity flag beside an unchanged adjacency.

### What changed

- `atlas/client.py`: `parse_traceroute_results` drops replies carrying `late`
  or `edst`. A hop with nothing else left is dark.
- `tests/atlas/test_parse_traceroute.py` freezes the two cases above, plus a
  guard that hop 4 in 211495010 keeps 202.128.2.86 from its on-time reply.
- The 28 affected files in `data/atlas/parsed/` were re-parsed from the local
  raw cache (no Atlas refetch). After the rewrite a second pass finds 0
  differences.

## 2. Probes whose country Atlas guessed

Atlas tags a probe `system-auto-geoip-country` when the host has not set a
location and Atlas has placed it from GeoIP. ixp-country-jedi never selects
these probes (`prepare.py`, `doit.py`).

This project picks sources by each probe's own Atlas country
(`corridor_backlog._probe_live_cc_by_asn`), so a guessed country can put a
source in the wrong economy. On 2026-10-22, two connected probes in scope had
the tag:

| Probe | Economy | ASN | Description | Coordinates |
|---|---|---|---|---|
| 1012513 | GU | AS152735 | (none) | 144.8175, 13.4785 (Guam centroid) |
| 1008625 | NC | AS45345 | "Nautile Studio Felix" | 165.4985, -21.5005 (New Caledonia centroid) |

Neither probe is the only source for its ASN (AS152735 also has 7385 and
60703; AS45345 has 7018, 33674 and 63050). Neither appears as the vantage in
any corroboration: #74 and #81 (vantage AS152735) came from probe 60703.

### What changed

- `atlas/probes.py`: each listing entry records `auto_geoip`.
- `analysis/corridor_backlog.py`: `_probe_live_cc_by_asn` skips probes with
  `auto_geoip` set. A listing written before the field existed still gives
  sources.
- The listing is rebuilt each night before the corridor batch, so the
  exclusion takes effect on the next nightly run.

### Not changed

`fleet_trace` and the weekly IPv6 and ROV checks still trace from every
connected probe, these two included, and label them by Atlas country. Their
output is reported but never filed as a finding.

## Verification

- Test-first: the three new parser tests and two new source-selection tests
  failed before the fix, for the expected reasons. One parser test is a guard
  and passed before and after.
- Full suite: 378 passed. `ruff check`: clean.
