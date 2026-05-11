# Metric Definitions

Source of truth for all 17 metrics used in the pizza chart system.
**Do not modify formulae without updating the position matrix simultaneously.**

---

## Defence (7 metrics)

### 1. Front-foot defending

| Field | Value |
|-------|-------|
| **FBref table(s)** | `defense`, `misc` |
| **Formula** | `(Tkl + Challenges.Att + Fls + Int + Blocks.Pass) / 90 ÷ (1 – team_poss)` |
| **Possession-adjusted** | Yes — divide by `(1 – team_poss)` to control for how often the player's team is off the ball |
| **High score means** | Player is very active in pressing, tackling challenges, intercepting, and blocking passes when their team doesn't have the ball |
| **Low score means** | Passive defensively; rarely engages when out of possession |

**Columns:** `defense.Tkl`, `defense.Challenges.Att`, `misc.Fls`, `defense.Int`, `defense.Blocks.Pass`
**team_poss:** `team_stats.Poss` (as a decimal, e.g. 0.55 for 55%)

---

### 2. Tackle success

| Field | Value |
|-------|-------|
| **FBref table(s)** | `defense` |
| **Formula** | `Challenges.Tkl%` (pre-computed by FBref) |
| **Possession-adjusted** | No |
| **High score means** | Player wins a high proportion of the tackles they attempt |
| **Low score means** | Often dives in and loses the ball; poor tackle timing |

**Columns:** `defense.Challenges.Tkl%`

---

### 3. Back-foot defending

| Field | Value |
|-------|-------|
| **FBref table(s)** | `defense` |
| **Formula** | `(Blocks.Sh + Clr) / 90 ÷ (1 – team_poss)` |
| **Possession-adjusted** | Yes |
| **High score means** | Player frequently blocks shots and clears the ball in last-ditch defensive actions |
| **Low score means** | Rarely in position to block shots or produce clearances |

**Columns:** `defense.Blocks.Sh`, `defense.Clr`

---

### 4. Loose ball recoveries

| Field | Value |
|-------|-------|
| **FBref table(s)** | `misc` |
| **Formula** | `Recov / 90` |
| **Possession-adjusted** | No |
| **High score means** | Player is excellent at winning second balls and contested possessions |
| **Low score means** | Rarely involved in loose ball situations |

**Columns:** `misc.Recov`

---

### 5. Aerial volume

| Field | Value |
|-------|-------|
| **FBref table(s)** | `misc` |
| **Formula** | `(Aerial.Won + Aerial.Lost) / 90` |
| **Possession-adjusted** | No |
| **High score means** | Player contests many aerial duels; physically dominant in the air |
| **Low score means** | Avoids aerial contests; ground-based player |

**Columns:** `misc.Aerial.Won`, `misc.Aerial.Lost`

---

### 6. Aerial success

| Field | Value |
|-------|-------|
| **FBref table(s)** | `misc` |
| **Formula** | `Aerial.Won%` (pre-computed by FBref) |
| **Possession-adjusted** | No |
| **High score means** | Wins most of the aerial duels they contest |
| **Low score means** | Gets into aerial battles but typically loses them |

**Columns:** `misc.Aerial.Won%`

---

### 7. One-v-one defending *(Full-back only)*

| Field | Value |
|-------|-------|
| **FBref table(s)** | `defense` |
| **Formula** | `Challenges.Tkl%` (same column as Tackle success, applied to FB position filter) |
| **Possession-adjusted** | No |
| **High score means** | Full-back wins individual defensive duels against wide attackers |
| **Low score means** | Gets beaten in 1v1 situations on the flank |
| **Note** | This metric only appears in the FB position profile, where `Challenges.Tkl%` carries a more specific positional interpretation |

**Columns:** `defense.Challenges.Tkl%`

---

## Possession (3 metrics)

### 8. Link-up play

| Field | Value |
|-------|-------|
| **FBref table(s)** | `passing` |
| **Formula** | `(Short.Att + Med.Att) / Total.Att` |
| **Possession-adjusted** | No |
| **High score means** | Player's passing is predominantly short/medium range; plays through-the-lines or recycles possession |
| **Low score means** | Plays a higher proportion of long balls |

**Columns:** `passing.Short.Att`, `passing.Med.Att`, `passing.Total.Att`

---

### 9. Ball retention

| Field | Value |
|-------|-------|
| **FBref table(s)** | `passing` |
| **Formula** | `Total.Cmp%` (pre-computed by FBref) |
| **Possession-adjusted** | No |
| **High score means** | Very accurate passer; keeps possession under pressure |
| **Low score means** | Gives the ball away often when passing |

**Columns:** `passing.Total.Cmp%`

---

### 10. Launched passes

| Field | Value |
|-------|-------|
| **FBref table(s)** | `passing` |
| **Formula** | `Long.Att / Total.Att` |
| **Possession-adjusted** | No |
| **High score means** | Player frequently plays long balls; direct distributor |
| **Low score means** | Rarely plays long; short-passing style |

