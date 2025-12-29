from django.contrib import admin
from .models import Producto


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['codigo_barras', 'codigo', 'id_api', 'nombre', 'marca', 'categoria', 'precio', 'activo']
    list_filter = ['categoria', 'marca', 'activo', 'fecha_creacion']
    search_fields = ['codigo_barras', 'codigo', 'id_api', 'nombre', 'marca', 'descripcion']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']

