from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from conteo.models import Conteo, ItemConteo
from productos.models import Producto
from movimientos.models import MovimientoConteo
from usuarios.models import ParejaConteo
from django.contrib.auth.models import User


@login_required
def dashboard(request):
    """Dashboard principal con estadísticas, progreso y alertas"""
    
    # Estadísticas generales
    total_productos = Producto.objects.count()  # Todos los productos (activos e inactivos)
    total_conteos = Conteo.objects.count()
    conteos_en_proceso = Conteo.objects.filter(estado='en_proceso').count()
    conteos_finalizados = Conteo.objects.filter(estado='finalizado').count()
    total_movimientos = MovimientoConteo.objects.count()
    total_usuarios = User.objects.filter(is_active=True).count()
    total_parejas = ParejaConteo.objects.filter(activa=True).count()
    
    # Progreso de conteos en proceso
    conteos_activos = Conteo.objects.filter(estado='en_proceso').prefetch_related('items')
    total_productos_sistema = Producto.objects.count()  # Todos los productos (activos e inactivos)
    progreso_conteos = []
    
    for conteo in conteos_activos:
        # Verificar si el conteo fue creado desde un comparativo
        productos_del_conteo = None
        productos_ids_conteo = None
        if conteo.observaciones and 'Productos:' in conteo.observaciones:
            try:
                productos_str = conteo.observaciones.split('Productos:')[1].strip()
                productos_ids_conteo = [int(pid.strip()) for pid in productos_str.split(',') if pid.strip().isdigit()]
                if productos_ids_conteo:
                    productos_del_conteo = Producto.objects.filter(id__in=productos_ids_conteo)
            except (ValueError, AttributeError):
                pass
        
        # Determinar el total de productos para el progreso
        if productos_del_conteo is not None:
            # Si el conteo tiene productos específicos, usar solo esos
            total_productos_conteo = len(productos_ids_conteo)
            # Contar solo items que corresponden a productos del conteo
            items_contados = conteo.items.filter(producto_id__in=productos_ids_conteo).count()
        else:
            # Lógica normal: todos los productos del sistema
            total_productos_conteo = total_productos_sistema
            items_contados = conteo.items.count()
        
        # Calcular porcentaje
        porcentaje = (items_contados / total_productos_conteo * 100) if total_productos_conteo > 0 else 0
        
        # Calcular total de cantidad (todos los items del conteo)
        total_cantidad = conteo.items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        
        # Items con cantidad > 0
        if productos_del_conteo is not None:
            items_con_cantidad = conteo.items.filter(producto_id__in=productos_ids_conteo, cantidad__gt=0).count()
        else:
            items_con_cantidad = conteo.items.filter(cantidad__gt=0).count()
        
        items_con_cero = items_contados - items_con_cantidad
        
        progreso_conteos.append({
            'conteo': conteo,
            'items_contados': items_contados,
            'total_productos_sistema': total_productos_conteo,  # Usar total del conteo o del sistema
            'items_con_cantidad': items_con_cantidad,  # Para mostrar cuántos tienen cantidad > 0
            'items_con_cero': items_con_cero,  # Items con cantidad 0
            'porcentaje': round(porcentaje, 1),
            'total_cantidad': total_cantidad,
        })
    
    # Ordenar por porcentaje descendente
    progreso_conteos.sort(key=lambda x: x['porcentaje'], reverse=True)
    
    # Alertas
    alertas = []
    
    # Conteos en proceso sin actividad reciente (más de 24 horas)
    hace_24_horas = timezone.now() - timedelta(hours=24)
    conteos_sin_actividad = Conteo.objects.filter(
        estado='en_proceso',
        fecha_modificacion__lt=hace_24_horas
    )
    if conteos_sin_actividad.exists():
        alertas.append({
            'tipo': 'warning',
            'icono': 'clock-history',
            'titulo': 'Conteos sin actividad reciente',
            'mensaje': f'{conteos_sin_actividad.count()} conteo(s) en proceso sin actividad en las últimas 24 horas',
            'link': '/conteo/',
            'link_texto': 'Ver conteos'
        })
    
    # Productos sin stock (calculado desde conteos) - todos los productos
    productos_sin_stock = []
    for producto in Producto.objects.all()[:10]:
        if producto.get_stock_actual() == 0:
            productos_sin_stock.append(producto)
    
    if productos_sin_stock:
        alertas.append({
            'tipo': 'danger',
            'icono': 'exclamation-triangle',
            'titulo': 'Productos sin stock',
            'mensaje': f'{len(productos_sin_stock)} producto(s) tienen stock en 0',
            'link': '/productos/?stock=0',
            'link_texto': 'Ver productos'
        })
    
    # Conteos sin parejas asignadas
    conteos_sin_parejas = Conteo.objects.filter(
        estado='en_proceso',
        parejas__isnull=True
    ).exclude(usuario_1__isnull=True, usuario_2__isnull=True).distinct()
    if conteos_sin_parejas.exists():
        conteos_sin_parejas_count = conteos_sin_parejas.count()
        if conteos_sin_parejas_count > 0:
            alertas.append({
                'tipo': 'info',
                'icono': 'people',
                'titulo': 'Conteos sin parejas asignadas',
                'mensaje': f'{conteos_sin_parejas_count} conteo(s) en proceso no tienen parejas asignadas',
                'link': '/conteo/',
                'link_texto': 'Ver conteos'
            })
    
    # Movimientos recientes (últimas 24 horas)
    movimientos_recientes = MovimientoConteo.objects.filter(
        fecha_movimiento__gte=hace_24_horas
    ).select_related('conteo', 'producto', 'usuario').order_by('-fecha_movimiento')[:10]
    
    # Actividades recientes
    actividades = []
    
    # Conteos creados recientemente
    conteos_creados = Conteo.objects.filter(
        fecha_creacion__gte=hace_24_horas
    ).select_related('usuario_creador').order_by('-fecha_creacion')[:5]
    for conteo in conteos_creados:
        actividades.append({
            'tipo': 'conteo_creado',
            'icono': 'plus-circle',
            'color': 'success',
            'mensaje': f'Conteo "{conteo.nombre}" creado por {conteo.usuario_creador.username if conteo.usuario_creador else "Sistema"}',
            'fecha': conteo.fecha_creacion,
            'link': f'/conteo/{conteo.id}/'
        })
    
    # Conteos finalizados recientemente
    conteos_finalizados_recientes = Conteo.objects.filter(
        estado='finalizado',
        fecha_fin__gte=hace_24_horas
    ).select_related('usuario_modificador').order_by('-fecha_fin')[:5]
    for conteo in conteos_finalizados_recientes:
        actividades.append({
            'tipo': 'conteo_finalizado',
            'icono': 'check-circle',
            'color': 'primary',
            'mensaje': f'Conteo "{conteo.nombre}" finalizado por {conteo.usuario_modificador.username if conteo.usuario_modificador else "Sistema"}',
            'fecha': conteo.fecha_fin,
            'link': f'/conteo/{conteo.id}/'
        })
    
    # Movimientos importantes (agregar/eliminar)
    movimientos_importantes = MovimientoConteo.objects.filter(
        fecha_movimiento__gte=hace_24_horas,
        tipo__in=['agregar', 'eliminar']
    ).select_related('conteo', 'producto', 'usuario').order_by('-fecha_movimiento')[:5]
    for movimiento in movimientos_importantes:
        tipo_texto = 'agregado' if movimiento.tipo == 'agregar' else 'eliminado'
        actividades.append({
            'tipo': 'movimiento',
            'icono': 'activity',
            'color': 'info',
            'mensaje': f'Producto "{movimiento.producto.nombre}" {tipo_texto} en conteo "{movimiento.conteo.nombre}" por {movimiento.usuario.username}',
            'fecha': movimiento.fecha_movimiento,
            'link': f'/movimientos/conteo/{movimiento.conteo.id}/'
        })
    
    # Ordenar actividades por fecha
    actividades.sort(key=lambda x: x['fecha'], reverse=True)
    actividades = actividades[:10]  # Limitar a 10 más recientes
    
    # Estadísticas por conteo
    conteos_por_numero = {}
    for num in [1, 2, 3]:
        conteos_num = Conteo.objects.filter(numero_conteo=num)
        conteos_por_numero[num] = {
            'total': conteos_num.count(),
            'en_proceso': conteos_num.filter(estado='en_proceso').count(),
            'finalizados': conteos_num.filter(estado='finalizado').count(),
        }
    
    # Top productos más contados
    top_productos = ItemConteo.objects.values(
        'producto__nombre', 'producto__codigo_barras'
    ).annotate(
        total_contado=Sum('cantidad'),
        veces_contado=Count('id')
    ).order_by('-total_contado')[:5]
    
    # Top usuarios más activos (últimas 24 horas)
    top_usuarios = MovimientoConteo.objects.filter(
        fecha_movimiento__gte=hace_24_horas
    ).values('usuario__username').annotate(
        total_movimientos=Count('id')
    ).order_by('-total_movimientos')[:5]
    
    return render(request, 'dashboard.html', {
        'total_productos': total_productos,
        'total_conteos': total_conteos,
        'conteos_en_proceso': conteos_en_proceso,
        'conteos_finalizados': conteos_finalizados,
        'total_movimientos': total_movimientos,
        'total_usuarios': total_usuarios,
        'total_parejas': total_parejas,
        'progreso_conteos': progreso_conteos,
        'alertas': alertas,
        'actividades': actividades,
        'conteos_por_numero': conteos_por_numero,
        'top_productos': top_productos,
        'top_usuarios': top_usuarios,
        'movimientos_recientes': movimientos_recientes,
    })

