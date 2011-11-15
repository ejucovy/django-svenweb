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
        if wiki.is_raw_path(root):
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

        os.chdir(curdir)
        return export_path
