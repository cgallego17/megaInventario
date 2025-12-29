from django.db import models
from django.contrib.auth.models import User
from productos.models import Producto
from django.core.validators import MinValueValidator


class Conteo(models.Model):
    ESTADO_CHOICES = [
        ('en_proceso', 'En Proceso'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]
    
    NUMERO_CONTEO_CHOICES = [
        (1, 'Conteo 1'),
        (2, 'Conteo 2'),
        (3, 'Conteo 3'),
    ]
    
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Conteo")
    numero_conteo = models.IntegerField(choices=NUMERO_CONTEO_CHOICES, default=1, verbose_name="Número de Conteo")
    usuario_1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conteos_usuario1', verbose_name="Usuario 1", null=True, blank=True)
    usuario_2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conteos_usuario2', verbose_name="Usuario 2", null=True, blank=True)
    parejas = models.ManyToManyField('usuarios.ParejaConteo', related_name='conteos', verbose_name="Parejas", blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='en_proceso', verbose_name="Estado")
    fecha_inicio = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Inicio")
    fecha_fin = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Fin")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    # Campos de auditoría
    usuario_creador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='conteos_creados', verbose_name="Usuario Creador")
    usuario_modificador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='conteos_modificados', verbose_name="Usuario Modificador")
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name="Fecha de Creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="Fecha de Modificación")
    
    class Meta:
        verbose_name = "Conteo"
        verbose_name_plural = "Conteos"
        ordering = ['numero_conteo', '-fecha_inicio']
        unique_together = [['nombre', 'numero_conteo']]
        db_table = 'conteo_sesionconteo'  # Mantener el nombre de tabla para compatibilidad
    
    def __str__(self):
        parejas_str = ", ".join([f"{p.usuario_1.username} & {p.usuario_2.username}" for p in self.parejas.all()])
        if parejas_str:
            return f"{self.nombre} - Conteo {self.numero_conteo} ({parejas_str})"
        elif self.usuario_1 and self.usuario_2:
            return f"{self.nombre} - Conteo {self.numero_conteo} ({self.usuario_1.username} & {self.usuario_2.username})"
        else:
            return f"{self.nombre} - Conteo {self.numero_conteo}"
    
    def get_usuarios(self):
        """Retorna todos los usuarios únicos del conteo (de parejas y usuario_1/usuario_2)"""
        usuarios = set()
        for pareja in self.parejas.all():
            usuarios.add(pareja.usuario_1)
            usuarios.add(pareja.usuario_2)
        if self.usuario_1:
            usuarios.add(self.usuario_1)
        if self.usuario_2:
            usuarios.add(self.usuario_2)
        return list(usuarios)


class ItemConteo(models.Model):
    conteo = models.ForeignKey(Conteo, on_delete=models.CASCADE, related_name='items', verbose_name="Conteo")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, verbose_name="Producto")
    cantidad = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Cantidad Contada")
    fecha_conteo = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Conteo")
    usuario_conteo = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Usuario que Contó")
    
    class Meta:
        verbose_name = "Item de Conteo"
        verbose_name_plural = "Items de Conteo"
        unique_together = [['conteo', 'producto']]
        ordering = ['-fecha_conteo']
    
    def __str__(self):
        return f"{self.producto.nombre} - {self.cantidad} unidades"

