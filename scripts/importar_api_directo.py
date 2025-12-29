"""
Script para importar productos desde API - Ejecución directa
Uso: python importar_api_directo.py <URL_API> [HEADERS_JSON] [MAPEO_JSON]
"""
import os
import sys
import django
import requests
import json
from urllib.parse import urljoin, urlparse
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

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
    'codigo_barras': ['codigo_barras', 'codigo_barra', 'barcode', 'ean', 'upc', 'codigo_de_barras', 'codigoBarras', 'codigoBarras', 'codigo'],
    'codigo': ['codigo', 'cod', 'code', 'sku', 'codigo_interno', 'codigoInterno', 'id_producto'],
    'nombre': ['nombre', 'nombre_producto', 'name', 'producto', 'descripcion', 'description', 'title', 'titulo'],
    'marca': ['nombre_marca', 'marca', 'brand', 'fabricante', 'manufacturer', 'marca_producto'],
    'descripcion': ['descripcion', 'description', 'detalle', 'detalles', 'observaciones', 'notas'],
    'categoria': ['categoria', 'category', 'categ', 'tipo', 'grupo', 'categoria_producto'],
    'atributo': ['atributo', 'nombreAtributo', 'attribute', 'attr', 'caracteristica', 'variante', 'atributos'],
    'precio': ['precio', 'precio1', 'precio_min', 'price', 'precio_unitario', 'precioUnitario', 'cost', 'costo', 'valor'],
    'unidad_medida': ['unidad_medida', 'unidad', 'um', 'unit', 'unidadMedida', 'medida'],
}

def mapear_campo(data, campo_sistema, mapeo_personalizado=None):
    """Mapea un campo de la API al campo del sistema"""
    # Si hay mapeo personalizado, usarlo primero
    if mapeo_personalizado and campo_sistema in mapeo_personalizado:
        campo_api = mapeo_personalizado[campo_sistema]
        # Manejar campos anidados (ej: "ficha_tecnica.descripcion")
        if '.' in campo_api:
            partes = campo_api.split('.')
            valor = data
            for parte in partes:
                if isinstance(valor, dict) and parte in valor:
                    valor = valor[parte]
                else:
                    valor = None
                    break
            if valor is not None and valor != '':
                return str(valor).strip()
        elif campo_api in data:
            valor = data[campo_api]
            if valor is not None and valor != '':
                return str(valor).strip()
    
    posibles_nombres = CAMPOS_SISTEMA.get(campo_sistema, [])
    
    # Buscar el campo en los posibles nombres
    for nombre_posible in posibles_nombres:
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
            return max(0.0, precio)
        except (ValueError, TypeError):
            return 0.0
    elif tipo == 'texto':
        return str(valor).strip() if valor else ''
    else:
        return str(valor).strip()

def descargar_imagen(url_imagen, base_url='https://tersacosmeticos.com'):
    """Descarga una imagen desde una URL y retorna el archivo para guardar"""
    if not url_imagen or url_imagen == '':
        return None
    
    try:
        # Construir URL completa si es relativa
        if url_imagen.startswith('/'):
            url_completa = urljoin(base_url, url_imagen)
        elif url_imagen.startswith('http'):
            url_completa = url_imagen
        else:
            url_completa = urljoin(base_url, '/' + url_imagen)
        
        # Descargar imagen
        response = requests.get(url_completa, timeout=10, stream=True)
        response.raise_for_status()
        
        # Obtener extensión del archivo
        parsed_url = urlparse(url_completa)
        nombre_archivo = os.path.basename(parsed_url.path)
        if not nombre_archivo or '.' not in nombre_archivo:
            # Si no hay extensión, intentar detectar desde content-type
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                nombre_archivo = 'imagen.jpg'
            elif 'png' in content_type:
                nombre_archivo = 'imagen.png'
            else:
                nombre_archivo = 'imagen.jpg'  # Por defecto
        
        # Crear archivo en memoria
        imagen_content = ContentFile(response.content)
        imagen_content.name = nombre_archivo
        
        return imagen_content
    except Exception as e:
        # No imprimir error para cada imagen, solo retornar None
        return None

