from ConfigParser import RawConfigParser, NoOptionError, NoSectionError
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import os
import subprocess
from sven.bzr import BzrAccess
from svenweb.sites.github import GithubSite
from svenweb.sites.compiler import WikiCompiler
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

    def wiki_type(self):
        return self.get_option("wiki_type", "raw")

    def custom_domain(self):
        return self.get_option("custom_domain", "")

    @property
    def github(self):
        return GithubSite(self)

    @property
    def compiler(self):
        return WikiCompiler(self)
    
    def viewable(self, request):
        try:
            user = self.users.get(pk=request.user.pk)
        except User.DoesNotExist:
            return False
        return True

    def switch_context(self):
        return "?%s=%s" % (SET_KEY, self.pk)

    @models.permalink
    def upload_file_url(self):
        if self.wiki_type() == "raw":
            subpath = ''
        elif self.wiki_type() == "managedhtml":
            subpath = 'b'
        else:
            raise AssertionError("Unknown wiki type %s" % self.wiki_type())
        return ('file_upload', [subpath])

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

from django.conf import settings

class UserProfile(models.Model):
    user = models.ForeignKey(User)
    github_username = models.TextField()
    github_api_token = models.TextField()

    _ssh_config_template = """# Client user (%(user)s)
Host github-%(user)s
  HostName github.com
  User git
  IdentityFile %(basedir)s%(user)s/id_rsa"""

    def maybe_generate_github_key(self):
        user = self.user.username
        basedir = settings.GITHUB_SSH_DIR.rstrip('/') + '/'

        config = self._ssh_config_template % locals()

        file = open(os.path.join(basedir, 'config'))
        config_contents = file.read()
        file.close()

        if config not in config_contents:
            with open(os.path.join(basedir, 'config'), 'a') as file:
                print >> file, config

        keyfile = os.path.join(settings.GITHUB_SSH_DIR, self.user.username, "id_rsa.pub")
        if not os.path.exists(keyfile):
            if not os.path.exists(os.path.join(settings.GITHUB_SSH_DIR, self.user.username)):
                os.makedirs(os.path.join(settings.GITHUB_SSH_DIR, self.user.username))
            subprocess.call(["ssh-keygen", "-t", "rsa",  "-N", '',
                             "-f", os.path.join(basedir, user, "id_rsa")])

    def register_github_key(self):
        from github2.client import Github
        github = Github(requests_per_second=1,
                        username=self.github_username,
                        api_token=self.github_api_token)
        import os
        keyfile = os.path.join(settings.GITHUB_SSH_DIR, self.user.username, "id_rsa.pub")
        
        self.maybe_generate_github_key()

        with open(keyfile) as keyfile:
            pubkey = keyfile.read().strip()
        resp = github.users.make_request(
            "key", "add", method="POST",
            post_data={'title': "wiki.socialplanning.org", 'key': pubkey})
        # error-check
        for key in resp['public_keys']:
            if (key['title'] == 'wiki.socialplanning.org' and 
                pubkey.startswith(key['key'])): # github trims the user suffix
                return True
        # @@todo: diagnose?
        return False
