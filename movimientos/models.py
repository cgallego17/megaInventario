from django.db import models
from django.contrib.auth.models import User
from conteo.models import Conteo, ItemConteo
from productos.models import Producto


class MovimientoConteo(models.Model):
    TIPO_CHOICES = [
        ('agregar', 'Agregar'),
        ('modificar', 'Modificar'),
        ('eliminar', 'Eliminar'),
    ]
    
    conteo = models.ForeignKey(Conteo, on_delete=models.CASCADE, related_name='movimientos', verbose_name="Conteo")
    item_conteo = models.ForeignKey(ItemConteo, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos', verbose_name="Item de Conteo")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, verbose_name="Producto")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuario")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de Movimiento")
    cantidad_anterior = models.IntegerField(default=0, verbose_name="Cantidad Anterior")
    cantidad_nueva = models.IntegerField(default=0, verbose_name="Cantidad Nueva")
    cantidad_cambiada = models.IntegerField(default=0, verbose_name="Cantidad Cambiada")
    fecha_movimiento = models.DateTimeField(auto_now_add=True, verbose_name="Fecha del Movimiento")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    class Meta:
        verbose_name = "Movimiento de Conteo"
        verbose_name_plural = "Movimientos de Conteo"
        ordering = ['-fecha_movimiento']
        indexes = [
            models.Index(fields=['-fecha_movimiento']),
            models.Index(fields=['conteo', '-fecha_movimiento']),
            models.Index(fields=['usuario', '-fecha_movimiento']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.producto.nombre} ({self.cantidad_cambiada:+}) por {self.usuario.username}"
