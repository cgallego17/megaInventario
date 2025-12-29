from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum, Count, Q
from .models import Conteo, ItemConteo
from .forms import ConteoForm, ItemConteoForm
from productos.models import Producto
from movimientos.models import MovimientoConteo


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
        conteos_por_numero[num] = conteos_num
    
    # Agregar estadísticas a todos los conteos para la vista general
    for conteo in conteos:
        conteo.total_items = conteo.items.count()
        conteo.total_cantidad = conteo.items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
    
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
    items = conteo.items.all().select_related('producto')
    
    # Estadísticas
    total_items = items.count()
    total_cantidad = items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
    
    # Total de productos en el sistema (todos, activos e inactivos)
    total_productos = Producto.objects.count()
    
    # Calcular porcentaje de productos contados
    porcentaje_contado = (total_items / total_productos * 100) if total_productos > 0 else 0
    
    return render(request, 'conteo/detalle_conteo.html', {
        'conteo': conteo,
        'items': items,
        'total_items': total_items,
        'total_cantidad': total_cantidad,
        'total_productos': total_productos,
        'porcentaje_contado': porcentaje_contado,
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
            # Si se proporciona un ID, usarlo directamente
            if producto_id:
                producto = Producto.objects.get(id=producto_id)
            else:
                # Buscar por código de barras, nombre, etc. (incluyendo inactivos)
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
                    return JsonResponse({'success': False, 'error': f'Producto no encontrado: {busqueda}'})
            
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
    
    # Buscar productos de forma flexible (incluyendo inactivos)
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
    
    productos = productos[:10]  # Limitar a 10 resultados
    
    if productos.count() == 0:
        return JsonResponse({'success': False, 'error': 'No se encontraron productos'})
    elif productos.count() == 1:
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
                'categoria': producto.categoria or '',
                'atributo': producto.atributo or '',
                'imagen': producto.imagen.url if producto.imagen else None,
            })
        return JsonResponse({
            'success': True,
            'productos': resultados,
            'unico': False,
            'total': productos.count()
        })


@login_required
def finalizar_conteo(request, pk):
    """Finaliza un conteo"""
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

