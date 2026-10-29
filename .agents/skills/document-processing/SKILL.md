---
name: document-processing
description: "Extract, transform, create, or validate local documents; use when PDF, DOCX, spreadsheet, or presentation structure and layout matter."
---
# Document Processing

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Original documents, requested changes, target format, layout/content requirements, local tools.

Read [references/formats.md](references/formats.md) and use only the subsection for the requested format.

## Procedure

1. Identify the actual format and inspect representative pages/sheets/slides; distinguish searchable text from scans.
2. Use a local parser/editor preserving required structure; work on a copy and retain source provenance.
3. Apply requested transformations while preserving required reading order, formulas, annotations, dimensions, and names.
4. Reopen output and inspect content plus rendered pages/sheets/slides when layout matters; validate counts, tables, and required values.

**Output contract:** Requested artifact, reusable transformation instructions/code where needed, content/rendering evidence, extraction limits.

**Tools:** Available local document libraries and conversion/rendering CLIs; preserve originals and avoid external upload.

**Verification:** Output opens, content is retained, structure is valid, and visual inspection covers representative/changed pages.

**Failure handling:** If parsing loses structure or OCR is uncertain, preserve originals and flag affected locations. Text extraction alone does not prove layout fidelity.

**Related skills:** [data-processing](../data-processing/SKILL.md), [visualization-and-dashboard](../visualization-and-dashboard/SKILL.md), [completion-verification](../completion-verification/SKILL.md).
