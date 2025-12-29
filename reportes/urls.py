from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.menu_reportes, name='menu'),
    path('conteo/', views.reporte_conteo, name='conteo'),
    path('inventario/', views.reporte_inventario, name='inventario'),
    path('diferencias/<int:conteo_id>/', views.reporte_diferencias, name='diferencias'),
    path('exportar/conteo/', views.exportar_reporte_conteo, name='exportar_conteo'),
    path('exportar/inventario/', views.exportar_reporte_inventario, name='exportar_inventario'),
]

