"""
Script para sincronizar productos con la API
- Elimina productos que no están en la API
- Asegura que todos los productos de la API estén en la BD
"""
import os
import sys
import django
import requests
import json
from urllib.parse import urljoin, urlparse

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
    print("SINCRONIZACIÓN DE PRODUCTOS CON LA API")
    print("="*70)
    print()
    
    try:
        # Obtener productos de la API
        print("Obteniendo productos de la API...")
        response = requests.get(URL_API, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Detectar formato de respuesta
        productos_api = []
        if isinstance(data, list):
            productos_api = data
        elif isinstance(data, dict):
            posibles_claves = ['data', 'products', 'productos', 'items', 'result', 'results', 'content']
            for clave in posibles_claves:
                if clave in data and isinstance(data[clave], list):
                    productos_api = data[clave]
                    break
            if not productos_api:
                productos_api = [data]
        
        print(f"Productos encontrados en la API: {len(productos_api)}")
        print()
        
        # Obtener IDs de productos en la API
        ids_api = set()
        productos_api_dict = {}
        
        for producto_api in productos_api:
            api_id = producto_api.get('id') or producto_api.get('pk') or producto_api.get('_id')
            if api_id:
                ids_api.add(str(api_id))
                productos_api_dict[str(api_id)] = producto_api
        
        print(f"IDs únicos en la API: {len(ids_api)}")
        print()
        
        # Obtener productos de la base de datos
        print("Obteniendo productos de la base de datos...")
        productos_db = Producto.objects.all()
        productos_con_id = productos_db.exclude(codigo__isnull=True).exclude(codigo='')
        productos_sin_id = productos_db.filter(codigo__isnull=True) | productos_db.filter(codigo='')
        
        print(f"Total productos en BD: {productos_db.count()}")
        print(f"Productos con ID de API: {productos_con_id.count()}")
        print(f"Productos sin ID de API: {productos_sin_id.count()}")
        print()
        
        # Identificar productos a eliminar
        productos_a_eliminar = []
        
        # Productos con ID de API que no están en la API
        for producto in productos_con_id:
            if producto.codigo not in ids_api:
                productos_a_eliminar.append(producto)
        
        # Productos sin ID de API (se eliminan todos porque no podemos verificar si están en la API)
        productos_a_eliminar.extend(productos_sin_id)
        
        print("="*70)
        print("ANÁLISIS DE SINCRONIZACIÓN")
        print("="*70)
        print()
        print(f"Productos en la API: {len(ids_api)}")
        print(f"Productos en la BD con ID de API: {productos_con_id.count()}")
        print(f"Productos en la BD sin ID de API: {productos_sin_id.count()}")
        print(f"Productos a eliminar: {len(productos_a_eliminar)}")
        print()
        
        if productos_a_eliminar:
            print("Productos que serán eliminados (primeros 20):")
            for idx, producto in enumerate(productos_a_eliminar[:20], 1):
                print(f"  {idx}. ID: {producto.codigo or 'N/A'} - {producto.nombre} ({producto.codigo_barras})")
            if len(productos_a_eliminar) > 20:
                print(f"  ... y {len(productos_a_eliminar) - 20} más")
            print()
        
        # Confirmar eliminación (no interactivo - ejecutar directamente)
        if len(productos_a_eliminar) > 0:
            print()
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
            
            # Verificar resultado final
            productos_finales = Producto.objects.count()
            productos_con_id_final = Producto.objects.exclude(codigo__isnull=True).exclude(codigo='').count()
            
            print("="*70)
            print("RESULTADO FINAL")
            print("="*70)
            print(f"Productos en la API: {len(ids_api)}")
            print(f"Productos en la BD: {productos_finales}")
            print(f"Productos en la BD con ID de API: {productos_con_id_final}")
            print()
            
            if productos_con_id_final == len(ids_api):
                print("✅ Sincronización exitosa: Todos los productos de la API están en la BD")
            else:
                print(f"⚠️  Diferencia: {abs(productos_con_id_final - len(ids_api))} productos")
                print("   Ejecute la importación para traer los productos faltantes")
        else:
            print("No hay productos a eliminar. La base de datos ya está sincronizada.")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al conectar con la API: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

