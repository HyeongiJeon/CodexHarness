---
name: visualization-and-dashboard
description: "Create charts or a dashboard from verified data; use for metric comparisons, filters, or visual explanations."
---
# Visualization And Dashboard

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Audience question, verified data/metric definitions, target artifact/application, interaction requirements.

For chart selection, metrics, or interactive filters, read [references/chart-checks.md](references/chart-checks.md).

## Procedure

1. Define the comparison, data grain, units, denominator, timezone, and filter semantics before choosing charts.
2. Choose forms exposing the comparison; use honest scales, direct labels, readable legends, and explicit missing-data handling.
3. Connect charts, totals, tables, and filters to the same data model. Provide loading, empty, and error states.
4. Check plotted values against source rows and independent calculations; inspect clipping, labels, responsive layout, and filter/reset behavior.

**Output contract:** Working dashboard or standalone chart, metric definitions, reproducible source, data/rendering evidence.

**Tools:** Project chart library for apps or installed plotting tools for shareable artifacts; manual local preview/viewers and local HTTP requests. Do not automate browser or GUI interaction.

**Verification:** Totals reconcile; filters update all relevant views consistently; axes/units and exported labels remain correct.

**Failure handling:** Mark unsupported metrics unavailable with reasons. Never present invented chart values as measured data.

**Related skills:** [data-processing](../data-processing/SKILL.md), [frontend-design](../frontend-design/SKILL.md), [web-application-development](../web-application-development/SKILL.md), [completion-verification](../completion-verification/SKILL.md).
