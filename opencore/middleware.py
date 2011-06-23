from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from libopencore import auth
from Cookie import BaseCookie

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
