from django.db import models


class Producto(models.Model):
    codigo_barras = models.CharField(max_length=100, unique=True, verbose_name="Código de Barras")
    codigo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Código")
    id_api = models.CharField(max_length=100, blank=True, null=True, unique=True, verbose_name="ID API", help_text="ID del producto en la API externa")
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Producto")
    marca = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marca")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    categoria = models.CharField(max_length=100, blank=True, null=True, verbose_name="Categoría")
    atributo = models.CharField(max_length=200, blank=True, null=True, verbose_name="Atributo")
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True, verbose_name="Imagen del Producto")
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Precio")
    unidad_medida = models.CharField(max_length=50, default="UN", verbose_name="Unidad de Medida")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Actualización")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    parejas_asignadas = models.ManyToManyField(
        'usuarios.ParejaConteo',
        related_name='productos_asignados',
        blank=True,
        verbose_name="Parejas Asignadas",
        help_text="Parejas de conteo asignadas para contar este producto"
    )

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.codigo_barras})"
    
    def get_stock_actual(self):
        """Calcula el stock actual desde el último conteo físico finalizado"""
        from conteo.models import ItemConteo, Conteo
        
        # Obtener el último conteo finalizado que contenga este producto
        ultimo_conteo = Conteo.objects.filter(
            estado='finalizado',
            items__producto=self
        ).order_by('-fecha_fin').first()
        
        if ultimo_conteo:
            item = ItemConteo.objects.filter(
                conteo=ultimo_conteo,
                producto=self
            ).first()
            if item:
                return item.cantidad
        
        return 0

