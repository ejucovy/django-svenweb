from Cookie import BaseCookie
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponseNotFound
from libopencore import auth
from libopencore.query_project import (get_users_for_project,
                                       admin_post)
from svenweb.sites.models import (Wiki,
                                  UserWikiLocalRoles,
                                  get_highest_role)

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

def get_security_policy(request):
    import elementtree.ElementTree as etree
    if hasattr(request, '_cached_opencore_policy'):
        return request._cached_opencore_policy
    url = "%s/projects/%s/info.xml" % (
        settings.OPENCORE_SERVER,
        request.META['HTTP_X_OPENPLANS_PROJECT'])
    admin_info = auth.get_admin_info(settings.OPENCORE_ADMIN_FILE)
    resp, content = admin_post(url, *admin_info)
    assert resp['status'] == '200'
    tree = etree.fromstring(content)
    policy = tree[0].text
    request._cached_opencore_policy = policy
    return policy

def get_role(request, wiki):
    if hasattr(request, '_cached_svenweb_role'):
        return request._cached_svenweb_role

    if request.user.is_anonymous():
        request._cached_svenweb_role = "Anonymous"
        return "Anonymous"

    roles = set(["Authenticated"])

    admin_info = auth.get_admin_info(settings.OPENCORE_ADMIN_FILE)

    users = get_users_for_project(request.META['HTTP_X_OPENPLANS_PROJECT'],
                                  settings.OPENCORE_SERVER,
                                  admin_info)
    found = False
    for member in users:
        if member['username'] == request.user.username:
            found = True
            remote_roles = member['roles']
            break
    if not found:
        role = get_highest_role(roles)
        request._cached_svenweb_role = role
        return role

    roles.update(remote_roles)
    
    local_roles, _ = UserWikiLocalRoles.objects.get_or_create(username=request.user.username, wiki=wiki)
    local_roles = local_roles.get_roles()
    roles.update(local_roles)

    role = get_highest_role(roles)
    request._cached_svenweb_role = role
    return role

def get_permissions(request, wiki):
    role = get_role(request, wiki)
    

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
