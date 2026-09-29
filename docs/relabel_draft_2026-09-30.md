# Findings relabel draft (2026-09-30)

**Status: draft, nothing applied.** Needs Terry's approval, per group or per item, before any DB write.

Context: `auto_classify` sourced new-corridor tests by `country=`, stored the corridor's *label* ASN as every corroboration's vantage, and hung every probe's corroboration on the first upstream's finding. Fixed going forward in `fec96da`. This draft repairs the existing record.

## Method

- **Wrong finding:** a candidate_peering / confirmed_local_transit corroboration belongs to finding S → T only if its chain's AS before T is S (or, when the trace went dark before T, its last AS is S).
- **No evidence:** the chain is only the target ASN, so the probe sat inside the target network.
- **Vantage:** a row's vantage should be its chain's first ASN when that ASN is one of the measurement's probe ASNs (current Atlas `asn_v4` plus `PROBE_ASN_OVERRIDES`). Caveat: current ASN, not the ASN at measurement time.
- Raw hops: `data/atlas/parsed/<measurement>.json`. `cNNN` = `corroborations.id`, `mNNN` = measurement.

## A. Move to the existing correct finding

| corroboration | chain | from | to | note |
|---|---|---|---|---|
| c316 (m213204603) | AS7131 -> AS9246 | #225 (candidate_peering, AS3605 → AS9246) | #255 (candidate_peering, AS7131 → AS9246) |  |
| c322 (m213205466) | AS7131 -> AS9246 | #225 (candidate_peering, AS3605 → AS9246) | #255 (candidate_peering, AS7131 → AS9246) |  |
| c325 (m213205473) | AS7131 -> AS9246 | #225 (candidate_peering, AS3605 → AS9246) | #255 (candidate_peering, AS7131 → AS9246) |  |
| c326 (m213205473) | AS152735 -> AS7131 -> AS9246 | #225 (candidate_peering, AS3605 → AS9246) | #255 (candidate_peering, AS7131 → AS9246) |  |
| c489 (m216991839) | AS3605 -> AS9246 | #255 (candidate_peering, AS7131 → AS9246) | #225 (candidate_peering, AS3605 → AS9246) | MARIIX crossing |
| c346 (m213207618) | AS3605 -> AS17456 -> AS23676 | #230 (candidate_peering, AS7131 → AS23676) | #229 (candidate_peering, AS17456 → AS23676) |  |
| c350 (m213207619) | AS3605 -> AS17456 -> AS23676 | #230 (candidate_peering, AS7131 → AS23676) | #229 (candidate_peering, AS17456 → AS23676) |  |
| c341 (m213206915) | AS7131 -> AS23676 | #229 (candidate_peering, AS17456 → AS23676) | #230 (candidate_peering, AS7131 → AS23676) | MARIIX crossing |
| c442 (m213460360) | AS45345 -> AS136402 | #245 (confirmed_local_transit, AS18200 → AS136402) | #221 (candidate_peering, AS45345 → AS136402) |  |
| c444 (m213460360) | AS45345 -> AS136402 | #245 (confirmed_local_transit, AS18200 → AS136402) | #221 (candidate_peering, AS45345 → AS136402) |  |

Net effect: #255 AS7131→AS9246 goes from 2 rows / 1 measurement to 5 rows / 4 measurements. #225 AS3605→AS9246 keeps its 5 MARIIX rows and gains 1. #245 is left with one row (c443), worth a look.

## B. Adjacencies with no finding yet: proposed new findings

Kind follows `auto_classify`'s own rule (ris_agrees → confirmed_local_transit, else candidate_peering).

| proposed finding | kind | corroborations | note |
|---|---|---|---|
| AS7131 → AS395400 | candidate_peering | c369, c370, c374, c375, c376 | all 5 cross MARIIX, ris_agrees=0, 3 measurements (213209267/268/280): the strongest new one |
| AS17456 → AS395400 | confirmed_local_transit | c373 | via Guam IX, ris_agrees=1 |
| AS7131 → AS17456 | candidate_peering | c334 | ris_agrees=0, single row |
| AS17456 → AS152735 | candidate_peering | c366 | ris_agrees=0, single row |
| AS56089 → AS17480 | candidate_peering | c260, c413 | both cross CAN'L IX, ris_agrees=0, 2 measurements |
| AS56089 → AS18200 | confirmed_local_transit | c267 | ris_agrees=1 |
| AS152735 → AS23676 | recommend: don't file | c340 | Guam IX's own infrastructure ASN to MARIIX's exchange ASN; the legacy FM→PW note already declined to treat AS152735 as a peering party. Recommend dropping this row instead |

## C. Drop: no evidence (probe inside the target network)

| corroboration | chain | on finding |
|---|---|---|
| c311 (m213204604) | AS3605 | #224 (candidate_peering, AS7131 → AS3605) |
| c314 (m213204605) | AS3605 | #224 (candidate_peering, AS7131 → AS3605) |
| c327 (m213205489) | AS17456 | #227 (confirmed_local_transit, AS3605 → AS17456) |
| c333 (m213206914) | AS17456 | #227 (confirmed_local_transit, AS3605 → AS17456) |
| c336 (m213206910) | AS17456 | #227 (confirmed_local_transit, AS3605 → AS17456) |
| c368 (m213209042) | AS152735 | #188 (confirmed_local_transit, AS7131 → AS152735) |

## D. Vantage-ASN relabels (mechanical)

