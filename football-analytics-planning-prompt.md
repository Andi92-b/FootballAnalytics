# Planning Prompt — Football Analytics App (Pizza Charts)

> Copy everything below this line into your AI coding agent's planning/architect mode.

---

## Context

I am building a full-stack football analytics web app. The first feature is **player pizza charts** — position-specific percentile visualisations across 17 metrics, sourced from FBref public data (Opta-powered, no API key required).

This project should be structured as an **AI-assisted development harness**, following the same pattern as an existing project called CreatorAI in my codebase. That pattern uses:
- A `CLAUDE.md` file at the repo root defining identity, a skill-routing protocol, and an execution protocol
- An atomic skill library under `.claude/skills/<domain>/<skill-name>/SKILL.md`
- Shared reference documents under `.claude/shared-references/` loaded on demand
- Claude Code hooks under `.claude/hooks/` and `.claude/settings.json`
- A Python library under `.libs/` installed into `.venv/`

**Your task in planning mode is to produce:**
1. The complete project folder structure
2. A draft `CLAUDE.md` for this project
3. A skill map (table of all skills with what they produce)
4. A skill file stub for every skill (frontmatter + section headers only — no implementation yet)
5. The content of all shared-reference files (these contain domain knowledge, not code)
6. The `settings.json` hook configuration
7. A numbered implementation sequence with explicit AI-tool handoff gates

Do not implement any code yet. Plan only.

---

## What the app does

Given a player name and season, the app:
1. Fetches the player's stats from FBref across multiple stat tables
2. Determines the player's position and selects the appropriate metric subset
3. Computes percentile ranks within the player's positional peer group (same league + position)
4. Returns a pizza chart — a polar/radar chart where each slice represents one metric's percentile score (0–99)
5. Displays the chart in a web UI where a user can type a player name and get their chart

The long-term roadmap includes: player comparison view, position-filtered leaderboards, season-over-season tracking, and integration into the existing CreatorAI video pipeline for automated data-viz scenes. Design the harness with this extensibility in mind, but implement only the pizza chart feature first.

---

## Pre-decided design decisions

### Metrics (17 total, across 4 categories)

These are fixed. The coding agent must not invent or change them.

**Defence (7 metrics)**
| Metric | FBref source | Formula / column |
|---|---|---|
| Front-foot defending | Defensive actions + Misc | (Tkl + Challenges.Att + Fls + Int + Blocks.Pass) / 90, ÷ (1 – team_poss) |
| Tackle success | Defensive actions | Challenges.Tkl% (already computed by FBref) |
| Back-foot defending | Defensive actions | (Blocks.Sh + Clr) / 90, ÷ (1 – team_poss) |
| Loose ball recoveries | Misc | Recov / 90 |
| Aerial volume | Misc | (Aerial.Won + Aerial.Lost) / 90 |
| Aerial success | Misc | Aerial.Won% |
| One-v-one defending *(FB only)* | Defensive actions | Challenges.Tkl% (same column, different position filter) |

**Possession (3 metrics)**
| Metric | FBref source | Formula |
|---|---|---|
| Link-up play | Passing | (Short.Att + Med.Att) / Total.Att |
| Ball retention | Passing | Total.Cmp% |
| Launched passes | Passing | Long.Att / Total.Att |

**Progression (6 metrics)**
| Metric | FBref source | Formula |
|---|---|---|
| Creative threat | Standard + Advanced passing | (0.8 × xAG + 0.2 × Ast) / 90 |
| Cross volume | Pass types + Possession | Crs / (Att3rd_touches / 100) |
| Dribble volume | Possession | Dribbles.Att / (Touches / 100) |
| Pass progression | Passing | Prog / Total.Att |
| Carry progression | Possession | PrgC / Carries |
| Progressive receptions | Possession (receiving) | PrgR / Rec |

**Attack (4 metrics)**
| Metric | FBref source | Formula |
|---|---|---|
| Goal threat | Standard + Shooting | (0.7 × npxG + 0.3 × (Gls – PK)) / 90 |
| Shot frequency | Shooting + Possession | Sh / (Touches / 100) |
| Box threat | Possession | AttPen_touches / (Mid3rd_touches + Att3rd_touches) |
| Shot quality | Shooting | npxG/Sh (pre-computed by FBref) |

