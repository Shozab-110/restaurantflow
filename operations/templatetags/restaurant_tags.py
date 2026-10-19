from django import template
register = template.Library()

@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    data = context['request'].GET.copy()
    for k, v in kwargs.items():
        data[k] = v
    return data.urlencode()

@register.simple_tag(takes_context=True)
def sort_query(context, field):
    current = context['request'].GET.get('sort', '')
    return querystring(context, sort=f'-{field}' if current == field else field, page=1)

@register.filter
def initials(user):
    return ((user.first_name[:1] + user.last_name[:1]) or user.username[:2]).upper()
