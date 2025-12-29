"""
Script para verificar la congruencia de movimientos y conteos en el sistema completo.
Verifica todos los conteos existentes y reporta cualquier inconsistencia.
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

from django.db.models import Sum, Count
from conteo.models import Conteo, ItemConteo
from movimientos.models import MovimientoConteo

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

def verificar_conteo(conteo):
    """Verifica la congruencia de un conteo específico"""
    errores = []
    advertencias = []
    
    # Obtener items del conteo
    items = ItemConteo.objects.filter(conteo=conteo)
    movimientos = MovimientoConteo.objects.filter(conteo=conteo)
    
    # Verificar cada item
    for item in items:
        # Calcular cantidad desde movimientos
        movimientos_item = movimientos.filter(producto=item.producto)
        
        cantidad_calculada = 0
        for movimiento in movimientos_item.order_by('fecha_movimiento'):
            if movimiento.tipo == 'agregar':
                cantidad_calculada += movimiento.cantidad_cambiada
            elif movimiento.tipo == 'modificar':
                cantidad_calculada += movimiento.cantidad_cambiada
            elif movimiento.tipo == 'eliminar':
                cantidad_calculada = 0
        
        # Verificar congruencia
        if item.cantidad != cantidad_calculada:
            errores.append({
                'tipo': 'incongruencia_cantidad',
                'item': item,
                'cantidad_item': item.cantidad,
                'cantidad_calculada': cantidad_calculada,
                'producto': item.producto.nombre
            })
        
        # Verificar que hay al menos un movimiento
        if not movimientos_item.exists():
            advertencias.append({
                'tipo': 'item_sin_movimientos',
                'item': item,
                'producto': item.producto.nombre
            })
    
    # Verificar totales
    total_items = items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
    
    movimientos_agregar = movimientos.filter(tipo='agregar').aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
    movimientos_modificar = movimientos.filter(tipo='modificar').aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
    movimientos_eliminar = movimientos.filter(tipo='eliminar').aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
    
    total_movimientos = movimientos_agregar + movimientos_modificar + movimientos_eliminar
    
    if abs(total_items - total_movimientos) > 0.01:  # Tolerancia para decimales
        errores.append({
            'tipo': 'incongruencia_total',
            'total_items': total_items,
            'total_movimientos': total_movimientos,
            'diferencia': total_items - total_movimientos
        })
    
    return errores, advertencias

def main():
    """Función principal"""
    print_header("VERIFICACIÓN DE CONGRUENCIA DEL SISTEMA")
    
    conteos = Conteo.objects.all().order_by('-fecha_inicio')
    print_info(f"Total de conteos a verificar: {conteos.count()}")
    
    total_errores = 0
    total_advertencias = 0
    conteos_con_errores = []
    conteos_con_advertencias = []
    
    for conteo in conteos:
        errores, advertencias = verificar_conteo(conteo)
        
        if errores:
            conteos_con_errores.append((conteo, errores))
            total_errores += len(errores)
        
        if advertencias:
            conteos_con_advertencias.append((conteo, advertencias))
            total_advertencias += len(advertencias)
    
    # Reportar resultados
    print_header("RESUMEN DE VERIFICACIÓN")
    
    if total_errores == 0 and total_advertencias == 0:
        print_success("¡Todos los conteos son congruentes!")
        print_success(f"Verificados {conteos.count()} conteos sin errores ni advertencias")
    else:
        if total_errores > 0:
            print_error(f"Se encontraron {total_errores} errores en {len(conteos_con_errores)} conteo(s)")
            
            for conteo, errores in conteos_con_errores:
                print_error(f"\nConteo: {conteo.nombre} (ID: {conteo.id})")
                for error in errores:
                    if error['tipo'] == 'incongruencia_cantidad':
                        print_error(f"  - {error['producto']}: Item={error['cantidad_item']}, Calculado={error['cantidad_calculada']}")
                    elif error['tipo'] == 'incongruencia_total':
                        print_error(f"  - Total: Items={error['total_items']}, Movimientos={error['total_movimientos']}, Diferencia={error['diferencia']}")
        
        if total_advertencias > 0:
            print_warning(f"Se encontraron {total_advertencias} advertencias en {len(conteos_con_advertencias)} conteo(s)")
            
            for conteo, advertencias in conteos_con_advertencias:
                print_warning(f"\nConteo: {conteo.nombre} (ID: {conteo.id})")
                for advertencia in advertencias:
                    if advertencia['tipo'] == 'item_sin_movimientos':
                        print_warning(f"  - {advertencia['producto']}: Item sin movimientos asociados")
    
    # Estadísticas generales
    print_header("ESTADÍSTICAS GENERALES")
    
    total_items_sistema = ItemConteo.objects.count()
    total_movimientos_sistema = MovimientoConteo.objects.count()
    total_conteos = Conteo.objects.count()
    
    movimientos_por_tipo = MovimientoConteo.objects.values('tipo').annotate(
        total=Count('id')
    ).order_by('tipo')
    
    print_info(f"Total conteos: {total_conteos}")
    print_info(f"Total items: {total_items_sistema}")
    print_info(f"Total movimientos: {total_movimientos_sistema}")
    print_info("\nMovimientos por tipo:")
    for item in movimientos_por_tipo:
        print_info(f"  - {item['tipo']}: {item['total']}")
    
    print_header("VERIFICACIÓN COMPLETADA")
    
    if total_errores == 0:
        print_success("El sistema está completamente congruente")
        return 0
    else:
        print_error("Se encontraron inconsistencias que requieren atención")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

