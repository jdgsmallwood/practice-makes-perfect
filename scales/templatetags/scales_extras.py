import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def get_item(d, key):
    """Return d[key] — lets templates access dicts with variable keys."""
    if isinstance(d, dict):
        return d.get(key)
    return None


@register.filter
def json_encode(value):
    return mark_safe(json.dumps(value))
