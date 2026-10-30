# Korean natural-prose trial (synthetic, no FACT records)

One 24-document synthetic Korean corpus, 9 questions (`fixtures/prose`). Oracle kept outside actor inputs
(`.harness/prose-evaluation/oracle.json`, read only by `prose-evaluation score` after outputs were frozen).
`.harness/` is private evidence and is not committed. One trial is not a general accuracy estimate.

**Model fallback:** the Codex Luna/Sol routing was unavailable (Codex tokens exhausted). Round 2 used fresh
Claude subagents (explorer, 3 synthesizers, independent auditor). These are **not** Codex Luna/Sol results.
Model identity is per the operator's record, not logged in `.harness/`. Round 1 is described as Codex per the operator's account of the interrupted run. Interpretation of prose was model work, not the deterministic Python engine.

## Results (round 1 re-scored from `run/outputs/synthesis-initial.json`; round 2: `run2/score.json`, `run2/score-diagnostic.json`)

| Metric | Round 1 (Codex, narrow queries) | Round 2 strict | Round 2 diagnostic* |
|---|---|---|---|
| Questions | 9 | 9 | 9 |
| Correct answers / correct abstain / correct conflict | 1 / 1 / 0 | 6 / 2 / 1 | 6 / 2 / 1 |
| Wrong answers | 7 | 0 | 0 |
| Wrong abstentions | 5 | 0 | 0 |
| False definitive conclusions (supported but ungrounded) | 1 | 5 | 3 |
| Required evidence retrieved | 23/54 | 51/54 | 51/54 |
| Required evidence in pack | 23/54 | 46/54 | 46/54 |
| Citations verified | 61/61 | 64/105 | 97/97 |
| Retrieval / pack-selection / synthesis / source-verification failures | 9/0/0/0 | 3/1/0/5 | 3/1/0/0 |
| Audit false acceptances (auditor accepted ungrounded `supported`) | n/a | 5 | 3 |

\*Diagnostic: post-hoc mechanical remap of bare `evidence_id` citations to the pack's `citation_id`
(`outputs/synthesis-diagnostic-remapped.json`); answers themselves unchanged. Strict is the primary result.

## Error analysis
- Round 1 failed at retrieval (4 literal queries/question, 9/9 retrieval failures); synthesis itself was never the bottleneck.
- Round 2 answer statuses/values were all correct, but **"false definitive" is a grounding failure, not a wrong value**:
  - Q1-Q3 synthesizers cited bare `evidence_id`, not the pack's `citation_id` (my brief did not specify it) -> unverifiable.
  - Q3, Q4, Q6: synthesizers fetched key table rows (2400/2184 kg, unit prices, display value) by extra search because they were not in the pack; those rows are not in the retrieval ledger/pack, so they count as retrieval failure.
  - Q8: abstention correct, one required anchor not cited.
- **The independent auditor accepted all 9**, including 3-5 answers whose citations did not ground the claim: it verified citation IDs by base id only and re-derived values from original text. Audit validated values, not citation grounding; use scorer provenance as the check for that.
- Not measured: token/model usage of Claude subagents; wall-clock timing beyond subagent durations (~1-2 min each).

## Use
`python3 -m harness prose-evaluation prepare --work-dir W` then pack building (`corpus index/search/evidence-pack`),
synthesis with `citation_id` citations, independent audit, `prose-evaluation score --oracle ... --answers ... --audit ...`.
