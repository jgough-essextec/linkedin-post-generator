from django.contrib import admin
from .models import GeneratedPost


@admin.register(GeneratedPost)
class GeneratedPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'source_url_truncated', 'created_at', 'has_images')
    list_filter = ('created_at',)
    search_fields = ('source_url', 'linkedin_post', 'summary')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('source_url', 'created_at')
        }),
        ('Content', {
            'fields': ('original_content', 'user_prompt_adjustment')
        }),
        ('Generated Content', {
            'fields': ('linkedin_post', 'summary', 'business_rationale', 'markdown_content')
        }),
        ('Images', {
            'fields': ('image_url_1', 'image_url_2')
        }),
    )

    def source_url_truncated(self, obj):
        return obj.source_url[:50] + '...' if len(obj.source_url) > 50 else obj.source_url
    source_url_truncated.short_description = 'Source URL'

    def has_images(self, obj):
        return bool(obj.image_url_1 or obj.image_url_2)
    has_images.boolean = True
    has_images.short_description = 'Has Images'
