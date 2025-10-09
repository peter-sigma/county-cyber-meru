from django.db import models

# Create your models here.
from django.conf import settings
from django.utils import timezone
from django.urls import reverse

class TaskCategory(models.Model):
    """Categories for tasks (Printing, Design, Consultation, etc.)"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    template_link = models.URLField(
        blank=True, 
        help_text="Optional: Link to template (Canvas, Google Docs, etc.)"
    )
    
    class Meta:
        verbose_name_plural = "Task Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

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
    category = models.ForeignKey(TaskCategory, on_delete=models.CASCADE, related_name='tasks')
    
    # Customer information (can be anonymous/unauthenticated)
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20, blank=True)
    
    # Task management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Staff assignment and pricing - using your custom StaffProfile
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # This now points to StaffProfile
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
        
        super().save(*args, **kwargs)
    
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

class TaskUpdate(models.Model):
    """Track updates and comments on tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='updates')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # StaffProfile
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
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # StaffProfile
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return f"Attachment for {self.task.title}"