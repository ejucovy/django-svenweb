from ConfigParser import RawConfigParser, NoOptionError, NoSectionError
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import os
import subprocess
from sven import exc as sven
from sven.bzr import BzrAccess
from svenweb.sites.github import GithubSite
from svenweb.sites.compiler import WikiCompiler
from StringIO import StringIO
from svenweb.sites.utils import permalink

SESSION_KEY = 'svenweb.sites.site'
UNSET_KEY = 'svenweb.unset_site'
SET_KEY = 'svenweb.set_site'

import re
wiki_link_text = re.compile(r"""                                                                                                                                                               
        (\(\(   )   # The opening (( of the Wicked link "(?<=" prevents the prefix from returning with the match                                                                          
        [^)]*            # The initial text (no closing parentheses) of the wicked link                                                                                                        
        ( \) [^)]+ )*    # Any amount of single closing parentheses with trailing text.                                                                                                        
                         # If there is no trailing text, this is not a single parentheses                                                                                                      
        (\)\))         # The closing )) of the Wicked link, "?=" prevents the suffix from returning with the match                                                                           
    """, re.VERBOSE)

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
    name = models.TextField(unique=True)
    config = models.TextField()

    def __unicode__(self):
        return self.name

    def set_options(self, kwargs, section="options"):
        if not self.config:
            self.config = "[%s]" % section
        config = RawConfigParser()
        fp = StringIO(self.config)
        config.readfp(fp)

        for key, val in kwargs.items():
            config.set(section, key, val)

        fp = StringIO()
        config.write(fp)
        fp.seek(0)
        self.config = fp.read()
        self.save()

    def get_option(self, key, default=NoDefault, asbool=False, section="options"):
        config = RawConfigParser()
        fp = StringIO(self.config)

        config.readfp(fp)
        try:
            value = config.get(section, key)
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

    def add_raw_path(self, path):
        self.set_options({path: "raw"}, section="path_properties")

    def get_raw_paths(self):
        config = RawConfigParser()
        fp = StringIO(self.config)

        config.readfp(fp)
        try:
            value = config.options("path_properties")
        except (NoOptionError, NoSectionError):
            return []
        paths = []
        for option in value:
            if config.get("path_properties", option) == "raw":
                paths.append(option)
        return paths

    def is_raw_path(self, subpath):
        for path in self.get_raw_paths():
            if subpath.startswith(path):
                return True
        return False

    def wiki_type(self):
        return self.get_option("wiki_type", "managedhtml")

    def custom_domain(self):
        return self.get_option("custom_domain", "")

    @property
    def github(self):
        return GithubSite(self)

    @property
    def compiler(self):
        return WikiCompiler(self)
    
    def get_permissions(self, request):
        if request.user.is_superuser:
            return [i[0] for i in PERMISSIONS]
        return request.get_permissions(self)

    def viewable(self, request):
        return "WIKI_VIEW" in self.get_permissions(request)

    def add_admin_user(self, user_or_username):
        """
        Normally you will pass a `auth.User` instance to this method,
        but you can also pass a username string directly.`
        """
        if isinstance(user_or_username, basestring):
            username = user_or_username
        else:
            username = user_or_username.username
        local_roles, _ = UserWikiLocalRoles.objects.get_or_create(
            username=username, wiki=self)
        local_roles.add_role("WikiManager")
        local_roles.save()

    def switch_context(self):
        return "?%s=%s" % (SET_KEY, self.pk)

    @property
    def raw_files_path(self):
        if self.wiki_type() == "raw":
            subpath = '/'
        elif self.wiki_type() == "managedhtml":
            subpath = '/b/'
        else:
            raise AssertionError("Unknown wiki type %s" % self.wiki_type())
        return subpath

    @permalink
    def upload_file_url(self):
        return ('file_upload', [self.raw_files_path.strip('/')])

    @permalink
    def site_home_url(self):
        return ('site_home', [])

    @permalink
    def page_view_url(self, subpath=""):
        return ('page_view', [subpath])

    @permalink
    def history_version_url(self, subpath=""):
        return ('page_history_version', [subpath])

    @permalink
    def latest_change_url(self, subpath=""):
        return ("latest_change", [subpath])

    @permalink
    def page_edit_url(self, subpath=""):
        return ('page_edit', [subpath])

    @permalink
    def page_create_url(self, subpath=""):
        return ('page_create', [subpath])

    @permalink
    def directory_index_url(self, subpath=""):
        return ('page_index', [subpath])

    @permalink
    def history_url(self, subpath=""):
        return ('page_history', [subpath])

    @permalink
    def page_diff_url(self, subpath=""):
        return ('page_diff', [subpath])

    @permalink
    def deploy_dashboard_url(self):
        return ('site_deploy', [])

    @permalink
    def wiki_configure_url(self):
        return ('site_configure', [])

    @permalink
    def xinha_linker_url(self):
        return ('xinha_linker', [])

    @permalink
    def xinha_image_manager_url(self):
        return ('xinha_image_manager', [])

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

    def get_page(self, path='/', rev=None):
        repo = BzrAccess(self.repo_path)
        return repo.read(path, rev=rev)

    def write_page(self, path, contents, msg=None, username=None):
        repo = BzrAccess(self.repo_path)
        return repo.write(path, contents, msg=msg, author=username)

    def write_pages(self, files, prefix='', msg=None, username=None):
        repo = BzrAccess(self.repo_path)
        for path, contents in files:
            repo.write("%s/%s" % (prefix, path),
                       contents, commit=False)
        return repo.commit(prefix, msg=msg, author=username)

    def latest_change(self, path=""):
        # @@todo: optimize this: only need to fetch one, not all
        repo = BzrAccess(self.repo_path)
        try:
            contents = repo.log(path)
        except sven.NoSuchResource:
            return None

        for obj in contents:
            timestamp = obj['fields']['timestamp']
            import datetime
            obj['fields']['timestamp'] = \
                datetime.datetime.fromtimestamp(timestamp)
        return contents[0]['fields']
        
    def get_history(self, path='/'):
        repo = BzrAccess(self.repo_path)
        contents = repo.log(path)
        for obj in contents:
            timestamp = obj['fields']['timestamp']
            import datetime
            obj['fields']['timestamp'] = \
                datetime.datetime.fromtimestamp(timestamp)
        return contents

    def new_page_template(self, ctx={}):
        """
        Render a template for the default new page content in the editor
        """
        from django.template import Template, Context
        
        t = Template("""
{% if created_from %}
<p>
Back to (({{created_from.title}}))
</p>
{% endif %}
""")
        ctx = Context(ctx)
        return t.render(ctx)

    def baked_content(self, content, content_href=None):
        """
        Applies any transformations to the given page content
        """
        def treat_link_text(match):
            link_text = match.group()[2:-2]
            from django.template.defaultfilters import slugify
            href = slugify(link_text)
            try:
                exists = self.latest_change(href) is not None
            except:
                exists = False
            if exists:
                return '<a class="wicked_resolved" href="%s">%s</a>' % (href, link_text)
            else:
                if content_href is not None:
                    href += "?created_from=%s" % content_href
                return '<a class="wickedadd" href="%s">%s +</a>' % (href, link_text)
        return re.sub(wiki_link_text, treat_link_text, content)        

