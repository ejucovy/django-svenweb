from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns(
    '',
    url(r'^.xinha/', include('svenweb.xinha.urls')),

    url(r'^.oauth/$', 'svenweb.sites.views.oauth',),
    
    url(r'^.home/$', 'svenweb.sites.views.site_home', name='site_home'),
    url(r'^.home/configure/$', 'svenweb.sites.views.site_configure', 
        name='site_configure'),
    url(r'^.home/account/$', 'svenweb.sites.views.user_account', 
        name='user_account'),

    url(r'^.deploy/$', 'svenweb.sites.views.deploy', name="site_deploy"),
    url(r'^.deploy/github/init/$', 'svenweb.sites.views.deploy_to_github_initial'),
    url(r'^.deploy/github/create/$', 'svenweb.sites.views.create_github_repo'),
    url(r'^.deploy/github/push/$', 'svenweb.sites.views.deploy_to_github'),

    url(r'^.index/(?P<subpath>.*)/*$', 'svenweb.sites.views.page_index', name='page_index'),
    url(r'^.history/(?P<subpath>.*)/*$', 'svenweb.sites.views.page_history', name='page_history'),
    url(r'^.version/(?P<subpath>.*)/*$', 'svenweb.sites.views.page_history_version', name='page_history_version'),
    url(r'^.latest_change/(?P<subpath>.*)/*$', 'svenweb.sites.views.latest_change', name='latest_change'),

    url(r'^.create/(?P<subpath>.*)/*$', 'svenweb.sites.views.page_create', name='page_create'),
    url(r'^.edit/(?P<subpath>.*)/*$', 'svenweb.sites.views.page_edit', name='page_edit'),
    url(r'^.diff/(?P<subpath>.*)/*$', 'svenweb.sites.views.page_diff', name='page_diff'),
    url(r'^.upload/(?P<subpath>.*)/*$', 'svenweb.sites.views.file_upload', name='file_upload'),

    url(r'^(?P<subpath>.*)/*$', 'svenweb.sites.views.page_view', name='page_view'),

)
