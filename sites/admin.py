from django.contrib import admin

from svenweb.sites.models import Wiki, UserProfile, UserWikiPermissions

admin.site.register(Wiki)
admin.site.register(UserProfile)
admin.site.register(UserWikiPermissions)

