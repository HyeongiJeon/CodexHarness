# Independent data and evidence review

Review date: 2026-10-30. A fresh reviewer context read `AGENTS.md`, the
independent-code-review skill, and the actual implementations of
`harness/large_data.py`, `documents.py`, `corpus.py`, `evidence.py`, `sources.py`,
and the associated CLI additions. The lead retained code ownership; this
reviewer owns this document only. All reproductions use temporary synthetic
inputs. No native model benchmark, package installation, external service,
browser, upload, or Git push was performed.

## Confirmed findings

These observations describe the implementation inspected before the lead's
repairs. Repair verification is recorded separately below.

| Severity | Location | Reproduction and consequence |
| --- | --- | --- |
| P1 | `harness/evidence.py:extract_facts` | Two approved, currently effective `FACT` records with JSON numeric values `9007199254740992.1` and `9007199254740992.2` both parse as float `9007199254740992.0`. Synthesis returns `supported` instead of detecting the conflict. |
| P1 | `harness/evidence.py:evidence_pack` | A single source line containing `ALPHA`, 3,000 filler characters, then `OMEGA`, queried with both terms, returns `evidence_found`, no uncovered queries, and one excerpt containing only `ALPHA`. Deduplication treats a matching segment as coverage even when the included excerpt omits the other match. |
| P1 | `harness/documents.py:_json` | Source JSON `{"amount":9007199254740992.1}` emits `/amount: 9007199254740992.0` with extraction status `ok` and no limitation. Default float parsing changes the source number before extraction. The same parser choice affects JSONL. |
| P2 | `harness/large_data.py:_rows` | Profiling one JSONL row containing an 8,000,000-character string consumes 24,139,993 peak traced bytes while returning a 1,134-character report. Whole-line iteration has no record-size bound, so bounded output does not establish bounded input allocation. |
| P2 | `harness/evidence.py:synthesize` | An approved source containing `FACT` value `10`, filler, and conflicting `FACT` value `20` is indexed with `max_chars=180`. The index reports `complete=false` and the cited document is `partial`, but synthesis still returns `supported` value `10`. Known extraction incompleteness must remain visible in the answer decision. |

An additional source-mutation reproduction changed a CSV from amount `1` to
`999` after the source hash was obtained and before row iteration. The current
integrated implementation raised `ValueError: source changed during aggregation`;
no stale-hash result was released in that run.

## Checks performed

From `/home/qwehk/5_WORK/CodexHarness`:

```sh
python3 -m unittest tests.test_large_data tests.test_documents tests.test_corpus tests.test_evidence -v
```

Exit 0: all 29 tests passed in 0.445 seconds at the initial review snapshot.
This includes actual locally generated PDF text extraction with the installed
`pdftotext`, explicit empty-PDF failure, DOCX paragraph/table extraction, XLSX
cells and cached formulas, regex timeout, corpus rebuild behavior, source quote
tampering, current-versus-draft facts, and exact string-valued numeric conflicts.
The defects above were found through additional temporary inline Python
reproductions; the initial tests did not cover those cases.

A separate inline Python run generated a CSV with header `id,region,amount`
and 1,000,000 rows `f'{i},G{i % 1000},0.1'`, then executed
`aggregate_files([path], group_by=['region'], value='amount',
id_column='id', max_groups=5)`. Exit 0, including assertions of exactly
1,000,000 seen/valid rows, zero excluded rows, exact sum `100000.0`,
1,000 total groups and five returned groups. Aggregation took 19.552 seconds;
`resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` was 32,132 KiB. The returned
report was 2,121 characters; the SQLite spill was 12,066,816 bytes and removed.
This run used small records and no dimension join. Peak RSS describes this
specific process and workload, not a universal memory ceiling.

After repairs, the same four-module test command exited 0 with all 33 tests
passing in 0.393 seconds. A subsequent `make check` exited 0: all 60 repository
tests passed in 2.424 seconds, configuration validation and example plan checks
reported `ok: true`, all three solution regressions passed, and the existing
`benchmark-check benchmarks/sample` reported all three scenarios true. That last
command checks existing local artifacts; it launches no model benchmark.
`git diff --check` also exited 0 at final reviewer inspection.

## Scope and remaining limits

Verification establishes local source hash, extraction locator, and exact
extracted excerpt provenance. It does not establish document authenticity,
approval authority, semantic correctness, or that retrieval found every relevant
document. Manifest-supplied metadata needs independent audit. Deterministic
synthesis reconciles explicit `FACT {JSON}` records; arbitrary prose remains
evidence for an agent or human to interpret.

PDF layout and image-only pages, DOCX revisions and omitted document regions,
spreadsheet formulas and formatting, and search segment boundaries retain their
documented limitations. Large-data aggregation requires caller-declared unit
semantics, explicit joins and dates, and sufficient local spill disk. A million
small records is distinct from accepting arbitrarily large individual records.
No model's reasoning capability, account availability, native role routing, or
agent performance is established by this review.

## Repair verification

The JSONL record cap was independently rechecked after repair with one
8,000,000-character record followed by a valid record. Profiling reports two
sampled rows and one `record_too_large` issue; peak traced allocation fell to
3,302,289 bytes. Aggregation reports two seen rows, one valid and one excluded,
`record_too_large: 1`, and exact sum `2`. Exit 0 with assertions; the following
record remains readable after the oversized line is drained.

The other four original reproductions were independently repeated against the
integrated fixes in one inline Python command, exit 0 with assertions:

| Original finding | Observed repair behavior |
| --- | --- |
| Numeric FACT conflict | Parsed decimal values remain the distinct exact strings `9007199254740992.1` and `9007199254740992.2`; synthesis returns `conflict`, and its output remains JSON serializable. |
| Distant matches within one segment | The pack retains two excerpts with different offset-qualified `citation_id` values. Both requested terms appear in included quotes, and source verification returns `verified`. |
| JSON numeric extraction | Both `.json` and `.jsonl` emit the exact decimal value `9007199254740992.1`. Extraction explicitly labels pointer rendering as distinct from a raw-byte quotation. |
| Known incomplete extraction | The truncated corpus reports `corpus_complete=false`; synthesis returns `insufficient_evidence` and `answer=null`. |

All five reported findings are repaired for the independently reproduced cases.
No additional actionable correctness finding remains from this review's stated
scope. The limitations above still apply. Files outside the reviewed data,
document, corpus, evidence, resource, and CLI paths may have changed concurrently;
the lead remains responsible for final integration and delivery claims.
