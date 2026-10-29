# Final focused independent audit

Reviewed on 2026-10-30 (Asia/Seoul), starting from `3fbf6a6` plus the final
working-tree additions. This fresh reviewer context inspected
`harness/benchmark.py`, `harness/install.py`, their CLI integration and tests,
role launch arguments, and existing local synthetic run evidence. The earlier
review is in [initial.md](initial.md). Only this review document is owned by
this reviewer; implementation and other documentation remain lead-owned.

No new model invocation, network request, browser automation, upload, Git push,
or nested agent was used. Runtime application checks used local loopback HTTP.
Personal session content and raw CLI logs remain under ignored local paths.

## Evidence checked

| Check | Result | Scope |
| --- | --- | --- |
| `make check` | Exit 0; 27 unit tests and three solution regressions pass; validation and example task-plan check report `ok: true` | Includes evidence integrity, existing-skill preservation, external symlink rejection, data, HTTP flow, role configuration, and ownership contracts. |
| `git diff --check` | Exit 0 | Working-tree diff at inspection time. |
| `python3 -m harness launch --project /tmp --mode inherited --dry-run` | Exit 0 | Absolute checked-in role paths; no forced main model or reasoning effort. No native CLI launch occurred. |
| Temporary generated inherited bundle, `launch --bundle ... --model gpt-6.1-sol --dry-run` | Exit 0 | All ten role paths point into the generated bundle; explicit parent `-m` is retained; inherited configuration adds no model/effort override. |
| Local mocked process-result checks of `benchmark.run` | Expected harness exits 0, 1, 1, 1 | CLI/acceptance exit pairs `(0,0)`, `(1,0)`, `(0,1)` with complete scenario evidence, then `(0,0)` with missing structured evidence. These are bookkeeping simulations, not native-agent runtime evidence. |
| `python3 -m harness benchmark-check .harness/runs/20261029T154528175479Z-multi/project` | Exit 0; A/B/C all true | Actual generated code, including noisy HTTP request logs, checked with the final structured-result implementation. No model was rerun. |
| `python3 -m harness benchmark-check .harness/runs/20261029T214100133174Z-single/project` | Exit 0; A/B/C all true | Same final acceptance suite against the single baseline. |

The following runtime records were inspected locally without publishing their
raw content or session identifiers:

| Existing run | Independent interpretation |
| --- | --- |
| Routed multi, 197.476 seconds | Five actual child sessions are linked to the parent by session ancestry; fresh spawn requests and overlapping session intervals are present. Observed models include Sol for frontend/core/reviewer and Terra for data/QA. CLI exited 1; the run is unsuccessful. Final corrected acceptance now passes all three generated tasks; that does not change the historical CLI failure. |
| First inherited smoke, 2.518 seconds | CLI exited 1 and no child/output evidence exists; unsuccessful. |
| Later inherited smoke, 23.101 seconds | CLI exited 0; two actual requirements/explorer child sessions use Sol/high, have fresh-context spawn requests, overlap, and contain no parent-only marker. Both returned JSON files match the requested values. |
| Routed single, 91.709 seconds | CLI exited 0, zero observed children, and all three final acceptance tests pass. Sol/high is observed in the root session metadata. |

The final `extract_events` / `augment_local_sessions` /
`orchestration_verified` functions were rerun read-only over the existing
events. The final orchestration predicate returns true for the later smoke,
the single baseline, and the original multi session evidence. The historical
summaries predate the final `orchestration_verified` field and were not
rewritten to imply that the final implementation produced those runs.
Session interval overlap demonstrates overlapping agent lifetimes; it does
not measure simultaneous CPU or model execution.

Agent final prose is insufficient: unit tests confirm that a claim of three
parallel agents supplies neither child IDs nor orchestration proof. The
reviewer additionally inspected ancestry, requests, timestamps, model metadata,
and the final freshness predicate rather than relying on those unit tests or
worker self-reports alone.

## Findings and disposition

One reporting defect was reproduced against actual generated multi-run code:
the original scenario regex assumed unittest prints `... ok` on one line.
The web implementation writes request logs between the test name and final
`ok`, causing scenario A to be reported false despite a passing test. Overall
acceptance and harness success still used the checker exit status correctly.
The lead replaced prose parsing with explicit JSON scenario results emitted
from the unittest result. Final `evaluate()` requires checker exit 0 and all
three scenarios true. The offline CLI commands above independently rechecked
both historical projects; the noisy web case now reports A true. Missing
structured evidence is rejected even when the mocked checker exits 0.

A stale runbook statement said custom generated bundles could not be launched,
despite the final `--bundle` option. The lead corrected the statement, and the
reviewer checked the actual generated-bundle dry run. No consequential finding
remains open within the inspected scope. No skill installer overwrite or
launch-argument regression was found in the inspected paths.

## Limits

This review does not establish a multi-agent speedup: the multi run failed at
the CLI level and used different routed models. It does not prove provider
availability beyond the recorded sessions, future quota availability, visual
browser quality, complete edge-case coverage of generated benchmark tasks,
or cross-platform process termination. Missing local session evidence makes
freshness/parallel orchestration unverified; output files alone cannot replace
it. The checker correction and final evidence-summary fields were audited
locally, not by an additional native benchmark run. Generated private evidence
must remain ignored and outside public commits.

A second multi run was active during this final document pass. It is outside
the evidence table and completion claims above; its generated project was not
evaluated while workers were writing it.
