"""
Script para eliminar productos duplicados y dejar solo los que están en la API
"""
import os
import sys
import django
import requests

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
from productos.models import Producto

# URL de la API
URL_API = 'https://tersacosmeticos.com/prod/api/productos-publicos/?format=json'

def main():
    print("="*70)
    print("ELIMINACIÓN DE PRODUCTOS DUPLICADOS")
    print("="*70)
    print()
    
    try:
        # Obtener productos de la API
        print("Obteniendo productos de la API...")
        response = requests.get(URL_API, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        productos_api = data if isinstance(data, list) else (data.get('results', [data]) if isinstance(data, dict) else [data])
        ids_api = {str(p.get('id')) for p in productos_api if p.get('id')}
        
        print(f"Productos en la API: {len(productos_api)}")
        print(f"IDs únicos en la API: {len(ids_api)}")
        print()
        
        # Obtener productos de la BD
        productos_bd = Producto.objects.all()
        print(f"Total productos en BD: {productos_bd.count()}")
        print()
        
        # Identificar duplicados por ID de API
        productos_por_id = {}
        productos_sin_id = []
        
        for producto in productos_bd:
            if producto.codigo and producto.codigo.strip():
                if producto.codigo not in productos_por_id:
                    productos_por_id[producto.codigo] = []
                productos_por_id[producto.codigo].append(producto)
            else:
                productos_sin_id.append(producto)
        
        # Encontrar duplicados
        duplicados = {k: v for k, v in productos_por_id.items() if len(v) > 1}
        productos_a_eliminar = []
        
        print("="*70)
        print("ANÁLISIS DE DUPLICADOS")
        print("="*70)
        print()
        print(f"IDs con duplicados: {len(duplicados)}")
        print(f"Productos sin ID de API: {len(productos_sin_id)}")
        print()
        
        # Para cada ID duplicado, mantener solo el más reciente y eliminar los demás
        for api_id, productos_list in duplicados.items():
            # Ordenar por fecha de actualización (más reciente primero)
            productos_list.sort(key=lambda p: p.fecha_actualizacion, reverse=True)
            # Mantener el primero (más reciente), eliminar los demás
            productos_a_eliminar.extend(productos_list[1:])
        
        # Eliminar productos sin ID de API que no están en la API
        for producto in productos_sin_id:
            productos_a_eliminar.append(producto)
        
        # Eliminar productos con ID que no está en la API
        for api_id, productos_list in productos_por_id.items():
            if api_id not in ids_api:
                productos_a_eliminar.extend(productos_list)
        
        print(f"Total productos a eliminar: {len(productos_a_eliminar)}")
        print()
        
        if productos_a_eliminar:
            print("Eliminando productos...")
            
            with transaction.atomic():
                eliminados = 0
                for producto in productos_a_eliminar:
                    try:
                        producto.delete()
                        eliminados += 1
                    except Exception as e:
                        print(f"Error al eliminar producto {producto.id}: {e}")
            
            print(f"Productos eliminados: {eliminados}")
            print()
        else:
            print("No hay productos a eliminar.")
            print()
        
        # Verificar resultado final
        productos_finales = Producto.objects.count()
        productos_con_id = Producto.objects.exclude(codigo__isnull=True).exclude(codigo='').count()
        
        print("="*70)
        print("RESULTADO FINAL")
        print("="*70)
        print(f"Productos en la API: {len(ids_api)}")
        print(f"Productos en la BD: {productos_finales}")
        print(f"Productos en la BD con ID de API: {productos_con_id}")
        print()
        
        if productos_con_id == len(ids_api):
            print("✅ Sincronización exitosa: Todos los productos de la API están en la BD")
            print("   y no hay duplicados")
        else:
            print(f"⚠️  Diferencia: {abs(productos_con_id - len(ids_api))} productos")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

