from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('registro/', views.registro, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('perfil/', views.perfil, name='perfil'),
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/<int:pk>/editar/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/<int:pk>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),
    path('parejas/', views.lista_parejas, name='lista_parejas'),
    path('parejas/crear/', views.crear_pareja, name='crear_pareja'),
    path('parejas/<int:pk>/editar/', views.editar_pareja, name='editar_pareja'),
    path('parejas/<int:pk>/desactivar/', views.desactivar_pareja, name='desactivar_pareja'),
    path('parejas/<int:pk>/eliminar/', views.eliminar_pareja, name='eliminar_pareja'),
    path('parejas/<int:pk>/usuarios/', views.obtener_usuarios_pareja, name='obtener_usuarios_pareja'),
]

