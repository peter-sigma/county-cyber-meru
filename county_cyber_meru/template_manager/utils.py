import os
import tempfile
from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont
import subprocess

def generate_template_preview(template):
    """
    Generate a preview image from the template file
    Returns the path to the preview image relative to MEDIA_ROOT
    """
    try:
        # Create previews directory if it doesn't exist
        previews_dir = os.path.join(settings.MEDIA_ROOT, 'previews')
        os.makedirs(previews_dir, exist_ok=True)
        
        preview_filename = f"preview_{template.id}.jpg"
        preview_full_path = os.path.join(previews_dir, preview_filename)
        
        # Check if preview already exists
        if os.path.exists(preview_full_path):
            return f"previews/{preview_filename}"
        
        file_extension = os.path.splitext(template.file.name)[1].lower()
        file_path = template.file.path
        
        if file_extension == '.pdf':
            return generate_pdf_preview(file_path, preview_full_path, template)
        elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            return generate_image_preview(file_path, preview_full_path)
        else:
            return generate_fallback_preview(template, preview_full_path, file_extension)
            
    except Exception as e:
        print(f"Error generating preview for template {template.id}: {e}")
        return generate_fallback_preview(template, preview_full_path, file_extension)

def generate_pdf_preview(pdf_path, output_path, template):
    """Generate preview for PDF files"""
    try:
        # Try using pdf2image if available
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=150)
            if images:
                image = images[0]
                # Resize to reasonable dimensions
                image.thumbnail((800, 1000), Image.Resampling.LANCZOS)
                image.save(output_path, 'JPEG', quality=85)
                return f"previews/preview_{template.id}.jpg"
        except ImportError:
            pass
        
        # Fallback: Create a simple PDF preview representation
        return create_pdf_placeholder(output_path, template)
        
    except Exception as e:
        print(f"PDF preview error: {e}")
        return create_pdf_placeholder(output_path, template)

def generate_image_preview(image_path, output_path):
    """Generate preview for image files"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Resize to reasonable dimensions
            img.thumbnail((800, 1000), Image.Resampling.LANCZOS)
            img.save(output_path, 'JPEG', quality=85)
            return f"previews/{os.path.basename(output_path)}"
    except Exception as e:
        print(f"Image preview error: {e}")
        return None

def generate_fallback_preview(template, output_path, file_extension):
    """Generate a fallback preview for unsupported file types"""
    try:
        # Create a simple placeholder image
        img = Image.new('RGB', (600, 800), color='#f8f9fa')
        draw = ImageDraw.Draw(img)
        
        # Try to use a font (this might fail on some systems)
        try:
            font_large = ImageFont.truetype("arial.ttf", 40)
            font_small = ImageFont.truetype("arial.ttf", 20)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Add text to the image
        text = f"{template.title}\n\n.{file_extension.upper()} File\n\nPreview not available\n\nClick download to get full file"
        
        # Simple text drawing (basic positioning)
        draw.text((50, 200), template.title, fill='#2563eb', font=font_large)
        draw.text((50, 300), f".{file_extension.upper()} File", fill='#64748b', font=font_small)
        draw.text((50, 350), "Preview not available", fill='#94a3b8', font=font_small)
        
        img.save(output_path, 'JPEG', quality=85)
        return f"previews/preview_{template.id}.jpg"
        
    except Exception as e:
        print(f"Fallback preview error: {e}")
        return None

def create_pdf_placeholder(output_path, template):
    """Create a PDF placeholder image"""
    try:
        img = Image.new('RGB', (600, 800), color='#ffffff')
        draw = ImageDraw.Draw(img)
        
        try:
            font_large = ImageFont.truetype("arial.ttf", 36)
            font_medium = ImageFont.truetype("arial.ttf", 24)
            font_small = ImageFont.truetype("arial.ttf", 18)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Draw PDF icon
        draw.rectangle([100, 100, 500, 200], outline='#2563eb', width=3)
        draw.rectangle([120, 120, 480, 180], fill='#dbeafe')
        draw.text((150, 130), "PDF", fill='#2563eb', font=font_large)
        
        # Draw document info
        draw.text((150, 250), template.title, fill='#1e293b', font=font_medium)
        draw.text((150, 300), "Page 1 Preview", fill='#64748b', font=font_small)
        draw.text((150, 330), "Download for full document", fill='#94a3b8', font=font_small)
        
        img.save(output_path, 'JPEG', quality=85)
        return f"previews/preview_{template.id}.jpg"
        
    except Exception as e:
        print(f"PDF placeholder error: {e}")
        return None

def delete_template_preview(template):
    """Delete preview file when template is deleted"""
    try:
        preview_path = os.path.join(settings.MEDIA_ROOT, 'previews', f"preview_{template.id}.jpg")
        if os.path.exists(preview_path):
            os.remove(preview_path)
    except Exception as e:
        print(f"Error deleting preview for template {template.id}: {e}")