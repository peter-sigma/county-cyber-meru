from django import forms
from django.contrib.auth import get_user_model
from .models import Task, TaskCategory, TaskUpdate, TaskAttachment

# This will automatically get your StaffProfile model
User = get_user_model()

class TaskSubmissionForm(forms.ModelForm):
    """Form for customers to submit new tasks"""
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'category', 
            'customer_name', 'customer_email', 'customer_phone',
            'attachment'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Please provide detailed information about your task...'}),
            'customer_name': forms.TextInput(attrs={'placeholder': 'Your full name'}),
            'customer_email': forms.EmailInput(attrs={'placeholder': 'your.email@example.com'}),
            'customer_phone': forms.TextInput(attrs={'placeholder': 'Optional phone number'}),
            'title': forms.TextInput(attrs={'placeholder': 'Brief title for your task'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active categories
        self.fields['category'].queryset = TaskCategory.objects.filter(is_active=True)
        
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class TaskStaffForm(forms.ModelForm):
    """Form for staff to manage tasks"""
    class Meta:
        model = Task
        fields = [
            'status', 'priority', 'assigned_to', 'price',
            'due_date', 'staff_notes', 'cancellation_reason'
        ]
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'staff_notes': forms.Textarea(attrs={'rows': 3}),
            'cancellation_reason': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit assigned_to to staff users only - now using your StaffProfile
        self.fields['assigned_to'].queryset = User.objects.filter(is_staff=True)
        
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # Make the assigned_to field display better names
        self.fields['assigned_to'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username} ({obj.get_rank_display()})"

class TaskUpdateForm(forms.ModelForm):
    """Form for adding updates/comments to tasks"""
    class Meta:
        model = TaskUpdate
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': 'Add an update or comment about this task...',
                'class': 'form-control'
            })
        }

class TaskAttachmentForm(forms.ModelForm):
    """Form for adding file attachments to tasks"""
    class Meta:
        model = TaskAttachment
        fields = ['file', 'description']
        widgets = {
            'description': forms.TextInput(attrs={
                'placeholder': 'Brief description of this file',
                'class': 'form-control'
            }),
            'file': forms.FileInput(attrs={'class': 'form-control'})
        }