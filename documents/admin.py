from django.contrib import admin

from .models import AccessLog, Notification

# Records and their enclosures are deliberately NOT registered here. Editing or
# deleting them through /django-admin/ would skip the recycle bin, the control
# number rules and the audit trail; all changes go through the archive's own pages.


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "action", "document", "ip_address")
    list_filter = ("action",)
    search_fields = ("user__username", "note")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "recipient", "actor", "verb", "is_read")
    list_filter = ("is_read",)
    search_fields = ("recipient__username", "actor__username", "verb")
