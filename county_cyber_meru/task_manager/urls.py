from django.urls import path
from . import views

app_name = 'task_manager'

urlpatterns = [
    # Public URLs (no authentication required)
    path('submit/', views.task_submission, name='task-submission'),
    path('submit/success/', views.task_submission_success, name='task-submission-success'),
    
    # Staff-only URLs
    path('', views.task_list, name='task-list'),
    path('dashboard/', views.task_dashboard, name='task-dashboard'),
    path('<int:pk>/', views.task_detail, name='task-detail'),
    
    # Task actions
    path('services/', views.services, name='services'),
    path('create/', views.task_submission, name='task-create'),
    path('<int:pk>/assign-to-me/', views.task_assign_to_me, name='task-assign-to-me'),
    path('<int:pk>/mark-completed/', views.task_mark_completed, name='task-mark-completed'),
    path('<int:pk>/cancel/', views.task_cancel, name='task-cancel'),
]