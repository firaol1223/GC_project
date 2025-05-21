from django.contrib import admin
from .models import ForumCategory, ForumThread, ForumPost

@admin.register(ForumCategory)
class ForumCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description_short')
    prepopulated_fields = {'slug': ('name',)}

    def description_short(self, obj):
        return obj.description[:75] + '...' if obj.description and len(obj.description) > 75 else obj.description
    description_short.short_description = 'Description'


class ForumPostInline(admin.TabularInline): # Or StackedInline
    model = ForumPost
    extra = 0 # Don't show empty forms by default, only existing posts
    readonly_fields = ('author', 'created_at', 'updated_at') # Make some fields read-only in inline
    can_delete = True # Allow deleting posts from thread admin

@admin.register(ForumThread)
class ForumThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'created_at', 'updated_at')
    list_filter = ('category', 'author', 'created_at')
    search_fields = ('title', 'author__username')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ForumPostInline] # View posts within thread admin
    # raw_id_fields = ('author', 'category') # Good for performance if many users/categories

@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display = ('author', 'thread_link', 'created_at_short', 'content_short')
    list_filter = ('thread__category', 'author', 'created_at')
    search_fields = ('content', 'author__username', 'thread__title')
    # raw_id_fields = ('author', 'thread')

    def content_short(self, obj):
        return obj.content[:75] + '...' if len(obj.content) > 75 else obj.content
    content_short.short_description = 'Content Preview'

    def created_at_short(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M")
    created_at_short.short_description = 'Created At'
    created_at_short.admin_order_field = 'created_at'

    def thread_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:forum_forumthread_change", args=[obj.thread.id])
        return format_html('<a href="{}">{}</a>', link, obj.thread.title[:50] + "...")
    thread_link.short_description = 'Thread'