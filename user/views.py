from django.contrib.auth.decorators import login_required
from .models import Profile, LoginHistory
from django.shortcuts import render, redirect
from django.contrib.auth.models import User


def banned_notice(request):
    banned = getattr(request.user, 'banned_account', None)
    return render(request, 'banned/banned.html', {'banned': banned})

@login_required
def dashboard_view(request):
    profile = request.user.profile
    history = request.user.login_history.first()
    device_info = history.get_device_info() if history else None
    referral_code = request.user.profile.referral_code

    current_domain = request.get_host().split(':')[0]  # e.g., "yourdomain.com" or "localhost"

    port = request.get_port()
    protocol = 'https' if request.is_secure() else 'http'

    referral_url = f"{protocol}://{referral_code}.{current_domain}"
    if 'localhost' in current_domain:  # For local dev with port
        referral_url += f":{port}"

    context = {
        'profile': profile,
        'history': history,
        'device_info': device_info,
        'referral_url': referral_url,
    }
    return render(request, 'dashboard/user.html', context)


    