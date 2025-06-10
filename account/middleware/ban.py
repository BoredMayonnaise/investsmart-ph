from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
import datetime
from django.utils import timezone
from django.conf import settings
from urllib.parse import urlparse


class BanCheckMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            banned = getattr(request.user, 'banned_account', None)
            if banned:
                allowed_paths = [
                    reverse('authentication:logout'),
                    reverse('authentication:login'),
                    reverse('user:banned_notice'),
                ]
                if request.path not in allowed_paths:
                    return redirect('user:banned_notice')
