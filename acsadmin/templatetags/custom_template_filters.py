from datetime import timedelta
from defusedxml.lxml import fromstring
from lxml import etree

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

@register.filter
def addstr(arg1, arg2):
    '''concatenate arg1 & arg2'''
    return str(arg1) + str(arg2)

@register.filter
def prettyprintjson(jsondata):
    return json.dumps(json.loads(jsondata), indent=4) if jsondata else 'N/A'

@register.filter
def prettyprintxml(xml):
    '''
    This assumes too much about encoding and stuff.
    Should be possible to prettyprint without changing the xml at all.
    '''
    return etree.tostring(
        fromstring(xml.encode('utf-8')),
        pretty_print=True,
        xml_declaration=True,
        encoding='utf-8',
    ).decode('utf-8')

