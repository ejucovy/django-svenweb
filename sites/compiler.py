import subprocess
import tempfile
import os

def managed_html_wiki_compiler(export_path, compiler):
    """
    Compiles according to these rules:
    * Items in /b/ are left alone
    * All other items are assumed to contain HTML snippets
    ** They are renamed to ensure a .html suffix
    ** TODO: Links within them are rewritten after the renaming
    ** TODO: They are wrapped in an HTML/HEAD/BODY block
    ** TODO: add interesting stuff to the head and body like ..
    *** standard CSS?
    *** link rel=favicon?
    *** other link rels?
    """

    renamed = []
    wiki = compiler.wiki

    raw_files_path = wiki.raw_files_path.lstrip('/')

    for root, dirs, files in os.walk(export_path):
        if root.startswith(os.path.join(
                export_path, raw_files_path)):
            continue
        for file in files:
            if file.endswith(".html"):
                continue

            # Modify it
            original_full_path = os.path.join(root, file)
            fp = open(original_full_path, 'r')
            contents = fp.read()
            fp.close()

            # Wrap it in standard html
            fp = open(original_full_path, 'w')
            contents = """\
<html><body>
<div id="content">
%s
</div>
</body></html>""" % contents
            fp.write(contents)
            fp.close()

            # Rename it
            original_full_path = os.path.join(root, file)
            new_name = "%s.html" % file
            new_full_path = os.path.join(root, new_name)
            os.rename(original_full_path, new_full_path)
            renamed.append((root[len(export_path):] + '/' + file, 
                            root[len(export_path):] + '/' + new_name))

    theme_path = wiki.themer.theme_path() or "b/theme/coactivate"

    http_host, script_name = compiler.compiled_site_root()
    if theme_path:
        theme_uri = script_name + '/' + theme_path + "/theme.html"
        from webob import Response
        def wsgi_app(environ, start_response):
            file = os.path.join(export_path.rstrip('/'),
                                environ['PATH_INFO'].lstrip('/'))
            with open(file
                      ) as fp:
                return Response(fp.read(), content_type="text/html")(environ, start_response)

        from deliverance.middleware import make_deliverance_middleware
        app = make_deliverance_middleware(
            wsgi_app, {}, debug=True,
            rule_filename="/home/egj/Code/cel/svenweb/rules.xml", 
            theme_uri=theme_uri)

        from paste.urlmap import URLMap
        _app = URLMap()
        _app[script_name] = app
        app = _app
        
        from webtest import TestApp
        app = TestApp(app, extra_environ={
                "HTTP_HOST": http_host,
                })

        for orig, new in renamed:
            resp = app.get("%s/%s" % (script_name, 
                                      new.lstrip("/")))
            fp = open(os.path.join(export_path.rstrip('/'), new.lstrip('/')), 'w')
            fp.write(resp.body)
            fp.close()

    return export_path

class WikiCompiler(object):
    """
    Adapts wiki objects
    """
    def __init__(self, wiki):
        self.wiki = wiki

    def wiki_type(self):
        type = self.wiki.wiki_type()
        assert type in ("raw", "managedhtml")
        return type

    def compiled_site_root(self):
        """ Return (HTTP_HOST, SCRIPT_NAME) """
        domain = self.wiki.custom_domain()
        if domain:
            return (domain, '')
        repo = self.wiki.github.repo()
        if repo:
            container, repo = repo.split('/')
            return (container, '/%s' % repo)
        raise TypeError("This wiki doesn't know where it's going")

    def compile(self):
        export_path = tempfile.mkdtemp()

        curdir = os.getcwd()
        os.chdir(self.wiki.repo_path)
        subprocess.call(["bzr", "export", export_path])
        os.chdir(curdir)

        if self.wiki_type() == "raw":
            pass
        if self.wiki_type() == "managedhtml":
            managed_html_wiki_compiler(export_path, self)

        os.chdir(curdir)
        return export_path
