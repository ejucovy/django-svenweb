from lxml.html import parse, tostring
import mimetypes
import urllib2
import posixpath

class Themer(object):

    def __init__(self, wiki):
        self.wiki = wiki

    def theme_path(self, name=None):
        name = name or self.wiki.get_option("theme_name", "")
        if not name:
            return None
        return self.wiki.raw_files_path + "theme/" + name

    def fetch_theme(self, theme_url, theme_name):
        mountpoint = self.wiki.theme_path(theme_name)
        content, files = self.get_content(theme_url, mountpoint)
        files = [("theme.html", content)] + files
        return self.wiki.write_pages(
            files, prefix=mountpoint,
            msg="Importing theme \"%s\" from %s" % (theme_name, theme_url))
    
    def get_content(self, url, mountpoint=''):
        """
        Gets the content and all embedded content (images, CSS, etc)
        Links to embedded content are rewritten to be relative
        """
        page = parse(urllib2.urlopen(url)).getroot()
        page.make_links_absolute()
        files = []
        for element, attr, link, pos in page.iterlinks():
            if not self._embedded_link(element):
                continue
            filename, content = self.get_embedded(link)
            if not filename:
                continue
            files.append((filename, content))
            if attr is None:
                old_value = element.text
            else:
                old_value = unicode(element.attrib[attr])
            new_value = old_value[:pos] + filename + old_value[pos+len(link):]
            if attr is None:
                element.text = new_value
            else:
                element.attrib[attr] = new_value
        return tostring(page), files

    def _embedded_link(self, element):
        """True if the element links to something embedded"""
        if element.tag in ('script', 'img', 'style'):
            return True
        if element.tag == 'link' and element.attrib.get('rel', '').lower() == 'stylesheet':
            return True
        return False

    def get_embedded(self, url):
        try:
            resp = urllib2.urlopen(url)
        except urllib2.HTTPError, e:
            #print 'Could not fetch %s: %s' % (url, e)
            return None, None
        url = resp.geturl()
        content = resp.read()
        content_type = resp.info()['content-type']
        filename = posixpath.basename(url).split('?')[0]
        filename, orig_ext = posixpath.splitext(filename)
        if not filename:
            filename = 'embedded'
        ext = mimetypes.guess_extension(content_type)
        if ext == '.jpeg' or ext == 'jpe':
            ext = '.jpg'
        ext = ext or orig_ext
        return filename + ext, content
