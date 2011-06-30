from django.conf import settings
from django.http import HttpResponseRedirect as redirect
from svenweb.sites.models import Wiki, SESSION_KEY, UNSET_KEY, SET_KEY
from svenweb.sites.models import (UserWikiLocalRoles, 
                                  WikiRolePermissions,
                                  apply_constraints)
                                  
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

            request.site = wiki
            wiki.create_repo()

def get_role(request, wiki):
    if hasattr(request, '_cached_svenweb_role'):
        if wiki.pk in request._cached_svenweb_role:
            return request._cached_svenweb_role[wiki.pk]
    request._cached_svenweb_role = {}

    roles = set()
    if request.user.is_anonymous():
        roles.add("Anonymous")
    else:
        roles.add("Authenticated")

    extra_role_getter = getattr(settings, 'SVENWEB_EXTRA_ROLE_GETTER', None)
    if extra_role_getter is not None:
        roles.update(extra_role_getter(request, wiki))

    local_roles, _ = UserWikiLocalRoles.objects.get_or_create(
        username=request.user.username, wiki=wiki)
    local_roles = local_roles.get_roles()
    roles.update(local_roles)

    role = settings.SVENWEB_HIGHEST_ROLE_FINDER(roles)
    request._cached_svenweb_role[wiki.pk] = role
    return role

def get_permissions(request, wiki):
    if hasattr(request, '_cached_svenweb_permissions'):
        if wiki.pk in request._cached_svenweb_permissions:
            return request._cached_svenweb_permissions[wiki.pk]
    request._cached_svenweb_permissions = {}

    role = get_role(request, wiki)

    constraints = settings.SVENWEB_PERMISSION_CONSTRAINT_GETTER(
        request, role)
    
    try:
        permissions = WikiRolePermissions.objects.get(wiki=wiki, role=role)
    except WikiRolePermissions.DoesNotExist:
        permissions = WikiRolePermissions(wiki=wiki, role=role)
        # The constraints serve fine as defaults too.
        permissions.set_permissions(constraints)
        permissions.save()
    permissions = permissions.get_permissions()
    permissions = apply_constraints(permissions, constraints)

    request._cached_svenweb_permissions[wiki.pk] = permissions
    return permissions

class SvenwebSecurityMiddleware(object):
    def process_request(self, request):
        request.get_role = lambda wiki: get_role(request, wiki)
        request.get_permissions = lambda wiki: get_permissions(request, wiki)