77 rows on 34 findings. Rows handled in A–C are excluded; a moved row gets its vantage fixed as part of the move. `vantage_point_asn` old → new:

| finding | rows |
|---|---|
| #20 (confirmed_detour, ASNone → AS4638) | c32 45345→56089 |
| #21 (confirmed_detour, ASNone → AS9241) | c467 3605→7131 |
| #35 (confirmed_detour, ASNone → AS9751) | c479 45345→56089 |
| #50 (confirmed_detour, ASNone → AS17828) | c73 3605→7131, c74 3605→152735 |
| #54 (confirmed_detour, ASNone → AS17893) | c81 3605→152735 |
| #55 (confirmed_detour, ASNone → AS17893) | c382 9471→2200 |
| #58 (confirmed_detour, ASNone → AS17993) | c88 3605→7131 |
| #115 (confirmed_detour, ASNone → AS45355) | c153 45345→56089 |
| #133 (confirmed_detour, ASNone → AS45891) | c174 3605→7131 |
| #137 (confirmed_detour, ASNone → AS45891) | c399 9471→2200 |
| #165 (confirmed_detour, ASNone → AS152093) | c213 3605→152735 |
| #177 (confirmed_local_transit, AS38442 → AS9249) | c231 3605→7131 |
| #188 (confirmed_local_transit, AS7131 → AS152735) | c364 3605→7131, c367 17456→7131 |
| #189 (confirmed_local_transit, AS3605 → AS395400) | c371 7131→3605, c372 152735→3605, c377 17456→3605 |
| #195 (confirmed_detour, AS141695 → AS134783) | c247 141695→56089, c248 141695→45345, c249 141695→45345 |
| #196 (confirmed_detour, AS141695 → AS154100) | c250 141695→45345, c251 141695→45345, c252 141695→45345 |
| #204 (confirmed_local_transit, AS18200 → AS17480) | c414 56089→45345, c415 56089→45345 |
| #209 (confirmed_local_transit, AS18200 → AS45461) | c271 45345→56089, c422 56089→45345, c423 56089→45345, c424 56089→45345 |
| #211 (confirmed_local_transit, AS18200 → AS56055) | c277 45345→56089, c427 56089→45345, c428 56089→45345 |
| #215 (confirmed_local_transit, AS18200 → AS131248) | c287 45345→56089, c431 56089→45345, c432 56089→45345 |
| #218 (confirmed_detour, AS45345 → AS131995) | c292 45345→56089, c434 56089→45345, c435 56089→45345, c436 56089→45345 |
| #220 (confirmed_local_transit, AS18200 → AS134405) | c298 45345→56089, c438 56089→45345, c440 56089→45345 |
| #222 (confirmed_local_transit, AS18200 → AS137243) | c446 56089→45345, c448 56089→45345 |
| #223 (confirmed_local_transit, AS18200 → AS140718) | c306 45345→56089, c451 56089→45345, c452 56089→45345 |
| #224 (candidate_peering, AS7131 → AS3605) | c309 152735→7131, c310 152735→7131 |
| #225 (candidate_peering, AS3605 → AS9246) | c321 152735→3605, c323 152735→3605, c324 7131→3605 |
| #227 (confirmed_local_transit, AS3605 → AS17456) | c335 7131→3605, c337 152735→3605 |
| #229 (candidate_peering, AS17456 → AS23676) | c343 17456→3605, c344 17456→3605 |
| #230 (candidate_peering, AS7131 → AS23676) | c348 152735→7131, c349 152735→7131 |
| #231 (confirmed_local_transit, AS7131 → AS56200) | c351 3605→17456, c352 3605→7131, c354 17456→3605, c355 17456→3605, c357 152735→17456, c358 152735→7131, c359 152735→3605, c360 7131→3605, c362 7131→3605 |
| #233 (confirmed_local_transit, AS139759 → AS45193) | c393 9471→2200, c470 9471→2200 |
| #236 (confirmed_local_transit, AS18200 → AS141197) | c408 45345→56089, c455 56089→45345, c456 56089→45345 |
| #238 (confirmed_local_transit, AS56055 → AS147030) | c458 56089→45345, c459 56089→45345, c460 56089→45345 |
| #255 (candidate_peering, AS7131 → AS9246) | c488 17456→7131 |

Not relabelled: 23 PF rows (findings #45, 55, 61, 95, 137, 232, 233) whose chain starts at AS6939. The probe's own hops are private, so the chain can't confirm AS9471, and it's left as is. Some of those measurements also included a PF probe on AS2200 (RENATER).

## E. Needs your call

1. **#195 and #196** (NC detours to KI) have `source_asn = 141695`, the SPC ASN excluded outright for Zscaler egress. Their probes were on AS45345/AS56089, never AS141695. Relabel to AS45345 (majority), set NULL like the legacy detours, or retract and retest?
2. **#218** (NC detour → AS131995): all 6 chains end at AS38195 and never reach the target. Unrelated to this bug; flagged only.
3. **Detours** (#20, 21, 35, 50, 54, 55, 58, 115, 133, 165) are economy-level with `source_asn` NULL, so only their vantage rows change (group D).

## Applying

On approval: one transaction on `data/analysis/findings.db` (move rows, `create_finding` for B, delete C, update D vantages, recompute `probe_agreement` for touched candidate_peering findings), then `export_jsonl`, regenerate reports, and one `fix(findings)` commit listing every ID.
