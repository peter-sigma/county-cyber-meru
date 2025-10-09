from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Q, Count
from django.utils import timezone
from .models import Task, TaskCategory, TaskUpdate, TaskAttachment
from .forms import TaskSubmissionForm, TaskStaffForm, TaskUpdateForm, TaskAttachmentForm
from django.db.models import Count, Q
from django.db.models import Case, When, IntegerField

# This gets your custom StaffProfile model
User = get_user_model()

# Helper function to check if user is staff
def is_staff_user(user):
    return user.is_staff


# Public views (no authentication required)
def task_submission(request):
    """Allow anyone to submit a task"""
    # Get category from query parameter
    category_id = request.GET.get('category')
    initial_data = {}
    
    if category_id:
        try:
            category = TaskCategory.objects.get(id=category_id, is_active=True)
            initial_data['category'] = category
        except TaskCategory.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = TaskSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            task = form.save()
            messages.success(
                request, 
                f'Task submitted successfully! Your reference is #{task.id}. '
                f'We will contact you at {task.customer_email} soon.'
            )
            return redirect('task_manager:task-submission-success')
    else:
        form = TaskSubmissionForm(initial=initial_data)
    
    context = {
        'form': form,
        'categories': TaskCategory.objects.filter(is_active=True),
        'title': 'Submit a Task'
    }
    return render(request, 'task_manager/task_submission.html', context)



def task_submission_success(request):
    """Success page after task submission"""
    return render(request, 'task_manager/task_submission_success.html', {'title': 'Task Submitted Successfully'})

