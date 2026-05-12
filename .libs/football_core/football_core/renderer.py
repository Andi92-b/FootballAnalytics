"""
renderer.py — mplsoccer.PyPizza → SVG string.
"""

import io

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — must be set before pyplot import
import matplotlib.pyplot as plt
from mplsoccer import PyPizza

from football_core.models import PizzaData

CATEGORY_FILL = {
    "Defence":    "#E63946",
    "Possession": "#457B9D",
    "Progression": "#2D6A4F",
    "Attack":     "#E07B39",
}

CATEGORY_BG = {
    "Defence":    "#FFCDD2",
    "Possession": "#BBDEFB",
    "Progression": "#C8E6C9",
    "Attack":     "#FFE0B2",
}


def render_pizza(pizza_data: PizzaData) -> str:
    """Render pizza chart SVG string for one player. Returns inline SVG (no XML declaration)."""
    metrics = pizza_data.metrics
    if not metrics:
        raise ValueError("PizzaData.metrics is empty — cannot render chart")

    params = [m.name for m in metrics]
    values = [m.percentile for m in metrics]
    slice_colors = [CATEGORY_FILL[m.category] for m in metrics]
    text_colors = ["#FFFFFF" if m.percentile >= 15 else "#666666" for m in metrics]

    baker = PyPizza(
        params=params,
        background_color="#FFFFFF",
        straight_line_color="#E0E0E0",
        straight_line_lw=1,
        last_circle_color="#E0E0E0",
        last_circle_lw=2,
        other_circle_lw=1,
        other_circle_color="#E0E0E0",
        inner_circle_size=20,
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
        kwargs_params={"color": "#333333", "fontsize": 8, "va": "center"},
        kwargs_values={
            "color": "#FFFFFF", "fontsize": 9, "zorder": 3,
            "bbox": {"edgecolor": "#FFFFFF", "facecolor": "none", "linewidth": 0},
        },
    )

    # Title block
    season_label = pizza_data.season
    fig.text(
        0.515, 0.97,
        pizza_data.player,
        ha="center", va="top",
        fontsize=14, fontweight="bold", color="#1a1a1a",
    )
    fig.text(
        0.515, 0.935,
        f"{pizza_data.position}  ·  {pizza_data.league}  ·  {season_label}",
        ha="center", va="top",
        fontsize=9, color="#666666",
    )

    # Export to SVG string
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    svg_string = buf.getvalue().decode("utf-8")

    # Strip XML declaration so the string can be embedded inline in HTML
    lines = svg_string.splitlines()
    svg_string = "\n".join(line for line in lines if not line.startswith("<?xml"))
    return svg_string
