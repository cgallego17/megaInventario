"""
Script para verificar que los cálculos mostrados en las vistas
coinciden con los datos reales en la base de datos.
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

from django.test import Client
from django.db.models import Sum, Count
from conteo.models import Conteo, ItemConteo
from movimientos.models import MovimientoConteo
from productos.models import Producto

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

def verificar_calculos_conteo(conteo):
    """Verifica que los cálculos del conteo sean correctos"""
    errores = []
    
    # Calcular desde items
    items = ItemConteo.objects.filter(conteo=conteo)
    total_items_count = items.count()
    total_cantidad_items = items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
    
    # Calcular desde movimientos
    movimientos = MovimientoConteo.objects.filter(conteo=conteo)
    total_movimientos_count = movimientos.count()
    
    movimientos_agregar = movimientos.filter(tipo='agregar').aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
    movimientos_modificar = movimientos.filter(tipo='modificar').aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
    movimientos_eliminar = movimientos.filter(tipo='eliminar').aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
    
    total_cantidad_movimientos = movimientos_agregar + movimientos_modificar + movimientos_eliminar
    
    # Verificar que coinciden
    if total_cantidad_items != total_cantidad_movimientos:
        errores.append({
            'tipo': 'total_cantidad',
            'total_items': total_cantidad_items,
            'total_movimientos': total_cantidad_movimientos,
            'diferencia': total_cantidad_items - total_cantidad_movimientos
        })
    
    return errores, {
        'total_items': total_items_count,
        'total_cantidad': total_cantidad_items,
        'total_movimientos': total_movimientos_count,
        'movimientos_agregar': movimientos.filter(tipo='agregar').count(),
        'movimientos_modificar': movimientos.filter(tipo='modificar').count(),
        'movimientos_eliminar': movimientos.filter(tipo='eliminar').count()
    }

def main():
    """Función principal"""
    print_header("VERIFICACIÓN DE CÁLCULOS EN VISTAS")
    
    conteos = Conteo.objects.all().order_by('-fecha_inicio')
    print_info(f"Total de conteos a verificar: {conteos.count()}")
    
    total_errores = 0
    
    for conteo in conteos:
        print_info(f"\nConteo: {conteo.nombre} (ID: {conteo.id})")
        errores, estadisticas = verificar_calculos_conteo(conteo)
        
        if errores:
            total_errores += len(errores)
            for error in errores:
                if error['tipo'] == 'total_cantidad':
                    print_error(f"  Incongruencia en total: Items={error['total_items']}, Movimientos={error['total_movimientos']}, Diferencia={error['diferencia']}")
        else:
            print_success("Cálculos correctos")
            print_info(f"  Items: {estadisticas['total_items']}")
            print_info(f"  Cantidad total: {estadisticas['total_cantidad']}")
            print_info(f"  Movimientos: {estadisticas['total_movimientos']} (Agregar: {estadisticas['movimientos_agregar']}, Modificar: {estadisticas['movimientos_modificar']}, Eliminar: {estadisticas['movimientos_eliminar']})")
    
    # Verificar cálculos globales
    print_header("VERIFICACIÓN DE CÁLCULOS GLOBALES")
    
    total_items_sistema = ItemConteo.objects.count()
    total_movimientos_sistema = MovimientoConteo.objects.count()
    
    # Calcular total de cantidad desde items
    total_cantidad_items = ItemConteo.objects.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
    
    # Calcular total desde movimientos
    total_movimientos_agregar = MovimientoConteo.objects.filter(tipo='agregar').aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
    total_movimientos_modificar = MovimientoConteo.objects.filter(tipo='modificar').aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
    total_movimientos_eliminar = MovimientoConteo.objects.filter(tipo='eliminar').aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
    
    total_cantidad_movimientos = total_movimientos_agregar + total_movimientos_modificar + total_movimientos_eliminar
    
    print_info(f"Total items en sistema: {total_items_sistema}")
    print_info(f"Total cantidad desde items: {total_cantidad_items}")
    print_info(f"Total cantidad desde movimientos: {total_cantidad_movimientos}")
    print_info(f"  - Agregar: {total_movimientos_agregar}")
    print_info(f"  - Modificar: {total_movimientos_modificar}")
    print_info(f"  - Eliminar: {total_movimientos_eliminar}")
    
    if abs(total_cantidad_items - total_cantidad_movimientos) > 0.01:
        print_error(f"Incongruencia global: Diferencia = {total_cantidad_items - total_cantidad_movimientos}")
        total_errores += 1
    else:
        print_success("Cálculos globales correctos")
    
    print_header("VERIFICACIÓN COMPLETADA")
    
    if total_errores == 0:
        print_success("✓ Todos los cálculos son correctos")
        print_success("✓ Las vistas mostrarán datos consistentes")
        return 0
    else:
        print_error(f"✗ Se encontraron {total_errores} errores en los cálculos")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

