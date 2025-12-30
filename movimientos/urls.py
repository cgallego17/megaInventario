from django.urls import path
from . import views

app_name = 'movimientos'

urlpatterns = [
    path('', views.lista_movimientos, name='lista'),
    path('resumen/', views.resumen_movimientos, name='resumen'),
    path('conteo/<int:conteo_id>/', views.movimientos_por_conteo, name='por_conteo'),
    path('usuario/<int:usuario_id>/', views.movimientos_por_usuario, name='por_usuario'),
]





