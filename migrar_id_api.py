"""
Script para migrar los IDs de API del campo 'codigo' al campo 'id_api'
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
from productos.models import Producto
import requests

# URL de la API
URL_API = 'https://tersacosmeticos.com/prod/api/productos-publicos/?format=json'

def main():
    print("="*70)
    print("MIGRACIÓN DE ID_API")
    print("="*70)
    print()
    
    try:
        # Obtener productos de la API
        print("Obteniendo productos de la API...")
        response = requests.get(URL_API, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        productos_api = data if isinstance(data, list) else (data.get('results', [data]) if isinstance(data, dict) else [data])
        
        # Crear diccionario de ID de API -> código de la API
        api_ids = {}
        for producto_api in productos_api:
            api_id = producto_api.get('id')
            codigo_api = producto_api.get('codigo', '')
            if api_id:
                api_ids[str(api_id)] = codigo_api
        
        print(f"Productos en la API: {len(productos_api)}")
        print(f"IDs únicos en la API: {len(api_ids)}")
        print()
        
        # Obtener productos de la BD
        productos_bd = Producto.objects.all()
        print(f"Total productos en BD: {productos_bd.count()}")
        print()
        
        # Migrar IDs
        print("Migrando IDs de API...")
        actualizados = 0
        sin_id_api = 0
        
        with transaction.atomic():
            for producto in productos_bd:
                # Si el producto tiene un código que es un ID de API (numérico)
                if producto.codigo and producto.codigo.strip():
                    codigo_actual = producto.codigo.strip()
                    
                    # Verificar si el código actual es un ID de API
                    if codigo_actual in api_ids:
                        # El código es un ID de API, migrarlo a id_api
                        producto.id_api = codigo_actual
                        # Actualizar el código con el código real de la API
                        codigo_real = api_ids[codigo_actual]
                        if codigo_real:
                            producto.codigo = codigo_real
                        else:
                            producto.codigo = ''  # Si no hay código en la API, dejar vacío
                        producto.save()
                        actualizados += 1
                    elif not producto.id_api:
                        # El código no es un ID de API, pero el producto no tiene id_api
                        # Intentar encontrar el ID de API por código de barras
                        sin_id_api += 1
        
        print(f"Productos actualizados: {actualizados}")
        print(f"Productos sin ID de API: {sin_id_api}")
        print()
        
        # Verificar resultado
        productos_con_id_api = Producto.objects.exclude(id_api__isnull=True).exclude(id_api='').count()
        print("="*70)
        print("RESULTADO")
        print("="*70)
        print(f"Productos con id_api: {productos_con_id_api}")
        print(f"Productos sin id_api: {Producto.objects.filter(id_api__isnull=True).count() + Producto.objects.filter(id_api='').count()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