def procesar_producto_api(producto_api, mapeo_personalizado=None, base_url='https://tersacosmeticos.com'):
    """Procesa un producto de la API y lo convierte al formato del sistema"""
    producto_data = {}
    
    # Guardar ID de la API en el campo id_api
    api_id = producto_api.get('id') or producto_api.get('pk') or producto_api.get('_id')
    if api_id:
        producto_data['id_api'] = str(api_id)
        producto_data['_api_id'] = str(api_id)  # Guardar temporalmente para usar en la importación
    
    # Campos requeridos
    codigo_barras = mapear_campo(producto_api, 'codigo_barras', mapeo_personalizado)
    nombre = mapear_campo(producto_api, 'nombre', mapeo_personalizado)
    
    # Validar campos requeridos
    if not codigo_barras:
        # Intentar usar código como código de barras si no existe
        codigo = mapear_campo(producto_api, 'codigo', mapeo_personalizado)
        if codigo:
            codigo_barras = codigo
        else:
            # Si aún no hay código de barras, usar el ID como último recurso
            if api_id:
                codigo_barras = f"API-{api_id}"
            else:
                return None, None, "Falta codigo_barras o codigo"
    
    if not nombre:
        return None, None, "Falta nombre"
    
    # Manejar descripción anidada en ficha_tecnica
    descripcion = None
    if 'ficha_tecnica' in producto_api and isinstance(producto_api['ficha_tecnica'], dict):
        descripcion = producto_api['ficha_tecnica'].get('descripcion', '')
    if not descripcion:
        descripcion = mapear_campo(producto_api, 'descripcion', mapeo_personalizado)
    
    # Manejar imagen - buscar en diferentes campos posibles
    imagen_url = None
    if 'imagen' in producto_api:
        imagen_url = producto_api['imagen']
    elif 'imgAtr' in producto_api:
        imagen_url = producto_api['imgAtr']
    elif 'imagen_atributo' in producto_api:
        imagen_url = producto_api['imagen_atributo']
    
    # Descargar imagen si existe
    imagen_file = None
    if imagen_url:
        imagen_file = descargar_imagen(imagen_url, base_url)
    
    # Mapear todos los campos
    producto_data['codigo_barras'] = limpiar_valor(codigo_barras)
    # El campo 'codigo' almacena el código que viene de la API (no el ID)
    codigo_api = mapear_campo(producto_api, 'codigo', mapeo_personalizado)
    producto_data['codigo'] = limpiar_valor(codigo_api) if codigo_api else ''
    producto_data['nombre'] = limpiar_valor(nombre)
    # Marca: buscar nombre_marca primero (campo específico de la API de Tersa)
    marca = None
    if 'nombre_marca' in producto_api:
        marca = producto_api['nombre_marca']
    else:
        marca = mapear_campo(producto_api, 'marca', mapeo_personalizado)
    producto_data['marca'] = limpiar_valor(marca) if marca else ''
    producto_data['descripcion'] = limpiar_valor(descripcion) or ''
    producto_data['categoria'] = limpiar_valor(mapear_campo(producto_api, 'categoria', mapeo_personalizado)) or ''
    producto_data['atributo'] = limpiar_valor(mapear_campo(producto_api, 'atributo', mapeo_personalizado)) or ''
    
    # Precio: usar precio1, si no existe usar precio_min
    precio = mapear_campo(producto_api, 'precio', mapeo_personalizado)
    if not precio and 'precio1' in producto_api:
        precio = producto_api['precio1']
    if not precio and 'precio_min' in producto_api:
        precio = producto_api['precio_min']
    producto_data['precio'] = limpiar_valor(precio, tipo='precio')
    
    producto_data['unidad_medida'] = limpiar_valor(mapear_campo(producto_api, 'unidad_medida', mapeo_personalizado)) or 'UN'
    
    # Mapear estado de la API al campo activo
    # El campo 'estado' en la API es un booleano (True/False)
    if 'estado' in producto_api:
        producto_data['activo'] = bool(producto_api['estado'])
    elif 'active' in producto_api:
        producto_data['activo'] = bool(producto_api['active'])
    elif 'status' in producto_api:
        # Si es string, convertir a booleano
        status = producto_api['status']
        if isinstance(status, bool):
            producto_data['activo'] = status
        elif isinstance(status, str):
            producto_data['activo'] = status.lower() in ['activo', 'active', 'true', '1', 'yes', 'si']
        else:
            producto_data['activo'] = bool(status)
    else:
        # Por defecto, activo si no se especifica
        producto_data['activo'] = True
    
    return producto_data, imagen_file, None

