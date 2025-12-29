"""
Script para borrar todos los datos del sistema
Mantiene la estructura de la base de datos pero elimina todos los registros
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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megaInventario.settings')
django.setup()

from django.db import transaction
from django.contrib.auth.models import User
from productos.models import Producto
from conteo.models import Conteo, ItemConteo
from usuarios.models import PerfilUsuario, ParejaConteo
from reportes.models import Reporte
from comparativos.models import ComparativoInventario, InventarioSistema, ItemComparativo
from movimientos.models import MovimientoConteo

def borrar_todos_datos():
    """Borra todos los datos del sistema excepto usuarios del sistema"""
    print("="*70)
    print("BORRANDO TODOS LOS DATOS DEL SISTEMA")
    print("="*70)
    print()
    
    try:
        with transaction.atomic():
            # 1. Borrar movimientos (no tiene dependencias)
            print("Borrando movimientos de conteo...")
            movimientos_count = MovimientoConteo.objects.all().count()
            MovimientoConteo.objects.all().delete()
            print(f"  OK: {movimientos_count} movimientos eliminados")
            
            # 2. Borrar items comparativos
            print("Borrando items comparativos...")
            items_comp_count = ItemComparativo.objects.all().count()
            ItemComparativo.objects.all().delete()
            print(f"  OK: {items_comp_count} items comparativos eliminados")
            
            # 3. Borrar inventarios de sistema
            print("Borrando inventarios de sistema...")
            inventarios_count = InventarioSistema.objects.all().count()
            InventarioSistema.objects.all().delete()
            print(f"  OK: {inventarios_count} inventarios de sistema eliminados")
            
            # 4. Borrar comparativos
            print("Borrando comparativos...")
            comparativos_count = ComparativoInventario.objects.all().count()
            ComparativoInventario.objects.all().delete()
            print(f"  OK: {comparativos_count} comparativos eliminados")
            
            # 5. Borrar items de conteo
            print("Borrando items de conteo...")
            items_count = ItemConteo.objects.all().count()
            ItemConteo.objects.all().delete()
            print(f"  OK: {items_count} items de conteo eliminados")
            
            # 6. Borrar conteos
            print("Borrando conteos...")
            conteos_count = Conteo.objects.all().count()
            Conteo.objects.all().delete()
            print(f"  OK: {conteos_count} conteos eliminados")
            
            # 7. Borrar parejas de conteo
            print("Borrando parejas de conteo...")
            parejas_count = ParejaConteo.objects.all().count()
            ParejaConteo.objects.all().delete()
            print(f"  OK: {parejas_count} parejas eliminadas")
            
            # 8. Borrar reportes
            print("Borrando reportes...")
            reportes_count = Reporte.objects.all().count()
            Reporte.objects.all().delete()
            print(f"  OK: {reportes_count} reportes eliminados")
            
            # 9. Borrar productos
            print("Borrando productos...")
            productos_count = Producto.objects.all().count()
            Producto.objects.all().delete()
            print(f"  OK: {productos_count} productos eliminados")
            
            # 10. Borrar perfiles de usuario (excepto superusuarios)
            print("Borrando perfiles de usuario...")
            perfiles_count = PerfilUsuario.objects.exclude(
                user__is_superuser=True
            ).count()
            PerfilUsuario.objects.exclude(user__is_superuser=True).delete()
            print(f"  OK: {perfiles_count} perfiles eliminados")
            
            # 11. Borrar usuarios (excepto superusuarios)
            print("Borrando usuarios (excepto superusuarios)...")
            usuarios_count = User.objects.filter(is_superuser=False).count()
            User.objects.filter(is_superuser=False).delete()
            print(f"  OK: {usuarios_count} usuarios eliminados")
            
            print()
            print("="*70)
            print("TODOS LOS DATOS HAN SIDO ELIMINADOS EXITOSAMENTE")
            print("="*70)
            print()
            print("Resumen:")
            print(f"  - Movimientos: {movimientos_count}")
            print(f"  - Items Comparativos: {items_comp_count}")
            print(f"  - Inventarios Sistema: {inventarios_count}")
            print(f"  - Comparativos: {comparativos_count}")
            print(f"  - Items Conteo: {items_count}")
            print(f"  - Conteos: {conteos_count}")
            print(f"  - Parejas: {parejas_count}")
            print(f"  - Reportes: {reportes_count}")
            print(f"  - Productos: {productos_count}")
            print(f"  - Perfiles: {perfiles_count}")
            print(f"  - Usuarios: {usuarios_count}")
            print()
            print("NOTA: Los superusuarios y su estructura de base de datos se mantienen intactos.")
            
    except Exception as e:
        print()
        print("="*70)
        print("ERROR AL BORRAR DATOS")
        print("="*70)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    # Verificar si se pasó el argumento --confirmar
    if len(sys.argv) > 1 and sys.argv[1] == '--confirmar':
        # Ejecutar directamente sin confirmación
        borrar_todos_datos()
    else:
        # Confirmación interactiva
        print()
        print("ADVERTENCIA: Este script borrara TODOS los datos del sistema.")
        print("   Se mantendran solo los superusuarios y la estructura de la base de datos.")
        print()
        print("Para ejecutar sin confirmacion, use: python borrar_todos_datos.py --confirmar")
        print()
        try:
            respuesta = input("Esta seguro que desea continuar? (escriba 'SI' para confirmar): ")
            
            if respuesta.upper() == 'SI':
                borrar_todos_datos()
            else:
                print()
                print("Operacion cancelada.")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            print()
            print("Operacion cancelada.")
            sys.exit(0)

