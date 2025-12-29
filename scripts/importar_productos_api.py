"""
Script para importar productos desde una API externa
Solo mapea los campos necesarios del sistema
"""
import os
import sys
import django
import requests
import json

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

# Campos del sistema que se mapean desde la API
CAMPOS_SISTEMA = {
    'codigo_barras': ['codigo_barras', 'barcode', 'ean', 'upc', 'codigo_de_barras', 'codigoBarras', 'codigoBarras'],
    'codigo': ['codigo', 'cod', 'code', 'sku', 'codigo_interno', 'codigoInterno', 'id_producto'],
    'nombre': ['nombre', 'name', 'producto', 'descripcion', 'description', 'title', 'titulo'],
    'marca': ['marca', 'brand', 'fabricante', 'manufacturer', 'marca_producto'],
    'descripcion': ['descripcion', 'description', 'detalle', 'detalles', 'observaciones', 'notas'],
    'categoria': ['categoria', 'category', 'categ', 'tipo', 'grupo', 'categoria_producto'],
    'atributo': ['atributo', 'attribute', 'attr', 'caracteristica', 'variante', 'atributos'],
    'precio': ['precio', 'price', 'precio_unitario', 'precioUnitario', 'cost', 'costo', 'valor'],
    'unidad_medida': ['unidad_medida', 'unidad', 'um', 'unit', 'unidadMedida', 'medida'],
}

def mapear_campo(data, campo_sistema):
    """Mapea un campo de la API al campo del sistema"""
    posibles_nombres = CAMPOS_SISTEMA.get(campo_sistema, [])
    
    # Buscar el campo en los posibles nombres
    for nombre_posible in posibles_nombres:
        # Buscar en diferentes niveles (directo, anidado con punto, etc.)
        if nombre_posible in data:
            valor = data[nombre_posible]
            if valor is not None and valor != '':
                return str(valor).strip()
        
        # Buscar con diferentes variaciones de mayúsculas/minúsculas
        for key in data.keys():
            if key.lower() == nombre_posible.lower():
                valor = data[key]
                if valor is not None and valor != '':
                    return str(valor).strip()
    
    return None

def limpiar_valor(valor, tipo='texto'):
    """Limpia y convierte un valor según su tipo"""
    if valor is None or valor == '':
        return None if tipo != 'precio' else 0.0
    
    if tipo == 'precio':
        try:
            precio = float(valor)
            return max(0.0, precio)  # No permitir precios negativos
        except (ValueError, TypeError):
            return 0.0
    elif tipo == 'texto':
        return str(valor).strip() if valor else ''
    else:
        return str(valor).strip()

def procesar_producto_api(producto_api):
    """Procesa un producto de la API y lo convierte al formato del sistema"""
    producto_data = {}
    
    # Campos requeridos
    codigo_barras = mapear_campo(producto_api, 'codigo_barras')
    nombre = mapear_campo(producto_api, 'nombre')
    
    # Validar campos requeridos
    if not codigo_barras:
        # Intentar usar código como código de barras si no existe
        codigo = mapear_campo(producto_api, 'codigo')
        if codigo:
            codigo_barras = codigo
        else:
            return None, "Falta codigo_barras o codigo"
    
    if not nombre:
        return None, "Falta nombre"
    
    # Mapear todos los campos
    producto_data['codigo_barras'] = limpiar_valor(codigo_barras)
    producto_data['codigo'] = limpiar_valor(mapear_campo(producto_api, 'codigo')) or ''
    producto_data['nombre'] = limpiar_valor(nombre)
    producto_data['marca'] = limpiar_valor(mapear_campo(producto_api, 'marca')) or ''
    producto_data['descripcion'] = limpiar_valor(mapear_campo(producto_api, 'descripcion')) or ''
    producto_data['categoria'] = limpiar_valor(mapear_campo(producto_api, 'categoria')) or ''
    producto_data['atributo'] = limpiar_valor(mapear_campo(producto_api, 'atributo')) or ''
    producto_data['precio'] = limpiar_valor(mapear_campo(producto_api, 'precio'), tipo='precio')
    producto_data['unidad_medida'] = limpiar_valor(mapear_campo(producto_api, 'unidad_medida')) or 'UN'
    producto_data['activo'] = True
    
    return producto_data, None

