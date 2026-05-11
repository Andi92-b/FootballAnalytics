---
name: "design-handoff"
description: "Produces design-spec.md — the complete artifact that travels FROM GitHub Copilot TO Claude Design. Contains component brief, props interface, data shape, visual requirements, reference chart images, and acceptance criteria. Fires at GATE: DESIGN."
version: 0.1.0
capabilities:
  - "design-spec.md written to frontend/design-spec.md"
  - "Component brief: what the component does, who uses it, where it lives in the page"
  - "Full TypeScript PizzaChartProps interface"
  - "Exact API response data shape with example values"
  - "Visual requirements pulled from pizza-chart-visual-spec.md (slice order, colours, typography)"
  - "Acceptance criteria: measurable conditions Claude Design should verify before returning the component"
triggers:
  - "design handoff"
  - "brief for claude design"
  - "prepare design spec"
  - "handoff to design"
  - "GATE: DESIGN"
  - "write design-spec"
last_updated: 2026-05-11
---

# Design Handoff

Produces the `design-spec.md` artifact that briefs Claude Design on what to build.
This skill fires at **GATE: DESIGN** — only after the API endpoint is stable.

**Before executing:** Read `.claude/shared-references/design/claude-design-handoff-guide.md`
and `.claude/shared-references/design/pizza-chart-visual-spec.md`.

---

## Step 1 — Confirm GATE: API is passed

Verify that `GET /api/player/{name}` returns a valid response before proceeding.
If not, stop and tell the operator to complete `player-endpoint` first.

---

## Step 2 — Read pizza-component spec output

Load `frontend/component-spec.md` (output of `pizza-component` skill).

---

## Step 3 — Read visual spec and handoff guide

Load `.claude/shared-references/design/pizza-chart-visual-spec.md`.
Load `.claude/shared-references/design/claude-design-handoff-guide.md`.

---

## Step 4 — Write design-spec.md

Write `frontend/design-spec.md` with sections as specified in `claude-design-handoff-guide.md`:
- Component brief
- Props interface
- Data shape + example JSON
- Visual requirements
- Acceptance criteria

---

## Step 5 — Print handoff message

Print:
```
GATE: DESIGN — design-spec.md written to frontend/design-spec.md.
Hand this file to Claude Design with the instruction: "Build the PizzaChart component per this spec."
Return here (GitHub Copilot) when Claude Design has returned the component file(s).
```
