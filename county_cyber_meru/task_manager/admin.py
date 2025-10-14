from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import ServiceCategory, TaskCategory, Task, TaskUpdate, TaskAttachment

# Custom Admin Filters
class StatusFilter(admin.SimpleListFilter):
    title = 'status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return Task.STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())

class PriorityFilter(admin.SimpleListFilter):
    title = 'priority'
    parameter_name = 'priority'

    def lookups(self, request, model_admin):
        return Task.PRIORITY_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(priority=self.value())

class OverdueFilter(admin.SimpleListFilter):
    title = 'overdue'
    parameter_name = 'overdue'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Overdue'),
            ('no', 'Not Overdue'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(
                due_date__lt=timezone.now(),
                status__in=['pending', 'in_progress']
            )
        if self.value() == 'no':
            return queryset.exclude(
                due_date__lt=timezone.now(),
                status__in=['pending', 'in_progress']
            )

class ServiceCategoryFilter(admin.SimpleListFilter):
    title = 'service category'
    parameter_name = 'service_category'

    def lookups(self, request, model_admin):
        service_categories = ServiceCategory.objects.filter(is_active=True)
        return [(sc.id, sc.name) for sc in service_categories]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(category__service_category_id=self.value())

# Inline Admin Classes
class TaskCategoryInline(admin.TabularInline):
    model = TaskCategory
    extra = 0
    fields = ['name', 'is_active', 'price', 'estimated_duration']
    show_change_link = True

class TaskUpdateInline(admin.TabularInline):
    model = TaskUpdate
    extra = 0
    readonly_fields = ['user', 'created_at']
    fields = ['user', 'message', 'created_at']
    
    def has_add_permission(self, request, obj=None):
        return True

class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 0
    readonly_fields = ['uploaded_by', 'uploaded_at']
    fields = ['file', 'description', 'uploaded_by', 'uploaded_at']

# Main Admin Classes
@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'icon_display', 'is_active', 'subcategory_count', 
        'task_count', 'order', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'order']
    inlines = [TaskCategoryInline]
    prepopulated_fields = {'color': ['name']}
    
    actions = ['activate_categories', 'deactivate_categories']

    def icon_display(self, obj):
        if obj.icon:
            return format_html('<i class="{}"></i> {}', obj.icon, obj.icon)
        return "No icon"
    icon_display.short_description = 'Icon'

    def subcategory_count(self, obj):
        return obj.subcategories.count()
    subcategory_count.short_description = 'Sub-Services'

    def task_count(self, obj):
        # Count tasks through subcategories
        return Task.objects.filter(category__service_category=obj).count()
    task_count.short_description = 'Total Tasks'

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Image Preview'

    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} service categories activated.')
    activate_categories.short_description = "Activate selected service categories"

    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} service categories deactivated.')
    deactivate_categories.short_description = "Deactivate selected service categories"

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active', 'order')
        }),
        ('Visual Design', {
            'fields': ('icon', 'color', 'image', 'cover_image', 'image_preview'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['image_preview']

@admin.register(TaskCategory)
class TaskCategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'service_category', 'icon_display', 'is_active', 
        'price_display', 'estimated_duration', 'task_count', 'created_at'
    ]
    list_filter = ['is_active', 'service_category', 'created_at']
    search_fields = ['name', 'description', 'service_category__name']
    list_editable = ['is_active', 'estimated_duration']
    list_select_related = ['service_category']
    
    actions = ['activate_categories', 'deactivate_categories']

    def icon_display(self, obj):
        icon = obj.display_icon
        return format_html('<i class="{}"></i> {}', icon, icon)
    icon_display.short_description = 'Icon'

    def price_display(self, obj):
        if obj.price:
            return f"KSh {obj.price:,.2f}"
        return "-"
    price_display.short_description = 'Price'

    def task_count(self, obj):
        return obj.tasks.count()
    task_count.short_description = 'Tasks'

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.image.url)
        elif obj.service_category.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px; opacity: 0.7;" title="Inherited from {}" />', 
                obj.service_category.image.url, obj.service_category.name
            )
        return "No image"
    image_preview.short_description = 'Image Preview'

    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} service categories activated.')
    activate_categories.short_description = "Activate selected categories"

    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} service categories deactivated.')
    deactivate_categories.short_description = "Deactivate selected categories"

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'service_category', 'is_active')
        }),
        ('Service Details', {
            'fields': ('price', 'estimated_duration', 'template_link')
        }),
        ('Visual Design', {
            'fields': ('icon', 'image', 'image_preview'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['image_preview']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'customer_name', 'service_category', 'category', 
        'status', 'priority', 'assigned_to',
        'price_display', 'due_date_display', 'is_overdue_display',
        'created_at', 'days_open'
    ]
    list_filter = [
        StatusFilter, PriorityFilter, OverdueFilter, ServiceCategoryFilter,
        'category', 'assigned_to', 'created_at', 'due_date'
    ]
    search_fields = [
        'title', 'description', 'customer_name', 
        'customer_email', 'customer_phone', 'category__name'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'completed_at', 
        'is_overdue', 'duration_display', 'task_updates_link',
        'status_display', 'priority_display', 'service_category_display'
    ]
    list_editable = ['status', 'priority', 'assigned_to']
    list_select_related = ['category', 'category__service_category', 'assigned_to']
    inlines = [TaskUpdateInline, TaskAttachmentInline]
    actions = [
        'mark_as_completed', 'mark_as_in_progress', 
        'assign_to_me', 'calculate_prices'
    ]

    def service_category(self, obj):
        return obj.category.service_category.name
    service_category.short_description = 'Service Category'
    service_category.admin_order_field = 'category__service_category__name'

    def service_category_display(self, obj):
        """Display service category with color (for change form)"""
        service_cat = obj.category.service_category
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">{}</span>',
            service_cat.color, service_cat.name
        )
    service_category_display.short_description = 'Service Category'

    # Custom display methods for better visualization
    def status_display(self, obj):
        """Display status with color coding (for change form)"""
        colors = {
            'pending': 'gray',
            'in_progress': 'blue',
            'completed': 'green',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status Display'

    def priority_display(self, obj):
        """Display priority with color coding (for change form)"""
        colors = {
            'low': 'gray',
            'medium': 'orange',
            'high': 'red',
            'urgent': 'darkred'
        }
        color = colors.get(obj.priority, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_display.short_description = 'Priority Display'

    def price_display(self, obj):
        if obj.price:
            return f"KSh {obj.price:,.2f}"
        return "-"
    price_display.short_description = 'Price'

    def due_date_display(self, obj):
        if obj.due_date:
            return obj.due_date.strftime("%b %d, %Y")
        return "-"
    due_date_display.short_description = 'Due Date'

    def is_overdue_display(self, obj):
        if obj.is_overdue:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠ OVERDUE</span>'
            )
        return "-"
    is_overdue_display.short_description = 'Overdue'

    def days_open(self, obj):
        if obj.completed_at:
            days = (obj.completed_at - obj.created_at).days
            return f"{days}d"
        else:
            days = (timezone.now() - obj.created_at).days
            return f"{days}d (open)"
    days_open.short_description = 'Days'

    def duration_display(self, obj):
        if obj.duration:
            total_seconds = int(obj.duration.total_seconds())
            days, remainder = divmod(total_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{days}d {hours}h {minutes}m"
        return "Not completed"
    duration_display.short_description = 'Duration'

    def task_updates_link(self, obj):
        count = obj.updates.count()
        url = reverse('admin:task_manager_taskupdate_changelist') + f'?task__id__exact={obj.id}'
        return format_html('<a href="{}">{} Updates</a>', url, count)
    task_updates_link.short_description = 'Updates'

    # Admin Actions
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f'{updated} tasks marked as completed.')
    mark_as_completed.short_description = "Mark selected tasks as completed"

    def mark_as_in_progress(self, request, queryset):
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated} tasks marked as in progress.')
    mark_as_in_progress.short_description = "Mark selected tasks as in progress"

    def assign_to_me(self, request, queryset):
        updated = queryset.update(assigned_to=request.user, status='in_progress')
        self.message_user(request, f'{updated} tasks assigned to you.')
    assign_to_me.short_description = "Assign selected tasks to me"

    def calculate_prices(self, request, queryset):
        # Use category price if available, otherwise calculate
        for task in queryset.filter(price__isnull=True):
            if task.category.price:
                task.price = task.category.price
            else:
                # Fallback pricing logic
                base_price = 500  # Base price in KSh
                if task.priority == 'high':
                    base_price *= 1.5
                elif task.priority == 'urgent':
                    base_price *= 2
                task.price = base_price
            task.save()
        self.message_user(request, f'Prices calculated for {queryset.count()} tasks.')
    calculate_prices.short_description = "Calculate prices for selected tasks"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category', 'category__service_category', 'assigned_to'
        )

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'service_category_display')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email', 'customer_phone'),
            'classes': ('collapse',)
        }),
        ('Task Management', {
            'fields': ('status', 'status_display', 'priority', 'priority_display', 'assigned_to', 'price')
        }),
        ('Timeline', {
            'fields': ('due_date', 'created_at', 'updated_at', 'completed_at', 'duration_display'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('staff_notes', 'cancellation_reason', 'attachment', 'task_updates_link'),
            'classes': ('collapse',)
        }),
    )

