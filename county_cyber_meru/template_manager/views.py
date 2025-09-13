from django.shortcuts import render

# Create your views here.
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from .models import TemplateDocument, Category
from .forms import TemplateUploadForm
from django.http import FileResponse, Http404

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
    """Download template file"""
    template = get_object_or_404(TemplateDocument, pk=pk, is_active=True)
    
    # Increment download count
    template.increment_download_count()
    
    # Here you would typically serve the file for download
    file_handle = template.file.open("rb")
    response = FileResponse(file_handle, as_attachment=True)
    response["Content-Disposition"] = f'attachment; filename="{template.file.name.split("/")[-1]}"'

    messages.success(request, f"Download started for: {template.title}")
    return response
    # return redirect('template_manager:template-detail', pk=template.pk)

def category_list(request):
    """List all categories"""
    categories = Category.objects.filter(is_active=True)
    context = {'categories': categories}
    return render(request, 'template_manager/category_list.html', context)

def category_detail(request, slug):
    """Templates in a specific category"""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    templates = TemplateDocument.objects.filter(
        category=category, 
        is_verified=True, 
        is_active=True
    )
    context = {
        'category': category,
        'templates': templates
    }
    return render(request, 'template_manager/category_detail.html', context)

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