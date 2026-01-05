from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum, Count, Q
from .models import Conteo, ItemConteo
from .forms import ConteoForm, ItemConteoForm, CompararConteosForm
from productos.models import Producto
from movimientos.models import MovimientoConteo
from usuarios.models import ParejaConteo


@login_required
def lista_conteos(request):
    """Lista todos los conteos organizados por número de conteo"""
    from django.db.models import Sum
    
    numero_conteo = request.GET.get('numero_conteo', '')
    
    conteos = Conteo.objects.all().prefetch_related('items', 'parejas')
    
    if numero_conteo:
        try:
            conteos = conteos.filter(numero_conteo=int(numero_conteo))
        except ValueError:
            pass
    
    # Organizar por número de conteo con estadísticas
    conteos_por_numero = {}
    for num in [1, 2, 3]:
        conteos_num = list(conteos.filter(numero_conteo=num))
        # Agregar estadísticas a cada conteo
        for conteo in conteos_num:
            conteo.total_items = conteo.items.count()
            conteo.total_cantidad = conteo.items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            
            # Para conteos en proceso, calcular productos pendientes
            if conteo.estado == 'en_proceso':
                # Verificar si el conteo fue creado desde un comparativo
                productos_ids_conteo = None
                if conteo.observaciones and 'Productos:' in conteo.observaciones:
                    try:
                        productos_str = conteo.observaciones.split('Productos:')[1].strip()
                        productos_ids_conteo = [int(pid.strip()) for pid in productos_str.split(',') if pid.strip().isdigit()]
                    except (ValueError, AttributeError):
                        pass
                
                # Obtener productos asignados
                if productos_ids_conteo:
                    # Si tiene productos específicos del conteo
                    productos_asignados = Producto.objects.filter(id__in=productos_ids_conteo)
                else:
                    # Obtener productos asignados a las parejas del conteo
                    parejas_conteo = conteo.parejas.all()
                    if parejas_conteo.exists():
                        productos_asignados = Producto.objects.filter(
                            parejas_asignadas__in=parejas_conteo
                        ).distinct()
                    else:
                        # Si no hay parejas asignadas, no hay productos asignados
                        productos_asignados = Producto.objects.none()
                
                # Obtener productos ya contados en el conteo (por cualquier usuario)
                productos_contados_ids = set(conteo.items.values_list('producto_id', flat=True))
                
                # Si el conteo tiene productos específicos, filtrar solo los items de esos productos
                if productos_ids_conteo:
                    productos_contados_ids = productos_contados_ids.intersection(set(productos_ids_conteo))
                
                # Calcular productos pendientes
                if productos_contados_ids:
                    productos_pendientes = productos_asignados.exclude(id__in=productos_contados_ids)
                else:
                    productos_pendientes = productos_asignados
                
                conteo.productos_pendientes = productos_pendientes.count()
            else:
                conteo.productos_pendientes = None
        conteos_por_numero[num] = conteos_num
    
    # Agregar estadísticas a todos los conteos para la vista general
    for conteo in conteos:
        conteo.total_items = conteo.items.count()
        conteo.total_cantidad = conteo.items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        
        # Para conteos en proceso, calcular productos pendientes
        if conteo.estado == 'en_proceso':
            # Verificar si el conteo fue creado desde un comparativo
            productos_ids_conteo = None
            if conteo.observaciones and 'Productos:' in conteo.observaciones:
                try:
                    productos_str = conteo.observaciones.split('Productos:')[1].strip()
                    productos_ids_conteo = [int(pid.strip()) for pid in productos_str.split(',') if pid.strip().isdigit()]
                except (ValueError, AttributeError):
                    pass
            
            # Obtener productos asignados
            if productos_ids_conteo:
                # Si tiene productos específicos del conteo
                productos_asignados = Producto.objects.filter(id__in=productos_ids_conteo)
            else:
                # Obtener productos asignados a las parejas del conteo
                parejas_conteo = conteo.parejas.all()
                if parejas_conteo.exists():
                    productos_asignados = Producto.objects.filter(
                        parejas_asignadas__in=parejas_conteo
                    ).distinct()
                else:
                    # Si no hay parejas asignadas, no hay productos asignados
                    productos_asignados = Producto.objects.none()
            
            # Obtener productos ya contados en el conteo (por cualquier usuario)
            productos_contados_ids = set(conteo.items.values_list('producto_id', flat=True))
            
            # Si el conteo tiene productos específicos, filtrar solo los items de esos productos
            if productos_ids_conteo:
                productos_contados_ids = productos_contados_ids.intersection(set(productos_ids_conteo))
            
            # Calcular productos pendientes
            if productos_contados_ids:
                productos_pendientes = productos_asignados.exclude(id__in=productos_contados_ids)
            else:
                productos_pendientes = productos_asignados
            
            conteo.productos_pendientes = productos_pendientes.count()
        else:
            conteo.productos_pendientes = None
    
    return render(request, 'conteo/lista_conteos.html', {
        'conteos': conteos,
        'conteos_por_numero': conteos_por_numero,
        'numero_conteo_filtro': numero_conteo,
    })


