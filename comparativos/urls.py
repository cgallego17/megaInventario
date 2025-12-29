from django.urls import path
from . import views

app_name = 'comparativos'

urlpatterns = [
    path('', views.lista_comparativos, name='lista'),
    path('crear/', views.crear_comparativo, name='crear'),
    path('<int:pk>/', views.detalle_comparativo, name='detalle'),
    path('<int:pk>/subir-inventario/', views.subir_inventario, name='subir_inventario'),
    path('<int:pk>/procesar/', views.procesar_comparativo, name='procesar'),
    path('<int:pk>/exportar/', views.exportar_comparativo, name='exportar'),
    path('descargar-ejemplo/', views.descargar_ejemplo, name='descargar_ejemplo'),
]

