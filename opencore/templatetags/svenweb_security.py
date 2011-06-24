from django import template

register = template.Library()

@register.filter
def permissions(request, wiki):
    return request.get_permissions(wiki)

@register.filter
def role(request, wiki):
    return request.get_role(wiki)
