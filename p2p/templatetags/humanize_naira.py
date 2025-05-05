# project_or_app/templatetags/humanize_naira.py

from django import template

register = template.Library()

@register.filter
def humanize_naira(value):
    try:
        num = float(value)
    except (ValueError, TypeError):
        return value

    if num < 1000:
        return f"₦{num:,.0f}"
    elif num < 1_000_000:
        return f"₦{num / 1000:.1f}K"
    elif num < 1_000_000_000:
        return f"₦{num / 1_000_000:.2f}M"
    else:
        return f"₦{num / 1_000_000_000:.2f}B"
