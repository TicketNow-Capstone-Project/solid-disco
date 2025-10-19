from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import login_view

urlpatterns = [
    # ✅ Default login page
    path('', login_view, name='login'),

    # ✅ Keep Django admin site (disabled for users unless you want to access it)
    path('admin/', admin.site.urls),

    # ✅ Include app routes
    path('accounts/', include('accounts.urls')),
    path('vehicles/', include('vehicles.urls')),
    path('terminal/', include('terminal.urls')),
    path('reports/', include('reports.urls')),
]

# ✅ Serve media files during development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