def importar_desde_api(url_api, headers=None, metodo='GET', datos_post=None, mapeo_personalizado=None):
    """
    Importa productos desde una API externa
    
    Args:
        url_api: URL de la API
        headers: Diccionario con headers (ej: {'Authorization': 'Bearer token'})
        metodo: Método HTTP ('GET' o 'POST')
        datos_post: Datos para POST (si aplica)
        mapeo_personalizado: Diccionario con mapeo personalizado de campos
                           ej: {'codigo_barras': 'barcode', 'nombre': 'product_name'}
    
    Returns:
        tupla: (productos_creados, productos_actualizados, errores)
    """
    print("="*70)
    print("IMPORTANDO PRODUCTOS DESDE API")
    print("="*70)
    print()
    print(f"URL de la API: {url_api}")
    print(f"Metodo: {metodo}")
    print()
    
    # Aplicar mapeo personalizado si existe
    if mapeo_personalizado:
        for campo_sistema, campo_api in mapeo_personalizado.items():
            if campo_sistema in CAMPOS_SISTEMA:
                CAMPOS_SISTEMA[campo_sistema].insert(0, campo_api)
        print(f"Mapeo personalizado aplicado: {mapeo_personalizado}")
        print()
    
    try:
        # Realizar petición a la API
        if metodo.upper() == 'POST':
            response = requests.post(url_api, json=datos_post, headers=headers, timeout=30)
        else:
            response = requests.get(url_api, headers=headers, timeout=30)
        
        response.raise_for_status()
        
        # Intentar parsear JSON
        try:
            data = response.json()
        except json.JSONDecodeError:
            print("ERROR: La respuesta de la API no es JSON valido")
            return 0, 0, ["La respuesta de la API no es JSON valido"]
        
        # Detectar formato de respuesta
        productos_api = []
        
        if isinstance(data, list):
            # Si es una lista directa
            productos_api = data
        elif isinstance(data, dict):
            # Buscar en diferentes claves comunes
            posibles_claves = ['data', 'products', 'productos', 'items', 'result', 'results', 'content']
            for clave in posibles_claves:
                if clave in data and isinstance(data[clave], list):
                    productos_api = data[clave]
                    break
            
            # Si no se encontró, usar el diccionario completo como un producto
            if not productos_api:
                productos_api = [data]
        
        if not productos_api:
            print("ERROR: No se encontraron productos en la respuesta de la API")
            return 0, 0, ["No se encontraron productos en la respuesta de la API"]
        
        print(f"Productos encontrados en la API: {len(productos_api)}")
        print()
        
        # Procesar productos
        productos_validos = []
        errores = []
        
        for idx, producto_api in enumerate(productos_api, 1):
            try:
                producto_data, error = procesar_producto_api(producto_api)
                if error:
                    errores.append(f"Producto {idx}: {error}")
                elif producto_data:
                    productos_validos.append(producto_data)
            except Exception as e:
                errores.append(f"Producto {idx}: Error al procesar - {str(e)}")
        
        print(f"Productos validos: {len(productos_validos)}")
        print(f"Errores: {len(errores)}")
        print()
        
        # Guardar productos en la base de datos
        creados = 0
        actualizados = 0
        errores_guardado = []
        
        with transaction.atomic():
            for producto_data in productos_validos:
                try:
                    codigo_barras = producto_data['codigo_barras']
                    
                    producto_existente = Producto.objects.filter(codigo_barras=codigo_barras).first()
                    
                    if producto_existente:
                        # Actualizar producto existente
                        for key, value in producto_data.items():
                            if key != 'codigo_barras':  # No actualizar el código de barras
                                setattr(producto_existente, key, value)
                        producto_existente.save()
                        actualizados += 1
                    else:
                        # Crear nuevo producto
                        Producto.objects.create(**producto_data)
                        creados += 1
                        
                except Exception as e:
                    errores_guardado.append(f"Error al guardar producto {producto_data.get('codigo_barras', 'N/A')}: {str(e)}")
        
        print("="*70)
        print("IMPORTACION COMPLETADA")
        print("="*70)
        print(f"  - Productos creados: {creados}")
        print(f"  - Productos actualizados: {actualizados}")
        print(f"  - Errores de procesamiento: {len(errores)}")
        print(f"  - Errores de guardado: {len(errores_guardado)}")
        print()
        
        if errores:
            print("Errores de procesamiento:")
            for error in errores[:10]:
                print(f"  - {error}")
            if len(errores) > 10:
                print(f"  ... y {len(errores) - 10} errores mas")
            print()
        
        if errores_guardado:
            print("Errores de guardado:")
            for error in errores_guardado[:10]:
                print(f"  - {error}")
            if len(errores_guardado) > 10:
                print(f"  ... y {len(errores_guardado) - 10} errores mas")
        
        return creados, actualizados, errores + errores_guardado
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR al conectar con la API: {str(e)}")
        return 0, 0, [f"Error al conectar con la API: {str(e)}"]
    except Exception as e:
        print(f"ERROR inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0, 0, [f"Error inesperado: {str(e)}"]

if __name__ == '__main__':
    # Ejemplo de uso
    print("Ejemplo de uso:")
    print()
    print("1. API simple (GET):")
    print("   importar_desde_api('https://api.ejemplo.com/productos')")
    print()
    print("2. API con autenticacion:")
    print("   headers = {'Authorization': 'Bearer tu_token'}")
    print("   importar_desde_api('https://api.ejemplo.com/productos', headers=headers)")
    print()
    print("3. API con mapeo personalizado:")
    print("   mapeo = {'codigo_barras': 'barcode', 'nombre': 'product_name'}")
    print("   importar_desde_api('https://api.ejemplo.com/productos', mapeo_personalizado=mapeo)")
    print()
    print("4. API POST:")
    print("   datos = {'filtro': 'activos'}")
    print("   importar_desde_api('https://api.ejemplo.com/productos', metodo='POST', datos_post=datos)")
    print()
    print("="*70)
    print("Para usar, importe la funcion y llame con los parametros de su API")
    print("="*70)
    
    # Si se pasan argumentos, ejecutar importación
    if len(sys.argv) > 1:
        url_api = sys.argv[1]
        headers = None
        mapeo = None
        
        # Procesar argumentos adicionales
        if len(sys.argv) > 2:
            # Intentar parsear headers como JSON
            try:
                headers = json.loads(sys.argv[2])
            except:
                pass
        
        if len(sys.argv) > 3:
            # Intentar parsear mapeo como JSON
            try:
                mapeo = json.loads(sys.argv[3])
            except:
                pass
        
        importar_desde_api(url_api, headers=headers, mapeo_personalizado=mapeo)

