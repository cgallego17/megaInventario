from django.urls import path
from . import views

app_name = 'conteo'

urlpatterns = [
    path('', views.lista_conteos, name='lista_conteos'),
    path('crear/', views.crear_conteo, name='crear_conteo'),
    path('<int:pk>/', views.detalle_conteo, name='detalle_conteo'),
    path('<int:pk>/finalizar/', views.finalizar_conteo, name='finalizar_conteo'),
    path('<int:conteo_id>/agregar-item/', views.agregar_item, name='agregar_item'),
    path('buscar-producto/', views.buscar_producto, name='buscar_producto'),
    path('item/<int:item_id>/eliminar/', views.eliminar_item, name='eliminar_item'),
    path('comparar/', views.comparar_conteos, name='comparar_conteos'),
    path('comparacion/<str:conteos_ids>/', views.detalle_comparacion, name='detalle_comparacion'),
]