@login_required
def crear_conteo(request):
    """Crea un nuevo conteo"""
    if request.method == 'POST':
        form = ConteoForm(request.POST)
        if form.is_valid():
            conteo = form.save(commit=False)
            conteo.usuario_creador = request.user
            conteo.usuario_modificador = request.user
            conteo.save()
            form.save_m2m()  # Guardar las parejas (ManyToMany)
            messages.success(request, 'Conteo creado exitosamente.')
            return redirect('conteo:detalle_conteo', pk=conteo.pk)
    else:
        form = ConteoForm()
    
    return render(request, 'conteo/form_conteo.html', {'form': form, 'titulo': 'Crear Conteo'})


@login_required
def detalle_conteo(request, pk):
    """Detalle de conteo con scanner"""
    conteo = get_object_or_404(Conteo, pk=pk)
    
    # Obtener parejas del usuario (donde es usuario_1 o usuario_2)
    parejas_usuario = ParejaConteo.objects.filter(
        Q(usuario_1=request.user) | Q(usuario_2=request.user),
        activa=True
    )
    
    # Obtener todos los usuarios de las parejas del usuario actual
    usuarios_pareja = set()
    usuarios_pareja.add(request.user)  # Incluir el usuario actual
    for pareja in parejas_usuario:
        usuarios_pareja.add(pareja.usuario_1)
        usuarios_pareja.add(pareja.usuario_2)
    
    # Verificar si el usuario es admin/superuser
    es_admin = request.user.is_superuser or request.user.is_staff
    
    # Si es admin, puede ver todos los items; si no, solo los de su pareja
    if es_admin:
        # Para admin: obtener todos los items del conteo
        items_todos_qs = conteo.items.all().select_related('producto', 'usuario_conteo')
        items_pareja_qs = conteo.items.filter(usuario_conteo__in=usuarios_pareja).select_related('producto', 'usuario_conteo')
        
        # Obtener IDs de items de la pareja para filtrar
        items_pareja_ids = set(items_pareja_qs.values_list('id', flat=True))
        
        # Items de otros usuarios (no de la pareja)
        items_otros = [item for item in items_todos_qs if item.id not in items_pareja_ids]
        
        items = items_pareja_qs  # Por defecto mostrar solo los de la pareja
        items_todos = items_todos_qs
    else:
        # Para usuario normal: solo items de su pareja
        items_pareja_qs = conteo.items.filter(usuario_conteo__in=usuarios_pareja).select_related('producto', 'usuario_conteo')
        items = items_pareja_qs
        items_todos = None
        items_otros = []
    
    # Verificar si el conteo fue creado desde un comparativo
    # Si tiene "Productos:" en las observaciones, usar solo esos productos
    productos_del_conteo = None
    productos_ids_conteo = None
    if conteo.observaciones and 'Productos:' in conteo.observaciones:
        try:
            productos_str = conteo.observaciones.split('Productos:')[1].strip()
            productos_ids_conteo = [int(pid.strip()) for pid in productos_str.split(',') if pid.strip().isdigit()]
            if productos_ids_conteo:
                productos_del_conteo = Producto.objects.filter(id__in=productos_ids_conteo)
        except (ValueError, AttributeError):
            productos_ids_conteo = None
    
    # Obtener productos asignados a las parejas del usuario
    productos_asignados = Producto.objects.filter(
        parejas_asignadas__in=parejas_usuario
    ).distinct()
    
    # Si el conteo tiene productos específicos (creado desde comparativo), usar esos
    if productos_del_conteo is not None:
        productos_asignados = productos_del_conteo
        tiene_productos_asignados = True
    else:
        # Si no hay productos asignados, usar todos los productos para estadísticas
        tiene_productos_asignados = productos_asignados.exists()
        if not tiene_productos_asignados:
            productos_asignados = Producto.objects.all()
    
    # Estadísticas (solo de los items contados por la pareja)
    if es_admin:
        total_items = items_pareja_qs.count()
        total_cantidad = items_pareja_qs.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        total_items_todos = items_todos.count()
        total_cantidad_todos = items_todos.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
    else:
        total_items = items.count()
        total_cantidad = items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        total_items_todos = total_items
        total_cantidad_todos = total_cantidad
    
    # Total de productos asignados al usuario (o del conteo si fue creado desde comparativo)
    total_productos_asignados = productos_asignados.count()
    
    # Calcular porcentaje de productos contados
    # Si el conteo tiene productos específicos, solo contar items de esos productos
    if productos_del_conteo is not None:
        # Contar solo items que corresponden a productos del conteo
        items_del_conteo = items.filter(producto_id__in=productos_ids_conteo)
        total_items_para_progreso = items_del_conteo.count()
        porcentaje_contado = (total_items_para_progreso / total_productos_asignados * 100) if total_productos_asignados > 0 else 0
    else:
        # Lógica normal: porcentaje basado en items contados vs productos asignados
        porcentaje_contado = (total_items / total_productos_asignados * 100) if total_productos_asignados > 0 else 0
    
    # Obtener IDs de productos ya contados en ESTE conteo (por CUALQUIER usuario)
    # Esto asegura que si un producto fue contado por cualquier usuario, no aparezca en pendientes
    productos_contados_ids_todos = set(conteo.items.values_list('producto_id', flat=True))
    
    # Si el conteo tiene productos específicos, filtrar solo los items de esos productos
    if productos_del_conteo is not None:
        productos_contados_ids_todos = productos_contados_ids_todos.intersection(set(productos_ids_conteo))
    
    # Obtener IDs de productos contados por la pareja (para mostrar en "contados")
    if es_admin:
        productos_contados_ids_pareja = set(items_pareja_qs.values_list('producto_id', flat=True))
    else:
        productos_contados_ids_pareja = set(items.values_list('producto_id', flat=True))
    
    # Si el conteo tiene productos específicos, filtrar solo los items de esos productos
    if productos_del_conteo is not None:
        productos_contados_ids_pareja = productos_contados_ids_pareja.intersection(set(productos_ids_conteo))
    
    # Separar productos en contados y no contados
    # Contados: solo los contados por la pareja (para mostrar en la tab de contados)
    # No contados: productos que NO han sido contados por NINGÚN usuario en el conteo
    if productos_contados_ids_pareja:
        productos_contados = productos_asignados.filter(id__in=productos_contados_ids_pareja).order_by('marca', 'nombre')
    else:
        productos_contados = productos_asignados.none()
    
    # Productos pendientes: excluir TODOS los productos que ya fueron contados en el conteo
    if productos_contados_ids_todos:
        productos_no_contados = productos_asignados.exclude(id__in=productos_contados_ids_todos).order_by('marca', 'nombre')
    else:
        # Si no hay productos contados en el conteo, todos los productos asignados están pendientes
        productos_no_contados = productos_asignados.order_by('marca', 'nombre')
    
    return render(request, 'conteo/detalle_conteo.html', {
        'conteo': conteo,
        'items': items,  # Items de la pareja por defecto
        'items_otros': items_otros if es_admin else [],  # Items de otros usuarios para admin
        'total_items': total_items,
        'total_cantidad': total_cantidad,
        'total_items_todos': total_items_todos if es_admin else None,
        'total_cantidad_todos': total_cantidad_todos if es_admin else None,
        'total_productos': total_productos_asignados,
        'porcentaje_contado': porcentaje_contado,
        'parejas_usuario': parejas_usuario,
        'productos_asignados': productos_asignados,
        'productos_contados': productos_contados,
        'productos_no_contados': productos_no_contados,
        'productos_contados_ids': productos_contados_ids_pareja,
        'productos_contados_ids_todos': productos_contados_ids_todos,
        'es_admin': es_admin,
    })