**Columns:** `passing.Long.Att`, `passing.Total.Att`

---

## Progression (6 metrics)

### 11. Creative threat

| Field | Value |
|-------|-------|
| **FBref table(s)** | `standard`, `passing` |
| **Formula** | `(0.8 × xAG + 0.2 × Ast) / 90` |
| **Possession-adjusted** | No |
| **High score means** | Player consistently creates goal-scoring chances; expected goal assists are high |
| **Low score means** | Rarely generates direct goal-creating actions |

**Columns:** `passing.xAG`, `standard.Ast`

---

### 12. Cross volume

| Field | Value |
|-------|-------|
| **FBref table(s)** | `passing_types`, `possession` |
| **Formula** | `Crs / (Att3rd_touches / 100)` |
| **Possession-adjusted** | No (normalised by own attacking third touches instead) |
| **High score means** | When the player has the ball in the final third, they cross frequently |
| **Low score means** | Rarely crosses; cuts inside or plays short |

**Columns:** `passing_types.Crs`, `possession.Touches.Att3rd`

---

### 13. Dribble volume

| Field | Value |
|-------|-------|
| **FBref table(s)** | `possession` |
| **Formula** | `Dribbles.Att / (Touches / 100)` |
| **Possession-adjusted** | No (normalised by total touches) |
| **High score means** | Player attempts many dribbles relative to how much they touch the ball |
| **Low score means** | Rarely takes players on; predominantly a passing outlet |

**Columns:** `possession.Dribbles.Att`, `possession.Touches`

---

### 14. Pass progression

| Field | Value |
|-------|-------|
| **FBref table(s)** | `passing` |
| **Formula** | `Prog / Total.Att` |
| **Possession-adjusted** | No |
| **High score means** | High proportion of the player's passes advance the ball significantly up the pitch |
| **Low score means** | Mostly sideways/backward passer; maintains possession without advancing it |

**Columns:** `passing.Prog`, `passing.Total.Att`

---

### 15. Carry progression

| Field | Value |
|-------|-------|
| **FBref table(s)** | `possession` |
| **Formula** | `PrgC / Carries` |
| **Possession-adjusted** | No |
| **High score means** | Player drives the ball forward with the ball at their feet regularly |
| **Low score means** | Carries are mostly lateral or stationary; rarely drives past opponents |

**Columns:** `possession.PrgC`, `possession.Carries`

---

### 16. Progressive receptions

| Field | Value |
|-------|-------|
| **FBref table(s)** | `possession` (receiving sub-table) |
| **Formula** | `PrgR / Rec` |
| **Possession-adjusted** | No |
| **High score means** | Player often receives the ball in advanced positions; movement creates depth |
| **Low score means** | Drops deep to receive; not exploiting space in behind |

**Columns:** `possession.Receiving.PrgR`, `possession.Receiving.Rec`

---

## Attack (4 metrics)

### 17. Goal threat

| Field | Value |
|-------|-------|
| **FBref table(s)** | `standard`, `shooting` |
| **Formula** | `(0.7 × npxG + 0.3 × (Gls – PK)) / 90` |
| **Possession-adjusted** | No |
| **High score means** | Player generates high-quality shots and converts chances; genuine scoring threat |
| **Low score means** | Rarely shoots or misses when they do |

**Columns:** `shooting.npxG`, `standard.Gls`, `standard.PK`

---

### 18. Shot frequency

| Field | Value |
|-------|-------|
| **FBref table(s)** | `shooting`, `possession` |
| **Formula** | `Sh / (Touches / 100)` |
| **Possession-adjusted** | No (normalised by total touches) |
| **High score means** | Player shoots often relative to how much they touch the ball; trigger-happy finisher |
| **Low score means** | Rarely pulls the trigger despite being on the ball |

**Columns:** `shooting.Sh`, `possession.Touches`

---

### 19. Box threat

| Field | Value |
|-------|-------|
| **FBref table(s)** | `possession` |
| **Formula** | `AttPen_touches / (Mid3rd_touches + Att3rd_touches)` |
| **Possession-adjusted** | No |
| **High score means** | Player spends a high proportion of their advanced touch-time inside the penalty area |
| **Low score means** | Operates predominantly in wide or mid-range areas; not a penalty-box presence |

**Columns:** `possession.Touches.AttPen`, `possession.Touches.Mid3rd`, `possession.Touches.Att3rd`

---

### 20. Shot quality

| Field | Value |
|-------|-------|
| **FBref table(s)** | `shooting` |
| **Formula** | `npxG/Sh` (pre-computed by FBref) |
| **Possession-adjusted** | No |
| **High score means** | Player takes shots from high-quality positions; clinical shot selection |
| **Low score means** | Takes shots from low-probability areas |

**Columns:** `shooting.npxG/Sh`

---

## Notes on metric numbering

Metrics are numbered 1–20 in this document for reference, but the canonical ordering on the
pizza chart follows the **position profile** (Defence → Possession → Progression → Attack),
not the numbering above. See `position-matrix.md` for the per-position display order.