from django.conf import settings

class UserProfile(models.Model):
    user = models.ForeignKey(User)
    config = models.TextField()

    @property
    def github_username(self):
        return self.get_option("github_username", default='')

    @property
    def github_api_token(self):
        return self.get_option("github_api_token", default='')

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

PERMISSIONS = (
    ("WIKI_VIEW", "view wiki content"),
    ("WIKI_HISTORY", "view wiki history"),
    ("WIKI_EDIT", ("edit wiki content, create new pages "
                   "and revert to old versions")),
    ("WIKI_DEPLOY", "manually redeploy the wiki's website"),
    ("WIKI_CONFIGURE", "change wiki settings"),
    )

def apply_constraints(recommendations, constraints):
    permissions = []
    for permission in recommendations:
        if permission in constraints:
            permissions.append(permission)
    return permissions

class UserWikiLocalRoles(models.Model):
    username = models.TextField()
    wiki = models.ForeignKey(Wiki)

    roles = models.TextField()

    def __unicode__(self):
        return "%s: %s" % (self.wiki, self.username)

    def get_roles(self):
        if not self.roles:
            return []
        return self.roles.split(',')

    def has_role(self, role):
        return role in self.get_roles()

    #def add_all_permissions(self):
    #    permissions = ','.join(PERMISSIONS.keys())
    #    self.permissions = permissions
    #    self.save()

    def add_role(self, role):
        roles = self.get_roles()
        if role not in roles:
            roles.append(role)
        self.roles = ','.join(roles)
        self.save()

    def remove_role(self, role):
        roles = self.get_roles()
        if role in roles:
            roles.remove(role)
        self.roles = roles
        self.save()

class WikiRolePermissions(models.Model):
    wiki = models.ForeignKey(Wiki)
    role = models.TextField()
    
    permissions = models.TextField()

    def __unicode__(self):
        return "%s: %s" % (self.wiki, self.role)

    def get_permissions(self):
        if not self.permissions:
            return []
        return self.permissions.split(',')

    def set_permissions(self, permissions):
        if not permissions:
            self.permissions = ''
        self.permissions = ','.join(permissions)
        self.save()

    def has_permission(self, permission):
        return permission in self.get_permissions()

    #def add_all_permissions(self):
    #    permissions = ','.join(PERMISSIONS.keys())
    #    self.permissions = permissions
    #    self.save()

    def add_permission(self, permission):
        permissions = self.get_permissions()
        if permission not in permissions:
            permissions.append(permissions)
        self.permissions = permissions
        self.save()

    def remove_permission(self, permission):
        permissions = self.get_permissions()
        if permission in permissions:
            permissions.remove(permission)
        self.permissions = permissions
        self.save()
