from django.urls import path
from . import views

app_name = 'productos'

urlpatterns = [
    path('', views.lista_productos, name='lista'),
    path('crear/', views.crear_producto, name='crear'),
    path('<int:pk>/', views.detalle_producto, name='detalle'),
    path('<int:pk>/editar/', views.editar_producto, name='editar'),
    path('<int:pk>/eliminar/', views.eliminar_producto, name='eliminar'),
    path('importar/', views.importar_productos, name='importar'),
    path('importar-api/', views.importar_productos_api, name='importar_api'),
    path('exportar/', views.exportar_productos, name='exportar'),
    path('descargar-plantilla/', views.descargar_plantilla_importacion, name='descargar_plantilla'),
    path('<int:pk>/asignar-pareja/', views.asignar_pareja, name='asignar_pareja'),
    path('asignar-multiples-parejas/', views.asignar_multiples_parejas, name='asignar_multiples_parejas'),
]

