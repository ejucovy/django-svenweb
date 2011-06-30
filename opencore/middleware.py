from Cookie import BaseCookie
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponseNotFound
from libopencore import auth
from libopencore.query_project import (get_users_for_project,
                                       admin_post)
from svenweb.sites.models import Wiki
from topp.utils.memorycache import cache as memorycache

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

@memorycache(600)
def _fetch_policy(project):
    import elementtree.ElementTree as etree
    url = "%s/projects/%s/info.xml" % (
        settings.OPENCORE_SERVER, project)
    admin_info = auth.get_admin_info(settings.OPENCORE_ADMIN_FILE)
    resp, content = admin_post(url, *admin_info)
    assert resp['status'] == '200'
    tree = etree.fromstring(content)
    policy = tree[0].text
    return policy

def get_security_policy(request):
    if hasattr(request, '_cached_opencore_policy'):
        return request._cached_opencore_policy
    policy = _fetch_policy(request.META['HTTP_X_OPENPLANS_PROJECT'])
    request._cached_opencore_policy = policy
    return policy

@memorycache(600)
def _fetch_user_roles(project):
    admin_info = auth.get_admin_info(settings.OPENCORE_ADMIN_FILE)
    users = get_users_for_project(project,
                                  settings.OPENCORE_SERVER,
                                  admin_info)
    return users

def get_project_members(request):
    if hasattr(request, '_cached_opencore_project_members'):
        return request._cached_opencore_project_members

    users = _fetch_user_roles(request.META['HTTP_X_OPENPLANS_PROJECT'])
    members = []
    for member in users:
        members.append(member['username'])
    members = sorted(members)
    request._cached_opencore_project_members = members
    return members

def get_project_role(request, wiki=None):
    if hasattr(request, '_cached_opencore_project_role'):
        return request._cached_opencore_project_role

    if request.user.is_anonymous():
        request._cached_opencore_project_role = []
        return []

    users = _fetch_user_roles(request.META['HTTP_X_OPENPLANS_PROJECT'])

    found = False
    for member in users:
        if member['username'] == request.user.username:
            found = True
            remote_roles = member['roles']
            break
    if not found:
        request._cached_opencore_project_role = []
        return []
    else:
        request._cached_opencore_project_role = remote_roles
        return remote_roles

class LazyUser(object):
    def __get__(self, request, obj_type=None):
        if not hasattr(request, '_cached_user'):
            request._cached_user = get_user(request)
        return request._cached_user

class AuthenticationMiddleware(object):
    def process_request(self, request):
        request.__class__.user = LazyUser()
        request.get_project_role = lambda: get_project_role(request)
        request.get_project_members = lambda: get_project_members(request)
        request.get_security_policy = lambda: get_security_policy(request)
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
        wiki.create_repo()
        return None
