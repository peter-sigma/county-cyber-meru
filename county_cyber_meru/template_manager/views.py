from django.shortcuts import render

# Create your views here.
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from .models import TemplateDocument, Category
from .forms import TemplateUploadForm, CategoryForm
from django.http import FileResponse, Http404
import os
from django.utils import timezone
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
import platform
import subprocess
import tempfile
import os




def template_list(request):
    """List all verified templates"""
    templates = TemplateDocument.objects.filter(is_verified=True, is_active=True)
    
    # Get filter parameters
    document_type = request.GET.get('document_type')
    paper_size = request.GET.get('paper_size')
    category_slug = request.GET.get('category')
    
    # Apply filters
    if document_type:
        templates = templates.filter(document_type=document_type)
    if paper_size:
        templates = templates.filter(paper_size=paper_size)
    if category_slug:
        templates = templates.filter(category__slug=category_slug)
    
    context = {
        'templates': templates,
        'categories': Category.objects.filter(is_active=True),
        'document_types': TemplateDocument.DOCUMENT_TYPES,
        'paper_sizes': TemplateDocument.PAPER_SIZES,
    }
    return render(request, 'template_manager/template_list.html', context)

def template_detail(request, pk):
    """Template detail view"""
    template = get_object_or_404(TemplateDocument, pk=pk, is_active=True)

    # Get related templates (same category, verified & active, exclude current one)
    related_templates = TemplateDocument.objects.filter(
        category=template.category,
        is_verified=True,
        is_active=True
    ).exclude(pk=template.pk)[:3]


    # Ensure category has a slug
    if not template.category.slug:
        template.category.save()  

    context = {
        'template': template,
        'related_templates': related_templates
    }
    return render(request, 'template_manager/template_detail.html', context)


@login_required
def template_upload(request):
    """Upload new template"""
    if request.method == 'POST':
        form = TemplateUploadForm(request.POST, request.FILES)
        if form.is_valid():
            template = form.save(commit=False)
            template.uploaded_by = request.user
            template.save()
            messages.success(request, 'Template uploaded successfully! It will be available after verification.')
            return redirect('template_manager:template-detail', pk=template.pk)
    else:
        form = TemplateUploadForm()
    
    context = {'form': form}
    return render(request, 'template_manager/template_upload.html', context)