### Position matrix — which metrics appear per position

| Metric | CB | FB | DM | CM | AM | W | CF |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Front-foot defending | ✓ | ✓ | ✓ | ✓ | ~ | – | – |
| Tackle success | ✓ | ✓ | ✓ | ✓ | – | – | – |
| Back-foot defending | ✓ | ✓ | ✓ | – | – | – | – |
| Loose ball recoveries | ✓ | ✓ | ✓ | ✓ | – | – | – |
| Aerial volume | ✓ | ~ | ✓ | – | – | – | ✓ |
| Aerial success | ✓ | ~ | ✓ | – | – | – | ✓ |
| One-v-one defending | – | ✓ | – | – | – | – | – |
| Link-up play | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | – |
| Ball retention | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Launched passes | ✓ | ~ | ✓ | ✓ | – | – | – |
| Creative threat | – | ~ | – | ✓ | ✓ | ✓ | ✓ |
| Cross volume | – | ✓ | – | ~ | ✓ | ✓ | – |
| Dribble volume | – | ✓ | – | ✓ | ✓ | ✓ | – |
| Pass progression | ✓ | ~ | ✓ | ✓ | ✓ | – | – |
| Carry progression | – | ✓ | – | ✓ | ✓ | ✓ | – |
| Progressive receptions | – | ✓ | ~ | ✓ | ✓ | ✓ | ✓ |
| Goal threat | – | – | – | ~ | ✓ | ✓ | ✓ |
| Shot frequency | – | – | – | ~ | ✓ | ✓ | ✓ |
| Box threat | – | – | – | – | ~ | ✓ | ✓ |
| Shot quality | – | – | – | – | ✓ | ✓ | ✓ |

`✓` = always shown, `~` = shown for this position variant, `–` = not shown

Positions map to FBref position strings as follows:
- CB → `CB`
- FB → `RB`, `LB`, `RWB`, `LWB`
- DM → `DM`
- CM → `CM`, `MF`
- AM → `AM`
- W → `RW`, `LW`, `LM`, `RM`
- CF → `CF`, `FW`, `ST`

### FBref tables to scrape (all via `soccerdata` Python library)

For each player, scrape these FBref stat tables for the relevant season and league:
- `standard` — goals, assists, xG, xAG, minutes, npxG
- `shooting` — Sh, npxG, npxG/Sh
- `passing` — total/short/medium/long Att + Cmp%, Prog, xAG, Ast
- `passing_types` — Crs
- `defense` — Tkl, Challenges (Att, Tkl%), Blocks (Sh, Pass), Int, Clr
- `possession` — Touches by zone (Def3rd, Mid3rd, Att3rd, AttPen), Dribbles (Att), Carries (PrgC, total), Receiving (PrgR, Rec)
- `misc` — Fls, Aerial (Won, Lost, Won%), Recov
- `team_stats` — team possession % (for possession-adjustment of defensive metrics)

The `soccerdata` library scrapes FBref without an API key. Use `FBref` class from `soccerdata`. Cache all raw scrape results as JSON in `.cache/fbref/` to avoid re-scraping.

### Tech stack

- **Backend:** Python 3.11+, FastAPI, `soccerdata`, `pandas`, `scipy`, `mplsoccer`
- **Frontend:** Next.js 14 (App Router), React, TypeScript, Tailwind CSS
- **Pizza chart rendering:** Server-side SVG via `mplsoccer.PyPizza`, returned as inline SVG string from the API. This enables Claude Design to work on a React component that receives SVG as a prop or renders a pure React polar chart later.
- **Cache:** JSON file cache under `.cache/` (no database for MVP)
- **Python library:** `football_core` under `.libs/`, installed into `.venv/`
- **Env vars:** `.env` file with `FBREF_CACHE_DIR`, `APP_ENV`, `LOG_LEVEL`

---

## AI tool handoff strategy

This project is built across multiple AI tools. The harness must support clean handoffs. Define these explicitly in the skill map and execution protocol:

