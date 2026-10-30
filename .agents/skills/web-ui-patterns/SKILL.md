---
name: web-ui-patterns
description: "Apply compact, reusable UI patterns (dashboard layout, tables, forms, modals, states, responsive, accessibility) to build a polished screen quickly in the project's own framework."
---
# Web UI Patterns

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** Core screen(s), existing framework and styling, real data contract, required viewports.

Read [references/patterns.md](references/patterns.md) for the pattern checklist and plain-HTML snippets; translate them to the project's framework.

## Procedure

1. Inspect existing components, CSS variables, and design system; reuse them. Do not introduce a framework or UI library the project lacks.
2. Fix the tokens first: one spacing scale, two font sizes for body/heading hierarchy, a neutral palette plus one accent, and semantic colors for success/error.
3. Build the main screen from the patterns: layout shell, data table with search/filter/sort, form with inline validation, status messages.
4. Bind every control to real data or API state. Provide loading, empty, error, disabled, and success states for each async region.
5. Check narrow and wide layout, keyboard order, visible focus, labels, and contrast; defer polish below the core flow.

**Output contract:** Working screens consistent with the project's style, state coverage list, and the viewport/keyboard checks that remain for the user's manual preview.

**Tools:** Project framework and CSS, local HTTP, user-operated preview; no browser or GUI automation.

**Verification:** Controls change real state; the five async states are reachable; labels and focus work; layout does not clip at narrow width (manual).

**Failure handling:** If time is short, keep semantic HTML, tokens, and states and drop animation and decoration. Never ship a control that does nothing.

**Related skills:** [frontend-design](../frontend-design/SKILL.md), [web-application-development](../web-application-development/SKILL.md), [visualization-and-dashboard](../visualization-and-dashboard/SKILL.md), [web-flow-verification](../web-flow-verification/SKILL.md).
