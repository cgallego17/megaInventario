"""
Script para eliminar todos los registros excepto productos, parejas y usuarios
"""
import os
import sys
import django
import io

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configurar Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megaInventario.settings')
django.setup()

from django.db import transaction
from django.contrib.auth.models import User
from conteo.models import Conteo, ItemConteo
from comparativos.models import ComparativoInventario, InventarioSistema, ItemComparativo
from movimientos.models import MovimientoConteo
from reportes.models import Reporte
from productos.models import Producto
from usuarios.models import ParejaConteo, PerfilUsuario

def main():
    print("="*70)
    print("LIMPIEZA DE REGISTROS")
    print("="*70)
    print()
    print("Este script eliminará:")
    print("  - Conteos y Items de Conteo")
    print("  - Comparativos, Inventarios e Items Comparativos")
    print("  - Movimientos")
    print("  - Reportes")
    print()
    print("Se mantendrán:")
    print("  - Productos")
    print("  - Usuarios")
    print("  - Parejas")
    print()
    
    # Contar registros antes
    conteos_count = Conteo.objects.count()
    items_count = ItemConteo.objects.count()
    comparativos_count = ComparativoInventario.objects.count()
    inventarios_count = InventarioSistema.objects.count()
    items_comparativo_count = ItemComparativo.objects.count()
    movimientos_count = MovimientoConteo.objects.count()
    reportes_count = Reporte.objects.count()
    productos_count = Producto.objects.count()
    usuarios_count = User.objects.count()
    parejas_count = ParejaConteo.objects.count()
    
    print("="*70)
    print("ESTADO ACTUAL")
    print("="*70)
    print(f"Conteos: {conteos_count}")
    print(f"Items de Conteo: {items_count}")
    print(f"Comparativos: {comparativos_count}")
    print(f"Inventarios: {inventarios_count}")
    print(f"Items Comparativos: {items_comparativo_count}")
    print(f"Movimientos: {movimientos_count}")
    print(f"Reportes: {reportes_count}")
    print()
    print(f"Productos (se mantienen): {productos_count}")
    print(f"Usuarios (se mantienen): {usuarios_count}")
    print(f"Parejas (se mantienen): {parejas_count}")
    print()
    
    total_a_eliminar = conteos_count + items_count + comparativos_count + inventarios_count + items_comparativo_count + movimientos_count + reportes_count
    
    if total_a_eliminar == 0:
        print("No hay registros para eliminar.")
        return
    
    print(f"Total de registros a eliminar: {total_a_eliminar}")
    print()
    
    # Verificar si se pasó el argumento --confirmar
    confirmar = '--confirmar' in sys.argv
    
    if not confirmar:
        try:
            respuesta = input("¿Desea continuar? (s/n): ")
            if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
                print("Operación cancelada.")
                return
        except EOFError:
            print("Error: No se puede leer entrada. Use --confirmar para ejecutar sin confirmación.")
            sys.exit(1)
    
    print()
    print("Eliminando registros...")
    
    try:
        with transaction.atomic():
            # Eliminar en orden (primero los dependientes)
            print("  - Eliminando Items Comparativos...")
            items_comparativo_eliminados = ItemComparativo.objects.all().delete()[0]
            print(f"    Eliminados: {items_comparativo_eliminados}")
            
            print("  - Eliminando Items de Conteo...")
            items_eliminados = ItemConteo.objects.all().delete()[0]
            print(f"    Eliminados: {items_eliminados}")
            
            print("  - Eliminando Movimientos...")
            movimientos_eliminados = MovimientoConteo.objects.all().delete()[0]
            print(f"    Eliminados: {movimientos_eliminados}")
            
            print("  - Eliminando Reportes...")
            reportes_eliminados = Reporte.objects.all().delete()[0]
            print(f"    Eliminados: {reportes_eliminados}")
            
            print("  - Eliminando Inventarios...")
            inventarios_eliminados = InventarioSistema.objects.all().delete()[0]
            print(f"    Eliminados: {inventarios_eliminados}")
            
            print("  - Eliminando Comparativos...")
            comparativos_eliminados = ComparativoInventario.objects.all().delete()[0]
            print(f"    Eliminados: {comparativos_eliminados}")
            
            print("  - Eliminando Conteos...")
            conteos_eliminados = Conteo.objects.all().delete()[0]
            print(f"    Eliminados: {conteos_eliminados}")
        
        print()
        print("="*70)
        print("LIMPIEZA COMPLETADA")
        print("="*70)
        print()
        
        # Verificar estado final
        print("Estado final:")
        print(f"  Conteos: {Conteo.objects.count()}")
        print(f"  Items de Conteo: {ItemConteo.objects.count()}")
        print(f"  Comparativos: {ComparativoInventario.objects.count()}")
        print(f"  Inventarios: {InventarioSistema.objects.count()}")
        print(f"  Items Comparativos: {ItemComparativo.objects.count()}")
        print(f"  Movimientos: {MovimientoConteo.objects.count()}")
        print(f"  Reportes: {Reporte.objects.count()}")
        print()
        print(f"  Productos: {Producto.objects.count()} (mantenidos)")
        print(f"  Usuarios: {User.objects.count()} (mantenidos)")
        print(f"  Parejas: {ParejaConteo.objects.count()} (mantenidas)")
        
    except Exception as e:
        print(f"❌ Error durante la eliminación: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

