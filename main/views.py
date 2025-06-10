from django.shortcuts import render
from datetime import datetime
from django.contrib.auth.decorators import login_required

# Create your views here.

def homepage(request):
    return render(request, 'main/homepage.html', {'year': datetime.now().year})

def custom_lockout_view(request, credentials=None, *args, **kwargs):
    return render(request, 'axes/lockout.html', status=403)