@login_required
def template_edit(request, pk):
    """Edit template - only allowed for uploader or staff"""
    template = get_object_or_404(TemplateDocument, pk=pk)
    
    # Check permission
    if template.uploaded_by != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to edit this template.')
        return redirect('template_manager:template-detail', pk=template.pk)
    
    if request.method == 'POST':
        form = TemplateUploadForm(request.POST, request.FILES, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Template updated successfully!')
            return redirect('template_manager:template-detail', pk=template.pk)
    else:
        form = TemplateUploadForm(instance=template)
    
    context = {'form': form, 'template': template}
    return render(request, 'template_manager/template_edit.html', context)

@login_required
def template_download(request, pk):
    """Handle template file downloads with proper tracking"""
    template = get_object_or_404(TemplateDocument, pk=pk, is_active=True)
    
    # Check if template is verified or user has permission
    if not template.is_verified and not (request.user.is_staff or request.user == template.uploaded_by):
        messages.error(request, 'This template is not yet verified and cannot be downloaded.')
        return redirect('template_manager:template-detail', pk=template.pk)
    
    try:
        # Get the file path
        file_path = template.file.path
        
        # Check if file exists
        if not os.path.exists(file_path):
            messages.error(request, 'The requested file does not exist.')
            return redirect('template_manager:template-detail', pk=template.pk)
        
        # Increment download count on the template
        template.download_count += 1
        template.save()
        
        # Create download record if user is authenticated
        if request.user.is_authenticated:
            from .models import TemplateDownload
            TemplateDownload.objects.create(
                template=template,
                downloaded_by=request.user,
                downloaded_at=timezone.now()
            )
        
        # Prepare file for download
        with open(file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type='application/octet-stream')
            
            # Create a safe filename for download
            import re
            filename = re.sub(r'[^a-zA-Z0-9\.]', '_', template.title) + os.path.splitext(template.file.name)[1]
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = template.file.size
            
            return response
            
    except Exception as e:
        messages.error(request, f'Error downloading file: {str(e)}')
        return redirect('template_manager:template-detail', pk=template.pk)
    


def category_list(request):
    """List all active categories"""
    categories = Category.objects.filter(is_active=True)
    context = {
        'categories': categories,
        'title': 'Template Categories'
    }
    return render(request, 'template_manager/category_list.html', context)


# In views.py - Update category_detail function
def category_detail(request, slug):
    """Show all templates in a specific category"""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    
    # Get verified templates only for regular users
    templates = TemplateDocument.objects.filter(
        category=category, 
        is_active=True,
        is_verified=True  # Only show verified templates to regular users
    ).order_by('-uploaded_at')
    
    # Staff users can see all templates
    if request.user.is_staff:
        templates = TemplateDocument.objects.filter(
            category=category, 
            is_active=True
        ).order_by('-uploaded_at')
    
    # Apply filters if provided
    document_type = request.GET.get('document_type')
    paper_size = request.GET.get('paper_size')
    
    if document_type:
        templates = templates.filter(document_type=document_type)
    if paper_size:
        templates = templates.filter(paper_size=paper_size)
    
    # Get template counts
    total_templates = templates.count()
    verified_count = templates.filter(is_verified=True).count()
    pending_count = templates.filter(is_verified=False).count()
    
    # Get unique document types and paper sizes for filter
    document_types = TemplateDocument.objects.filter(
        category=category, 
        is_active=True
    ).values_list('document_type', flat=True).distinct()
    
    paper_sizes = TemplateDocument.objects.filter(
        category=category, 
        is_active=True
    ).values_list('paper_size', flat=True).distinct()
    
    context = {
        'category': category,
        'templates': templates,
        'verified_count': verified_count,
        'pending_count': pending_count,
        'total_templates': total_templates,
        'document_types': document_types,
        'paper_sizes': paper_sizes,
        'title': f'{category.name} Templates',
        'current_filters': {
            'document_type': document_type,
            'paper_size': paper_size,
        }
    }
    return render(request, 'template_manager/category_detail.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def category_create(request):
    """Create a new category (staff only)"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            print("form is valid")
            messages.success(request, f'Category "{category.name}" created successfully!')
            return redirect('template_manager:category-list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        print("fetching form")
        form = CategoryForm()
    
    context = {
        'form': form,
        'title': 'Create New Category'
    }
    return render(request, 'template_manager/category_form.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def category_edit(request, slug):
    """Edit an existing category (staff only)"""
    category = get_object_or_404(Category, slug=slug)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" updated successfully!')
            return redirect('template_manager:category-list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'title': f'Edit Category: {category.name}'
    }
    return render(request, 'template_manager/category_form.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def category_toggle(request, slug):
    """Toggle category active status (staff only)"""
    category = get_object_or_404(Category, slug=slug)
    
    if category.is_active:
        # Check if category has templates before deactivating
        template_count = category.templates.filter(is_active=True).count()
        if template_count > 0:
            messages.warning(
                request, 
                f'Cannot deactivate "{category.name}" because it has {template_count} active template(s). '
                f'Move or delete the templates first.'
            )
            return redirect('template_manager:category-list')
        
        category.is_active = False
        action = "deactivated"
    else:
        category.is_active = True
        action = "activated"
    
    category.save()
    messages.success(request, f'Category "{category.name}" has been {action}.')
    return redirect('template_manager:category-list')

@login_required
@user_passes_test(lambda u: u.is_staff)
def category_delete(request, slug):
    """Delete a category (staff only)"""
    category = get_object_or_404(Category, slug=slug)
    
    # Check if category has templates
    template_count = category.templates.filter(is_active=True).count()
    if template_count > 0:
        messages.error(
            request, 
            f'Cannot delete "{category.name}" because it has {template_count} active template(s). '
            f'Move or delete the templates first.'
        )
        return redirect('template_manager:category-list')
    
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'Category "{category_name}" has been deleted.')
        return redirect('template_manager:category-list')
    
    context = {
        'category': category,
        'title': f'Delete Category: {category.name}'
    }
    return render(request, 'template_manager/category_confirm_delete.html', context)


def template_search(request):
    """Search templates"""
    query = request.GET.get('q', '')
    
    if query:
        templates = TemplateDocument.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__icontains=query),
            is_verified=True,
            is_active=True
        )
    else:
        templates = TemplateDocument.objects.filter(is_verified=True, is_active=True)
    
    context = {
        'templates': templates,
        'query': query,
        'results_count': templates.count()
    }
    return render(request, 'template_manager/search_results.html', context)

# Staff-only views
def is_staff_user(user):
    return user.is_staff

@user_passes_test(is_staff_user)
@login_required
def template_verify(request, pk):
    """Verify template (staff only)"""
    template = get_object_or_404(TemplateDocument, pk=pk)
    template.is_verified = True
    template.verified_by = request.user
    template.save()
    messages.success(request, f'Template "{template.title}" has been verified.')
    return redirect('admin:template_manager_templatedocument_changelist')


@login_required
def template_view(request, pk):
    """Open template in Google Docs Viewer"""
    template = get_object_or_404(TemplateDocument, pk=pk, is_active=True)
    
    # Check if template is verified or user has permission
    if not template.is_verified and not (request.user.is_staff or request.user == template.uploaded_by):
        messages.error(request, 'This template is not yet verified and cannot be viewed.')
        return redirect('template_manager:template-detail', pk=template.pk)
    
    try:
        # Get file extension
        file_extension = os.path.splitext(template.file.name)[1].lower()
        
        print(f"File extension: {file_extension}")  # Debug
        
        # Files that can be displayed directly in browser
        direct_browser_files = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.txt', '.html', '.htm']
        
        # Files that can be opened with Google Docs Viewer
        google_docs_supported = [
            '.doc', '.docx',  # Word documents
            '.xls', '.xlsx',  # Excel spreadsheets  
            '.ppt', '.pptx',  # PowerPoint presentations
            '.odt', '.ods', '.odp',  # OpenDocument formats
            '.rtf',  # Rich Text Format
            '.pub' #Publisher
        ]
        
        if file_extension in direct_browser_files:
            # Serve PDF, images, and text files directly
            return serve_file_directly(template, file_extension)
            
        elif file_extension in google_docs_supported:
            # Use Google Docs Viewer
            return redirect_to_google_docs_viewer(request, template)
            
        else:
            # For unsupported files, offer download
            messages.info(request, f'{file_extension.upper()} files need to be downloaded to be viewed properly.')
            return redirect('template_manager:template-detail', pk=template.pk)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        messages.error(request, f'Error viewing file: {str(e)}')
        return redirect('template_manager:template-detail', pk=template.pk)


def serve_file_directly(template, file_extension):
    """Serve files that can be displayed directly in browser"""
    file_path = template.file.path
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise Http404("File does not exist")
    
    # Set content types
    content_types = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.gif': 'image/gif', 
        '.bmp': 'image/bmp', '.svg': 'image/svg+xml',
        '.txt': 'text/plain; charset=utf-8',
        '.html': 'text/html; charset=utf-8', '.htm': 'text/html; charset=utf-8',
    }
    
    content_type = content_types.get(file_extension, 'application/octet-stream')
    
    with open(file_path, 'rb') as file:
        file_content = file.read()
    
    response = HttpResponse(file_content, content_type=content_type)
    response['Content-Disposition'] = f'inline; filename="{os.path.basename(template.file.name)}"'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


def redirect_to_google_docs_viewer(request, template):
    """Redirect to Google Docs Viewer for Office files"""
    try:
        # Get the absolute URL to the file
        file_url = request.build_absolute_uri(template.file.url)
        
        # URL encode the file URL for Google Docs Viewer
        import urllib.parse
        encoded_file_url = urllib.parse.quote(file_url, safe='')
        
        # Google Docs Viewer URL
        google_docs_url = f"https://docs.google.com/gview?url={encoded_file_url}&embedded=true"
        
        # Redirect directly to Google Docs Viewer
        return redirect(google_docs_url)
        
    except Exception as e:
        # Fallback: serve file directly if Google Docs fails
        print(f"Google Docs Viewer error: {str(e)}")
        messages.info(request, 'Opening file directly. Some features may require download.')
        return serve_file_directly(template, os.path.splitext(template.file.name)[1].lower())


@login_required
def template_view_embedded(request, pk):
    """Enhanced file viewer with multiple preview options for development"""
    template = get_object_or_404(TemplateDocument, pk=pk, is_active=True)
    
    if not template.is_verified and not (request.user.is_staff or request.user == template.uploaded_by):
        messages.error(request, 'This template is not yet verified and cannot be viewed.')
        return redirect('template_manager:template-detail', pk=template.pk)
    
    file_extension = template.get_file_extension()
    
    # Determine the best viewing method for development
    if file_extension in ['pdf']:
        viewing_method = 'browser_pdf'
    elif file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg']:
        viewing_method = 'browser_image'
    elif file_extension in ['txt', 'html', 'htm', 'css', 'js', 'json', 'xml']:
        viewing_method = 'browser_text'
    elif file_extension in ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'pub']:
        viewing_method = 'office_info'
    else:
        viewing_method = 'download_info'
    
    context = {
        'template': template,
        'viewing_method': viewing_method,
        'file_extension': file_extension,
        'title': f'Viewing {template.title}'
    }
    
    return render(request, 'template_manager/template_view_embedded.html', context)

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def template_public_file(request, pk):
    """Public file view that serves files without authentication for external services"""
    template = get_object_or_404(TemplateDocument, pk=pk, is_active=True, is_verified=True)
    
    try:
        file_path = template.file.path
        
        if not os.path.exists(file_path):
            return HttpResponse("File not found", status=404)
        
        # Get file extension for content type
        file_extension = os.path.splitext(template.file.name)[1].lower()
        
        content_types = {
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.odt': 'application/vnd.oasis.opendocument.text',
            '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
            '.odp': 'application/vnd.oasis.opendocument.presentation',
            '.rtf': 'application/rtf',
            '.pdf': 'application/pdf',
            '.txt': 'text/plain; charset=utf-8',
            '.html': 'text/html; charset=utf-8',
            '.htm': 'text/html; charset=utf-8',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.svg': 'image/svg+xml',
        }
        
        content_type = content_types.get(file_extension, 'application/octet-stream')
        
        # Serve the file
        response = FileResponse(open(file_path, 'rb'), content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(template.file.name)}"'
        
        # Allow cross-origin requests for external services
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = '*'
        
        return response
        
    except Exception as e:
        print(f"Error serving public file: {str(e)}")
        return HttpResponse(f"Error serving file: {str(e)}", status=500)


# Add this function to handle OPTIONS requests for CORS
def template_public_file_options(request, pk):
    """Handle OPTIONS requests for CORS"""
    response = HttpResponse()
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response['Access-Control-Allow-Headers'] = '*'
    return response


def template_view_debug(request, pk):
    """Debug view to check file access and URLs"""
    template = get_object_or_404(TemplateDocument, pk=pk)
    
    # Build URLs for testing
    public_file_url = request.build_absolute_uri(
        reverse('template_manager:template-public-file', kwargs={'pk': template.pk})
    )
    
    import urllib.parse
    encoded_file_url = urllib.parse.quote(public_file_url, safe='')
    google_docs_url = f"https://docs.google.com/gview?url={encoded_file_url}&embedded=true"
    
    # Test if public file URL is accessible (with better error handling)
    import requests
    public_url_accessible = False
    test_error = None
    
    try:
        # Add a timeout and user agent to avoid blocking
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; CountyCyberMeru/1.0)'}
        test_response = requests.get(public_file_url, timeout=10, headers=headers, verify=False)
        public_url_accessible = test_response.status_code == 200
    except requests.exceptions.ConnectionError as e:
        test_error = f"Connection Error: {str(e)}"
    except requests.exceptions.Timeout as e:
        test_error = f"Timeout Error: {str(e)}"
    except Exception as e:
        test_error = f"Error: {str(e)}"
    
    context = {
        'template': template,
        'public_file_url': public_file_url,
        'google_docs_url': google_docs_url,
        'public_url_accessible': public_url_accessible,
        'test_error': test_error,
        'file_extension': template.get_file_extension(),
    }
    
    return render(request, 'template_manager/template_view_debug.html', context)




@login_required
def template_open_system(request, pk):
    """Open template in system's default application with user feedback"""
    template = get_object_or_404(TemplateDocument, pk=pk, is_active=True)
    
    if not template.is_verified and not (request.user.is_staff or request.user == template.uploaded_by):
        messages.error(request, 'This template is not yet verified and cannot be viewed.')
        return redirect('template_manager:template-detail', pk=template.pk)
    
    try:
        # Get the file path
        file_path = template.file.path
        
        if not os.path.exists(file_path):
            messages.error(request, f"File not found: {template.file.name}")
            return redirect('template_manager:template-detail', pk=template.pk)
        
        # Determine the system and open method
        system = platform.system()
        file_extension = template.get_file_extension()
        
        # Map file extensions to application names for better messages
        app_names = {
            'pdf': 'PDF reader',
            'doc': 'Microsoft Word',
            'docx': 'Microsoft Word', 
            'xls': 'Microsoft Excel',
            'xlsx': 'Microsoft Excel',
            'ppt': 'Microsoft PowerPoint',
            'pptx': 'Microsoft PowerPoint',
            'pub': 'Microsoft Publisher',
            'jpg': 'image viewer',
            'jpeg': 'image viewer',
            'png': 'image viewer',
            'gif': 'image viewer',
            'txt': 'text editor',
        }
        
        app_name = app_names.get(file_extension, 'default application')
        
        opening_success = False
        error_message = None
        
        if system == "Windows":
            # Windows - use os.startfile
            try:
                os.startfile(file_path)
                opening_success = True
                message = f"✅ '{template.title}' is now opening in your default {app_name}..."
            except Exception as e:
                error_message = f"Windows error: {str(e)}"
                
        elif system == "Darwin":  # macOS
            # macOS - use open command
            try:
                subprocess.run(["open", file_path], check=True, timeout=10)
                opening_success = True
                message = f"✅ '{template.title}' is now opening in your default {app_name}..."
            except subprocess.TimeoutExpired:
                error_message = "Opening timed out - the application may be taking longer to start"
            except subprocess.CalledProcessError as e:
                error_message = f"macOS error: Could not open file (code {e.returncode})"
            except Exception as e:
                error_message = f"macOS error: {str(e)}"
                
        elif system == "Linux":
            # Linux - use xdg-open
            try:
                subprocess.run(["xdg-open", file_path], check=True, timeout=10)
                opening_success = True
                message = f"✅ '{template.title}' is now opening in your default {app_name}..."
            except subprocess.TimeoutExpired:
                error_message = "Opening timed out - the application may be taking longer to start"
            except subprocess.CalledProcessError as e:
                error_message = f"Linux error: Could not open file (code {e.returncode})"
            except FileNotFoundError:
                error_message = "xdg-open not found - this feature requires xdg-utils package on Linux"
            except Exception as e:
                error_message = f"Linux error: {str(e)}"
                
        else:
            error_message = "Unsupported operating system for automatic file opening."
        
        if opening_success:
            # Success - show success message
            messages.success(request, message)
            
            # Also add an info message with tips
            tips = {
                'pdf': 'Tip: If PDF doesn\'t open, check if you have Adobe Acrobat or another PDF reader installed.',
                'doc': 'Tip: For best experience, use Microsoft Word or LibreOffice Writer.',
                'docx': 'Tip: For best experience, use Microsoft Word or LibreOffice Writer.',
                'xls': 'Tip: For best experience, use Microsoft Excel or LibreOffice Calc.',
                'xlsx': 'Tip: For best experience, use Microsoft Excel or LibreOffice Calc.',
                'ppt': 'Tip: For best experience, use Microsoft PowerPoint or LibreOffice Impress.',
                'pptx': 'Tip: For best experience, use Microsoft PowerPoint or LibreOffice Impress.',
                'pub': 'Tip: Publisher files require Microsoft Publisher installed.',
            }
            
            tip = tips.get(file_extension)
            if tip:
                messages.info(request, tip)
                
        else:
            # Error - show error message and fallback options
            error_msg = f"Could not open file automatically. {error_message}"
            messages.error(request, error_msg)
            messages.info(request, "Please try downloading the file and opening it manually.")
            
    except Exception as e:
        print(f"Error opening file: {str(e)}")
        messages.error(request, f"Unexpected error: {str(e)}")
    
    return redirect('template_manager:template-detail', pk=template.pk)


@login_required
def template_system_view(request, pk):
    """View for opening files with system applications"""
    template = get_object_or_404(TemplateDocument, pk=pk, is_active=True)
    
    if not template.is_verified and not (request.user.is_staff or request.user == template.uploaded_by):
        messages.error(request, 'This template is not yet verified and cannot be viewed.')
        return redirect('template_manager:template-detail', pk=template.pk)
    
    file_extension = template.get_file_extension()
    
    # Map file extensions to default applications
    app_suggestions = {
        'pdf': ['Adobe Acrobat', 'Chrome', 'Firefox', 'Edge'],
        'doc': ['Microsoft Word', 'LibreOffice Writer', 'Google Docs'],
        'docx': ['Microsoft Word', 'LibreOffice Writer', 'Google Docs'],
        'xls': ['Microsoft Excel', 'LibreOffice Calc', 'Google Sheets'],
        'xlsx': ['Microsoft Excel', 'LibreOffice Calc', 'Google Sheets'],
        'ppt': ['Microsoft PowerPoint', 'LibreOffice Impress', 'Google Slides'],
        'pptx': ['Microsoft PowerPoint', 'LibreOffice Impress', 'Google Slides'],
        'pub': ['Microsoft Publisher'],
        'jpg': ['Photos', 'Paint', 'Photoshop', 'GIMP'],
        'png': ['Photos', 'Paint', 'Photoshop', 'GIMP'],
        'txt': ['Notepad', 'TextEdit', 'VS Code', 'Sublime Text'],
    }
    
    suggested_apps = app_suggestions.get(file_extension, ['Default System Application'])
    
    context = {
        'template': template,
        'file_extension': file_extension,
        'suggested_apps': suggested_apps,
        'system': platform.system(),
        'title': f'Open {template.title}'
    }
    
    return render(request, 'template_manager/template_system_view.html', context)