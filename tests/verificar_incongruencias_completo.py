"""
Script exhaustivo para verificar todas las posibles incongruencias en el sistema.
Verifica:
1. Congruencia entre items y movimientos
2. Integridad de relaciones
3. Consistencia de datos
4. Cálculos correctos
"""

import os
import sys
import django

# Configurar encoding para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configurar Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megaInventario.settings')
django.setup()

from django.db.models import Sum, Count, Q
from conteo.models import Conteo, ItemConteo
from movimientos.models import MovimientoConteo
from productos.models import Producto
from django.contrib.auth.models import User

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_success(text):
    print(f"  ✓ {text}")

def print_error(text):
    print(f"  ✗ {text}")

def print_info(text):
    print(f"  ℹ {text}")

def print_warning(text):
    print(f"  ⚠ {text}")

def verificar_conteo_detallado(conteo):
    """Verificación detallada de un conteo"""
    errores = []
    advertencias = []
    
    items = ItemConteo.objects.filter(conteo=conteo)
    movimientos = MovimientoConteo.objects.filter(conteo=conteo)
    
    # 1. Verificar cada item individualmente
    for item in items:
        movimientos_item = movimientos.filter(producto=item.producto).order_by('fecha_movimiento')
        
        # Reconstruir cantidad desde movimientos
        cantidad_reconstruida = 0
        for movimiento in movimientos_item:
            if movimiento.tipo == 'agregar':
                cantidad_reconstruida += movimiento.cantidad_cambiada
            elif movimiento.tipo == 'modificar':
                cantidad_reconstruida += movimiento.cantidad_cambiada
            elif movimiento.tipo == 'eliminar':
                cantidad_reconstruida = 0
        
        if item.cantidad != cantidad_reconstruida:
            errores.append({
                'tipo': 'incongruencia_cantidad',
                'item_id': item.id,
                'producto': item.producto.nombre,
                'cantidad_item': item.cantidad,
                'cantidad_reconstruida': cantidad_reconstruida,
                'diferencia': item.cantidad - cantidad_reconstruida
            })
        
        # Verificar que hay movimientos
        if not movimientos_item.exists():
            advertencias.append({
                'tipo': 'item_sin_movimientos',
                'item_id': item.id,
                'producto': item.producto.nombre
            })
        
        # Verificar integridad del último movimiento
        ultimo_movimiento = movimientos_item.last()
        if ultimo_movimiento and ultimo_movimiento.tipo != 'eliminar':
            if ultimo_movimiento.cantidad_nueva != item.cantidad:
                errores.append({
                    'tipo': 'ultimo_movimiento_incongruente',
                    'item_id': item.id,
                    'producto': item.producto.nombre,
                    'cantidad_item': item.cantidad,
                    'cantidad_ultimo_movimiento': ultimo_movimiento.cantidad_nueva
                })
    
    # 2. Verificar totales
    total_items = items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
    
    movimientos_agregar = movimientos.filter(tipo='agregar').aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
    movimientos_modificar = movimientos.filter(tipo='modificar').aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
    movimientos_eliminar = movimientos.filter(tipo='eliminar').aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
    
    total_movimientos = movimientos_agregar + movimientos_modificar + movimientos_eliminar
    
    if abs(total_items - total_movimientos) > 0.01:
        errores.append({
            'tipo': 'incongruencia_total',
            'total_items': total_items,
            'total_movimientos': total_movimientos,
            'diferencia': total_items - total_movimientos
        })
    
    # 3. Verificar movimientos sin item asociado (excepto eliminaciones)
    movimientos_sin_item = movimientos.filter(
        Q(item_conteo__isnull=True) & ~Q(tipo='eliminar')
    )
    if movimientos_sin_item.exists():
        for movimiento in movimientos_sin_item:
            advertencias.append({
                'tipo': 'movimiento_sin_item',
                'movimiento_id': movimiento.id,
                'producto': movimiento.producto.nombre,
                'tipo': movimiento.tipo
            })
    
    # 4. Verificar movimientos con datos inconsistentes
    for movimiento in movimientos:
        cantidad_calculada = movimiento.cantidad_nueva - movimiento.cantidad_anterior
        if movimiento.cantidad_cambiada != cantidad_calculada:
            errores.append({
                'tipo': 'movimiento_inconsistente',
                'movimiento_id': movimiento.id,
                'producto': movimiento.producto.nombre,
                'cantidad_cambiada': movimiento.cantidad_cambiada,
                'cantidad_calculada': cantidad_calculada
            })
    
    return errores, advertencias

