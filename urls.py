from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$', 'svenweb.sites.views.home', name='home'),
    url(r'^.index/(?P<subpath_id>.*)$', 'svenweb.sites.views.page_index', name='page_index'),
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url(r'^admin/', include(admin.site.urls)),
)
