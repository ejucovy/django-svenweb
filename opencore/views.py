from django.http import HttpResponse
from djangohelpers.lib import rendered_with, allow_http

@allow_http("GET")
def home(request):
    return HttpResponse("welcome to the site, %s" % request.user)
