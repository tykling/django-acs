from datetime import timedelta

from django import template

register = template.Library()

@register.filter
def datetimerange_as_pretty_delta(value):
    if value:
        return pretty_timedelta(value.upper-value.lower)

@register.filter
def pretty_timedelta(value):
    if value:
        # return a pretty printed version without microseconds
        return str(timedelta(seconds=int(value.total_seconds())))

