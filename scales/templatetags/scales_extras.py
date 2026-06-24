from django import template

register = template.Library()


@register.filter
def get_item(d, key):
    """Return d[key] — lets templates access dicts with variable keys."""
    if isinstance(d, dict):
        return d.get(key)
    return None
