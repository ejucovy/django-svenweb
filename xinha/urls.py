from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns(
    'svenweb.xinha.views',

    url(r'^linker/$', 'xinha_linker_backend',),
    url(r'^image_manager/$', 'xinha_image_manager_backend',),
    url(r'^image_manager/images/*$',
        'xinha_image_manager_backend_images',),
    url(r'^image_manager/upload/$', 
        'xinha_image_manager_backend_upload',),

    # @@ TODO: weird bug somewhere in xinha insisting on this url sometimes
    url(r'^image_manager/__function=images.*$',
        'xinha_image_manager_backend_images',),
    
    )
