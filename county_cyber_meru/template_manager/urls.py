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
    
    # Category management
    path('categories/', views.category_list, name='category-list'),
    # path('category/<slug:slug>/', views.category_detail, name='category-detail'),
    path('category/create/', views.category_create, name='category-create'),
    path('category/<slug:slug>/edit/', views.category_edit, name='category-edit'),
    path('category/<slug:slug>/delete/', views.category_delete, name='category-delete'),
    path('category/<slug:slug>/toggle/', views.category_toggle, name='category-toggle'),
    
    # Search
    path('search/', views.template_search, name='template-search'),
]