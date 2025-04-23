# courses/templatetags/course_tags.py

import os
from django import template

register = template.Library()

@register.filter
def filename(value):
    if hasattr(value, 'name'):
        return os.path.basename(value.name)
    return value

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''
