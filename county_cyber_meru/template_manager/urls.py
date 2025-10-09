from django.urls import path
from . import views

app_name = 'template_manager'

urlpatterns = [
    # Template management
    path('', views.template_list, name='template-list'),
    path('template/<int:pk>/', views.template_detail, name='template-detail'),
    path('template/upload/', views.template_upload, name='template-upload'),
    path('template/<int:pk>/edit/', views.template_edit, name='template-edit'),
    # path('template/<int:pk>/delete/', views.template_delete, name='template-delete'),
    path('template/<int:pk>/download/', views.template_download, name='template-download'),
    path('template/<int:pk>/view/', views.template_view, name='template-view'),
     path('template/<int:pk>/view-embedded/', views.template_view_embedded, name='template-view-embedded'),
    path('template/<int:pk>/public-file/', views.template_public_file, name='template-public-file'),
    path('template/<int:pk>/view-debug/', views.template_view_debug, name='template-view-debug'),
    path('template/<int:pk>/system-view/', views.template_system_view, name='template-system-view'),
    path('template/<int:pk>/open-system/', views.template_open_system, name='template-open-system'),
    
    # Category management
    path('categories/', views.category_list, name='category-list'),
    # path('category/<slug:slug>/', views.category_detail, name='category-detail'),
    path('category/create/', views.category_create, name='category-create'),
    path('category/<slug:slug>/', views.category_detail, name='category-detail'),
    path('category/<slug:slug>/edit/', views.category_edit, name='category-edit'),
    path('category/<slug:slug>/delete/', views.category_delete, name='category-delete'),
    path('category/<slug:slug>/toggle/', views.category_toggle, name='category-toggle'),
    
    # Search
    path('search/', views.template_search, name='template-search'),
]