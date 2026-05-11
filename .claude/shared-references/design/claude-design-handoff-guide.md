# Claude Design Handoff Guide

How to write a `design-spec.md` that Claude Design can act on to produce a production-ready
React component. Follow this guide when executing the `design-handoff` skill.

---

## What Claude Design needs

Claude Design (a visual/UI-specialised AI mode) excels at translating a clear visual brief
into production React + Tailwind code. It works best when given:

1. **What to build** — component name, purpose, where it lives in the UI
2. **What data it receives** — TypeScript props interface, example JSON
3. **How it should look** — colour palette, typography, layout, visual states
4. **How it should behave** — loading, error, empty, and data-loaded states
5. **What "done" looks like** — acceptance criteria it can verify itself

Claude Design does **not** need:
- Business logic or data-fetching code (that is wired later by `wire-component`)
- API route implementations
- Backend code of any kind
- A full design system (keep Tailwind utility classes and inline styles minimal)

---

## Required sections in `design-spec.md`

### 1. Component brief

```markdown
## Component Brief

**Component name:** `PizzaChart`
**File:** `frontend/src/components/PizzaChart.tsx`
**Purpose:** [one sentence]
**Context:** [where it sits in the page layout — e.g. "below the PlayerSearch input, centred"]
```

### 2. Props interface

Provide the exact TypeScript interface. This is the contract Claude Design must implement against.

```markdown
## Props Interface

\`\`\`typescript
export interface MetricResult {
  name: string;
  category: "Defence" | "Possession" | "Progression" | "Attack";
  raw: number;
  percentile: number; // 0–99
}

export interface PizzaChartProps {
  svg: string;                    // Raw SVG string from API — primary render path
  player: string;
  position: string;               // e.g. "CB", "FB"
  season: string;                 // e.g. "2024-25"
  league: string;                 // e.g. "ENG-Premier League"
  metrics: MetricResult[];        // For accessible metric list below chart
  isLoading: boolean;
  error: string | null;
}
\`\`\`
```

### 3. Data shape + example

Provide an example JSON payload so Claude Design can understand what real data looks like:

```markdown
## Example API Response

\`\`\`json
{
  "player": "Virgil van Dijk",
  "position": "CB",
  "season": "2024-25",
  "league": "ENG-Premier League",
  "metrics": [
    { "name": "Front-foot defending", "category": "Defence", "raw": 4.21, "percentile": 78 },
    { "name": "Tackle success",       "category": "Defence", "raw": 65.3, "percentile": 62 }
  ],
  "svg": "<svg xmlns=..."
}
\`\`\`
```

### 4. Visual requirements

Reference the visual spec and spell out the non-negotiables:

```markdown
## Visual Requirements

- Render the `svg` prop via `dangerouslySetInnerHTML={{ __html: svg }}` inside a responsive container
- Container: `max-w-[600px] w-full mx-auto`
- The SVG is square — maintain 1:1 aspect ratio
- Background: white (`bg-white`)
- Category colours per `pizza-chart-visual-spec.md`:
  | Category    | Hex      |
  |-------------|----------|
  | Defence     | #E63946  |
  | Possession  | #457B9D  |
  | Progression | #2D6A4F  |
  | Attack      | #E07B39  |
- Metric list below the chart: small font, dimmed text, category colour dot per metric
```

### 5. State specifications

```markdown
## States

| State     | What to render |
|-----------|----------------|
| Loading   | Centred animated spinner, same container size as chart |
| Error     | `"Could not load player data: {error}"` in red-tinted box |
| Empty     | `"Search for a player above"` in dimmed text, centred |
| Data      | SVG chart + accessible metric list below |
```

### 6. Accessibility requirements

```markdown
## Accessibility

- Chart wrapper: `role="img"` `aria-label="{player} pizza chart"`
- Metric list: `role="list"`, each item `role="listitem"`
- Loading region: `aria-live="polite"` `aria-busy={isLoading}`
```

### 7. Acceptance criteria

These are the conditions Claude Design should verify before returning the component:

```markdown
## Acceptance Criteria

- [ ] Component renders SVG without distortion at 300px, 500px, 600px widths
- [ ] Loading spinner visible when `isLoading=true`, SVG hidden
- [ ] Error message visible when `error` is non-null, SVG hidden
- [ ] Empty state message visible when `svg=""` and not loading
- [ ] Accessible metric list present below the chart with correct `role` attributes
- [ ] No TypeScript errors (`tsc --noEmit` passes)
- [ ] No console errors on render
- [ ] Tailwind only — no custom CSS files
```

---

## What to say when handing off to Claude Design

Copy-paste this message when opening a Claude Design session:

```
Build the PizzaChart React component per the spec in `frontend/design-spec.md`.
Return: `frontend/src/components/PizzaChart.tsx` (and any sub-components).
Do not add data fetching — the component is purely presentational.
Check all acceptance criteria before returning the file.
```

---

## After Claude Design returns the component

1. Copy the returned file(s) into `frontend/src/components/`
2. Run `tsc --noEmit` in `frontend/` — fix any type errors
3. Proceed to the `wire-component` skill (GATE: WIRE)