# Staff-only views
@user_passes_test(is_staff_user)
@login_required
def task_list(request):
    """List all tasks for staff"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    category_filter = request.GET.get('category', '')
    assigned_filter = request.GET.get('assigned', '')
    date_filter = request.GET.get('date', '')
    search_query = request.GET.get('q', '')
    
    tasks = Task.objects.all().select_related('category', 'assigned_to')
    
    # Apply filters
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    if category_filter:
        tasks = tasks.filter(category_id=category_filter)
    if assigned_filter == 'me':
        tasks = tasks.filter(assigned_to=request.user)
    elif assigned_filter == 'unassigned':
        tasks = tasks.filter(assigned_to__isnull=True)
    
    # Date filters
    today = timezone.now().date()
    if date_filter:
        if date_filter == 'today':
            tasks = tasks.filter(created_at__date=today)
        elif date_filter == 'yesterday':
            yesterday = today - timezone.timedelta(days=1)
            tasks = tasks.filter(created_at__date=yesterday)
        elif date_filter == 'this_week':
            start_of_week = today - timezone.timedelta(days=today.weekday())
            tasks = tasks.filter(created_at__date__gte=start_of_week)
        elif date_filter == 'last_week':
            start_of_last_week = today - timezone.timedelta(days=today.weekday() + 7)
            end_of_last_week = start_of_last_week + timezone.timedelta(days=6)
            tasks = tasks.filter(created_at__date__range=[start_of_last_week, end_of_last_week])
        elif date_filter == 'this_month':
            tasks = tasks.filter(created_at__year=today.year, created_at__month=today.month)
        elif date_filter == 'last_month':
            first_day_of_current_month = today.replace(day=1)
            last_day_of_last_month = first_day_of_current_month - timezone.timedelta(days=1)
            first_day_of_last_month = last_day_of_last_month.replace(day=1)
            tasks = tasks.filter(created_at__date__range=[first_day_of_last_month, last_day_of_last_month])
    
    # Search filter (apply after date filters)
    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_email__icontains=search_query)
        )
    
    # Get counts for statistics
    total_tasks = Task.objects.count()
    pending_count = Task.objects.filter(status='pending').count()
    completed_count = Task.objects.filter(status='completed').count()
    overdue_count = Task.objects.filter(
        due_date__lt=timezone.now(),
        status__in=['pending', 'in_progress']
    ).count()
    
    context = {
        'tasks': tasks,
        'total_tasks': total_tasks,
        'pending_count': pending_count,
        'completed_count': completed_count,
        'overdue_count': overdue_count,
        'status_choices': Task.STATUS_CHOICES,
        'priority_choices': Task.PRIORITY_CHOICES,
        'staff_members': User.objects.filter(is_staff=True),
        'categories': TaskCategory.objects.filter(is_active=True),
        'current_filters': {
            'status': status_filter,
            'priority': priority_filter,
            'category': category_filter,
            'assigned': assigned_filter,
            'date': date_filter,
        },
        'title': 'Task Management'
    }
    return render(request, 'task_manager/task_list.html', context)




@user_passes_test(is_staff_user)
@login_required
def task_detail(request, pk):
    """View task details and manage task"""
    task = get_object_or_404(Task, pk=pk)
    
    # Forms
    staff_form = TaskStaffForm(instance=task)
    update_form = TaskUpdateForm()
    attachment_form = TaskAttachmentForm()
    
    if request.method == 'POST':
        if 'update_status' in request.POST:
            staff_form = TaskStaffForm(request.POST, instance=task)
            if staff_form.is_valid():
                staff_form.save()
                messages.success(request, 'Task updated successfully!')
                return redirect('task_manager:task-detail', pk=task.pk)
        
        elif 'add_update' in request.POST:
            update_form = TaskUpdateForm(request.POST)
            if update_form.is_valid():
                update = update_form.save(commit=False)
                update.task = task
                update.user = request.user
                update.save()
                messages.success(request, 'Update added successfully!')
                return redirect('task_manager:task-detail', pk=task.pk)
        
        elif 'add_attachment' in request.POST:
            attachment_form = TaskAttachmentForm(request.POST, request.FILES)
            if attachment_form.is_valid():
                attachment = attachment_form.save(commit=False)
                attachment.task = task
                attachment.uploaded_by = request.user
                attachment.save()
                messages.success(request, 'Attachment added successfully!')
                return redirect('task_manager:task-detail', pk=task.pk)
    
    context = {
        'task': task,
        'staff_form': staff_form,
        'update_form': update_form,
        'attachment_form': attachment_form,
        'title': f'Task: {task.title}'
    }
    return render(request, 'task_manager/task_detail.html', context)

@user_passes_test(is_staff_user)
@login_required


def task_dashboard(request):
    """Staff dashboard with task statistics"""
    # Get all counts in single queries using conditional aggregation
    
    # Get status counts in one query
    status_counts = Task.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        completed=Count('id', filter=Q(status='completed')),
        cancelled=Count('id', filter=Q(status='cancelled'))
    )
    
    # Get overdue count
    overdue_count = Task.objects.filter(
        due_date__lt=timezone.now(),
        status__in=['pending', 'in_progress']
    ).count()
    
    # Get counts by priority
    tasks_by_priority = Task.objects.values('priority').annotate(count=Count('id'))
    
    # Get counts by category
    tasks_by_category = Task.objects.values('category__name').annotate(count=Count('id'))
    
    # Recent tasks
    recent_tasks = Task.objects.all().select_related('category', 'assigned_to').order_by('-created_at')[:10]
    
    # Overdue tasks
    overdue_tasks = Task.objects.filter(
        due_date__lt=timezone.now(),
        status__in=['pending', 'in_progress']
    ).select_related('category', 'assigned_to')[:10]
    
    # My assigned tasks
    if request.user.is_authenticated:
        my_tasks = Task.objects.filter(assigned_to=request.user).exclude(
            status__in=['completed', 'cancelled']
        ).select_related('category')[:10]
    else:
        my_tasks = []
    
    context = {
        'tasks_by_status': status_counts,  # This is now a proper dictionary
        'overdue_count': overdue_count,
        'tasks_by_priority': list(tasks_by_priority),
        'tasks_by_category': list(tasks_by_category),
        'recent_tasks': recent_tasks,
        'overdue_tasks': overdue_tasks,
        'my_tasks': my_tasks,
        'title': 'Task Dashboard'
    }
    return render(request, 'task_manager/task_dashboard.html', context)



# Task actions
@user_passes_test(is_staff_user)
@login_required
def task_assign_to_me(request, pk):
    """Assign task to current staff user"""
    task = get_object_or_404(Task, pk=pk)
    task.assigned_to = request.user
    task.status = 'in_progress'
    task.save()
    
    # Add update
    TaskUpdate.objects.create(
        task=task,
        user=request.user,
        message=f"Task assigned to {request.user.get_full_name() or request.user.username} ({request.user.get_rank_display()})"
    )
    
    messages.success(request, f'Task #{task.id} assigned to you and marked as in progress.')
    return redirect('task_manager:task-detail', pk=task.pk)

@user_passes_test(is_staff_user)
@login_required
def task_mark_completed(request, pk):
    """Mark task as completed"""
    task = get_object_or_404(Task, pk=pk)
    task.status = 'completed'
    task.completed_at = timezone.now()
    task.save()
    
    # Add update
    TaskUpdate.objects.create(
        task=task,
        user=request.user,
        message="Task marked as completed"
    )
    
    messages.success(request, f'Task #{task.id} marked as completed.')
    return redirect('task_manager:task-detail', pk=task.pk)

@user_passes_test(is_staff_user)
@login_required
def task_cancel(request, pk):
    """Cancel task with reason"""
    task = get_object_or_404(Task, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('cancellation_reason', '')
        if reason:
            task.status = 'cancelled'
            task.cancellation_reason = reason
            task.save()
            
            # Add update
            TaskUpdate.objects.create(
                task=task,
                user=request.user,
                message=f"Task cancelled. Reason: {reason}"
            )
            
            messages.success(request, f'Task #{task.id} has been cancelled.')
            return redirect('task_manager:task-detail', pk=task.pk)
        else:
            messages.error(request, 'Please provide a reason for cancellation.')
    
    return render(request, 'task_manager/task_cancel.html', {
        'task': task,
        'title': f'Cancel Task: {task.title}'
    })


def services(request):
    categories = TaskCategory.objects.filter(is_active=True)
    return render(request, 'public/services.html', {
        'categories': categories,
        'title': 'Our Services'
    })