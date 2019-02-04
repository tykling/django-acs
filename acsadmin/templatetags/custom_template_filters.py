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

@register.filter
def truefalseicon(value):
    '''Returns a icon with a green checkmark or a red X depending on true/false input, requires font-awesome to be any good'''
    if value:
        return '<i class="fa fa-check" style="color:#00947d"></i>'
    else:
        return '<i class="fa fa-times" style="color:#494849"></i>'

