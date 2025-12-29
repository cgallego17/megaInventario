from django.db import models
from django.contrib.auth.models import User
from conteo.models import Conteo
from productos.models import Producto


class ComparativoInventario(models.Model):
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Comparativo")
    nombre_sistema1 = models.CharField(max_length=100, default="Sistema 1", verbose_name="Nombre Sistema 1")
    nombre_sistema2 = models.CharField(max_length=100, default="Sistema 2", verbose_name="Nombre Sistema 2")
    conteo = models.ForeignKey(Conteo, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Conteo Físico")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuario")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    class Meta:
        verbose_name = "Comparativo de Inventario"
        verbose_name_plural = "Comparativos de Inventario"
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.nombre} - {self.fecha_creacion.strftime('%Y-%m-%d')}"


class InventarioSistema(models.Model):
    SISTEMA_CHOICES = [
        ('sistema1', 'Sistema 1'),
        ('sistema2', 'Sistema 2'),
    ]
    
    comparativo = models.ForeignKey(ComparativoInventario, on_delete=models.CASCADE, related_name='inventarios', verbose_name="Comparativo")
    sistema = models.CharField(max_length=20, choices=SISTEMA_CHOICES, verbose_name="Sistema")
    archivo = models.FileField(upload_to='inventarios_sistema/', verbose_name="Archivo de Inventario")
    fecha_carga = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Carga")
    
    class Meta:
        verbose_name = "Inventario de Sistema"
        verbose_name_plural = "Inventarios de Sistema"
        unique_together = [['comparativo', 'sistema']]
    
    def __str__(self):
        return f"{self.get_sistema_display()} - {self.comparativo.nombre}"


class ItemComparativo(models.Model):
    comparativo = models.ForeignKey(ComparativoInventario, on_delete=models.CASCADE, related_name='items', verbose_name="Comparativo")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, verbose_name="Producto")
    cantidad_sistema1 = models.IntegerField(default=0, verbose_name="Cantidad Sistema 1")
    cantidad_sistema2 = models.IntegerField(default=0, verbose_name="Cantidad Sistema 2")
    cantidad_fisico = models.IntegerField(default=0, verbose_name="Cantidad Físico")
    diferencia_sistema1 = models.IntegerField(default=0, verbose_name="Diferencia Sistema 1")
    diferencia_sistema2 = models.IntegerField(default=0, verbose_name="Diferencia Sistema 2")
    
    class Meta:
        verbose_name = "Item Comparativo"
        verbose_name_plural = "Items Comparativos"
        unique_together = [['comparativo', 'producto']]
    
    def __str__(self):
        return f"{self.producto.nombre} - Comparativo {self.comparativo.id}"
    
    def calcular_diferencias(self):
        """Calcula las diferencias entre sistemas y conteo físico"""
        self.diferencia_sistema1 = self.cantidad_fisico - self.cantidad_sistema1
        self.diferencia_sistema2 = self.cantidad_fisico - self.cantidad_sistema2
        self.save()
    
    def get_precio(self):
        """Retorna el precio del producto"""
        return float(self.producto.precio)
    
    def get_valor_sistema1(self):
        """Calcula el valor total del Sistema 1 (precio * cantidad)"""
        return float(self.producto.precio) * self.cantidad_sistema1
    
    def get_valor_sistema2(self):
        """Calcula el valor total del Sistema 2 (precio * cantidad)"""
        return float(self.producto.precio) * self.cantidad_sistema2
    
    def get_valor_fisico(self):
        """Calcula el valor total del conteo físico (precio * cantidad)"""
        return float(self.producto.precio) * self.cantidad_fisico
    
    def get_diferencia_valor_sistema1(self):
        """Calcula la diferencia de valor entre físico y Sistema 1"""
        return self.get_valor_fisico() - self.get_valor_sistema1()
    
    def get_diferencia_valor_sistema2(self):
        """Calcula la diferencia de valor entre físico y Sistema 2"""
        return self.get_valor_fisico() - self.get_valor_sistema2()

