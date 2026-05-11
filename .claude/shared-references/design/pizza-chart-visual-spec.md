# Pizza Chart Visual Specification

Source of truth for the visual grammar of the pizza chart. All rendering code in
`render-pizza` skill and `football_core/renderer.py` must follow this spec.

---

## Chart anatomy

A pizza chart is a polar/radar chart where:
- Each **slice** represents one metric
- The slice's **fill depth** encodes the percentile (0 = empty, 99 = full)
- Slices are ordered clockwise starting from the top
- Metrics are grouped into **categories**, rendered in consecutive arcs

---

## Slice order (clockwise from top)

Categories render in this fixed order, starting at 12 o'clock and going clockwise:

1. **Defence** (red arc)
2. **Possession** (blue arc)
3. **Progression** (green arc)
4. **Attack** (orange arc)

Within each category, metric order follows `metric-definitions.md` (top to bottom within each
category section).

---

## Colour palette

| Category | Slice fill colour | Slice background | Hex |
|---|---|---|---|
| Defence | Crimson red | Light pink | Fill: `#E63946` / BG: `#FFCDD2` |
| Possession | Steel blue | Light blue | Fill: `#457B9D` / BG: `#BBDEFB` |
| Progression | Forest green | Light green | Fill: `#2D6A4F` / BG: `#C8E6C9` |
| Attack | Amber orange | Light amber | Fill: `#E07B39` / BG: `#FFE0B2` |

**Outer ring (boundary circle):** `#E0E0E0` at 20% opacity  
**Chart background:** `#FAFAFA` (near-white)  
**Figure background:** `#FFFFFF` (pure white) — used when embedding in the UI

---

## Percentile scale

- Minimum fill: 0 (percentile = 0 → empty slice up to the inner ring)
- Maximum fill: 99 (percentile = 99 → slice fills to the outer ring)
- The inner ring radius is fixed at a value representing the 0-percentile baseline

---

## Labels

### Metric name labels (outer)
- Position: just outside the outer ring, at the midpoint of each slice's angle
- Font: sans-serif, 8–9pt
- Colour: `#333333`
- Truncate names longer than 18 characters with `…`

### Percentile value labels (inner)
- Position: inside the filled slice area, roughly 70% of the way to the outer ring
- Font: bold, sans-serif, 9–10pt
- Colour: `#FFFFFF` (white) on filled slices; `#666666` on empty/near-empty slices (< 15th percentile)

---

## Title block

Rendered above the chart (or below on mobile):

```
{Player name}                          {Season}
{Position bucket} · {League}
```

- Player name: bold, 14pt
- Metadata line: regular, 10pt, colour `#666666`

---

## Category label arcs (optional, recommended)

A thin arc label on the outer edge of each category group:
- Text: `DEFENCE`, `POSSESSION`, `PROGRESSION`, `ATTACK` (all caps)
- Font: bold, 7pt, same colour as category fill
- Position: outside the metric name labels

---

## PyPizza parameter mapping

When implementing with `mplsoccer.PyPizza`:

```python
from mplsoccer import PyPizza

# Slice values: list of percentile ints in clockwise order
params = [m["name"] for m in metrics]        # metric name labels
values = [m["percentile"] for m in metrics]  # 0–99 int list

slice_colors  = [CATEGORY_FILL[m["category"]] for m in metrics]
text_colors   = ["#FFFFFF" if m["percentile"] >= 15 else "#666666" for m in metrics]

baker = PyPizza(
    params=params,
    background_color="#FFFFFF",
    straight_line_color="#E0E0E0",
    straight_line_lw=1,
    last_circle_color="#E0E0E0",
    last_circle_lw=2,
    other_circle_lw=1,
    other_circle_color="#E0E0E0",
)

fig, ax = baker.make_pizza(
    values,
    figsize=(8, 8),
    color_blank_space=["#FAFAFA"] * len(values),
    slice_colors=slice_colors,
    value_colors=text_colors,
    value_bck_colors=slice_colors,
    blank_alpha=0.4,
    kwargs_slices={"edgecolor": "#FFFFFF", "zorder": 2, "linewidth": 1},
    kwargs_params={"color": "#333333", "fontsize": 9, "va": "center"},
    kwargs_values={"color": "#FFFFFF", "fontsize": 9, "zorder": 3,
                   "bbox": {"edgecolor": "#FFFFFF", "facecolor": "none", "linewidth": 0}},
)
```

---

## SVG export

Export to SVG (not PNG) so the browser can scale it without pixelation:

```python
import io
buf = io.BytesIO()
fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.1)
svg_string = buf.getvalue().decode("utf-8")
```

Strip the XML declaration line (`<?xml ...?>`) before returning, so the string can be
embedded inline in HTML:

```python
lines = svg_string.splitlines()
svg_string = "\n".join(l for l in lines if not l.startswith("<?xml"))
```

---

## Reference examples

See FBref's own pizza charts (e.g. from StatsBomb / Opta via FBref) for visual targets.
The spec above matches the widely-used `mplsoccer` pizza chart style as seen on Twitter/X
football analytics accounts — high contrast, clean white background, category colour arcs.
