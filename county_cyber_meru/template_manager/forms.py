from django import forms
from .models import TemplateDocument,Category

class TemplateUploadForm(forms.ModelForm):
    class Meta:
        model = TemplateDocument
        fields = [
            'title', 'description', 'category', 'document_type', 
            'paper_size', 'template_category', 'file', 'thumbnail', 
            'tags', 'price'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter template title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the template...'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'document_type': forms.Select(attrs={'class': 'form-control'}),
            'paper_size': forms.Select(attrs={'class': 'form-control'}),
            'template_category': forms.Select(attrs={'class': 'form-control'}),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'comma, separated, tags'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].widget.attrs.update({'class': 'form-control'})
        self.fields['thumbnail'].widget.attrs.update({'class': 'form-control'})




class TemplateUploadForm(forms.ModelForm):
    class Meta:
        model = TemplateDocument
        fields = [
            'title', 'description', 'category', 'document_type', 
            'paper_size', 'template_category', 'file', 'thumbnail', 
            'tags', 'price', 'is_featured'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a descriptive title for the template'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the template, its purpose, and any special features...'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'document_type': forms.Select(attrs={'class': 'form-control'}),
            'paper_size': forms.Select(attrs={'class': 'form-control'}),
            'template_category': forms.Select(attrs={'class': 'form-control'}),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., wedding, business, modern, classic (comma separated)'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00 (leave as 0 for free templates)'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        help_texts = {
            'file': 'Upload the template file (PDF, DOC, PUB, etc.)',
            'thumbnail': 'Optional: Upload a preview image of the template',
            'price': 'Set price in KSh (0.00 for free templates)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].widget.attrs.update({'class': 'form-control'})
        self.fields['thumbnail'].widget.attrs.update({'class': 'form-control'})
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        
        # Make thumbnail optional
        self.fields['thumbnail'].required = False
        self.fields['price'].required = False
        self.fields['tags'].required = False