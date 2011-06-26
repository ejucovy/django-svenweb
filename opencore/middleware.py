from Cookie import BaseCookie
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponseNotFound
from libopencore import auth
from libopencore.query_project import (get_users_for_project,
                                       admin_post)
from svenweb.sites.models import (Wiki,
                                  UserWikiLocalRoles,
                                  WikiRolePermissions,
                                  get_highest_role,
                                  get_permission_constraints,
                                  apply_constraints,
                                  )
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

def get_project_role(request):
    if hasattr(request, '_cached_opencore_project_role'):
        return request._cached_opencore_project_role

    if request.user.is_anonymous():
        request._cached_opencore_project_role = "Anonymous"
        return "Anonymous"

    users = _fetch_user_roles(request.META['HTTP_X_OPENPLANS_PROJECT'])

    found = False
    for member in users:
        if member['username'] == request.user.username:
            found = True
            remote_roles = member['roles']
            break
    if not found:
        request._cached_opencore_project_role = "Authenticated"
        return "Authenticated"
    else:
        role = get_highest_role(remote_roles)
        request._cached_opencore_project_role = role
        return role

def get_role(request, wiki):
    if hasattr(request, '_cached_svenweb_role'):
        return request._cached_svenweb_role

    roles = set()
    roles.add(get_project_role(request))

    local_roles, _ = UserWikiLocalRoles.objects.get_or_create(
        username=request.user.username, wiki=wiki)
    local_roles = local_roles.get_roles()
    roles.update(local_roles)

    role = get_highest_role(roles)
    request._cached_svenweb_role = role
    return role

def get_permissions(request, wiki):
    if hasattr(request, '_cached_svenweb_permissions'):
        return request._cached_svenweb_permissions

    policy = get_security_policy(request)
    role = get_role(request, wiki)
    constraints = get_permission_constraints(policy, role)
    try:
        permissions = WikiRolePermissions.objects.get(wiki=wiki, role=role)
    except WikiRolePermissions.DoesNotExist:
        permissions = WikiRolePermissions(wiki=wiki, role=role)
        # The constraints serve fine as defaults too.
        permissions.set_permissions(constraints)
        permissions.save()
    permissions = permissions.get_permissions()
    permissions = apply_constraints(permissions, constraints)
    request._cached_svenweb_permissions = permissions
    return permissions

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
        request.get_role = lambda x: get_role(request, x)
        request.get_permissions = lambda x: get_permissions(request, x)
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
