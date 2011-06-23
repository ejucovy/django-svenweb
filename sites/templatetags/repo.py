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

def history_url(wiki, path):
    return wiki.history_url(path)
register.filter("page_history_url", history_url)

def last_modified_author(wiki, path):
    return wiki.last_modified_author(path)
register.filter("last_modified_author", last_modified_author)

def last_modified_date(wiki, path):
    print wiki.last_modified_date(path)
    return wiki.last_modified_date(path)
register.filter("last_modified_date", last_modified_date)
