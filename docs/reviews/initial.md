# Independent review and regression evidence

Reviewed baseline: `e8302a6`. Review date: 2026-10-30. The reviewer used a fresh
agent context, read the implementation and actual working-tree diff, and ran
local reproductions with synthetic inputs. Baseline modules were loaded from
`git show e8302a6:<path>` into temporary Python modules; no checkout or starter
file was rewritten. No browser automation, external service, upload, or Git push
was used.

## Confirmed baseline findings

| Severity | Location | Reproduction and observed impact | Repair checked |
| --- | --- | --- | --- |
| P1 | `harness/tasks.py:validate_plan` | Two independent valid tasks own `./src` and `src/core.py`. The baseline returns `[]`, allowing simultaneous writers to the same tree. Equivalent aliases using repeated separators or `.` components also bypass the original string comparison. | Normalize both paths before overlap comparison. Regression tests cover aliases, disjoint siblings, transitive handoffs, shared-predecessor siblings, cycles, unknown dependencies, missing fields, invalid paths, and duplicate IDs. |
| P1 | `configs/inherited/config.toml` and all `configs/inherited/agents/*.toml` | Parsing baseline inherited `core.toml` with `tomllib` yields `model = "gpt-6.1-sol"`; other role files and the bundle also force models/effort. This violates the advertised parent-inheritance contract and can select an unavailable model. The generator itself already omitted these keys correctly; the checked-in bundle was stale. | Remove model and effort keys from the inherited bundle. Tests inspect both freshly generated and checked-in bundles, including every role. |
| P2 | `harness/roles.py:launch_overrides` | Generate a routed bundle in a temporary directory and inspect `launch_overrides(bundle)`: there is no `model=...` or `model_reasoning_effort=...` assignment although both appear in its main config. An explicit routed launch can therefore use the installed main-model defaults. | Include the two main settings when present. Tests parse generated CLI values as TOML and check model/effort, actual role-file paths, thread settings, and disabled browser/computer features. |
| P2 | `harness/data.py:clean_sales_csv` date validation | `transaction_id,date,region,units,revenue\nA,20261031,East,1,2.00\n` accepts one row despite the documented `YYYY-MM-DD` format; Python accepts compact ISO dates. | Compare parsed canonical date with input. Data regression rejects compact/week dates and retains a following valid row. |
| P2 | `harness/data.py:clean_sales_csv` currency serialization | With the same header, `A,2026-10-31,East,1,1E+40` raises `decimal.InvalidOperation` during quantization instead of producing a row issue, aborting the import. | Perform quantization inside the handled validation boundary. Data regression expects `invalid_number` and continues importing valid rows. |
| P2 | `harness/demo.py:create_server.Handler.do_PATCH` | Run an ephemeral loopback server, PATCH `/api/tasks/1` with `{"status":"blocked"}`, and capture `server.handle_error`. Baseline sends HTTP 400 then raises `UnboundLocalError`, because execution continues to the unassigned `task` variable. | Return after the 400 response. HTTP regression checks the response, captures handler errors, and confirms subsequent requests remain usable. |
| P2 | `examples/bugfix/starter/tickets.py:count_open` | `python3 -m unittest -v` from the starter directory exits 1: `AssertionError: 1 != 2`. Slicing `tickets[:-1]` omits the final record, also making a single open ticket count as zero. | Preserve the intentionally broken starter. Separate `solution/tickets.py` iterates every record; the original regression plus empty/singleton/mixed/missing-status and non-mutation cases pass there. |

Severity denotes practical consequence: P1 compromises concurrent ownership or
the specified model-selection mode; P2 is an incorrect result or reachable
exception with narrower inputs. These are local development-tool findings, not
claims about platform-level controls.

## Reproduction and repair commands

Commands below run from the repository root unless a directory is stated.

```sh
python3 -m unittest discover -s examples/bugfix/starter -v
python3 -m unittest discover -s examples/bugfix/solution -v
python3 -m unittest discover -s tests -p test_harness.py -v
make check
git diff --check
```

Observed results at review time:

| Check | Exit | Evidence |
| --- | --- | --- |
| Starter suite (`python3 -m unittest -v` from `examples/bugfix/starter`) | 1, expected | One test fails with `1 != 2`; starter source preserved. |
| Solution suite (`python3 -m unittest -v` from `examples/bugfix/solution`) | 0 | Three regression tests pass. |
| Harness regression suite | 0 | Twelve tests pass in the final integrated suite, including checked-in inherited configuration and malformed-plan structures. |
| `make check` | 0 | Final reviewer run passes all 22 tests; `harness validate` returns `{"ok": true, "errors": []}`. This includes the additional numeric and malformed-plan repairs described below. |
| `git diff --check` | 0 | No whitespace errors in the integrated working-tree diff at inspection time. |

## Additional boundary findings, repairs, and scope limits

Two further boundaries were independently reproduced after the first repair
checks, reported to the lead, repaired in the integrated code, and rechecked:

1. `aggregate_by_region` can fail on input already accepted by the cleaner.
   Two rows in region `East`, each with units `1` and revenue
   `99999999999999999999999999.99`, produce two accepted rows and no issues,
   then aggregation raises `decimal.InvalidOperation`. Default Decimal
   precision rounds the total and the later cents quantization fails. This
   is P2 for extreme accepted currency values. The repair uses sufficient local
   Decimal precision for addition and ratio calculation. The final data
   regression asserts the exact large total and cents-rounded per-unit result;
   it passes in the final `make check` run.
2. `validate_plan({"tasks": None})`, or a complete task with
   `"depends_on": None`, raises uncaught `TypeError` rather than returning
   errors. This is P2 for malformed JSON contracts. The repair checks plan,
   task-list, task-ID, path-list and dependency-list structure before traversal.
   The final harness regression covers null/scalar/container errors and
   non-string list members and passes without exceptions.

All findings listed above are repaired for the reproduced cases, with the
starter deliberately preserved and its solution kept separately. The review
does not establish exhaustive numeric-range support, arbitrary malformed
plan handling, cross-platform path semantics, or actual model-routing runtime
availability. Config tests establish generated and launch arguments only. No
live model call, visual browser review, deployment, or platform-permission
change was performed by this reviewer. Benchmark evidence, if separately
produced, requires its own runtime audit and must not be inferred from these
unit tests. `harness/benchmark.py` remained under active implementation during
this review and is outside this review's completion claim; it requires a
separate inspection after native run results are available.
