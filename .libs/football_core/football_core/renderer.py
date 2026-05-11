"""
renderer.py — mplsoccer.PyPizza → SVG string.

Public functions:
  render_pizza(pizza_data) -> str
      Accepts a PizzaData object (with metrics populated).
      Renders a pizza chart using mplsoccer.PyPizza per the visual spec.
      Returns an inline SVG string (XML declaration stripped).

      Raises ValueError if pizza_data.metrics is empty.

See .claude/shared-references/design/pizza-chart-visual-spec.md for all visual parameters:
category colours, PyPizza constructor kwargs, title block layout, SVG export pattern.
"""

# Implementation: import mplsoccer.PyPizza, matplotlib.
# Category colour map from pizza-chart-visual-spec.md.
# Export via io.BytesIO + fig.savefig(format="svg").
# Strip <?xml ...?> declaration line before returning.
# Call plt.close(fig) after export to free memory.
