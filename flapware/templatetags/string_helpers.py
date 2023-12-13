from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter(is_safe=True)
@stringfilter
def get_safety_colour(safety_rating):
    pct = int(safety_rating) / 100
    pct_diff = 1.0 - pct
    red_color = min(255, int(pct * 2 * 255))
    green_color = min(255, int(pct_diff * 2 * 255))
    col = (red_color, green_color, 0)
    return col
