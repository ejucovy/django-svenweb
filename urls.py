from django.conf.urls.defaults import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url(r'^admin/', include(admin.site.urls)),

    url(r'^.oauth/$', 'svenweb.sites.views.oauth',),

    url(r'^.home/$', 'svenweb.sites.views.site_home', name='site_home'),
    url(r'^.home/configure/$', 'svenweb.sites.views.site_configure', name='site_configure'),
    url(r'^.home/account/$', 'svenweb.sites.views.user_account', 
        name='user_account'),

    url(r'^$', 'svenweb.sites.views.home', name='home'),

    url(r'^.deploy/$', 'svenweb.sites.views.deploy', name="site_deploy"),
    url(r'^.deploy/github/init/$', 'svenweb.sites.views.deploy_to_github_initial'),
    url(r'^.deploy/github/create/$', 'svenweb.sites.views.create_github_repo'),
    url(r'^.deploy/github/push/$', 'svenweb.sites.views.deploy_to_github'),

    url(r'^.index/(?P<subpath>.*)/*$', 'svenweb.sites.views.page_index', name='page_index'),
    url(r'^.history/(?P<subpath>.*)/*$', 'svenweb.sites.views.page_history', name='page_history'),
    url(r'^.create/(?P<subpath>.*)/*$', 'svenweb.sites.views.page_create', name='page_create'),
    url(r'^.edit/(?P<subpath>.*)/*$', 'svenweb.sites.views.page_edit', name='page_edit'),
    url(r'^.upload/(?P<subpath>.*)/*$', 'svenweb.sites.views.file_upload', name='file_upload'),

    url(r'^(?P<subpath>.*)/*$', 'svenweb.sites.views.page_view', name='page_view'),
)
