from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from datetime import datetime, timedelta
import csv
import json

from conteo.models import Conteo, ItemConteo
from productos.models import Producto
from .models import Reporte


@login_required
def menu_reportes(request):
    """Menú principal de reportes"""
    return render(request, 'reportes/menu.html')


@login_required
def reporte_conteo(request):
    """Reporte de conteos"""
    conteos = Conteo.objects.all()
    
    # Filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estado = request.GET.get('estado')
    
    if fecha_inicio:
        conteos = conteos.filter(fecha_inicio__gte=fecha_inicio)
    if fecha_fin:
        conteos = conteos.filter(fecha_inicio__lte=fecha_fin)
    if estado:
        conteos = conteos.filter(estado=estado)
    
    # Estadísticas
    total_conteos = conteos.count()
    conteos_finalizados = conteos.filter(estado='finalizado').count()
    total_items = ItemConteo.objects.filter(conteo__in=conteos).count()
    total_cantidad = ItemConteo.objects.filter(conteo__in=conteos).aggregate(Sum('cantidad'))['cantidad__sum'] or 0
    
    return render(request, 'reportes/reporte_conteo.html', {
        'conteos': conteos,
        'total_conteos': total_conteos,
        'conteos_finalizados': conteos_finalizados,
        'total_items': total_items,
        'total_cantidad': total_cantidad,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'estado': estado,
    })


@login_required
def reporte_inventario(request):
    """Reporte de inventario actual"""
    productos = Producto.objects.all()  # Todos los productos (activos e inactivos)
    
    # Filtros
    categoria = request.GET.get('categoria')
    busqueda = request.GET.get('busqueda')
    
    if categoria:
        productos = productos.filter(categoria=categoria)
    if busqueda:
        productos = productos.filter(
            Q(codigo_barras__icontains=busqueda) |
            Q(nombre__icontains=busqueda)
        )
    
    # Estadísticas
    total_productos = productos.count()
    total_stock = sum(p.get_stock_actual() for p in productos)
    valor_inventario = sum(float(p.precio) * p.get_stock_actual() for p in productos)
    categorias = Producto.objects.all().values_list('categoria', flat=True).distinct()
    
    # Agregar valor_total a cada producto para el template
    productos_list = []
    for p in productos[:100]:
        stock = p.get_stock_actual()
        productos_list.append({
            'producto': p,
            'stock_actual': stock,
            'valor_total': float(p.precio) * stock
        })
    
    return render(request, 'reportes/reporte_inventario.html', {
        'productos': productos_list,
        'total_productos': total_productos,
        'total_stock': total_stock,
        'valor_inventario': valor_inventario,
        'categorias': categorias,
        'categoria': categoria,
        'busqueda': busqueda,
    })


@login_required
def reporte_diferencias(request, conteo_id):
    """Reporte de diferencias entre inventario y conteo físico"""
    conteo = Conteo.objects.get(pk=conteo_id)
    items = conteo.items.all().select_related('producto')
    
    diferencias = []
    for item in items:
        stock_sistema = item.producto.get_stock_actual()
        diferencia = item.cantidad - stock_sistema
        diferencias.append({
            'producto': item.producto,
            'stock_sistema': stock_sistema,
            'conteo_fisico': item.cantidad,
            'diferencia': diferencia,
            'porcentaje': (diferencia / stock_sistema * 100) if stock_sistema > 0 else 0
        })
    
    # Ordenar por mayor diferencia
    diferencias.sort(key=lambda x: abs(x['diferencia']), reverse=True)
    
    return render(request, 'reportes/reporte_diferencias.html', {
        'conteo': conteo,
        'diferencias': diferencias,
    })


@login_required
def exportar_reporte_conteo(request):
    """Exporta reporte de conteo a CSV"""
    conteos = Conteo.objects.all()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="reporte_conteo_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Nombre', 'Número Conteo', 'Usuario 1', 'Usuario 2', 'Estado', 'Fecha Inicio', 'Fecha Fin', 'Total Items', 'Total Cantidad'])
    
    for conteo in conteos:
        total_items = conteo.items.count()
        total_cantidad = conteo.items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        writer.writerow([
            conteo.nombre,
            conteo.numero_conteo,
            conteo.usuario_1.username,
            conteo.usuario_2.username,
            conteo.get_estado_display(),
            conteo.fecha_inicio.strftime('%Y-%m-%d %H:%M:%S'),
            conteo.fecha_fin.strftime('%Y-%m-%d %H:%M:%S') if conteo.fecha_fin else '',
            total_items,
            total_cantidad
        ])
    
    return response


@login_required
def exportar_reporte_inventario(request):
    """Exporta reporte de inventario a CSV"""
    productos = Producto.objects.all()  # Todos los productos (activos e inactivos)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="reporte_inventario_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Código de Barras', 'Nombre', 'Categoría', 'Stock Actual', 'Precio', 'Valor Total'])
    
    for producto in productos:
        stock = producto.get_stock_actual()
        valor_total = producto.precio * stock
        writer.writerow([
            producto.codigo_barras,
            producto.nombre,
            producto.categoria or '',
            stock,
            producto.precio,
            valor_total
        ])
    
    return response

