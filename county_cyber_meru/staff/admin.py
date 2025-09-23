from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import StaffProfile

@admin.register(StaffProfile)
class StaffProfileAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'department')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'department')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Information', {
            'fields': ('phone_number', 'department', 'position')
        }),
    )