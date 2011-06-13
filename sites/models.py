from ConfigParser import RawConfigParser, NoOptionError, NoSectionError
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import os
import subprocess
from sven.bzr import BzrAccess
from StringIO import StringIO

SESSION_KEY = 'svenweb.sites.site'
UNSET_KEY = 'svenweb.unset_site'
SET_KEY = 'svenweb.set_site'

def _create_repo(path):
    cmd = ["bzr", "init", "--create-prefix", path]
    result = subprocess.call(cmd)
    if result != 0:
        raise RuntimeError("error creating bzr repo %s: exit code %s" % (path, result))
    
class _NoDefault(object):
    pass
NoDefault = _NoDefault()
del _NoDefault

class Wiki(models.Model):
    name = models.TextField()
    users = models.ManyToManyField(User)
    config = models.TextField()

    def set_options(self, kwargs):
        if not self.config:
            self.config = "[options]"
        config = RawConfigParser()
        fp = StringIO(self.config)
        config.readfp(fp)

        for key, val in kwargs.items():
            config.set("options", key, val)

        fp = StringIO()
        config.write(fp)
        fp.seek(0)
        self.config = fp.read()
        self.save()

    def get_option(self, key, default=NoDefault, asbool=False):
        config = RawConfigParser()
        fp = StringIO(self.config)

        config.readfp(fp)
        try:
            value = config.get("options", key)
        except (NoOptionError, NoSectionError):
            if default is NoDefault:
                raise
            return default

        if not asbool:
            return value.strip()

        value = value.lower()
        if value in ("1", "true", "t", "yes", "y", "on"):
            return True
        elif value in ("0", "false", "f", "no", "n", "off"):
            return False
        else:
            raise TypeError("Cannot convert to bool: %s" % value)

    def custom_domain(self):
        return self.get_option("custom_domain", "")

    def github_repo(self):
        return self.get_option("github_repo", "")

    def github_site(self):
        return GithubSite(self)

    def viewable(self, request):
        try:
            user = self.users.get(pk=request.user.pk)
        except User.DoesNotExist:
            return False
        return True

    def switch_context(self):
        return "?%s=%s" % (SET_KEY, self.pk)

    @models.permalink
    def site_home_url(self):
        return ('site_home', [])

    @models.permalink
    def page_view_url(self, subpath=""):
        return ('page_view', [subpath])

    @models.permalink
    def page_edit_url(self, subpath="/"):
        return ('page_edit', [subpath])

    @models.permalink
    def page_create_url(self, subpath=""):
        return ('page_create', [subpath])

    @models.permalink
    def directory_index_url(self, subpath=""):
        return ('page_index', [subpath])

    @models.permalink
    def history_url(self, subpath=""):
        return ('page_history', [subpath])

    @models.permalink
    def deploy_dashboard_url(self):
        return ('site_deploy', [])

    @property
    def repo_path(self):
        path = settings.SVENWEB_REPO_PATH
        path = os.path.abspath(path)
        path = os.path.join(path, str(self.pk))
        return path

    def create_repo(self):
        path = self.repo_path
        if not os.path.exists(path):
            _create_repo(path)
        if os.path.isfile(path):
            raise RuntimeError("path %s exists but is a file" % path)
        if os.path.isdir(path):
            if not os.path.exists(os.path.join(path, ".bzr")):
                raise RuntimeError("path %s exists but is not a bzr repo" % path)

    def get_contents(self, path='/'):
        repo = BzrAccess(self.repo_path)
        paths = []
        for page in repo.ls(path):
            paths.append(page['href'])
        return paths

    def get_page(self, path='/'):
        repo = BzrAccess(self.repo_path)
        return repo.read(path)

    def write_page(self, path, contents):
        repo = BzrAccess(self.repo_path)
        return repo.write(path, contents)

    def get_history(self, path='/'):
        repo = BzrAccess(self.repo_path)
        contents = repo.log(path)
        for obj in contents:
            timestamp = obj['fields']['timestamp']
            from wsgiref.handlers import format_date_time
            obj['fields']['timestamp'] = \
                format_date_time(timestamp)
        return contents

class GithubSite(object):
    """
    Adapts Wiki objects
    """
    def __init__(self, wiki):
        self.wiki = wiki

    def repo(self):
        repo = self.wiki.github_repo()
        assert "/" in repo
        return repo

    def push_url(self):
        return "git@github.com:%s.git" % self.repo()

    def repo_exists(self):
        from github2.client import Github
        github = Github(requests_per_second=1)
        try:
            repo = github.repos.show(self.repo())
        except RuntimeError:
            return False
        return True

    def ghpages_exists(self):
        from github2.client import Github
        github = Github(requests_per_second=1)
        try:
            branches = github.repos.branches(self.repo())
        except RuntimeError:
            return False
        return 'gh-pages' in branches

    def create_repo(self, username, token):
        """
        Returns True if creation succeeds.
        Returns False if user is unauthorized.
        Raises underlying exception otherwise.
        """
        assert not self.repo_exists()
        from github2.client import Github
        github = Github(requests_per_second=1,
                        username=username, api_token=token)
        try:
            repo = github.repos.create(self.repo())
        except RuntimeError, exc:
            if "401" in exc.args[0]:
                return False
            raise
        return True

class UserProfile(models.Model):
    user = models.ForeignKey(User)
    github_username = models.TextField()
    github_api_token = models.TextField()

