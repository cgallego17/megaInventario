"""
Script para verificar que todos los lugares del sistema muestren
todos los productos (activos e inactivos)
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

from productos.models import Producto
import re

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

def verificar_archivo(archivo_path, problemas):
    """Verifica un archivo Python buscando filtros por activo=True"""
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
            lineas = contenido.split('\n')
            
        # Buscar filtros problemáticos (excluyendo scripts de test y comentarios)
        patrones_problematicos = [
            r'Producto\.objects\.filter\(activo=True\)',
            r'\.filter\(.*activo=True\)',
            r'Producto\.objects\.get\(.*activo=True\)',
        ]
        
        for i, linea in enumerate(lineas, 1):
            # Ignorar comentarios y scripts de test
            if '#' in linea and linea.strip().startswith('#'):
                continue
            if 'test_' in archivo_path or 'test' in archivo_path.lower():
                continue
            
            for patron in patrones_problematicos:
                if re.search(patron, linea):
                    # Verificar si es un filtro opcional (como en productos/views.py)
                    if 'mostrar_solo_activos' in linea or 'solo_activos' in linea:
                        continue  # Es un filtro opcional, está bien
                    
                    problemas.append({
                        'archivo': archivo_path,
                        'linea': i,
                        'codigo': linea.strip(),
                        'tipo': 'Filtro por activo=True'
                    })
    except Exception as e:
        print_error(f"Error al leer {archivo_path}: {str(e)}")

def verificar_vistas():
    """Verifica las vistas principales"""
    print_header("VERIFICACIÓN DE VISTAS")
    
    total_productos = Producto.objects.count()
    total_activos = Producto.objects.filter(activo=True).count()
    total_inactivos = Producto.objects.filter(activo=False).count()
    
    print_info(f"Total productos en BD: {total_productos}")
    print_info(f"  - Activos: {total_activos}")
    print_info(f"  - Inactivos: {total_inactivos}")
    
    # Verificar consultas directas
    print_header("VERIFICACIÓN DE CONSULTAS DIRECTAS")
    
    # Dashboard
    from megaInventario.views import dashboard
    print_info("Dashboard: Verificando código fuente...")
    with open('megaInventario/views.py', 'r', encoding='utf-8') as f:
        contenido = f.read()
        if 'Producto.objects.count()' in contenido:
            print_success("Dashboard usa Producto.objects.count() (todos los productos)")
        elif 'Producto.objects.filter(activo=True).count()' in contenido:
            print_error("Dashboard filtra solo productos activos")
        else:
            print_info("Dashboard: Revisar manualmente")
    
    # Productos
    print_info("Lista productos: Verificando código fuente...")
    with open('productos/views.py', 'r', encoding='utf-8') as f:
        contenido = f.read()
        if 'productos = Producto.objects.all()' in contenido:
            print_success("Lista productos usa Producto.objects.all() (todos los productos)")
        else:
            print_error("Lista productos: Revisar manualmente")
    
    # Conteo
    print_info("Conteo: Verificando código fuente...")
    with open('conteo/views.py', 'r', encoding='utf-8') as f:
        contenido = f.read()
        if 'total_productos = Producto.objects.count()' in contenido:
            print_success("Conteo usa Producto.objects.count() (todos los productos)")
        else:
            print_error("Conteo: Revisar manualmente")
    
    # Comparativos
    print_info("Comparativos: Verificando código fuente...")
    with open('comparativos/views.py', 'r', encoding='utf-8') as f:
        contenido = f.read()
        if 'productos = Producto.objects.all()' in contenido:
            print_success("Comparativos usa Producto.objects.all() (todos los productos)")
        elif 'Producto.objects.filter(activo=True)' in contenido:
            print_error("Comparativos filtra solo productos activos")
        else:
            print_info("Comparativos: Revisar manualmente")
    
    # Reportes
    print_info("Reportes: Verificando código fuente...")
    with open('reportes/views.py', 'r', encoding='utf-8') as f:
        contenido = f.read()
        if 'productos = Producto.objects.all()' in contenido:
            print_success("Reportes usa Producto.objects.all() (todos los productos)")
        else:
            print_error("Reportes: Revisar manualmente")

def verificar_archivos_python():
    """Verifica todos los archivos Python del proyecto"""
    print_header("BÚSQUEDA DE FILTROS POR ACTIVO EN ARCHIVOS")
    
    problemas = []
    archivos_importantes = [
        'megaInventario/views.py',
        'productos/views.py',
        'productos/admin.py',
        'conteo/views.py',
        'conteo/forms.py',
        'comparativos/views.py',
        'reportes/views.py',
        'movimientos/views.py',
    ]
    
    for archivo in archivos_importantes:
        if os.path.exists(archivo):
            verificar_archivo(archivo, problemas)
    
    if problemas:
        print_error(f"Se encontraron {len(problemas)} problema(s):")
        for problema in problemas:
            print(f"  - {problema['archivo']}:{problema['linea']} - {problema['codigo']}")
    else:
        print_success("No se encontraron filtros problemáticos en archivos importantes")

def main():
    print_header("VERIFICACIÓN COMPLETA DE PRODUCTOS EN EL SISTEMA")
    
    total_productos = Producto.objects.count()
    total_activos = Producto.objects.filter(activo=True).count()
    total_inactivos = Producto.objects.filter(activo=False).count()
    
    print_info(f"Total productos en BD: {total_productos}")
    print_info(f"  - Activos: {total_activos}")
    print_info(f"  - Inactivos: {total_inactivos}")
    
    verificar_vistas()
    verificar_archivos_python()
    
    print_header("RESUMEN")
    print_success(f"Total productos que deberían mostrarse: {total_productos}")
    print_info("Todos los lugares del sistema deben mostrar estos {total_productos} productos")
    print_info("(no solo los {total_activos} activos)")

if __name__ == '__main__':
    main()

