from djangohelpers.lib import allow_http, rendered_with
from django.http import HttpResponse, HttpResponseRedirect as redirect
import mimetypes
from sven import exc as sven
from svenweb.sites.models import Wiki

@allow_http("GET", "POST")
@rendered_with("sites/user_index.html")
def home(request):
    if request.method == "GET":
        if request.site is not None:
            return redirect(request.site.site_home_url())

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

    try:
        subpaths = site.get_contents(subpath)
    except sven.NotADirectory:
        return redirect(site.page_view_url(subpath))

    return dict(site=site, path=subpath, subpaths=subpaths)

@allow_http("GET")
def page_view(request, subpath):
    site = request.site

    try:
        contents = site.get_page(subpath)
    except sven.NotAFile:
        return redirect(site.directory_index_url(subpath))

    mimetype = mimetypes.guess_type(subpath)[0]
    return HttpResponse(contents, mimetype=mimetype)
