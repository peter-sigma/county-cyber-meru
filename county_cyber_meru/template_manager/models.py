from django.db import models

# Create your models here.
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
import os

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category-detail', kwargs={'pk': self.pk})


def template_upload_path(instance, filename):
    """Generate upload path for template files"""
    ext = filename.split('.')[-1]
    filename = f"{instance.title.replace(' ', '_')}_{instance.id}.{ext}"
    return os.path.join('templates', instance.category.name, filename)


class TemplateDocument(models.Model):
    DOCUMENT_TYPES = [
        ('PUB', 'Microsoft Publisher (.pub)'),
        ('PDF', 'PDF Document'),
        ('XLS', 'Excel Spreadsheet'),
        ('DOC', 'Word Document'),
        ('PPT', 'PowerPoint Presentation'),
        ('JPG', 'JPEG Image'),
        ('PNG', 'PNG Image'),
        ('PSD', 'Photoshop File'),
        ('AI', 'Adobe Illustrator'),
        ('OTHER', 'Other Format'),
    ]
    
    PAPER_SIZES = [
        ('A4', 'A4 (210×297 mm)'),
        ('A3', 'A3 (297×420 mm)'),
        ('A5', 'A5 (148×210 mm)'),
        ('LETTER', 'Letter (8.5×11 in)'),
        ('LEGAL', 'Legal (8.5×14 in)'),
        ('BUSINESS', 'Business Card'),
        ('BANNER', 'Banner'),
        ('CUSTOM', 'Custom Size'),
    ]
    
    TEMPLATE_CATEGORIES = [
        ('WEDDING', 'Wedding Cards'),
        ('BUSINESS', 'Business Cards'),
        ('BANNERS', 'Banners & Posters'),
        ('STICKERS', 'Stickers & Labels'),
        ('INVITATIONS', 'Invitation Cards'),
        ('CERTIFICATES', 'Certificates'),
        ('FLYERS', 'Flyers & Brochures'),
        ('LETTERHEADS', 'Letterheads'),
        ('RECEIPTS', 'Receipts & Invoices'),
        ('OTHER', 'Other Templates'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='templates')
    
    document_type = models.CharField(max_length=10, choices=DOCUMENT_TYPES)
    paper_size = models.CharField(max_length=20, choices=PAPER_SIZES)
    template_category = models.CharField(max_length=20, choices=TEMPLATE_CATEGORIES)
    
    file = models.FileField(upload_to=template_upload_path)
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_templates')
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='verified_templates')

    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    download_count = models.PositiveIntegerField(default=0)
    
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['document_type']),
            models.Index(fields=['paper_size']),
            models.Index(fields=['template_category']),
            models.Index(fields=['is_verified']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()})"

    def get_absolute_url(self):
        return reverse('template-detail', kwargs={'pk': self.pk})

    def get_file_extension(self):
        return os.path.splitext(self.file.name)[1].lower()

    def increment_download_count(self):
        self.download_count += 1
        self.save()

    def save(self, *args, **kwargs):
        # Auto-set verified fields if verified
        if self.is_verified and not self.verified_at:
            self.verified_at = timezone.now()
        super().save(*args, **kwargs)


class TemplateDownload(models.Model):
    template = models.ForeignKey(TemplateDocument, on_delete=models.CASCADE, related_name='downloads')
    downloaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ['-downloaded_at']

    def __str__(self):
        return f"{self.template.title} - {self.downloaded_by.username}"


class TemplateRating(models.Model):
    template = models.ForeignKey(TemplateDocument, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['template', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.template.title} - {self.rating} stars"