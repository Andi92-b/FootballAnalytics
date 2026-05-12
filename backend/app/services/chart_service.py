"""chart_service — renders pizza chart SVG from PizzaData."""
from football_core.models import PizzaData
from football_core.renderer import render_pizza


def render(pizza_data: PizzaData) -> str:
    """Render pizza chart, return SVG string."""
    return render_pizza(pizza_data)
