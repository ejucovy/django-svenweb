from django.http import (HttpResponse, HttpResponseForbidden, 
                         HttpResponseRedirect as redirect)
from djangohelpers.lib import rendered_with, allow_http
from svenweb.sites.models import Wiki

def requires_project_admin(func):
    def inner(request, *args, **kw):
        role = request.get_project_role()
        if role != "ProjectAdmin":
            return HttpResponseForbidden()
        return func(request, *args, **kw)
    return inner

@allow_http("GET", "POST")
@rendered_with("opencore/index.html")
def home(request):
    if request.method == "POST":
        return create_wiki(request)

    project = request.META['HTTP_X_OPENPLANS_PROJECT']
    wikis = Wiki.objects.filter(name__startswith=project+'/')

    return {'wikis': wikis, 'project': project}

@requires_project_admin
@allow_http("POST")
def create_wiki(request):
    name = request.POST['name']
    name = request.META['HTTP_X_OPENPLANS_PROJECT'] + '/' + name
    site = Wiki(name=name)
    site.save()

    return redirect(site.site_home_url())
