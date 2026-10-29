---
name: frontend-design
description: "Design or refine web visual hierarchy and interaction states; use when layout, consistency, responsiveness, or usability is required."
---
# Frontend Design

Original project and exam instructions take precedence over this workflow.
Exam profile: no Astra, computer-use, push, external uploads, or AI-prohibited written answers.

**Inputs:** User journey, existing UI/design system, supplied assets, target viewports, accessibility requirements.

When building a page or checking responsive/interactive states, read [references/interface-checks.md](references/interface-checks.md).

## Procedure

1. Inspect existing components, tokens, fonts, and assets; preserve the established visual system unless replacement is requested.
2. Choose clear information hierarchy and reusable spacing/type/color decisions; make the primary action and current state legible.
3. Implement responsive layout plus loading, empty, error, focus, and disabled states for required interactions.
4. Inspect actual rendered output through a user-operated local preview or supplied screenshots; validate semantic markup and keyboard interaction. Do not automate browser or GUI interaction.

**Output contract:** Implemented UI in the existing stack, rendering evidence when available, and unverified visual states.

**Tools:** HTML/CSS, project components, supplied/local assets, manual local preview and screenshots; no browser/GUI/computer-use automation or external upload.

**Verification:** Main flow works at narrow/wide widths; labels, focus, contrast, wrapping, and required states remain usable.

**Failure handling:** Without rendering tools, run build/structural checks and state the visual limitation; do not claim pixel accuracy.

**Related skills:** [web-application-development](../web-application-development/SKILL.md), [visualization-and-dashboard](../visualization-and-dashboard/SKILL.md), [completion-verification](../completion-verification/SKILL.md).
