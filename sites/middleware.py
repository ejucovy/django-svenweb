from django.http import HttpResponseRedirect as redirect
from svenweb.sites.models import Wiki, SESSION_KEY, UNSET_KEY, SET_KEY

class SiteContextMiddleware(object):
    
    def process_request(self, request):
        request.site = None #must be present to be a caching key

        if UNSET_KEY in request.GET:
            if request.session.has_key(SESSION_KEY):
                del request.session[SESSION_KEY]
            return redirect(request.path)

        if SET_KEY in request.GET:
            request.session[SESSION_KEY] = request.GET[SET_KEY]
            return redirect(request.path)

        if SESSION_KEY in request.session:
            try:
                wiki = Wiki.objects.get(pk=request.session[SESSION_KEY])
            except Wiki.DoesNotExist:
                del request.session[SESSION_KEY]
                return None
            if not wiki.viewable(request):
                del request.session[SESSION_KEY]
                return None

            request.site = wiki
            wiki.create_repo()
