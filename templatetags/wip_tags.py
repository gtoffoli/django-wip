# -*- coding: utf-8 -*-

from django import template
register = template.Library()

@register.filter
def lookup(d, key):
    try:
        return d[key]
    except KeyError:
        return ''