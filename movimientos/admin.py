from django.contrib import admin
from .models import MovimientoConteo


@admin.register(MovimientoConteo)
class MovimientoConteoAdmin(admin.ModelAdmin):
    list_display = ['fecha_movimiento', 'conteo', 'producto', 'usuario', 'tipo', 'cantidad_anterior', 'cantidad_nueva', 'cantidad_cambiada']
    list_filter = ['tipo', 'fecha_movimiento', 'conteo', 'usuario']
    search_fields = ['producto__nombre', 'producto__codigo_barras', 'usuario__username', 'conteo__nombre']
    readonly_fields = ['fecha_movimiento']
    date_hierarchy = 'fecha_movimiento'
    ordering = ['-fecha_movimiento']
