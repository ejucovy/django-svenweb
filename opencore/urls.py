from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url(r'^admin/', include(admin.site.urls)),
    
    url(r'^$', 'svenweb.opencore.views.home', name='home'),
    url(r'^(?P<site_name>\w+)/', include('svenweb.sites.urls')),
    
    )
