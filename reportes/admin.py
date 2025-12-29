from django.contrib import admin
from .models import Reporte


@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'usuario', 'fecha_creacion']
    list_filter = ['tipo', 'fecha_creacion']
    search_fields = ['nombre', 'usuario__username']
    readonly_fields = ['fecha_creacion']


