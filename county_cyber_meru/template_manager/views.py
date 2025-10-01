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


def category_detail(request, slug):
    """Show all templates in a specific category"""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    
    # Get templates with optional filtering
    templates = TemplateDocument.objects.filter(
        category=category, 
        is_active=True
    ).order_by('-uploaded_at')
    
    # Apply filters if provided
    document_type = request.GET.get('document_type')
    verification_status = request.GET.get('verification')
    
    if document_type:
        templates = templates.filter(document_type=document_type)
    
    if verification_status == 'verified':
        templates = templates.filter(is_verified=True)
    elif verification_status == 'pending':
        templates = templates.filter(is_verified=False)
    
    # Get template counts
    total_templates = templates.count()
    verified_count = templates.filter(is_verified=True).count()
    pending_count = templates.filter(is_verified=False).count()
    
    # Get unique document types for filter
    document_types = TemplateDocument.objects.filter(
        category=category, 
        is_active=True
    ).values_list('document_type', flat=True).distinct()
    
    context = {
        'category': category,
        'templates': templates,
        'verified_count': verified_count,
        'pending_count': pending_count,
        'total_templates': total_templates,
        'document_types': document_types,
        'title': f'{category.name} Templates',
        'current_filters': {
            'document_type': document_type,
            'verification': verification_status,
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