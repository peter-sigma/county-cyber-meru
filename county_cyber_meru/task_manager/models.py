from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.core.files.storage import FileSystemStorage
import os

def service_category_image_path(instance, filename):
    """File path for service category images"""
    return f'service_categories/{instance.name}/{filename}'

def task_category_image_path(instance, filename):
    """File path for task category images"""
    return f'task_categories/{instance.service_category.name}/{instance.name}/{filename}'

class ServiceCategory(models.Model):
    """Main service categories (KRA, Printing, Design, etc.)"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Visual enhancements
    icon = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="Font Awesome icon class (e.g., fas fa-print, fas fa-chart-line)"
    )
    image = models.ImageField(
        upload_to=service_category_image_path,
        blank=True,
        null=True,
        help_text="Main image for this service category (recommended: 400x300px)"
    )
    cover_image = models.ImageField(
        upload_to=service_category_image_path,
        blank=True,
        null=True,
        help_text="Cover/banner image (recommended: 1200x400px)"
    )
    color = models.CharField(
        max_length=7,
        default='#4e73df',
        help_text="Hex color code for this category (e.g., #4e73df)"
    )
    
    order = models.IntegerField(default=0, help_text="Display order")
    
    class Meta:
        verbose_name_plural = "Service Categories"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    @property
    def active_subcategories(self):
        """Get active subcategories for this service category"""
        return self.subcategories.filter(is_active=True)
    
    @property
    def subcategory_count(self):
        """Count of active subcategories"""
        return self.subcategories.filter(is_active=True).count()
    
    @property
    def active_subcategories(self):
        """Get active subcategories for this service category"""
        return self.subcategories.filter(is_active=True)
    
    @property
    def image_url(self):
        """Return image URL or default"""
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return '/static/images/default-service.png'
    
    @property
    def cover_image_url(self):
        """Return cover image URL or default"""
        if self.cover_image and hasattr(self.cover_image, 'url'):
            return self.cover_image.url
        return '/static/images/default-cover.png'

class TaskCategory(models.Model):
    """Sub-categories/services under main categories (File Returns, Zero Returns, ToT under KRA)"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    service_category = models.ForeignKey(
        ServiceCategory, 
        on_delete=models.CASCADE, 
        related_name='subcategories',
        default=1  # Default to General service category
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Visual enhancements
    icon = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Font Awesome icon class for this specific service"
    )
    image = models.ImageField(
        upload_to=task_category_image_path,
        blank=True,
        null=True,
        help_text="Service-specific image (recommended: 300x200px)"
    )
    
    template_link = models.URLField(
        blank=True, 
        help_text="Optional: Link to template (Canvas, Google Docs, etc.)"
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Standard price for this service"
    )
    estimated_duration = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g., 30 minutes, 2 hours, 1 day"
    )

    service_category = models.ForeignKey(
        ServiceCategory, 
        on_delete=models.CASCADE, 
        related_name='subcategories',
        null=True,  # Allow null initially
        #blank=True  # Allow blank in forms
        default=1
    )
    
    class Meta:
        verbose_name_plural = "Task Categories"
        ordering = ['service_category', 'name']
        verbose_name = "Service"
    
    def __str__(self):
        return f"{self.service_category.name} - {self.name}"
    
    @property
    def image_url(self):
        """Return image URL or inherit from service category"""
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        elif self.service_category.image:
            return self.service_category.image_url
        return '/static/images/default-service.png'
    
    @property
    def display_icon(self):
        """Return icon or inherit from service category"""
        return self.icon or self.service_category.icon or 'fas fa-cog'
    
    @property
    def display_color(self):
        """Return color from service category"""
        return self.service_category.color

class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Basic task information
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        TaskCategory, 
        on_delete=models.CASCADE, 
        related_name='tasks'
    )
    
    # Customer information (can be anonymous/unauthenticated)
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20, blank=True)
    
    # Task management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Staff assignment and pricing - using your custom StaffProfile
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        limit_choices_to={'is_staff': True},
        related_name='assigned_tasks'
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Cancellation and notes
    cancellation_reason = models.TextField(blank=True)
    staff_notes = models.TextField(blank=True, help_text="Internal notes for staff")
    
    # File attachments
    attachment = models.FileField(upload_to='task_attachments/', blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.customer_name}"
    
    def get_absolute_url(self):
        return reverse('task_manager:task-detail', kwargs={'pk': self.pk})
    
    def save(self, *args, **kwargs):
        # Auto-set completed_at when status changes to completed
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != 'completed' and self.completed_at:
            self.completed_at = None
        
        # Auto-set price from category if not set
        if not self.price and self.category.price:
            self.price = self.category.price
        
        super().save(*args, **kwargs)
    
    @property
    def service_category(self):
        """Get the main service category"""
        return self.category.service_category
    
    @property
    def service_image(self):
        """Get the service image"""
        return self.category.image_url
    
    @property
    def service_icon(self):
        """Get the service icon"""
        return self.category.display_icon
    
    @property
    def service_color(self):
        """Get the service color"""
        return self.category.display_color
    
    @property
    def is_overdue(self):
        if self.due_date and self.status not in ['completed', 'cancelled']:
            return timezone.now() > self.due_date
        return False
    
    @property
    def duration(self):
        if self.completed_at and self.created_at:
            return self.completed_at - self.created_at
        return None
    
    @property
    def assigned_staff_name(self):
        """Get the assigned staff member's display name"""
        if self.assigned_to:
            return self.assigned_to.get_full_name() or self.assigned_to.username
        return "Unassigned"

# ... (TaskUpdate and TaskAttachment models remain the same)
class TaskUpdate(models.Model):
    """Track updates and comments on tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='updates')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Update for {self.task.title} by {self.user.username}"

class TaskAttachment(models.Model):
    """Additional file attachments for tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return f"Attachment for {self.task.title}"