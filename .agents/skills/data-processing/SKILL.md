---
name: data-processing
description: "Transform, clean, join, or analyze structured data with traceable assumptions; use when dataset or metric correctness is central."
---
# Data Processing

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Source files, schema, transformation rules, output format, size/quality constraints.

For joins, messy schemas, large files, or derived metrics, read [references/data-contracts.md](references/data-contracts.md).

## Procedure

1. Inspect actual encoding, schema/types, row counts, representative records, and missing values before transforming.
2. Define keys, units, null/duplicate policy, and expected row-count changes. Preserve sources and meaningful deterministic ordering.
3. Build a repeatable pipeline; stream or chunk when memory requires it. Reject or quarantine malformed records explicitly.
4. Validate schema, counts, uniqueness, join cardinality, totals, and representative hand calculations; save and reopen the requested artifact.

**Output contract:** Reproducible transformation code, final dataset/analysis, assumptions, input/output quality evidence.

**Tools:** Installed Python/SQL/data tools appropriate to volume; local inspection without external upload.

**Verification:** Denominators and units are explicit; joins do not unexpectedly multiply rows; output reopens in its target format.

**Failure handling:** Report affected records and rule choices for inconsistent data. Never invent values or silently coerce invalid records into plausible results.

**Related skills:** [document-processing](../document-processing/SKILL.md), [visualization-and-dashboard](../visualization-and-dashboard/SKILL.md), [decision-and-evidence-recording](../decision-and-evidence-recording/SKILL.md), [completion-verification](../completion-verification/SKILL.md).
