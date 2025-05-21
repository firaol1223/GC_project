# ai_elearning_platform/users/admin.py
from django.contrib import admin
from .models import Profile
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser  # Import your custom user model
from .models import Profile, PointLog, Badge, UserBadge # Add new models
from .forms import CustomUserCreationForm, CustomUserChangeForm
admin.site.register(Profile) # Already registered, but ensure it's here

@admin.register(PointLog)
class PointLogAdmin(admin.ModelAdmin):
    list_display = ('user_profile_link', 'points_awarded', 'reason', 'timestamp')
    list_filter = ('timestamp', 'user_profile__user__email')  
    def user_profile_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:users_profile_change", args=[obj.user_profile.id])
        return format_html('<a href="{}">{}</a>', link, obj.user_profile.user.email)  # changed to email
    user_profile_link.short_description = 'User'

    


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user_profile_link', 'badge', 'awarded_at')
    list_filter = ('badge', 'awarded_at', 'user_profile__user__email')  
    search_fields = ('user_profile__user__email', 'badge__name')        

    def user_profile_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:users_profile_change", args=[obj.user_profile.id])
        return format_html('<a href="{}">{}</a>', link, obj.user_profile.user.email)  # changed
    user_profile_link.short_description = 'User'



class CustomUserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ['email', 'first_name', 'last_name', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_active', 'groups']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['email']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = ( # For the "add user" page in admin
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'password2'), # password2 is from UserCreationForm
        }),
    )
admin.site.register(CustomUser, CustomUserAdmin)  # Register your custom user model
admin.site.register(Badge)  # Register the Badge model