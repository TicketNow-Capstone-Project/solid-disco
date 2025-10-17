# accounts/middleware.py
from django.shortcuts import redirect
from django.utils import timezone
from django.conf import settings

class SessionSecurityMiddleware:
    """Force session timeout and block cached pages after logout."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Block page cache on every request
        response = self.get_response(request)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'

        # Skip checks for login or static requests
        if request.path.startswith('/static/') or request.path in ['/login/', '/logout/']:
            return response

        # Auto logout after inactivity
        if request.user.is_authenticated:
            # Check user role permissions
            if hasattr(request.user, 'role') and request.user.role == 'SUSPENDED':
                from django.contrib.auth import logout
                logout(request)
                request.session.flush()
                return redirect('login')
                
            last_activity = request.session.get('last_activity')
            now = timezone.now().timestamp()
            timeout = getattr(settings, 'SESSION_COOKIE_AGE', 900)  # 15 minutes by default

            if last_activity and now - last_activity > timeout:
                from django.contrib.auth import logout
                logout(request)
                request.session.flush()
                return redirect('login')

            request.session['last_activity'] = now

        return response
