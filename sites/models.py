from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import os
import subprocess
from sven.bzr import BzrAccess

SESSION_KEY = 'svenweb.sites.site'
UNSET_KEY = 'svenweb.unset_site'
SET_KEY = 'svenweb.set_site'

def _create_repo(path):
    cmd = ["bzr", "init", "--create-prefix", path]
    result = subprocess.call(cmd)
    if result != 0:
        raise RuntimeError("error creating bzr repo %s: exit code %s" % (path, result))
    
class Wiki(models.Model):
    name = models.TextField()
    users = models.ManyToManyField(User)
    config = models.TextField()

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
    def page_view_url(self, subpath="/"):
        return ('page_view', [subpath])

    @models.permalink
    def page_edit_url(self, subpath="/"):
        return ('page_edit', [subpath])

    @models.permalink
    def page_create_url(self, subpath="/"):
        return ('page_create', [subpath])

    @models.permalink
    def directory_index_url(self, subpath="/"):
        return ('page_index', [subpath])

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
