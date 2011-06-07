from djangohelpers.lib import allow_http, rendered_with
from django.http import HttpResponse, HttpResponseRedirect
from svenweb.sites.models import Wiki
from django.core.urlresolvers import reverse

@allow_http("GET", "POST")
@rendered_with("sites/user_index.html")
def home(request):
    if request.method == "GET":
        if request.site is not None:
            return HttpResponseRedirect(request.site.site_home_url())

        sites = Wiki.objects.filter(users=request.user)
        return dict(sites=sites)

    site = Wiki(name=request.POST['name'])
    site.save()
    site.users.add(request.user)
    return HttpResponseRedirect(".")

@allow_http("GET")
@rendered_with("sites/site/home.html")
def site_home(request):
    site = request.site

    return dict(site=site)


@allow_http("GET")
@rendered_with("sites/site/page-index.html")
def page_index(request, subpath):
    site = request.site

    return dict(site=site, path=subpath)
