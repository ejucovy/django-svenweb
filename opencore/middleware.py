from Cookie import BaseCookie
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponseNotFound
from libopencore import auth
from svenweb.sites.models import Wiki

def get_user(request):
    try:
        morsel = BaseCookie(request.META['HTTP_COOKIE'])['__ac']
        secret = settings.OPENCORE_SHARED_SECRET_FILE
        secret = auth.get_secret(secret)
        username, hash = auth.authenticate_from_cookie(
            morsel.value, secret)
    except (IOError, KeyError,
            auth.BadCookie, auth.NotAuthenticated):
        return AnonymousUser()
    user, _ = User.objects.get_or_create(username=username)
    return user

class LazyUser(object):
    def __get__(self, request, obj_type=None):
        if not hasattr(request, '_cached_user'):
            request._cached_user = get_user(request)
        return request._cached_user

class AuthenticationMiddleware(object):
    def process_request(self, request):
        request.__class__.user = LazyUser()
        return None

class SiteContextMiddleware(object):
    def process_view(self, request, view_func, view_args, view_kwargs):
        site_name = view_kwargs.pop("site_name", None)
        if not site_name:
            return None
        try:
            project = request.META['HTTP_X_OPENPLANS_PROJECT']
        except KeyError:
            return None

        site_name = "%s/%s" % (project, site_name)
        try:
            wiki = Wiki.objects.get(name=site_name)
        except Wiki.DoesNotExist:
            return HttpResponseNotFound()

        request.site = wiki
        return None
