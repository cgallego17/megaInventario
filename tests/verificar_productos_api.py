"""
Script para verificar si faltan productos de la API en la base de datos
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

from productos.models import Producto

# URL de la API
URL_API = 'https://tersacosmeticos.com/prod/api/productos-publicos/?format=json'

# Campos del sistema que se mapean desde la API
CAMPOS_SISTEMA = {
    'codigo_barras': ['codigo_barras', 'codigo_barra', 'barcode', 'ean', 'upc', 'codigo_de_barras', 'codigoBarras', 'codigo'],
    'codigo': ['codigo', 'cod', 'code', 'sku', 'codigo_interno', 'codigoInterno', 'id_producto'],
    'nombre': ['nombre', 'nombre_producto', 'name', 'producto', 'descripcion', 'description', 'title', 'titulo'],
    'marca': ['nombre_marca', 'marca', 'brand', 'fabricante', 'manufacturer', 'marca_producto'],
}

def mapear_campo(data, campo_sistema):
    """Mapea un campo de la API al campo del sistema"""
    posibles_campos = CAMPOS_SISTEMA.get(campo_sistema, [campo_sistema])
    
    for campo_api in posibles_campos:
        # Buscar directamente
        if campo_api in data and data[campo_api] is not None:
            return str(data[campo_api]).strip()
        
        # Buscar con diferentes variaciones de mayúsculas/minúsculas
        for key in data.keys():
            if key.lower() == campo_api.lower():
                if data[key] is not None:
                    return str(data[key]).strip()
    
    return None

def obtener_codigo_barras_api(producto_api):
    """Obtiene el código de barras de un producto de la API"""
    codigo_barras = mapear_campo(producto_api, 'codigo_barras')
    if codigo_barras:
        return codigo_barras
    
    # Si no hay código de barras, intentar con código
    codigo = mapear_campo(producto_api, 'codigo')
    if codigo:
        return codigo
    
    return None

def main():
    print("="*70)
    print("VERIFICACIÓN DE PRODUCTOS DE LA API")
    print("="*70)
    print()
    print(f"URL de la API: {URL_API}")
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
        
        # Obtener códigos de barras de la API
        codigos_api = set()
        productos_api_info = {}
        productos_sin_codigo = []
        codigos_duplicados = {}
        
        for idx, producto_api in enumerate(productos_api):
            codigo_barras = obtener_codigo_barras_api(producto_api)
            if codigo_barras:
                # Verificar duplicados
                if codigo_barras in codigos_api:
                    if codigo_barras not in codigos_duplicados:
                        codigos_duplicados[codigo_barras] = [productos_api_info[codigo_barras]['producto_completo']]
                    codigos_duplicados[codigo_barras].append(producto_api)
                else:
                    codigos_api.add(codigo_barras)
                    nombre = mapear_campo(producto_api, 'nombre') or 'Sin nombre'
                    marca = mapear_campo(producto_api, 'marca') or 'Sin marca'
                    productos_api_info[codigo_barras] = {
                        'nombre': nombre,
                        'marca': marca,
                        'producto_completo': producto_api,
                        'indice': idx
                    }
            else:
                nombre = mapear_campo(producto_api, 'nombre') or 'Sin nombre'
                productos_sin_codigo.append({
                    'indice': idx,
                    'nombre': nombre,
                    'producto': producto_api
                })
        
        print(f"Códigos de barras únicos en la API: {len(codigos_api)}")
        if productos_sin_codigo:
            print(f"⚠️  Productos sin código de barras en la API: {len(productos_sin_codigo)}")
        if codigos_duplicados:
            print(f"⚠️  Códigos de barras duplicados en la API: {len(codigos_duplicados)}")
        print()
        
        # Obtener productos de la base de datos
        print("Obteniendo productos de la base de datos...")
        productos_db = Producto.objects.filter(activo=True)
        codigos_db = set(productos_db.values_list('codigo_barras', flat=True))
        
        print(f"Productos activos en la base de datos: {productos_db.count()}")
        print(f"Códigos de barras únicos en BD: {len(codigos_db)}")
        print()
        
        # Comparar
        productos_faltantes = codigos_api - codigos_db
        productos_extra = codigos_db - codigos_api
        
        print("="*70)
        print("RESULTADOS")
        print("="*70)
        print()
        print(f"✅ Productos en API y BD: {len(codigos_api & codigos_db)}")
        print(f"❌ Productos en API pero NO en BD: {len(productos_faltantes)}")
        print(f"⚠️  Productos en BD pero NO en API: {len(productos_extra)}")
        print()
        
        if productos_faltantes:
            print("="*70)
            print("PRODUCTOS FALTANTES EN LA BASE DE DATOS")
            print("="*70)
            print()
            for idx, codigo in enumerate(sorted(productos_faltantes), 1):
                info = productos_api_info.get(codigo, {})
                nombre = info.get('nombre', 'Sin nombre')
                marca = info.get('marca', 'Sin marca')
                print(f"{idx}. Código: {codigo}")
                print(f"   Nombre: {nombre}")
                print(f"   Marca: {marca}")
                print()
            
            print(f"\nTotal de productos faltantes: {len(productos_faltantes)}")
        else:
            print("✅ No hay productos faltantes. Todos los productos de la API están en la base de datos.")
        
        if productos_sin_codigo:
            print()
            print("="*70)
            print("PRODUCTOS EN LA API SIN CÓDIGO DE BARRAS")
            print("="*70)
            print()
            for idx, producto_info in enumerate(productos_sin_codigo[:10], 1):
                print(f"{idx}. Índice en API: {producto_info['indice']}")
                print(f"   Nombre: {producto_info['nombre']}")
                print(f"   Datos: {json.dumps(producto_info['producto'], indent=2, ensure_ascii=False)[:300]}...")
                print()
            if len(productos_sin_codigo) > 10:
                print(f"... y {len(productos_sin_codigo) - 10} más")
        
        if codigos_duplicados:
            print()
            print("="*70)
            print("CÓDIGOS DE BARRAS DUPLICADOS EN LA API")
            print("="*70)
            print()
            for idx, (codigo, productos_dup) in enumerate(list(codigos_duplicados.items())[:10], 1):
                print(f"{idx}. Código: {codigo}")
                print(f"   Aparece {len(productos_dup)} veces en la API")
                for p_idx, producto_dup in enumerate(productos_dup, 1):
                    nombre = mapear_campo(producto_dup, 'nombre') or 'Sin nombre'
                    print(f"   {p_idx}. {nombre}")
                print()
            if len(codigos_duplicados) > 10:
                print(f"... y {len(codigos_duplicados) - 10} códigos duplicados más")
        
        if productos_extra:
            print()
            print("="*70)
            print("PRODUCTOS EN BD PERO NO EN LA API")
            print("="*70)
            print()
            productos_extra_list = productos_db.filter(codigo_barras__in=productos_extra)
            for idx, producto in enumerate(productos_extra_list[:20], 1):  # Mostrar solo los primeros 20
                print(f"{idx}. Código: {producto.codigo_barras} - {producto.nombre} ({producto.marca or 'Sin marca'})")
            if len(productos_extra) > 20:
                print(f"\n... y {len(productos_extra) - 20} más")
        
        print()
        print("="*70)
        print("VERIFICACIÓN COMPLETADA")
        print("="*70)
        
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

