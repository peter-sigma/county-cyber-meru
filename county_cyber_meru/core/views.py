from django.shortcuts import render
from task_manager.models import TaskCategory
from .models import SliderImage

# Create your views here.
def home(request):
    slider_images = SliderImage.objects.filter(is_active=True)[:5]
    return render(request, 'public/home.html', {'slider_images': slider_images})

def about(request):
    return render(request, 'public/about.html')

def contact(request):
    return render(request, 'public/contact.html')
