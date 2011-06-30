from django.contrib import admin

from svenweb.sites.models import (Wiki, UserProfile, 
                                  UserWikiLocalRoles,
                                  WikiRolePermissions)

admin.site.register(Wiki)
admin.site.register(UserProfile)
admin.site.register(UserWikiLocalRoles)
admin.site.register(WikiRolePermissions)
