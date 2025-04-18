# core/admin.py
from django.contrib import admin
from .models import Notification # Add other core models if any
from django.contrib.admin import AdminSite
from django.contrib.auth.models import Group
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'verb', 'message_preview', 'is_read', 'created_at')
    list_filter = ('is_read', 'verb', 'created_at', 'recipient__email')
    search_fields = ('recipient__email', 'message', 'actor__email')
    list_editable = ('is_read',)
    readonly_fields = ('created_at',)
    raw_id_fields = ('recipient', 'actor') # Useful if many users

    def recipient_email(self, obj):
        return obj.recipient.email
    recipient_email.short_description = "Recipient"
    recipient_email.admin_order_field = 'recipient__email'

    def message_preview(self, obj):
        return (obj.message[:75] + '...') if len(obj.message) > 75 else obj.message
    message_preview.short_description = "Message"
class InstructorAdminSite(AdminSite):
    site_header = "Instructor Administration"
    site_title = "Instructor Admin"
    index_title = "Welcome to Instructor Admin"

    def has_permission(self, request):
        # Restrict access to users in the 'instructor' group
        return request.user.is_authenticated and request.user.groups.filter(name='instructors').exists()
    

instructor_admin_site = InstructorAdminSite(name='instructoradmin')