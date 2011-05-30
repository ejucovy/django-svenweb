from django import template
from svenweb.sites.models import Wiki

register = template.Library()

def get_contents(wiki, path):
    return wiki.get_contents(path)

register.filter("get_contents", get_contents)
