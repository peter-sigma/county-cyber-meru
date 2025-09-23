import os
from django.conf import settings
from pdf2image import convert_from_path
from PIL import Image
import tempfile

def generate_template_preview(template):
    """
    Generate a preview image from the first page of the template
    """
    preview_path = os.path.join(settings.MEDIA_ROOT, 'previews')
    os.makedirs(preview_path, exist_ok=True)
    
    preview_filename = f"preview_{template.id}.jpg"
    preview_full_path = os.path.join(preview_path, preview_filename)
    
    # If preview already exists, return it
    if os.path.exists(preview_full_path):
        return os.path.join('previews', preview_filename)
    
    try:
        file_extension = template.get_file_extension().lower()
        
        if file_extension == '.pdf':
            # Convert PDF first page to image
            images = convert_from_path(template.file.path, first_page=1, last_page=1)
            if images:
                # Resize and save
                image = images[0]
                image.thumbnail((800, 1000), Image.Resampling.LANCZOS)
                image.save(preview_full_path, 'JPEG', quality=85)
                return os.path.join('previews', preview_filename)
        
        elif file_extension in ['.jpg', '.jpeg', '.png', '.gif']:
            # For image files, create a resized preview
            with Image.open(template.file.path) as img:
                img.thumbnail((800, 1000), Image.Resampling.LANCZOS)
                img.save(preview_full_path, 'JPEG', quality=85)
                return os.path.join('previews', preview_filename)
                
    except Exception as e:
        print(f"Error generating preview for template {template.id}: {e}")
    
    return None

def delete_template_preview(template):
    """Delete preview when template is deleted"""
    preview_path = os.path.join(settings.MEDIA_ROOT, 'previews', f"preview_{template.id}.jpg")
    if os.path.exists(preview_path):
        os.remove(preview_path)