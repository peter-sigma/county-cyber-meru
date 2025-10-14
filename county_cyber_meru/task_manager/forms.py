from django import forms
from django.contrib.auth import get_user_model
from .models import Task, TaskCategory, TaskUpdate, TaskAttachment
from datetime import datetime, timedelta
from django.utils import timezone

# This will automatically get your StaffProfile model
User = get_user_model()

class TaskSubmissionForm(forms.ModelForm):
    """Form for customers to submit new tasks"""
    deadline = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control',
            'min': timezone.now().strftime('%Y-%m-%dT%H:%M')
        }),
        help_text="Optional: When do you need this completed? We'll adjust urgency based on your deadline."
    )
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'category', 
            'customer_name', 'customer_email', 'customer_phone',
            'deadline', 'attachment'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief description of what you need'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Detailed description of your requirements...'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your.email@example.com'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your phone number'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = TaskCategory.objects.filter(is_active=True)
        self.fields['category'].empty_label = "Select a service"
    
    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline and deadline < timezone.now():
            raise forms.ValidationError("Deadline cannot be in the past.")
        return deadline
    
    def calculate_priority_from_deadline(self, deadline):
        """Calculate priority based on deadline"""
        if not deadline:
            return 'medium'
            
        now = timezone.now()
        time_until_due = deadline - now
        hours_until_due = time_until_due.total_seconds() / 3600
        
        if hours_until_due <= 24:
            return 'urgent'
        elif hours_until_due <= 72:
            return 'high'
        elif hours_until_due <= 168:
            return 'medium'
        else:
            return 'low'
    
    def save(self, commit=True):
        task = super().save(commit=False)
        deadline = self.cleaned_data.get('deadline')
        
        if deadline:
            task.due_date = deadline
            # Set priority based on deadline
            task.priority = self.calculate_priority_from_deadline(deadline)
        else:
            task.priority = 'medium'  # Default priority
        
        if commit:
            task.save()
        return task
    

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