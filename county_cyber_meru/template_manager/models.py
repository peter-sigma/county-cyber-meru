from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from .utils import generate_template_preview, delete_template_preview
import os
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    template_link = models.URLField(
        blank=True, 
        help_text="Optional: Link to template (Canvas, Google Docs, etc.)"
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('category-detail', kwargs={'slug': self.slug})

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
    preview_image = models.ImageField(upload_to='previews/', blank=True, null=True)
    
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
        return reverse('template_manager:template-detail', kwargs={'pk': self.pk})

    def get_file_extension(self):
        """Get file extension without the dot"""
        if self.file:
            return os.path.splitext(self.file.name)[1].lower().replace('.', '')
        return ''

    def get_file_type_display(self):
        """Get user-friendly file type"""
        ext = self.get_file_extension()
        file_types = {
            'pdf': 'PDF Document',
            'doc': 'Word Document',
            'docx': 'Word Document',
            'xls': 'Excel Spreadsheet',
            'xlsx': 'Excel Spreadsheet',
            'ppt': 'PowerPoint',
            'pptx': 'PowerPoint',
            'pub': 'Publisher Document',
            'txt': 'Text File',
            'html': 'Web Page',
            'htm': 'Web Page',
        }
        return file_types.get(ext, f'{ext.upper()} File')

    def increment_download_count(self):
        self.download_count += 1
        self.save()

    @property
    def can_view_in_browser(self):
        """Check if file can be viewed in browser"""
        browser_compatible = [
            'pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg',  # Images
            'txt', 'html', 'htm', 'csv',                       # Text
            'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',       # Office (via Google Docs)
            'odt', 'ods', 'odp', 'rtf',                       # OpenDocument
            # Note: 'pub' is NOT included here since it can't be viewed in browser
        ]
        return self.get_file_extension() in browser_compatible

    @property
    def uses_google_docs_viewer(self):
        """Check if this file uses Google Docs Viewer"""
        google_docs_extensions = ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp', 'rtf']
        return self.get_file_extension() in google_docs_extensions

    def get_browser_view_info(self):
        """Get information about browser viewing capabilities"""
        ext = self.get_file_extension()
        
        view_info = {
            'pdf': 'Opens directly in browser',
            'jpg': 'Displays as image',
            'jpeg': 'Displays as image', 
            'png': 'Displays as image',
            'gif': 'Displays as image',
            'doc': 'Opens in Google Docs Viewer',
            'docx': 'Opens in Google Docs Viewer',
            'xls': 'Opens in Google Docs Viewer', 
            'xlsx': 'Opens in Google Docs Viewer',
            'ppt': 'Opens in Google Docs Viewer',
            'pptx': 'Opens in Google Docs Viewer',
            'pub': 'Download required - Opens in Microsoft Publisher',
            'txt': 'Opens as text in browser',
            'html': 'Opens as web page',
            'odt': 'Opens in Google Docs Viewer',
            'ods': 'Opens in Google Docs Viewer',
            'odp': 'Opens in Google Docs Viewer',
            'rtf': 'Opens in Google Docs Viewer',
        }
        
        return view_info.get(ext, 'Download required for viewing')

    def save(self, *args, **kwargs):
        # Auto-set verified fields if verified
        if self.is_verified and not self.verified_at:
            self.verified_at = timezone.now()
        
        # Call super save first to get an ID
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Generate preview after saving for new templates or if file changed
        if is_new or (self.file and not self.preview_image):
            preview_path = generate_template_preview(self)
            if preview_path:
                self.preview_image = preview_path
                # Save again to update preview_image field without triggering signal again
                super().save(update_fields=['preview_image'])

    @property
    def tags_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []

    def get_average_rating(self):
        """Calculate average rating from reviews"""
        from django.db.models import Avg
        return self.ratings.aggregate(Avg('rating'))['rating__avg']

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

# SIGNALS - Defined outside the classes
@receiver(post_delete, sender=TemplateDocument)
def auto_delete_template_files(sender, instance, **kwargs):
    """Delete file and preview when template is deleted"""
    # Delete main file
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)
    
    # Delete thumbnail
    if instance.thumbnail:
        if os.path.isfile(instance.thumbnail.path):
            os.remove(instance.thumbnail.path)
    
    # Delete preview image
    if instance.preview_image:
        if os.path.isfile(instance.preview_image.path):
            os.remove(instance.preview_image.path)
    
    # Delete from utils
    delete_template_preview(instance)

@receiver(post_save, sender=TemplateDocument)
def generate_template_preview_on_save(sender, instance, created, **kwargs):
    """Generate preview when template is saved (alternative approach)"""
    if created and instance.file and not instance.preview_image:
        preview_path = generate_template_preview(instance)
        if preview_path:
            instance.preview_image = preview_path
            instance.save(update_fields=['preview_image'])



