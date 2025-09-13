from django.contrib import admin
from django.utils.text import slugify
from .models import Category, TemplateDocument, TemplateDownload, TemplateRating
from django.utils.html import format_html

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    prepopulated_fields = {'slug': ('name',)}  # Now this will work

    def save_model(self, request, obj, form, change):
        if not obj.slug:
            obj.slug = slugify(obj.name)
        super().save_model(request, obj, form, change)


@admin.register(TemplateDocument)
class TemplateDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 
        'category', 
        'document_type', 
        'paper_size',
        'uploaded_by',
        'uploaded_at',
        'is_verified',
        'is_active',
        'download_count'
    ]
    
    list_filter = [
        'is_verified',
        'is_active',
        'document_type',
        'paper_size',
        'template_category',
        'uploaded_at'
    ]
    
    search_fields = ['title', 'description', 'tags']
    readonly_fields = ['uploaded_at', 'verified_at', 'updated_at', 'download_count']
    date_hierarchy = 'uploaded_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'tags')
        }),
        ('Technical Details', {
            'fields': ('document_type', 'paper_size', 'template_category', 'file', 'thumbnail')
        }),
        ('Pricing', {
            'fields': ('price',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_verified', 'is_active', 'is_featured')
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'verified_by', 'uploaded_at', 'verified_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TemplateDownload)
class TemplateDownloadAdmin(admin.ModelAdmin):
    list_display = ['template', 'downloaded_by', 'downloaded_at']
    list_filter = ['downloaded_at']
    readonly_fields = ['downloaded_at']


@admin.register(TemplateRating)
class TemplateRatingAdmin(admin.ModelAdmin):
    list_display = ['template', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    readonly_fields = ['created_at', 'updated_at']