@login_required
def agregar_item(request, conteo_id):
    """Agrega o actualiza un item en el conteo"""
    conteo = get_object_or_404(Conteo, pk=conteo_id)
    
    if request.method == 'POST':
        busqueda = request.POST.get('busqueda', '').strip()
        producto_id = request.POST.get('producto_id', '')
        cantidad = int(request.POST.get('cantidad', 0))
        if cantidad < 0:
            return JsonResponse({'success': False, 'error': 'La cantidad no puede ser negativa'})
        
        if not busqueda and not producto_id:
            return JsonResponse({'success': False, 'error': 'Búsqueda o ID de producto requerido'})
        
        try:
            # Obtener parejas del usuario (donde es usuario_1 o usuario_2)
            parejas_usuario = ParejaConteo.objects.filter(
                Q(usuario_1=request.user) | Q(usuario_2=request.user),
                activa=True
            )
            
            # Si tiene productos asignados, verificar que esté asignado; si no, permitir cualquier producto
            if parejas_usuario.exists():
                productos_asignados = Producto.objects.filter(
                    parejas_asignadas__in=parejas_usuario
                ).distinct()
                tiene_productos_asignados = productos_asignados.exists()
            else:
                tiene_productos_asignados = False
            
            # Si se proporciona un ID
            if producto_id:
                if tiene_productos_asignados:
                    # Si tiene productos asignados, verificar que esté asignado
                    producto = Producto.objects.filter(
                        id=producto_id,
                        parejas_asignadas__in=parejas_usuario
                    ).first()
                    if not producto:
                        return JsonResponse({
                            'success': False,
                            'error': 'Este producto no está asignado a su pareja de conteo'
                        })
                else:
                    # Si no tiene productos asignados, permitir cualquier producto
                    producto = Producto.objects.filter(id=producto_id).first()
                    if not producto:
                        return JsonResponse({
                            'success': False,
                            'error': f'Producto con ID {producto_id} no encontrado'
                        })
            else:
                # Buscar productos
                if tiene_productos_asignados:
                    # Si tiene productos asignados, buscar solo esos
                    productos = productos_asignados
                else:
                    # Si no tiene productos asignados, buscar todos
                    productos = Producto.objects.all()
                
                # Intentar buscar por ID si es un número
                try:
                    busqueda_id = int(busqueda)
                    producto = productos.filter(
                        Q(id=busqueda_id) |
                        Q(codigo_barras__iexact=busqueda) |
                        Q(codigo_barras__icontains=busqueda) |
                        Q(codigo__iexact=busqueda) |
                        Q(codigo__icontains=busqueda) |
                        Q(nombre__icontains=busqueda) |
                        Q(marca__icontains=busqueda) |
                        Q(atributo__icontains=busqueda)
                    ).first()
                except ValueError:
                    producto = productos.filter(
                        Q(codigo_barras__iexact=busqueda) |
                        Q(codigo_barras__icontains=busqueda) |
                        Q(codigo__iexact=busqueda) |
                        Q(codigo__icontains=busqueda) |
                        Q(nombre__icontains=busqueda) |
                        Q(marca__icontains=busqueda) |
                        Q(descripcion__icontains=busqueda) |
                        Q(atributo__icontains=busqueda)
                    ).first()
                
                if not producto:
                    if tiene_productos_asignados:
                        return JsonResponse({
                            'success': False,
                            'error': f'Producto no encontrado o no está asignado a su pareja de conteo: {busqueda}'
                        })
                    else:
                        return JsonResponse({
                            'success': False,
                            'error': f'Producto no encontrado: {busqueda}'
                        })
            
            with transaction.atomic():
                cantidad_anterior = 0
                item, created = ItemConteo.objects.get_or_create(
                    conteo=conteo,
                    producto=producto,
                    defaults={
                        'cantidad': cantidad,
                        'usuario_conteo': request.user
                    }
                )
                
                if not created:
                    # Si ya existe, sumar la cantidad
                    cantidad_anterior = item.cantidad
                    item.cantidad += cantidad
                    item.usuario_conteo = request.user
                    item.save()
                    tipo_movimiento = 'modificar'
                else:
                    tipo_movimiento = 'agregar'
                
                # Registrar movimiento
                MovimientoConteo.objects.create(
                    conteo=conteo,
                    item_conteo=item,
                    producto=producto,
                    usuario=request.user,
                    tipo=tipo_movimiento,
                    cantidad_anterior=cantidad_anterior,
                    cantidad_nueva=item.cantidad,
                    cantidad_cambiada=cantidad,
                )
            
            return JsonResponse({
                'success': True,
                'producto': {
                    'nombre': producto.nombre,
                    'codigo_barras': producto.codigo_barras,
                    'marca': producto.marca or '',
                    'atributo': producto.atributo or '',
                    'cantidad': item.cantidad,
                    'imagen': producto.imagen.url if producto.imagen else None
                },
                'item_id': item.id,
                'mensaje': f'Producto agregado: {producto.nombre} (Total: {item.cantidad})'
            })
            
        except Producto.DoesNotExist:
            return JsonResponse({'success': False, 'error': f'Producto con código {codigo_barras} no encontrado'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required
def buscar_producto(request):
    """API para buscar producto por código de barras, nombre, ID o cualquier atributo"""
    busqueda = request.GET.get('busqueda', '').strip()
    
    if not busqueda:
        return JsonResponse({'success': False, 'error': 'Búsqueda requerida'})
    
    # Obtener parejas del usuario (donde es usuario_1 o usuario_2)
    parejas_usuario = ParejaConteo.objects.filter(
        Q(usuario_1=request.user) | Q(usuario_2=request.user),
        activa=True
    )
    
    # Si tiene productos asignados, buscar solo esos; si no, buscar todos
    if parejas_usuario.exists():
        productos_asignados = Producto.objects.filter(
            parejas_asignadas__in=parejas_usuario
        ).distinct()
        # Si hay productos asignados, usar solo esos; si no, usar todos
        if productos_asignados.exists():
            productos = productos_asignados
        else:
            productos = Producto.objects.all()
    else:
        # Si no tiene parejas, buscar todos los productos
        productos = Producto.objects.all()
    
    # Buscar en todos los campos relevantes: código de barras, código, nombre, marca, descripción, categoría, atributo
    # Intentar buscar por ID si es un número
    try:
        busqueda_id = int(busqueda)
        productos = productos.filter(
            Q(id=busqueda_id) |
            Q(codigo_barras__icontains=busqueda) |
            Q(codigo_barras__iexact=busqueda) |
            Q(codigo__icontains=busqueda) |
            Q(codigo__iexact=busqueda) |
            Q(nombre__icontains=busqueda) |
            Q(marca__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(categoria__icontains=busqueda) |
            Q(atributo__icontains=busqueda)
        )
    except ValueError:
        # Si no es un número, buscar por texto en todos los campos
        productos = productos.filter(
            Q(codigo_barras__icontains=busqueda) |
            Q(codigo_barras__iexact=busqueda) |
            Q(codigo__icontains=busqueda) |
            Q(codigo__iexact=busqueda) |
            Q(nombre__icontains=busqueda) |
            Q(marca__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(categoria__icontains=busqueda) |
            Q(atributo__icontains=busqueda)
        )
    
    # Obtener el total antes de evaluar el queryset
    total_productos = productos.count()
    
    if total_productos == 0:
        return JsonResponse({'success': False, 'error': 'No se encontraron productos'})
    elif total_productos == 1:
            # Si hay un solo resultado, retornarlo directamente
            producto = productos.first()
            return JsonResponse({
                'success': True,
                'producto': {
                    'id': producto.id,
                    'nombre': producto.nombre,
                    'codigo_barras': producto.codigo_barras,
                    'marca': producto.marca or '',
                    'categoria': producto.categoria or '',
                    'atributo': producto.atributo or '',
                    'imagen': producto.imagen.url if producto.imagen else None,
                },
                'unico': True
            })
    else:
        # Si hay múltiples resultados, retornar la lista
        resultados = []
        for producto in productos:
            resultados.append({
                'id': producto.id,
                'nombre': producto.nombre,
                'codigo_barras': producto.codigo_barras,
                'marca': producto.marca or '',
                'categoria': producto.categoria or '',
                'atributo': producto.atributo or '',
                'imagen': producto.imagen.url if producto.imagen else None,
            })
        return JsonResponse({
            'success': True,
            'productos': resultados,
            'unico': False,
            'total': total_productos
        })


@login_required
def finalizar_conteo(request, pk):
    """Finaliza un conteo - Solo administradores"""
    # Verificar que el usuario sea administrador
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, 'No tienes permisos para finalizar conteos. Solo los administradores pueden realizar esta acción.')
        return redirect('conteo:lista_conteos')
    
    conteo = get_object_or_404(Conteo, pk=pk)
    
    if request.method == 'POST':
        from django.utils import timezone
        conteo.estado = 'finalizado'
        conteo.fecha_fin = timezone.now()
        conteo.usuario_modificador = request.user
        conteo.save()
        messages.success(request, 'Conteo finalizado exitosamente.')
        return redirect('conteo:lista_conteos')
    
    return render(request, 'conteo/finalizar.html', {'conteo': conteo})


@login_required
def editar_item(request, item_id):
    """Edita la cantidad de un item de conteo - Solo administradores"""
    # Verificar que el usuario sea administrador
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'No tienes permisos para editar items. Solo los administradores pueden realizar esta acción.'})
    
    item = get_object_or_404(ItemConteo, pk=item_id)
    conteo_id = item.conteo.id
    conteo = item.conteo
    producto = item.producto
    cantidad_anterior = item.cantidad
    
    if request.method == 'POST':
        try:
            nueva_cantidad = int(request.POST.get('cantidad', 0))
            if nueva_cantidad < 0:
                return JsonResponse({'success': False, 'error': 'La cantidad no puede ser negativa'})
            
            with transaction.atomic():
                # Actualizar cantidad
                item.cantidad = nueva_cantidad
                item.usuario_conteo = request.user
                item.save()
                
                # Registrar movimiento
                MovimientoConteo.objects.create(
                    conteo=conteo,
                    item_conteo=item,
                    producto=producto,
                    usuario=request.user,
                    tipo='modificar',
                    cantidad_anterior=cantidad_anterior,
                    cantidad_nueva=nueva_cantidad,
                    cantidad_cambiada=nueva_cantidad - cantidad_anterior
                )
            
            return JsonResponse({
                'success': True,
                'mensaje': f'Cantidad actualizada: {nueva_cantidad}',
                'cantidad': nueva_cantidad,
                'producto': {
                    'nombre': producto.nombre,
                    'codigo_barras': producto.codigo_barras,
                    'marca': producto.marca or '',
                    'atributo': producto.atributo or '',
                }
            })
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Cantidad inválida'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET request - retornar datos del item
    return JsonResponse({
        'success': True,
        'item': {
            'id': item.id,
            'producto': {
                'nombre': producto.nombre,
                'codigo_barras': producto.codigo_barras,
                'marca': producto.marca or '',
                'atributo': producto.atributo or '',
            },
            'cantidad': item.cantidad
        }
    })


@login_required
def eliminar_item(request, item_id):
    """Elimina un item de conteo"""
    item = get_object_or_404(ItemConteo, pk=item_id)
    conteo_id = item.conteo.id
    conteo = item.conteo
    producto = item.producto
    cantidad_eliminada = item.cantidad
    
    if request.method == 'POST':
        with transaction.atomic():
            # Registrar movimiento antes de eliminar
            MovimientoConteo.objects.create(
                conteo=conteo,
                item_conteo=None,  # Item será eliminado
                producto=producto,
                usuario=request.user,
                tipo='eliminar',
                cantidad_anterior=cantidad_eliminada,
                cantidad_nueva=0,
                cantidad_cambiada=-cantidad_eliminada
            )
            item.delete()
        messages.success(request, 'Item eliminado exitosamente.')
        return redirect('conteo:detalle_conteo', pk=conteo_id)
    
    return render(request, 'conteo/eliminar_item.html', {'item': item})


@login_required
def comparar_conteos(request):
    """Compara múltiples conteos entre sí"""
    if request.method == 'POST':
        form = CompararConteosForm(request.POST)
        if form.is_valid():
            conteos_seleccionados = form.cleaned_data['conteos']
            return redirect('conteo:detalle_comparacion', conteos_ids=','.join(str(c.id) for c in conteos_seleccionados))
    else:
        form = CompararConteosForm()
    
    return render(request, 'conteo/comparar_conteos.html', {'form': form})


@login_required
def detalle_comparacion(request, conteos_ids):
    """Muestra el detalle de la comparación entre conteos"""
    # Parsear IDs de conteos
    try:
        ids = [int(id_str) for id_str in conteos_ids.split(',')]
        conteos = Conteo.objects.filter(id__in=ids, estado='finalizado').order_by('numero_conteo', '-fecha_fin')
    except (ValueError, Conteo.DoesNotExist):
        messages.error(request, 'Error al cargar los conteos seleccionados.')
        return redirect('conteo:comparar_conteos')
    
    if conteos.count() < 2:
        messages.error(request, 'Debe seleccionar al menos 2 conteos finalizados para comparar.')
        return redirect('conteo:comparar_conteos')
    
    # Obtener todos los productos
    productos = Producto.objects.all().order_by('marca', 'nombre')
    
    # Crear diccionario con cantidades por producto por conteo
    comparacion_data = []
    for producto in productos:
        producto_data = {
            'producto': producto,
            'cantidades_por_conteo': [],  # Lista de tuplas (conteo_id, cantidad)
            'total': 0,
            'promedio': 0,
            'maximo': 0,
            'minimo': 0,
            'diferencias': []  # Lista de diferencias
        }
        
        cantidades = []
        cantidades_por_conteo = []
        for conteo in conteos:
            item = ItemConteo.objects.filter(conteo=conteo, producto=producto).first()
            cantidad = item.cantidad if item else 0
            cantidades_por_conteo.append((conteo.id, cantidad))
            cantidades.append(cantidad)
        
        producto_data['cantidades_por_conteo'] = cantidades_por_conteo
        
        if cantidades:
            producto_data['total'] = sum(cantidades)
            producto_data['promedio'] = sum(cantidades) / len(cantidades)
            producto_data['maximo'] = max(cantidades)
            producto_data['minimo'] = min(cantidades)
            
            # Calcular diferencias entre conteos
            diferencias = []
            for i, conteo1 in enumerate(conteos):
                for j, conteo2 in enumerate(conteos):
                    if i < j:
                        diff = cantidades[i] - cantidades[j]
                        if diff != 0:
                            diferencias.append({
                                'conteo1': conteo1.nombre,
                                'conteo2': conteo2.nombre,
                                'diferencia': diff
                            })
            producto_data['diferencias'] = diferencias
        
        comparacion_data.append(producto_data)
    
    # Estadísticas generales
    productos_con_diferencias = sum(1 for p in comparacion_data if any(d != 0 for d in p['diferencias'].values()))
    
    total_items_por_conteo = {}
    for conteo in conteos:
        total_items = ItemConteo.objects.filter(conteo=conteo).count()
        total_cantidad = ItemConteo.objects.filter(conteo=conteo).aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        total_items_por_conteo[conteo.id] = {
            'items': total_items,
            'cantidad': total_cantidad,
        }
    
    estadisticas = {
        'total_productos': productos.count(),
        'productos_con_diferencias': productos_con_diferencias,
        'total_items_por_conteo': total_items_por_conteo,
    }
    
    return render(request, 'conteo/detalle_comparacion.html', {
        'conteos': conteos,
        'comparacion_data': comparacion_data,
        'estadisticas': estadisticas,
    })

