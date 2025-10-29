from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import login_view, admin_dashboard_view, staff_dashboard_view

urlpatterns = [
    # ✅ Default login page
    path('', login_view, name='login'),

    # ✅ Django admin site
    path('admin/', admin.site.urls),

    # ✅ Include app routes with namespaces
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('vehicles/', include(('vehicles.urls', 'vehicles'), namespace='vehicles')),
    path('terminal/', include(('terminal.urls', 'terminal'), namespace='terminal')),
    path('reports/', include(('reports.urls', 'reports'), namespace='reports')),

    # ✅ Dashboards (explicit routes, not included in app urls)
    path('dashboard/admin/', admin_dashboard_view, name='admin_dashboard'),
    path('dashboard/staff/', staff_dashboard_view, name='staff_dashboard'),
]

# ✅ Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
