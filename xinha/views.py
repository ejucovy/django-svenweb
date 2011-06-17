from djangohelpers.lib import allow_http, rendered_with
from django.http import HttpResponse, HttpResponseRedirect as redirect
from django.contrib import messages
import mimetypes
from sven import exc as sven
from svenweb.sites.models import Wiki, UserProfile
from django.conf import settings
from restclient import POST
import json
from django.views.decorators.csrf import csrf_exempt
import os

@csrf_exempt
@allow_http("GET", "POST")
def xinha_linker_backend(request):
    site = request.site

    def recursive_walk(path):
        files = []
        for subpath in site.get_contents(path):
            data = {'url': subpath}
            file_path = os.path.join(site.repo_path, path, subpath)
            if os.path.isdir(file_path):
                data['children'] = recursive_walk(subpath)
            files.append(data)
        return files
    
    files = recursive_walk('')
    return HttpResponse(json.dumps(files), mimetype="application/json")

import imghdr

@csrf_exempt
@allow_http("GET", "POST")
@rendered_with("xinha/image_manager.html")
def xinha_image_manager_backend(request):
    return {}

from PIL import Image
@csrf_exempt
@allow_http("GET", "POST")
@rendered_with("xinha/image_manager_images.html")
def xinha_image_manager_backend_images(request):
    site = request.site

    def recursive_walk(path):
        files = []
        for subpath in site.get_contents(path):
            file_path = os.path.join(site.repo_path, subpath)
            if os.path.isdir(file_path):
                files.extend(recursive_walk(subpath))
            elif imghdr.what(file_path) is not None:
                image = Image.open(file_path)
                width, height = image.size
                files.append({
                        'path': '/' + subpath.lstrip('/'),
                        'thumb_uri': '/' + subpath.lstrip('/'),
                        'title': os.path.basename(file_path),
                        'description': os.path.basename(file_path),
                        'id': subpath,
                        'width': width, 'height': height,
                        })
        return files
    
    images = recursive_walk(site.raw_files_path.strip('/'))
    return {'images': images}

@csrf_exempt
def xinha_image_manager_backend_upload(request):
    pass
