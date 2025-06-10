from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
import datetime
from django.utils import timezone
from django.conf import settings
from urllib.parse import urlparse

class ActiveUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            now = timezone.now()
            if hasattr(request.user, 'profile'):
                if not request.user.profile.last_seen or (
                    now - request.user.profile.last_seen
                ).total_seconds() > 60:
                    request.user.profile.last_seen = now
                    request.user.profile.save(update_fields=['last_seen'])

        return response
