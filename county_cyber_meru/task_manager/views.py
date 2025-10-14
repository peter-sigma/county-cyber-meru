from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Q, Count
from django.utils import timezone
from .models import Task, TaskCategory, TaskUpdate, TaskAttachment, ServiceCategory
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
    """Staff view of tasks"""
    tasks = Task.objects.all().select_related('category', 'category__service_category', 'assigned_to')
    
    # Filtering
    status_filter = request.GET.get('status')
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    category_filter = request.GET.get('category')
    if category_filter:
        tasks = tasks.filter(category_id=category_filter)
    
    context = {
        'tasks': tasks,
        'status_choices': Task.STATUS_CHOICES,
    }
    return render(request, 'task_manager/task_list.html', context)





@user_passes_test(is_staff_user)
@login_required
def task_detail(request, pk):
    """Detail view for a specific task"""
    task = get_object_or_404(Task, pk=pk)
    context = {
        'task': task,
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


def services(request):  # Changed from services_view to match your URL pattern
    """Display all service categories and their subcategories"""
    try:
        # Get all active service categories with their active subcategories
        service_categories = ServiceCategory.objects.filter(
            is_active=True
        ).prefetch_related(
            'subcategories'
        ).order_by('order', 'name')
        
        # Debug info
        print(f"Found {service_categories.count()} service categories")
        for category in service_categories:
            print(f"Category: {category.name}, Subcategories: {category.subcategories.filter(is_active=True).count()}")
        
        context = {
            'service_categories': service_categories,
        }
        return render(request, 'public/services.html', context)
        
    except Exception as e:
        print(f"Error in services_view: {e}")
        context = {
            'service_categories': [],
            'error': str(e)
        }
        return render(request, 'public/services.html', context)



def services_view(request):
    """Display all service categories and their subcategories"""
    try:
        # Get all active service categories with their active subcategories
        service_categories = ServiceCategory.objects.filter(
            is_active=True
        ).prefetch_related(
            'subcategories'
        ).order_by('order', 'name')
        
        # Debug info
        print(f"Found {service_categories.count()} service categories")
        for category in service_categories:
            print(f"Category: {category.name}, Subcategories: {category.subcategories.filter(is_active=True).count()}")
        
        context = {
            'service_categories': service_categories,
        }
        return render(request, 'public/services.html', context)
        
    except Exception as e:
        print(f"Error in services_view: {e}")
        context = {
            'service_categories': [],
            'error': str(e)
        }
        return render(request, 'public/services.html', context)

def task_submission(request):
    """Handle task submission with category pre-selection"""
    category_id = request.GET.get('category') or request.POST.get('category')
    service_category_id = request.GET.get('service_category') or request.POST.get('service_category')
    
    initial_data = {}
    selected_category = None
    
    # Get the selected category if provided
    if category_id:
        try:
            selected_category = get_object_or_404(TaskCategory, id=category_id, is_active=True)
            initial_data['category'] = selected_category
        except:
            messages.error(request, "Invalid service category selected.")
    
    if request.method == 'POST':
        form = TaskSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                task = form.save(commit=False)
                
                # Set category based on what was selected
                if selected_category:
                    task.category = selected_category
                
                # Set price from category if available
                if not task.price and task.category and task.category.price:
                    task.price = task.category.price
                
                task.save()
                messages.success(request, f"Your task '{task.title}' has been submitted successfully! We'll contact you soon.")
                return redirect('task_manager:task-submission-success')
                
            except Exception as e:
                print(f"Error saving task: {e}")
                messages.error(request, f"There was an error submitting your task: {str(e)}")
        else:
            # Form is invalid - show errors
            print("Form errors:", form.errors)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = TaskSubmissionForm(initial=initial_data)
    
    context = {
        'form': form,
        'selected_category': selected_category,
    }
    
    return render(request, 'task_manager/task_submission_form.html', context)  # Changed template

def task_submission_success(request):
    """Display success page after task submission"""
    return render(request, 'task_manager/submission_success.html')


