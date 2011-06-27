from djangohelpers.lib import allow_http, rendered_with
from django.http import (HttpResponse,
                         HttpResponseRedirect as redirect, 
                         HttpResponseForbidden)
from django.contrib import messages
import mimetypes
from sven import exc as sven
from svenweb.sites.models import Wiki, UserProfile
from django.conf import settings
from restclient import POST
import json
from django.views.decorators.csrf import csrf_exempt
import os

def requires(permissions):
    if isinstance(permissions, basestring):
        permissions = [permissions]
    def wrapper(func):
        def inner(request, *args, **kw):
            available_permissions = request.site.get_permissions(request)
            for permission in permissions:
                if permission not in available_permissions:
                    return HttpResponseForbidden()
            return func(request, *args, **kw)
        return inner
    return wrapper

def oauth(request):
    if 'start' in request.GET:
        return redirect("https://github.com/login/oauth/authorize?scope=public_repo&client_id=%s" %
                        settings.GITHUB_CLIENT_ID)
    elif request.method == "GET":
        code = request.GET['code']
        params = {'client_id': settings.GITHUB_CLIENT_ID,
                  'client_secret': settings.GITHUB_SECRET,
                  'code': code}
        resp, content = POST("https://github.com/login/oauth/access_token", params, async=False, resp=True)
        for item in content.split("&"):
            if item.split("=")[0] == "access_token":
                token = item.split("=")[1]
                request.session['github_oauth_token'] = token
        return redirect("/")

@allow_http("GET", "POST")
@rendered_with("sites/user_index.html")
def home(request):
    if request.method == "GET":
        if request.site is not None:
            return redirect(request.site.site_home_url())

        _sites = Wiki.objects.all()
        sites = []
        for site in _sites:
            if site.viewable(request):
                sites.append(site)
        return dict(sites=sites)

    site = Wiki(name=request.POST['name'])
    site.save()
    site.add_admin_user(request.user)
    return redirect(site.wiki_configure_url() + "?svenweb.set_site=%s" % site.pk)

@requires("WIKI_VIEW")
@allow_http("GET")
@rendered_with("sites/site/home.html")
def site_home(request):
    site = request.site

    return dict(site=site)

@requires("WIKI_CONFIGURE")
@allow_http("GET", "POST")
@rendered_with("sites/site/configure.html")
def site_configure(request):
    site = request.site
    if request.method == "GET":
        return dict(site=site)
    wiki_type = request.POST['wiki_type']
    site.set_options({'wiki_type': wiki_type})
    return redirect(site.site_home_url())

@allow_http("GET", "POST")
@rendered_with("sites/user_account.html")
def user_account(request):
    user = request.user
    profile = UserProfile.objects.get_or_create(user=user)[0]

    if request.method == "POST":
        redirect_to = request.POST.get('redirect_to', '.')

        if 'ssh_key' in request.POST:
            if not profile.register_github_key():
                messages.error(request, "missingsshkey")
                return redirect(".")
        else:
            username = request.POST['github_username']
            token = request.POST['github_api_token']
            profile.set_options({'github_username': username,
                                 'github_api_token': token})
            profile.save()

        return redirect(redirect_to)

    message = None
    redirect_to = "."
    msgs = messages.get_messages(request)
    for msg in msgs:
        if 'failedauth' in msg.message:
            message = ("Github authorization failed. " 
                       "Please check your account's username "
                       "and api token, and try again.")
            redirect_to = request.site.deploy_dashboard_url()
        if 'noprofile' in msg.message:
            message = ("To create Github Repos, I need your "
                       "Github username and API token. "
                       "Please provide those, and then try again.")
            redirect_to = request.site.deploy_dashboard_url()
        if 'missingsshkey' in msg.message:
            message = ("To work with your Github Repos, I need to "
                       "register my SSH public key with your account. "
                       "Make sure your username and API token are set, "
                       "and then click \"Register SSH Key\".  Thanks!")
            redirect_to = request.site.deploy_dashboard_url()

    return {
        'profile': profile,
        'message': message,
        'redirect_to': redirect_to,
        }

