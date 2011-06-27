from django.http import (HttpResponse, HttpResponseForbidden, 
                         HttpResponseRedirect as redirect)
from djangohelpers.lib import rendered_with, allow_http
from svenweb.sites.models import (Wiki,
                                  UserWikiLocalRoles)

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
    wikis = [i for i in Wiki.objects.filter(name__startswith=project+'/')
             if i.viewable(request)]

    policy = request.get_security_policy()

    from svenweb.sites.models import PERMISSION_CONSTRAINTS, PERMISSIONS
    member_constraints = PERMISSION_CONSTRAINTS[policy]["ProjectMember"]
    other_constraints = PERMISSION_CONSTRAINTS[policy]["Authenticated"]

    _member_permissions = [i for i in PERMISSIONS
                           if i[0] in member_constraints]
    _other_permissions = [i for i in PERMISSIONS
                          if i[0] in other_constraints]

    member_permissions = [(-1, "not even see this wiki")]
    for i in range(len(_member_permissions)):
        prefix = ""
        if i > 0:
            prefix = "and "
        member_permissions.append((i, prefix + _member_permissions[i][1]))
    
    other_permissions = [(-1, "not even see this wiki")]
    for i in range(len(_other_permissions)):
        prefix = ""
        if i > 0:
            prefix = "and "
        other_permissions.append((i, prefix + _other_permissions[i][1]))
    
    return {'wikis': wikis, 'project': project,
            'member_permissions': member_permissions,
            'other_permissions': other_permissions,
            }

@requires_project_admin
@allow_http("POST")
def create_wiki(request):
    name = request.POST.get('name') or "default-wiki"
    from django.template.defaultfilters import slugify
    name = slugify(name)
    name = request.META['HTTP_X_OPENPLANS_PROJECT'] + '/' + name
    site = Wiki(name=name)
    site.save()

    managers = request.POST.getlist("managers")
    for manager in managers:
        role = UserWikiLocalRoles(username=manager, wiki=site)
        role.add_role("WikiManager")
        role.save()

    member_permissions = int(request.POST.get("member_perms", "-1"))
    other_permissions = int(request.POST.get("other_perms", "-1"))

    from svenweb.sites.models import (get_permission_constraints, PERMISSIONS,
                                      WikiRolePermissions)

    member_permissions = PERMISSIONS[:member_permissions + 1]
    other_permissions = PERMISSIONS[:other_permissions + 1]

    member_permissions = [i[0] for i in member_permissions 
                          if i[0] in get_permission_constraints(
            request.get_security_policy(),
            "ProjectMember")]

    other_permissions = [i[0] for i in other_permissions 
                          if i[0] in get_permission_constraints(
            request.get_security_policy(),
            "Authenticated")]

    p = WikiRolePermissions(wiki=site, role="ProjectMember")
    p.set_permissions(member_permissions)
    p.save()

    p = WikiRolePermissions(wiki=site, role="Authenticated")
    p.set_permissions(other_permissions)
    p.save()

    other_permissions = [i for i in other_permissions 
                          if i in get_permission_constraints(
            request.get_security_policy(),
            "Anonymous")]
    p = WikiRolePermissions(wiki=site, role="Anonymous")
    p.set_permissions(other_permissions)
    p.save()

    return redirect(site.site_home_url())
