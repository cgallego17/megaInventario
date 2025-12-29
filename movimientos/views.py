from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from .models import MovimientoConteo
from conteo.models import Conteo
from productos.models import Producto


@login_required
def lista_movimientos(request):
    """Lista todos los movimientos de conteo - Solo muestra conteos (agregar y modificar)"""
    # Por defecto, solo mostrar movimientos de conteo (agregar y modificar), excluir eliminaciones
    movimientos = MovimientoConteo.objects.filter(
        tipo__in=['agregar', 'modificar']
    ).select_related('conteo', 'producto', 'usuario', 'item_conteo', 'conteo__usuario_creador', 'conteo__usuario_modificador').prefetch_related('conteo__parejas')
    
    # Filtros
    conteo_id = request.GET.get('conteo')
    usuario_id = request.GET.get('usuario')
    producto_id = request.GET.get('producto')
    tipo = request.GET.get('tipo')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    busqueda = request.GET.get('busqueda', '').strip()
    mostrar_eliminados = request.GET.get('mostrar_eliminados', 'false') == 'true'
    
    # Si el usuario quiere ver eliminados, incluirlos
    if mostrar_eliminados:
        movimientos = MovimientoConteo.objects.all().select_related('conteo', 'producto', 'usuario', 'item_conteo', 'conteo__usuario_creador', 'conteo__usuario_modificador').prefetch_related('conteo__parejas')
    
    if conteo_id:
        movimientos = movimientos.filter(conteo_id=conteo_id)
    if usuario_id:
        movimientos = movimientos.filter(usuario_id=usuario_id)
    if producto_id:
        movimientos = movimientos.filter(producto_id=producto_id)
    if tipo:
        movimientos = movimientos.filter(tipo=tipo)
    if fecha_inicio:
        movimientos = movimientos.filter(fecha_movimiento__gte=fecha_inicio)
    if fecha_fin:
        movimientos = movimientos.filter(fecha_movimiento__lte=fecha_fin)
    if busqueda:
        movimientos = movimientos.filter(
            Q(producto__nombre__icontains=busqueda) |
            Q(producto__codigo_barras__icontains=busqueda) |
            Q(producto__codigo__icontains=busqueda) |
            Q(producto__atributo__icontains=busqueda) |
            Q(producto__descripcion__icontains=busqueda) |
            Q(usuario__username__icontains=busqueda) |
            Q(usuario__first_name__icontains=busqueda) |
            Q(usuario__last_name__icontains=busqueda) |
            Q(usuario__email__icontains=busqueda) |
            Q(conteo__nombre__icontains=busqueda) |
            Q(observaciones__icontains=busqueda)
        )
    
    # Estadísticas
    total_movimientos = movimientos.count()
    movimientos_agregar = movimientos.filter(tipo='agregar').count()
    movimientos_modificar = movimientos.filter(tipo='modificar').count()
    movimientos_eliminar = movimientos.filter(tipo='eliminar').count() if mostrar_eliminados else 0
    total_cantidad_contada = movimientos.aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
    
    # Paginación - mostrar más por página
    paginator = Paginator(movimientos, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opciones para filtros - sin límites
    conteos = Conteo.objects.all().order_by('-fecha_inicio')
    usuarios = User.objects.filter(movimientoconteo__isnull=False).distinct().order_by('username')
    productos = Producto.objects.filter(movimientoconteo__isnull=False).distinct().order_by('nombre')
    
    return render(request, 'movimientos/lista.html', {
        'page_obj': page_obj,
        'total_movimientos': total_movimientos,
        'movimientos_agregar': movimientos_agregar,
        'movimientos_modificar': movimientos_modificar,
        'movimientos_eliminar': movimientos_eliminar,
        'total_cantidad_contada': total_cantidad_contada,
        'conteos': conteos,
        'usuarios': usuarios,
        'productos': productos,
        'mostrar_eliminados': mostrar_eliminados,
        'filtros': {
            'conteo': conteo_id,
            'usuario': usuario_id,
            'producto': producto_id,
            'tipo': tipo,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'busqueda': busqueda,
        }
    })


@login_required
def movimientos_por_conteo(request, conteo_id):
    """Lista los movimientos de un conteo específico"""
    conteo = get_object_or_404(Conteo.objects.prefetch_related('parejas').select_related('usuario_creador', 'usuario_modificador'), pk=conteo_id)
    movimientos = MovimientoConteo.objects.filter(conteo=conteo).select_related('producto', 'usuario', 'item_conteo').order_by('-fecha_movimiento')
    
    # Estadísticas del conteo
    total_movimientos = movimientos.count()
    movimientos_por_usuario = movimientos.values('usuario__username').annotate(
        total=Count('id'),
        cantidad_total=Sum('cantidad_cambiada')
    ).order_by('-total')
    
    movimientos_por_producto = movimientos.values('producto__nombre', 'producto__codigo_barras').annotate(
        total=Count('id'),
        cantidad_total=Sum('cantidad_cambiada')
    ).order_by('-total')
    
    # Paginación - mostrar más por página
    paginator = Paginator(movimientos, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'movimientos/por_conteo.html', {
        'conteo': conteo,
        'page_obj': page_obj,
        'total_movimientos': total_movimientos,
        'movimientos_por_usuario': movimientos_por_usuario,
        'movimientos_por_producto': movimientos_por_producto,
    })


@login_required
def movimientos_por_usuario(request, usuario_id):
    """Lista los movimientos de un usuario específico"""
    usuario = get_object_or_404(User, pk=usuario_id)
    movimientos = MovimientoConteo.objects.filter(usuario=usuario).select_related('conteo', 'producto', 'item_conteo', 'conteo__usuario_creador', 'conteo__usuario_modificador').prefetch_related('conteo__parejas').order_by('-fecha_movimiento')
    
    # Estadísticas del usuario
    total_movimientos = movimientos.count()
    movimientos_por_conteo = movimientos.values('conteo__nombre', 'conteo__numero_conteo').annotate(
        total=Count('id'),
        cantidad_total=Sum('cantidad_cambiada')
    ).order_by('-total')
    
    movimientos_por_producto = movimientos.values('producto__nombre', 'producto__codigo_barras').annotate(
        total=Count('id'),
        cantidad_total=Sum('cantidad_cambiada')
    ).order_by('-total')
    
    # Paginación - mostrar más por página
    paginator = Paginator(movimientos, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'movimientos/por_usuario.html', {
        'usuario': usuario,
        'page_obj': page_obj,
        'total_movimientos': total_movimientos,
        'movimientos_por_conteo': movimientos_por_conteo,
        'movimientos_por_producto': movimientos_por_producto,
    })


@login_required
def resumen_movimientos(request):
    """Resumen general de movimientos"""
    movimientos = MovimientoConteo.objects.all()
    
    # Estadísticas generales
    total_movimientos = movimientos.count()
    total_usuarios = movimientos.values('usuario').distinct().count()
    total_productos = movimientos.values('producto').distinct().count()
    total_conteos = movimientos.values('conteo').distinct().count()
    
    # Movimientos por tipo
    por_tipo = movimientos.values('tipo').annotate(
        total=Count('id'),
        cantidad_total=Sum('cantidad_cambiada')
    ).order_by('tipo')
    
    # Top usuarios
    top_usuarios = movimientos.values('usuario__username').annotate(
        total=Count('id'),
        cantidad_total=Sum('cantidad_cambiada')
    ).order_by('-total')[:10]
    
    # Top productos
    top_productos = movimientos.values('producto__nombre', 'producto__codigo_barras').annotate(
        total=Count('id'),
        cantidad_total=Sum('cantidad_cambiada')
    ).order_by('-total')[:10]
    
    # Movimientos recientes - mostrar más
    movimientos_recientes = movimientos.select_related('conteo', 'producto', 'usuario', 'item_conteo', 'conteo__usuario_creador', 'conteo__usuario_modificador').prefetch_related('conteo__parejas').order_by('-fecha_movimiento')[:100]
    
    return render(request, 'movimientos/resumen.html', {
        'total_movimientos': total_movimientos,
        'total_usuarios': total_usuarios,
        'total_productos': total_productos,
        'total_conteos': total_conteos,
        'por_tipo': por_tipo,
        'top_usuarios': top_usuarios,
        'top_productos': top_productos,
        'movimientos_recientes': movimientos_recientes,
    })