@requires("WIKI_CONFIGURE")
@allow_http("GET", "POST")
@rendered_with("sites/site/deploy.html")
def deploy(request):
    site = request.site
    
    if request.method == "POST":
        options = {'custom_domain': request.POST.get("custom_domain", ''),
                   'github_repo': request.POST.get("github_repo", ''),
                   }
        site.set_options(options)
        return redirect(".")

    return dict(site=site)

@allow_http("POST")
def create_github_repo(request):
    site = request.site
    user = request.user
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        messages.error(request, "noprofile")
        # @@todo: reverse urlconf
        return redirect("/.home/account/")
    
    username, token = profile.github_username, profile.github_api_token
    if not username or not token:
        messages.error(request, "noprofile")
        # @@todo: reverse urlconf
        return redirect("/.home/account/")

    if not site.github.create_repo(username, token):
        messages.error(request, "failedauth")
        # @@todo: reverse urlconf
        return redirect("/.home/account/")
        
    return redirect(site.deploy_dashboard_url())
    
@requires("WIKI_DEPLOY")
@allow_http("POST")
def deploy_to_github_initial(request):
    site = request.site

    import subprocess
    import os
    import tempfile
    import shutil

    curdir = os.getcwd()

    checkout_path = tempfile.mkdtemp()
    os.chdir(checkout_path)

    domain = "github-%s" % request.user.username
    url = site.github.push_url(domain)

    subprocess.call(["git", "init"])
    subprocess.call(["git", "remote", "add", "github", url])

    gitignore = open(".gitignore", 'w')
    gitignore.write(".bzr")
    gitignore.close()
    subprocess.call(["git", "add", ".gitignore"])

    subprocess.call(["git", "commit",
                     "-m", "initializing site"])

    subprocess.call(["git", "branch", "gh-pages"])
    subprocess.call(["git", "checkout", "gh-pages"])
    import tempfile
    with tempfile.TemporaryFile() as capture:
        ret = subprocess.call(["git", "push", "github", "gh-pages"],
                              stdout=capture, stderr=subprocess.STDOUT)
        if ret != 0:
            capture.seek(0)
            _captured = capture.read()

            if ("Permission denied" in _captured or
                "Permission to %s.git denied" % site.github.repo() in _captured or
                "Could not resolve hostname" in _captured): # @@todo: this last one belongs elsewhere
                
                os.chdir(curdir)
                shutil.rmtree(checkout_path)

                messages.error(request, "missingsshkey")
                # @@todo: reverse urlconf
                return redirect("/.home/account/")

    os.chdir(curdir)
    shutil.rmtree(checkout_path)

    return redirect(site.deploy_dashboard_url())

@requires("WIKI_DEPLOY")
@allow_http("POST")
def deploy_to_github(request):
    site = request.site

    import subprocess
    import os
    import tempfile
    import shutil
    import glob
    curdir = os.getcwd()

    checkout_path = tempfile.mkdtemp()
    os.chdir(checkout_path)

    domain = "github-%s" % request.user.username
    subprocess.call(["git", "clone", "-b", "gh-pages",
                     site.github.push_url(domain),
                     "."])

    gitfiles = glob.glob(".*")
    for file in os.listdir(checkout_path):
        if file in gitfiles:
            continue
        if os.path.isfile(file):
            os.remove(file)
        elif os.path.isdir(file):
            shutil.rmtree(file)

    export_path = site.compiler.compile()

    from distutils.dir_util import copy_tree
    copy_tree(export_path, checkout_path)
    shutil.rmtree(export_path)

    os.chdir(checkout_path)

    if site.custom_domain():
        gitcname = open("CNAME", 'w')
        gitcname.write(site.custom_domain())
        gitcname.close()
    elif os.path.exists("CNAME"):
        os.unlink("CNAME")
        subprocess.call(["git", "rm", "CNAME"])

    subprocess.call(["git", "add", "."])
    subprocess.call(["git", "commit", 
                     "-m", "pushing to github"])
    subprocess.call(["git", "push"])

    os.chdir(curdir)
    shutil.rmtree(checkout_path)

    return redirect(site.deploy_dashboard_url())

