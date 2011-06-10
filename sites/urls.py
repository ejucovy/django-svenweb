from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns(
    '',
    url(r'^.home/$', 'svenweb.sites.views.site_home', name='site_home'),
    url(r'^$', 'svenweb.sites.views.home', name='home'),

    url(r'^.deploy/$', 'svenweb.sites.views.deploy'),
    url(r'^.deploy/github/init/$', 'svenweb.sites.views.deploy_to_github_initial'),
    url(r'^.deploy/github/push/$', 'svenweb.sites.views.deploy_to_github'),

    url(r'^.index/(?P<subpath>.*)/*$', 'svenweb.sites.views.page_index', name='page_index'),
    url(r'^.history/(?P<subpath>.*)/*$', 'svenweb.sites.views.page_history', name='page_history'),
    url(r'^.create/(?P<subpath>.*)/*$', 'svenweb.sites.views.page_create', name='page_create'),
    url(r'^.edit/(?P<subpath>.*)/*$', 'svenweb.sites.views.page_edit', name='page_edit'),
    url(r'^(?P<subpath>.*)/*$', 'svenweb.sites.views.page_view', name='page_view'),
)
