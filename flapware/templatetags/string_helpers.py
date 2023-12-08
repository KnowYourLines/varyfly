from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter(is_safe=True)
@stringfilter
def get_comma_split_index(value, index):
    index = int(index)
    return value.split(",")[index]
