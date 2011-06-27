from django import template
from svenweb.sites.models import Wiki

register = template.Library()

def get_contents(wiki, path):
    return wiki.get_contents(path)
register.filter("get_contents", get_contents)

def view_url(wiki, path):
    return wiki.page_view_url(path)
register.filter("page_view_url", view_url)

def edit_url(wiki, path):
    return wiki.page_edit_url(path)
register.filter("page_edit_url", edit_url)

@register.filter
def page_create_url(wiki, path):
    return wiki.page_create_url(path)

def history_url(wiki, path):
    return wiki.history_url(path)
register.filter("page_history_url", history_url)

@register.filter
def latest_change_url(wiki, path):
    return wiki.latest_change_url(path)

@register.filter
def page_history_version_url(wiki, path):
    return wiki.history_version_url(path)

@register.filter
def latest_change(wiki, path):
    try:
        return wiki.latest_change(path)
    except IndexError:
        return None
