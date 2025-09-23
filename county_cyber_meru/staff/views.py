from django.shortcuts import render

# Create your views here.
from django.shortcuts import redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect

@csrf_protect
def staff_login(request):
    """Staff login view - only allows staff users"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_staff:  # Only allow staff users to login
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                
                # Redirect to next page if specified
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('dashboard')
            else:
                messages.error(request, 'This account does not have staff privileges.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'staff/login.html')

@login_required
def staff_logout(request):
    """Staff logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')

@login_required
def staff_dashboard(request):
    """Staff dashboard - only accessible to logged-in staff"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    context = {
        'user': request.user,
    }
    return render(request, 'staff/dashboard.html', context)