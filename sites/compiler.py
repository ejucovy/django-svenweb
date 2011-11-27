import subprocess
import tempfile
import os

def managed_html_wiki_compiler(export_path, wiki):
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
    for root, dirs, files in os.walk(export_path):
        if root.startswith(os.path.join(
                export_path, wiki.raw_files_path.lstrip('/'))):
            continue
        wiki_path = canonical_path(root[len(export_path):])
        print "%s -- raw path? %s" % (wiki_path, wiki.is_raw_path(wiki_path))
        print wiki.get_raw_paths()
        if wiki.is_raw_path(wiki_path):
            continue
        for file in files:
            if file.endswith(".html"):
                continue
            original_full_path = os.path.join(root, file)
            new_name = "%s.html" % file
            new_full_path = os.path.join(root, new_name)
            os.rename(original_full_path, new_full_path)
            renamed.append((file, new_name))

    return export_path

def canonical_path(path):
    path = path.strip("/")
    path = "/" + path
    if not path.endswith("/"):
        path = path + "/"
    return path

def deploy_from_subpath_compiler(export_path, wiki):
    renamed = []
    removed = []
    deploy_path = canonical_path(wiki.deploy_path())
    if deploy_path == "/":
        return

    for root, dirs, files in os.walk(export_path):
        current_path = canonical_path(root[len(export_path):])

        for file in files:
            original_full_path = os.path.join(root, file)
            if not current_path.startswith(deploy_path):
                os.unlink(original_full_path)
                removed.append(original_full_path)
                continue
            trimmed_path = current_path[len(deploy_path):]
            new_parent_path = os.path.join(export_path, trimmed_path)
            new_full_path = os.path.join(new_parent_path, file)
            if not os.path.exists(new_parent_path):
                os.makedirs(new_parent_path)
            os.rename(original_full_path, new_full_path)
            renamed.append((original_full_path, new_full_path))

    print renamed
    print removed
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

    def compile(self):
        export_path = tempfile.mkdtemp()

        curdir = os.getcwd()
        os.chdir(self.wiki.repo_path)
        subprocess.call(["bzr", "export", export_path])
        os.chdir(export_path)

        if self.wiki_type() == "raw":
            pass
        if self.wiki_type() == "managedhtml":
            managed_html_wiki_compiler(export_path, self.wiki)

        deploy_from_subpath_compiler(export_path, self.wiki)

        os.chdir(curdir)
        return export_path