# ... (TaskUpdateAdmin and TaskAttachmentAdmin remain the same)
@admin.register(TaskUpdate)
class TaskUpdateAdmin(admin.ModelAdmin):
    list_display = ['task_link', 'user', 'message_preview', 'created_at']
    list_filter = ['created_at', 'user']
    search_fields = ['task__title', 'message', 'user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    def task_link(self, obj):
        url = reverse('admin:task_manager_task_change', args=[obj.task.id])
        return format_html('<a href="{}">{}</a>', url, obj.task.title)
    task_link.short_description = 'Task'

    def message_preview(self, obj):
        return obj.message[:100] + "..." if len(obj.message) > 100 else obj.message
    message_preview.short_description = 'Message'

@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ['task_link', 'file_name', 'uploaded_by', 'uploaded_at']
    list_filter = ['uploaded_at', 'uploaded_by']
    search_fields = ['task__title', 'description']
    readonly_fields = ['uploaded_at', 'uploaded_by']

    def task_link(self, obj):
        url = reverse('admin:task_manager_task_change', args=[obj.task.id])
        return format_html('<a href="{}">{}</a>', url, obj.task.title)
    task_link.short_description = 'Task'

    def file_name(self, obj):
        return obj.file.name.split('/')[-1]
    file_name.short_description = 'File Name'

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)