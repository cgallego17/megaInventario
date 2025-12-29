from django.db import models
from django.contrib.auth.models import User


class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Usuario")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    departamento = models.CharField(max_length=100, blank=True, null=True, verbose_name="Departamento")
    pin = models.CharField(max_length=4, blank=True, null=True, verbose_name="PIN de Acceso", help_text="PIN de 4 dígitos para acceso al sistema")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
    
    def __str__(self):
        return f"Perfil de {self.user.username}"


class ParejaConteo(models.Model):
    COLORES_DISPONIBLES = [
        ('primary', 'Azul'),
        ('success', 'Verde'),
        ('danger', 'Rojo'),
        ('warning', 'Amarillo'),
        ('info', 'Cian'),
        ('secondary', 'Gris'),
        ('dark', 'Negro'),
        ('light', 'Claro'),
    ]
    
    usuario_1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parejas_como_usuario1', verbose_name="Usuario 1")
    usuario_2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='parejas_como_usuario2', verbose_name="Usuario 2")
    activa = models.BooleanField(default=True, verbose_name="Pareja Activa")
    color = models.CharField(max_length=20, choices=COLORES_DISPONIBLES, default='primary', verbose_name="Color")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    class Meta:
        verbose_name = "Pareja de Conteo"
        verbose_name_plural = "Parejas de Conteo"
        unique_together = [['usuario_1', 'usuario_2']]
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.usuario_1.username} & {self.usuario_2.username}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.usuario_1 == self.usuario_2:
            raise ValidationError("Un usuario no puede ser pareja de sí mismo")

