"""
URL configuration for megaInventario project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),
    path('productos/', include('productos.urls')),
    path('conteo/', include('conteo.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('reportes/', include('reportes.urls')),
    path('comparativos/', include('comparativos.urls')),
    path('movimientos/', include('movimientos.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