@requires("WIKI_HISTORY")
@allow_http("GET")
@rendered_with("sites/site/page-history.html")
def page_history(request, subpath):
    site = request.site

    try:
        history = site.get_history(subpath)
    except sven.NoSuchResource:
        return redirect(site.page_edit_url(subpath))
        
    return dict(site=site, history=history, path=subpath)

@requires("WIKI_VIEW")
@allow_http("GET")
@rendered_with("sites/site/page-index.html")
def page_index(request, subpath):
    site = request.site

    try:
        subpaths = site.get_contents(subpath)
    except sven.NotADirectory:
        return redirect(site.page_view_url(subpath))
    except sven.NoSuchResource:
        return redirect(site.page_edit_url(subpath))

    # @@todo: maybe check for user-supplied index page?
    return dict(site=site, path=subpath, subpaths=subpaths)

@requires("WIKI_VIEW")
@allow_http("GET")
def page_view(request, subpath):
    site = request.site

    try:
        contents = site.get_page(subpath)
    except sven.NotAFile:
        return redirect(site.directory_index_url(subpath))
    except sven.NoSuchResource:
        return redirect(site.page_edit_url(subpath))

    mimetype = mimetypes.guess_type(subpath)[0]
    return HttpResponse(contents, mimetype=mimetype)

@requires("WIKI_EDIT")
@allow_http("GET", "POST")
@rendered_with("sites/site/page-create.html")
def page_create(request, subpath):
    site = request.site

    if request.method == "POST":
        path = request.POST['path']

        # @@todo: don't slugify for raw wikis? dunno
        from django.template.defaultfilters import slugify
        path = '/'.join(slugify(i) for i in path.split('/'))
        
        path = subpath.rstrip('/') + '/' + path.strip('/')

        # @@todo: do something else if the page already exists, i guess?
        return redirect(site.page_edit_url(path.strip('/')))

    try:
        subpaths = site.get_contents(subpath)
    except sven.NotADirectory:
        return redirect(site.page_view_url(subpath))
    except sven.NoSuchResource:
        return redirect(site.page_edit_url(subpath))

    # @@todo: maybe check for user-supplied index page?
    return dict(site=site, path=subpath, subpaths=subpaths,
                form_url=site.page_create_url(subpath))

@requires("WIKI_EDIT")
@allow_http("GET", "POST")
@rendered_with("sites/site/file-upload.html")
def file_upload(request, subpath):
    site = request.site

    if request.method == "GET":
        return {'site': site, 'path': subpath}

    file = request.FILES['file']
    contents = file.read()

    file_path = subpath

    path = request.POST.get('subpath', None)
    if path and path.strip():
        file_path = file_path.rstrip('/') + '/' + path.lstrip('/')
        
    filename = request.POST.get('filename', None)
    if not filename or not filename.strip():
        filename = file.name

    file_path = file_path.rstrip('/') + '/' + filename.lstrip('/')

    msg = request.POST.get("comment", None)
    site.write_page(file_path, contents, 
                    username=request.user.username,
                    msg=msg)

    return redirect(site.page_view_url(file_path))

@requires("WIKI_EDIT")
@allow_http("GET", "POST")
@rendered_with("sites/site/page-edit.html")
def page_edit(request, subpath):
    site = request.site

    if request.method == "POST":
        if 'file' in request.POST:
            file = request.FILES['file']
            contents = file.read()
        else:
            contents = request.POST['contents']

        msg = request.POST.get("comment") or None

        site.write_page(subpath, contents, 
                        msg=msg,
                        username=request.user.username)

        return redirect(site.page_view_url(subpath))

    try:
        contents = site.get_page(subpath)
    except sven.NoSuchResource:  # this is fine, we can edit a new file
        contents = ""
    except sven.NotAFile:  # this is not fine, we can't edit a directory
        # @@todo: maybe check for user-supplied index page?
        return redirect(site.directory_index_url(subpath))

    # @@todo: dispatch to different editors based on mimetype

    raw_edit = ("/%s" % subpath.lstrip('/')).startswith(site.raw_files_path)

    return dict(site=site,
                raw_edit=raw_edit,
                contents=contents, path=subpath,
                form_url=site.page_edit_url(subpath))
