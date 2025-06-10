from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse

class ReferralMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip middleware for API/fetch requests
        if self._is_api_request(request):
            return self.get_response(request)
            
        host = request.get_host().split(':')[0]
        parts = host.split('.')
        
        # Check for referral subdomain
        if len(parts) > 2 or (len(parts) == 2 and parts[1] == 'localhost'):
            subdomain = parts[0].upper()
            if subdomain not in ['WWW', 'LOCALHOST']:
                # Store in session without interfering with normal browsing
                if 'referral_code' not in request.session:
                    request.session['referral_code'] = subdomain
                    request.session['referral_source'] = 'subdomain'
                
                # Only redirect to register if not logged in and not already there
                if (not request.user.is_authenticated and 
                    request.path != reverse('authentication:login')):
                    return redirect(reverse('authentication:login'))

        return self.get_response(request)

    def _is_api_request(self, request):
        """Check if the request is an API/fetch request"""
        return (
            request.path.startswith('/api/') or 
            request.path.startswith('/fetch/') or
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            request.content_type == 'application/json'
        )