def importar_desde_api(url_api, headers=None, metodo='GET', datos_post=None, mapeo_personalizado=None):
    """Importa productos desde una API externa"""
    print("="*70)
    print("IMPORTANDO PRODUCTOS DESDE API")
    print("="*70)
    print()
    print(f"URL de la API: {url_api}")
    print(f"Metodo: {metodo}")
    if headers:
        print(f"Headers: {json.dumps(headers, indent=2)}")
    if mapeo_personalizado:
        print(f"Mapeo personalizado: {json.dumps(mapeo_personalizado, indent=2)}")
    print()
    
    try:
        # Realizar petición a la API
        print("Conectando con la API...")
        if metodo.upper() == 'POST':
            response = requests.post(url_api, json=datos_post, headers=headers, timeout=30)
        else:
            response = requests.get(url_api, headers=headers, timeout=30)
        
        response.raise_for_status()
        print("Conexion exitosa!")
        print()
        
        # Intentar parsear JSON
        try:
            data = response.json()
        except json.JSONDecodeError:
            print("ERROR: La respuesta de la API no es JSON valido")
            return 0, 0, ["La respuesta de la API no es JSON valido"]
        
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
        
        if not productos_api:
            print("ERROR: No se encontraron productos en la respuesta de la API")
            return 0, 0, ["No se encontraron productos en la respuesta de la API"]
        
        print(f"Productos encontrados en la API: {len(productos_api)}")
        print()
        
        # Procesar productos
        print("Procesando productos y descargando imagenes...")
        print("(Esto puede tardar varios minutos debido a la descarga de imagenes)")
        print()
        productos_validos = []
        errores = []
        imagenes_descargadas = 0
        imagenes_fallidas = 0
        
        # Extraer base_url de la URL de la API
        from urllib.parse import urlparse
        parsed_url = urlparse(url_api)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        for idx, producto_api in enumerate(productos_api, 1):
            if idx % 50 == 0:
                print(f"  Procesados {idx}/{len(productos_api)} productos...")
            try:
                producto_data, imagen_file, error = procesar_producto_api(producto_api, mapeo_personalizado, base_url)
                if error:
                    errores.append(f"Producto {idx}: {error}")
                elif producto_data:
                    if imagen_file:
                        imagenes_descargadas += 1
                    productos_validos.append((producto_data, imagen_file))
            except Exception as e:
                errores.append(f"Producto {idx}: Error al procesar - {str(e)}")
        
        print(f"Productos validos: {len(productos_validos)}")
        print(f"Imagenes descargadas: {imagenes_descargadas}")
        print(f"Errores: {len(errores)}")
        print()
        
        # Guardar productos en la base de datos
        print("Guardando productos en la base de datos...")
        creados = 0
        actualizados = 0
        errores_guardado = []
        
        with transaction.atomic():
            for producto_data, imagen_file in productos_validos:
                try:
                    codigo_barras = producto_data['codigo_barras']
                    nombre = producto_data.get('nombre', '')
                    atributo = producto_data.get('atributo', '')
                    api_id = producto_data.pop('_api_id', None)  # Extraer y remover el ID de la API
                    
                    # Usar el ID de la API como identificador único principal
                    # Si un producto tiene el mismo ID de API, es el mismo producto (actualizar)
                    # Si tiene diferente ID de API pero mismo código de barras, es un producto diferente (crear nuevo)
                    producto_existente = None
                    
                    if api_id:
                        # Buscar por ID de la API almacenado en el campo id_api (identificador único)
                        producto_existente = Producto.objects.filter(
                            id_api=str(api_id)
                        ).first()
                    
                    # Si no hay API ID, buscar por código de barras + nombre + atributo como fallback
                    if not producto_existente and not api_id:
                        producto_existente = Producto.objects.filter(
                            codigo_barras=codigo_barras,
                            nombre=nombre,
                            atributo=atributo
                        ).first()
                    
                    if producto_existente:
                        # Actualizar producto existente (mismo ID de API = mismo producto)
                        for key, value in producto_data.items():
                            if key != 'codigo_barras' and key != 'imagen' and key != '_api_id':
                                setattr(producto_existente, key, value)
                        # Asegurar que id_api tenga el ID de la API
                        if api_id:
                            producto_existente.id_api = str(api_id)
                        # Actualizar imagen si existe
                        if imagen_file:
                            producto_existente.imagen.save(imagen_file.name, imagen_file, save=False)
                        producto_existente.save()
                        actualizados += 1
                    else:
                        # Crear nuevo producto (incluso si tiene código de barras duplicado)
                        # El campo id_api ya está en producto_data si existe api_id
                        
                        # Verificar si ya existe un producto con el mismo código de barras
                        # Si existe, modificar el código de barras para hacerlo único
                        producto_mismo_codigo = Producto.objects.filter(codigo_barras=codigo_barras).first()
                        
                        if producto_mismo_codigo:
                            # Hay un producto con el mismo código pero diferente ID de API, crear uno nuevo
                            # Modificar el código de barras para hacerlo único
                            if api_id:
                                # Usar el ID de la API para crear un código único
                                codigo_barras_unico = f"{codigo_barras}-ID{api_id}"
                            elif atributo:
                                # Usar el atributo para diferenciar
                                codigo_barras_unico = f"{codigo_barras}-{atributo[:20]}".replace(' ', '_').replace('/', '_').replace('\\', '_')
                            else:
                                # Si no hay atributo ni API ID, usar un contador basado en productos con mismo código
                                productos_mismo_codigo = Producto.objects.filter(codigo_barras__startswith=codigo_barras).count()
                                codigo_barras_unico = f"{codigo_barras}-V{productos_mismo_codigo + 1}"
                            
                            # Verificar que el código único no exista
                            contador = 1
                            codigo_original = codigo_barras_unico
                            while Producto.objects.filter(codigo_barras=codigo_barras_unico).exists():
                                if api_id:
                                    codigo_barras_unico = f"{codigo_barras}-ID{api_id}-{contador}"
                                elif atributo:
                                    codigo_barras_unico = f"{codigo_original}-{contador}"
                                else:
                                    productos_mismo_codigo = Producto.objects.filter(codigo_barras__startswith=codigo_barras).count()
                                    codigo_barras_unico = f"{codigo_barras}-V{productos_mismo_codigo + contador + 1}"
                                contador += 1
                            
                            producto_data['codigo_barras'] = codigo_barras_unico
                        
                        # Crear nuevo producto (con su estado activo/inactivo según la API)
                        producto = Producto(**{k: v for k, v in producto_data.items() if k != 'imagen'})
                        if imagen_file:
                            producto.imagen.save(imagen_file.name, imagen_file, save=False)
                        producto.save()
                        creados += 1
                        
                except Exception as e:
                    errores_guardado.append(f"Error al guardar producto {producto_data.get('codigo_barras', 'N/A')}: {str(e)}")
        
        print()
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
    if len(sys.argv) < 2:
        print("Uso: python importar_api_directo.py <URL_API> [HEADERS_JSON] [MAPEO_JSON]")
        print()
        print("Ejemplos:")
        print("  python importar_api_directo.py https://api.ejemplo.com/productos")
        print("  python importar_api_directo.py https://api.ejemplo.com/productos '{\"Authorization\": \"Bearer token\"}'")
        print("  python importar_api_directo.py https://api.ejemplo.com/productos '{\"Authorization\": \"Bearer token\"}' '{\"codigo_barras\": \"barcode\", \"nombre\": \"product_name\"}'")
        sys.exit(1)
    
    url_api = sys.argv[1]
    headers = None
    mapeo = None
    
    if len(sys.argv) > 2:
        try:
            headers = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print(f"ERROR: El formato de headers no es JSON valido: {sys.argv[2]}")
            sys.exit(1)
    
    if len(sys.argv) > 3:
        try:
            mapeo = json.loads(sys.argv[3])
        except json.JSONDecodeError:
            print(f"ERROR: El formato de mapeo no es JSON valido: {sys.argv[3]}")
            sys.exit(1)
    
    importar_desde_api(url_api, headers=headers, mapeo_personalizado=mapeo)

