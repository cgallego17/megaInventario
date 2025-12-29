from django.contrib import admin
from .models import ComparativoInventario, InventarioSistema, ItemComparativo


class InventarioSistemaInline(admin.TabularInline):
    model = InventarioSistema
    extra = 0


class ItemComparativoInline(admin.TabularInline):
    model = ItemComparativo
    extra = 0
    readonly_fields = ['diferencia_sistema1', 'diferencia_sistema2']


@admin.register(ComparativoInventario)
class ComparativoInventarioAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'nombre_sistema1', 'nombre_sistema2', 'conteo', 'usuario', 'fecha_creacion']
    list_filter = ['fecha_creacion']
    search_fields = ['nombre', 'usuario__username']
    readonly_fields = ['fecha_creacion']
    inlines = [InventarioSistemaInline, ItemComparativoInline]


@admin.register(InventarioSistema)
class InventarioSistemaAdmin(admin.ModelAdmin):
    list_display = ['comparativo', 'sistema', 'fecha_carga']
    list_filter = ['sistema', 'fecha_carga']


@admin.register(ItemComparativo)
class ItemComparativoAdmin(admin.ModelAdmin):
    list_display = ['producto', 'comparativo', 'cantidad_sistema1', 'cantidad_sistema2', 'cantidad_fisico', 'diferencia_sistema1', 'diferencia_sistema2']
    list_filter = ['comparativo']
    search_fields = ['producto__nombre', 'producto__codigo_barras']

