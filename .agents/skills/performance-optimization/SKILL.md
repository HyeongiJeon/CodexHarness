---
name: performance-optimization
description: "Measure and improve the speed or memory of existing code with before/after evidence; use when a specific slow path, algorithm, query or data volume must be optimized without changing behavior."
---
# Performance Optimization

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Target operation, input size/shape, success criterion (time/memory), existing tests, isolated working copy.

Read [references/measurement.md](references/measurement.md) for measurement rules and the complexity checklist.

## Procedure

1. Agree target and success criterion with the user; fix a correctness oracle (existing tests or a saved reference output).
2. Measure first: `python3 -m harness measure --label before --out before.json -- <command>`; find the real hotspot with a profiler before changing code.
3. Compare options (algorithm/data structure, SQL index or JOIN shape, I/O batching, caching) by expected gain, risk and memory; implement only the approved one.
4. Re-measure under identical conditions with `--baseline before.json`; run all existing tests and boundary inputs.

**Output contract:** Hotspot evidence, change summary, before/after table (input size, repeats, median, range, peak RSS), correctness result, limits.

**Tools:** `harness measure`, language profilers already installed, `data profile`, SQLite `EXPLAIN QUERY PLAN`.

**Verification:** `status=ok` with identical stdout hash; `distinguishable=true` before claiming a speed-up; full tests green.

**Failure handling:** Any changed output or failing test makes the optimization a failure: revert it. Do not claim gains inside noise or from a single run.

**Related skills:** [systematic-debugging](../systematic-debugging/SKILL.md), [completion-verification](../completion-verification/SKILL.md), [data-processing](../data-processing/SKILL.md).
