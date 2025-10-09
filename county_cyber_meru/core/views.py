from django.shortcuts import render
from task_manager.models import TaskCategory

# Create your views here.
def home(request):
    return render(request, 'public/home.html')

def about(request):
    return render(request, 'public/about.html')

def contact(request):
    return render(request, 'public/contact.html')
