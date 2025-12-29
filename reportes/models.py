from django.db import models
from django.contrib.auth.models import User
from conteo.models import Conteo
from productos.models import Producto


class Reporte(models.Model):
    TIPO_CHOICES = [
        ('conteo', 'Reporte de Conteo'),
        ('inventario', 'Reporte de Inventario'),
        ('diferencias', 'Reporte de Diferencias'),
        ('productos', 'Reporte de Productos'),
    ]
    
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Reporte")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de Reporte")
    conteo = models.ForeignKey(Conteo, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Conteo")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuario")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    parametros = models.JSONField(default=dict, blank=True, verbose_name="Parámetros del Reporte")
    archivo = models.FileField(upload_to='reportes/', null=True, blank=True, verbose_name="Archivo Generado")
    
    class Meta:
        verbose_name = "Reporte"
        verbose_name_plural = "Reportes"
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.nombre} - {self.get_tipo_display()}"

