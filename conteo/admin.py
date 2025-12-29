from django.contrib import admin
from .models import Conteo, ItemConteo


class ItemConteoInline(admin.TabularInline):
    model = ItemConteo
    extra = 0
    readonly_fields = ['fecha_conteo']


@admin.register(Conteo)
class ConteoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'numero_conteo', 'usuario_1', 'usuario_2', 'estado', 'usuario_creador', 'fecha_creacion', 'usuario_modificador', 'fecha_modificacion', 'fecha_inicio', 'fecha_fin']
    list_filter = ['estado', 'numero_conteo', 'fecha_inicio', 'fecha_creacion']
    search_fields = ['nombre', 'usuario_1__username', 'usuario_2__username', 'usuario_creador__username', 'usuario_modificador__username']
    readonly_fields = ['fecha_inicio', 'fecha_creacion', 'fecha_modificacion']
    inlines = [ItemConteoInline]


@admin.register(ItemConteo)
class ItemConteoAdmin(admin.ModelAdmin):
    list_display = ['producto', 'conteo', 'cantidad', 'usuario_conteo', 'fecha_conteo']
    list_filter = ['conteo', 'fecha_conteo']
    search_fields = ['producto__nombre', 'producto__codigo_barras']
    readonly_fields = ['fecha_conteo']