def main():
    """Función principal"""
    print_header("VERIFICACIÓN EXHAUSTIVA DE INCONGRUENCIAS")
    
    conteos = Conteo.objects.all().order_by('-fecha_inicio')
    print_info(f"Total de conteos a verificar: {conteos.count()}")
    
    total_errores = 0
    total_advertencias = 0
    conteos_con_problemas = []
    
    # Verificar cada conteo
    for conteo in conteos:
        errores, advertencias = verificar_conteo_detallado(conteo)
        
        if errores or advertencias:
            conteos_con_problemas.append((conteo, errores, advertencias))
            total_errores += len(errores)
            total_advertencias += len(advertencias)
    
    # Verificaciones globales
    print_header("VERIFICACIONES GLOBALES")
    
    # 1. Items sin movimientos en ningún conteo
    items_sin_movimientos = ItemConteo.objects.filter(
        producto__movimientoconteo__isnull=True
    ).distinct()
    
    if items_sin_movimientos.exists():
        print_warning(f"Items sin movimientos: {items_sin_movimientos.count()}")
        for item in items_sin_movimientos[:5]:  # Mostrar solo los primeros 5
            print_warning(f"  - Item ID {item.id}: {item.producto.nombre} (Conteo: {item.conteo.nombre})")
        total_advertencias += items_sin_movimientos.count()
    else:
        print_success("Todos los items tienen movimientos asociados")
    
    # 2. Movimientos con relaciones inválidas
    movimientos_invalidos = MovimientoConteo.objects.filter(
        Q(conteo__isnull=True) | Q(producto__isnull=True) | Q(usuario__isnull=True)
    )
    
    if movimientos_invalidos.exists():
        print_error(f"Movimientos con relaciones inválidas: {movimientos_invalidos.count()}")
        total_errores += movimientos_invalidos.count()
    else:
        print_success("Todos los movimientos tienen relaciones válidas")
    
    # 3. Items con relaciones inválidas
    items_invalidos = ItemConteo.objects.filter(
        Q(conteo__isnull=True) | Q(producto__isnull=True)
    )
    
    if items_invalidos.exists():
        print_error(f"Items con relaciones inválidas: {items_invalidos.count()}")
        total_errores += items_invalidos.count()
    else:
        print_success("Todos los items tienen relaciones válidas")
    
    # 4. Verificar consistencia de cantidades negativas
    items_negativos = ItemConteo.objects.filter(cantidad__lt=0)
    if items_negativos.exists():
        print_error(f"Items con cantidades negativas: {items_negativos.count()}")
        total_errores += items_negativos.count()
    else:
        print_success("No hay items con cantidades negativas")
    
    # Reportar resultados por conteo
    print_header("RESUMEN POR CONTEO")
    
    if total_errores == 0 and total_advertencias == 0:
        print_success("¡Todos los conteos son completamente congruentes!")
        print_success(f"Verificados {conteos.count()} conteos sin errores ni advertencias")
    else:
        for conteo, errores, advertencias in conteos_con_problemas:
            print_error(f"\nConteo: {conteo.nombre} (ID: {conteo.id}, Estado: {conteo.estado})")
            
            if errores:
                print_error(f"  Errores encontrados: {len(errores)}")
                for error in errores[:5]:  # Mostrar solo los primeros 5
                    if error['tipo'] == 'incongruencia_cantidad':
                        print_error(f"    - {error['producto']}: Item={error['cantidad_item']}, Reconstruido={error['cantidad_reconstruida']}, Diferencia={error['diferencia']}")
                    elif error['tipo'] == 'incongruencia_total':
                        print_error(f"    - Total: Items={error['total_items']}, Movimientos={error['total_movimientos']}, Diferencia={error['diferencia']}")
                    elif error['tipo'] == 'movimiento_inconsistente':
                        print_error(f"    - Movimiento {error['movimiento_id']} ({error['producto']}): Cambiada={error['cantidad_cambiada']}, Calculada={error['cantidad_calculada']}")
                    elif error['tipo'] == 'ultimo_movimiento_incongruente':
                        print_error(f"    - {error['producto']}: Item={error['cantidad_item']}, Último movimiento={error['cantidad_ultimo_movimiento']}")
            
            if advertencias:
                print_warning(f"  Advertencias: {len(advertencias)}")
                for advertencia in advertencias[:3]:  # Mostrar solo las primeras 3
                    if advertencia['tipo'] == 'item_sin_movimientos':
                        print_warning(f"    - {advertencia['producto']}: Item sin movimientos")
                    elif advertencia['tipo'] == 'movimiento_sin_item':
                        print_warning(f"    - Movimiento {advertencia['movimiento_id']} ({advertencia['producto']}): Sin item asociado")
    
    # Estadísticas finales
    print_header("ESTADÍSTICAS FINALES")
    
    total_items = ItemConteo.objects.count()
    total_movimientos = MovimientoConteo.objects.count()
    total_conteos = Conteo.objects.count()
    
    movimientos_por_tipo = MovimientoConteo.objects.values('tipo').annotate(
        total=Count('id')
    ).order_by('tipo')
    
    print_info(f"Total conteos: {total_conteos}")
    print_info(f"Total items: {total_items}")
    print_info(f"Total movimientos: {total_movimientos}")
    print_info("\nMovimientos por tipo:")
    for item in movimientos_por_tipo:
        print_info(f"  - {item['tipo']}: {item['total']}")
    
    # Verificar proporción items/movimientos
    if total_items > 0:
        ratio = total_movimientos / total_items
        print_info(f"\nRatio movimientos/items: {ratio:.2f}")
        if ratio < 1.0:
            print_warning("Hay menos movimientos que items (algunos items pueden no tener movimientos)")
    
    print_header("VERIFICACIÓN COMPLETADA")
    
    if total_errores == 0 and total_advertencias == 0:
        print_success("✓ El sistema está completamente congruente")
        print_success("✓ No se encontraron errores ni advertencias")
        return 0
    else:
        print_error(f"✗ Se encontraron {total_errores} errores y {total_advertencias} advertencias")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