| Gate | Trigger | From tool | To tool | Deliverable |
|---|---|---|---|---|
| `GATE: DATA` | `fetch-player` + `compute-percentiles` work for one test player | GitHub Copilot | — | Verified JSON output: `{ player, position, season, metrics: { name, raw, percentile }[] }` |
| `GATE: API` | `player-endpoint` returns valid pizza data at `/api/player/{name}` | GitHub Copilot | — | OpenAPI spec + curl example output |
| `GATE: DESIGN` | API is stable; pizza component spec written | GitHub Copilot | **Claude Design** | `design-spec.md` — component props interface, data shape, visual requirements, reference chart images |
| `GATE: WIRE` | Claude Design returns a React component | **Claude Design** | GitHub Copilot | Component file(s) + design tokens → wire to API via `wire-component` skill |
| `GATE: SHIP` | End-to-end flow works; type a name, see a chart | GitHub Copilot | — | Working localhost demo |

The `design-handoff` skill produces the `design-spec.md` artifact that travels TO Claude Design. The `wire-component` skill receives the designed component and wires it to the backend. These are the two seams in the workflow.

---

## Skill map (what the agent must produce stubs for)

| Domain | Skill | What it produces |
|---|---|---|
| Setup | `install` | Python venv + soccerdata + FastAPI + Next.js deps |
| Setup | `scaffold-app` | Full-stack skeleton with folder structure and config files |
| Data | `fetch-player` | Raw FBref stats JSON for one player + season |
| Data | `compute-percentiles` | Percentile scores (0–99) for all metrics in position profile |
| Data | `position-profile` | Metric subset selection for a given FBref position string |
| Viz | `render-pizza` | Pizza chart SVG string for one player via mplsoccer.PyPizza |
| API | `player-endpoint` | FastAPI route: `/api/player/{name}?season=2024&league=Premier+League` |
| UI | `pizza-component` | React component spec: props, data contract, visual behaviour |
| UI | `design-handoff` | `design-spec.md` artifact for Claude Design — component brief, data shape, visual reference |
| UI | `wire-component` | Imports a designed React component and connects it to the player API endpoint |

---

## Shared references to create (domain knowledge, not code)

| File | Contents |
|---|---|
| `metrics/metric-definitions.md` | All 17 metrics: definition, FBref table, formula, what high/low means tactically |
| `metrics/position-matrix.md` | The full position × metric matrix above — source of truth for `position-profile` skill |
| `fbref/table-guide.md` | Which soccerdata table names map to which FBref stat pages; column naming quirks; known scraping gotchas |
| `fbref/soccerdata-recipes.md` | Canonical Python snippets for fetching each of the 8 required tables; how to join them on player name + season |
| `design/pizza-chart-visual-spec.md` | Visual grammar of a pizza chart: slice order (D → P → Pr → A, clockwise), colour palette per category, label placement, percentile shading, typography norms |
| `design/claude-design-handoff-guide.md` | How to write a `design-spec.md` that Claude Design can act on: required sections, what to include, link to reference chart images |

---

## Hooks to configure

Follow the CreatorAI pattern exactly:
- `UserPromptSubmit` → `session-start.sh` (prints skill-routing reminder once per session)
- `PostToolUse` on Bash → `log-skill.sh` (logs which skill was active)
- `SessionEnd` → `analyze-session.py` (summarises what was built, what to continue next session)
- `PermissionRequest` on Bash → `guard.sh` (blocks destructive commands: `rm -rf`, `DROP TABLE`, etc.)

---

## Expected planning output

Produce the following — in order, as files you will write:

1. **`CLAUDE.md`** — full draft, following the CreatorAI identity/protocol/structure pattern, adapted for this project
2. **Project folder tree** — complete structure from repo root, annotated
3. **All 10 skill stubs** — `.claude/skills/<domain>/<name>/SKILL.md` with full frontmatter and section headers, no implementation code yet
4. **All 6 shared-reference files** — full content (these are docs, not code — write them completely)
5. **`.claude/settings.json`** — hook registrations
6. **Hook script stubs** — `.claude/hooks/` with the 4 scripts as empty shells with comments
7. **`.libs/football_core/` structure** — Python package layout only (no implementation): what modules exist and what each will contain
8. **Implementation sequence** — numbered steps from zero to working pizza chart, with GATE markers at each AI tool handoff point

After producing all of the above, pause and ask: "Harness scaffold complete. Review the structure and skill map. Tell me to start implementing at step 1 when ready."
