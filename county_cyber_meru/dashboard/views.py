from django.shortcuts import render, redirect

# Create your views here.
from django.contrib.auth.decorators import login_required
from template_manager.models import Category, TemplateDocument, TemplateDownload, TemplateRating
from django.contrib import messages
from django.db.models import Count, Sum
from task_manager.models import Task

@login_required
def dashboard(request):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    # Calculate statistics
    total_templates = TemplateDocument.objects.filter(is_active=True).count()
    user_uploads = TemplateDocument.objects.filter(uploaded_by=request.user, is_active=True).count()
    pending_verification = TemplateDocument.objects.filter(is_verified=False, is_active=True).count()
    total_downloads = TemplateDownload.objects.count()
    task_stats = {
        'total_tasks': Task.objects.count(),
        'pending_tasks': Task.objects.filter(status='pending').count(),
        'in_progress_tasks': Task.objects.filter(status='in_progress').count(),
        'my_tasks': Task.objects.filter(assigned_to=request.user).exclude(
            status__in=['completed', 'cancelled']
        ).count(),
        'recent_tasks': Task.objects.all().order_by('-created_at')[:5],
    }
    # User-specific downloads
    user_downloads = TemplateDownload.objects.filter(downloaded_by=request.user).count()
    
    # Recent templates (last 5)
    recent_templates = TemplateDocument.objects.filter(is_active=True).order_by('-uploaded_at')[:5]
    
    # Top categories
    top_categories = Category.objects.annotate(
        template_count=Count('templates')
    ).filter(template_count__gt=0, is_active=True).order_by('-template_count')[:5]
    
    # User's recent activity
    user_recent_uploads = TemplateDocument.objects.filter(
        uploaded_by=request.user, 
        is_active=True
    ).order_by('-uploaded_at')[:3]
    
    user_recent_downloads = TemplateDownload.objects.filter(
        downloaded_by=request.user
    ).select_related('template').order_by('-downloaded_at')[:3]

    context = {
        'user': request.user,
        'total_templates': total_templates,
        'user_uploads': user_uploads,
        'pending_verification': pending_verification,
        'total_downloads': total_downloads,
        'user_downloads': user_downloads,
        'recent_templates': recent_templates,
        'top_categories': top_categories,
        'user_recent_uploads': user_recent_uploads,
        'user_recent_downloads': user_recent_downloads,
        'task_stats': task_stats,
    }
    return render(request, 'staff/dashboard.html', context)