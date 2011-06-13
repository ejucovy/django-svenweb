from djangohelpers.lib import allow_http, rendered_with
from django.http import HttpResponse, HttpResponseRedirect as redirect
from django.contrib import messages
import mimetypes
from sven import exc as sven
from svenweb.sites.models import Wiki, UserProfile

@allow_http("GET", "POST")
@rendered_with("sites/user_index.html")
def home(request):
    if request.method == "GET":
        if request.site is not None:
            return redirect(request.site.site_home_url())

        sites = Wiki.objects.filter(users=request.user)
        return dict(sites=sites)

    site = Wiki(name=request.POST['name'])
    site.save()
    site.users.add(request.user)
    return redirect(".")

@allow_http("GET")
@rendered_with("sites/site/home.html")
def site_home(request):
    site = request.site

    return dict(site=site)

@allow_http("GET", "POST")
@rendered_with("sites/user_account.html")
def user_account(request):
    user = request.user
    profile = UserProfile.objects.get_or_create(user=user)[0]

    if request.method == "POST":
        redirect_to = request.POST.get('redirect_to', '.')

        username = request.POST['github_username']
        token = request.POST['github_api_token']
        profile.github_username = username
        profile.github_api_token = token
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

    return {
        'profile': profile,
        'message': message,
        'redirect_to': redirect_to,
        }

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
        
    repo = site.github_site()
    if not repo.create_repo(username, token):
        messages.error(request, "failedauth")
        # @@todo: reverse urlconf
        return redirect("/.home/account/")
        
    return redirect(site.deploy_dashboard_url())
    
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

    subprocess.call(["git", "init"])
    subprocess.call(["git", "remote", "add", "github",
                     site.github_site().push_url()])

    gitignore = open(".gitignore", 'w')
    gitignore.write(".bzr")
    gitignore.close()
    subprocess.call(["git", "add", ".gitignore"])

    subprocess.call(["git", "commit",
                     "-m", "initializing site"])

    subprocess.call(["git", "branch", "gh-pages"])
    subprocess.call(["git", "checkout", "gh-pages"])
    subprocess.call(["git", "push", "github", "gh-pages"])

    os.chdir(curdir)
    shutil.rmtree(checkout_path)

    return redirect(site.deploy_dashboard_url())

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

    subprocess.call(["git", "clone", "-b", "gh-pages",
                     site.github_site().push_url(),
                     "."])

    gitfiles = glob.glob(".*")
    for file in os.listdir(checkout_path):
        if file in gitfiles:
            continue
        if os.path.isfile(file):
            os.remove(file)
        elif os.path.isdir(file):
            shutil.rmtree(file)

    subprocess.call(["bzr", "co", site.repo_path, "."])

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

@allow_http("GET")
@rendered_with("sites/site/page-history.html")
def page_history(request, subpath):
    site = request.site

    try:
        history = site.get_history(subpath)
    except sven.NoSuchResource:
        return redirect(site.page_edit_url(subpath))
        
    return dict(site=site, history=history)

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

@allow_http("GET", "POST")
@rendered_with("sites/site/page-create.html")
def page_create(request, subpath):
    site = request.site

    if request.method == "POST":
        path = request.POST['path']
        path = subpath.rstrip('/') + '/' + path.strip('/')

        # @@todo: do something else if the page already exists, i guess?
        return redirect(site.page_edit_url(path))

    try:
        subpaths = site.get_contents(subpath)
    except sven.NotADirectory:
        return redirect(site.page_view_url(subpath))
    except sven.NoSuchResource:
        return redirect(site.page_edit_url(subpath))

    # @@todo: maybe check for user-supplied index page?
    return dict(site=site, path=subpath, subpaths=subpaths,
                form_url=site.page_create_url(subpath))

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
        site.write_page(subpath, contents)
        return redirect(site.page_view_url(subpath))

    try:
        contents = site.get_page(subpath)
    except sven.NoSuchResource:  # this is fine, we can edit a new file
        contents = ""
    except sven.NotAFile:  # this is not fine, we can't edit a directory
        # @@todo: maybe check for user-supplied index page?
        return redirect(site.directory_index_url(subpath))

    # @@todo: dispatch to different editors based on mimetype

    return dict(contents=contents, path=subpath,
                form_url=site.page_edit_url(subpath))
