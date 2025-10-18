from django.contrib import admin

from .models import SliderImage

@admin.register(SliderImage)
class SliderImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_active', 'uploaded_at')
    list_editable = ('is_active',)
    search_fields = ('title', 'description')
    list_filter = ('is_active', 'uploaded_at')