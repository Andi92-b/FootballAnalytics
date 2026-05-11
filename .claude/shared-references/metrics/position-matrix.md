# Position Matrix

Source of truth for which metrics appear in each position's pizza chart.
**Do not modify without updating metric-definitions.md simultaneously.**

---

## FBref Position String → Position Bucket Mapping

| FBref string(s) | Position bucket | Abbreviation |
|-----------------|-----------------|--------------|
| `CB` | Centre-back | CB |
| `RB`, `LB`, `RWB`, `LWB` | Full-back | FB |
| `DM` | Defensive midfielder | DM |
| `CM`, `MF` | Central midfielder | CM |
| `AM` | Attacking midfielder | AM |
| `RW`, `LW`, `LM`, `RM` | Wide forward / winger | W |
| `CF`, `FW`, `ST` | Centre-forward | CF |

**Note:** FBref sometimes lists two positions separated by a comma (e.g. `"CB,RB"`). Use the
**primary position** (first listed) for bucket assignment. If the primary position is not in
the map, try the secondary.

---

## Position × Metric Matrix

`✓` = always shown | `~` = shown for this position variant | `–` = not shown

| Metric | CB | FB | DM | CM | AM | W | CF |
|--------|:--:|:--:|:--:|:--:|:--:|:-:|:--:|
| **Defence** | | | | | | | |
| Front-foot defending | ✓ | ✓ | ✓ | ✓ | ~ | – | – |
| Tackle success | ✓ | ✓ | ✓ | ✓ | – | – | – |
| Back-foot defending | ✓ | ✓ | ✓ | – | – | – | – |
| Loose ball recoveries | ✓ | ✓ | ✓ | ✓ | – | – | – |
| Aerial volume | ✓ | ~ | ✓ | – | – | – | ✓ |
| Aerial success | ✓ | ~ | ✓ | – | – | – | ✓ |
| One-v-one defending | – | ✓ | – | – | – | – | – |
| **Possession** | | | | | | | |
| Link-up play | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | – |
| Ball retention | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Launched passes | ✓ | ~ | ✓ | ✓ | – | – | – |
| **Progression** | | | | | | | |
| Creative threat | – | ~ | – | ✓ | ✓ | ✓ | ✓ |
| Cross volume | – | ✓ | – | ~ | ✓ | ✓ | – |
| Dribble volume | – | ✓ | – | ✓ | ✓ | ✓ | – |
| Pass progression | ✓ | ~ | ✓ | ✓ | ✓ | – | – |
| Carry progression | – | ✓ | – | ✓ | ✓ | ✓ | – |
| Progressive receptions | – | ✓ | ~ | ✓ | ✓ | ✓ | ✓ |
| **Attack** | | | | | | | |
| Goal threat | – | – | – | ~ | ✓ | ✓ | ✓ |
| Shot frequency | – | – | – | ~ | ✓ | ✓ | ✓ |
| Box threat | – | – | – | – | ~ | ✓ | ✓ |
| Shot quality | – | – | – | – | ✓ | ✓ | ✓ |

---

## Per-position metric counts

| Position | Defence | Possession | Progression | Attack | Total |
|----------|--------:|----------:|------------:|-------:|------:|
| CB | 6 | 3 | 2 | 0 | 11 |
| FB | 7 | 3 | 5 | 0 | 15 |
| DM | 6 | 3 | 3 | 0 | 12 |
| CM | 5 | 4 | 5 | 2 | 16 |
| AM | 1 | 3 | 5 | 4 | 13 |
| W | 0 | 3 | 5 | 4 | 12 |
| CF | 3 | 2 | 3 | 4 | 12 |

---

## Implementation notes

- The `~` flag means "include for this position bucket". Treat `~` identically to `✓` in code.
  The distinction is only editorial (it marks metrics that are non-obvious for the position).
- Metric ordering within each category follows the order in `metric-definitions.md`.
- For peer-group filtering, use the **position bucket**, not the raw FBref string.
  All `RB`, `LB`, `RWB`, `LWB` players are peers when evaluating a full-back.
