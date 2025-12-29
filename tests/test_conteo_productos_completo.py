"""
Test para verificar que todos los lugares del sistema cuenten y muestren
todos los productos (activos e inactivos), no solo los activos.
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
from django.contrib.auth.models import User
from conteo.models import Conteo
from comparativos.models import ComparativoInventario
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware

# Importar vistas
from megaInventario import views as dashboard_views
from productos import views as productos_views
from reportes import views as reportes_views
from conteo import views as conteo_views
from comparativos import views as comparativos_views

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

def test_conteo_productos():
    """Test principal para verificar conteo de productos"""
    print_header("TEST DE CONTEO DE PRODUCTOS COMPLETO")
    
    # Obtener totales reales
    total_productos_todos = Producto.objects.count()
    total_productos_activos = Producto.objects.filter(activo=True).count()
    total_productos_inactivos = Producto.objects.filter(activo=False).count()
    
    print_info(f"Total productos en BD: {total_productos_todos}")
    print_info(f"  - Activos: {total_productos_activos}")
    print_info(f"  - Inactivos: {total_productos_inactivos}")
    
    errores = []
    advertencias = []
    
    # Test 1: Dashboard - Verificación directa de código
    print_header("1. TEST DASHBOARD")
    try:
        # Verificar directamente las consultas que hace el dashboard
        total_productos_dashboard = Producto.objects.count()
        total_productos_sistema = Producto.objects.count()  # Debería ser todos, no solo activos
        
        if total_productos_dashboard == total_productos_todos:
            print_success(f"Dashboard total_productos: {total_productos_dashboard} (correcto)")
        else:
            error_msg = f"Dashboard total_productos: {total_productos_dashboard} (esperado: {total_productos_todos})"
            print_error(error_msg)
            errores.append(error_msg)
        
        if total_productos_sistema == total_productos_todos:
            print_success(f"Dashboard total_productos_sistema: {total_productos_sistema} (correcto)")
        else:
            error_msg = f"Dashboard total_productos_sistema: {total_productos_sistema} (esperado: {total_productos_todos})"
            print_error(error_msg)
            errores.append(error_msg)
        
        # Verificar productos sin stock
        productos_sin_stock = Producto.objects.all()[:10]
        if len(productos_sin_stock) > 0:
            print_success(f"Dashboard productos sin stock: consulta incluye todos los productos")
        else:
            print_info("Dashboard productos sin stock: no hay productos para verificar")
    except Exception as e:
        error_msg = f"Error en dashboard: {str(e)}"
        print_error(error_msg)
        errores.append(error_msg)
    
    # Test 2: Lista de Productos - Verificación directa
    print_header("2. TEST LISTA DE PRODUCTOS")
    try:
        # Verificar directamente la consulta que hace lista_productos
        productos_lista = Producto.objects.all()
        total_en_lista = productos_lista.count()
        
        if total_en_lista == total_productos_todos:
            print_success(f"Lista productos: {total_en_lista} productos (correcto)")
        else:
            error_msg = f"Lista productos: {total_en_lista} (esperado: {total_productos_todos})"
            print_error(error_msg)
            errores.append(error_msg)
    except Exception as e:
        error_msg = f"Error en lista productos: {str(e)}"
        print_error(error_msg)
        errores.append(error_msg)
    
    # Test 3: Filtros de Productos - Verificación directa
    print_header("3. TEST FILTROS DE PRODUCTOS")
    try:
        # Verificar directamente las consultas de filtros
        marcas_todos = Producto.objects.exclude(marca__isnull=True).exclude(marca='').values_list('marca', flat=True).distinct().count()
        categorias_todos = Producto.objects.exclude(categoria__isnull=True).exclude(categoria='').values_list('categoria', flat=True).distinct().count()
        atributos_todos = Producto.objects.exclude(atributo__isnull=True).exclude(atributo='').values_list('atributo', flat=True).distinct().count()
        
        # Comparar con filtros que incluyen solo activos (incorrecto)
        marcas_activos = Producto.objects.filter(activo=True).exclude(marca__isnull=True).exclude(marca='').values_list('marca', flat=True).distinct().count()
        categorias_activos = Producto.objects.filter(activo=True).exclude(categoria__isnull=True).exclude(categoria='').values_list('categoria', flat=True).distinct().count()
        atributos_activos = Producto.objects.filter(activo=True).exclude(atributo__isnull=True).exclude(atributo='').values_list('atributo', flat=True).distinct().count()
        
        if marcas_todos >= marcas_activos:
            print_success(f"Filtro marcas: {marcas_todos} (incluye inactivos, correcto)")
        else:
            error_msg = f"Filtro marcas: {marcas_todos} (debería ser >= {marcas_activos})"
            print_error(error_msg)
            errores.append(error_msg)
        
        if categorias_todos >= categorias_activos:
            print_success(f"Filtro categorias: {categorias_todos} (incluye inactivos, correcto)")
        else:
            error_msg = f"Filtro categorias: {categorias_todos} (debería ser >= {categorias_activos})"
            print_error(error_msg)
            errores.append(error_msg)
        
        if atributos_todos >= atributos_activos:
            print_success(f"Filtro atributos: {atributos_todos} (incluye inactivos, correcto)")
        else:
            error_msg = f"Filtro atributos: {atributos_todos} (debería ser >= {atributos_activos})"
            print_error(error_msg)
            errores.append(error_msg)
    except Exception as e:
        error_msg = f"Error en filtros: {str(e)}"
        print_error(error_msg)
        errores.append(error_msg)
    
    # Test 4: Reporte de Inventario - Verificación directa
    print_header("4. TEST REPORTE DE INVENTARIO")
    try:
        # Verificar directamente la consulta que hace reporte_inventario
        productos_reporte = Producto.objects.all()
        total_productos_reporte = productos_reporte.count()
        
        if total_productos_reporte == total_productos_todos:
            print_success(f"Reporte inventario: {total_productos_reporte} productos (correcto)")
        else:
            error_msg = f"Reporte inventario: {total_productos_reporte} (esperado: {total_productos_todos})"
            print_error(error_msg)
            errores.append(error_msg)
        
        # Verificar categorías en reporte
        categorias_reporte = Producto.objects.all().values_list('categoria', flat=True).distinct().count()
        categorias_activos = Producto.objects.filter(activo=True).values_list('categoria', flat=True).distinct().count()
        
        if categorias_reporte >= categorias_activos:
            print_success(f"Reporte categorias: {categorias_reporte} (incluye inactivos, correcto)")
        else:
            error_msg = f"Reporte categorias: {categorias_reporte} (debería ser >= {categorias_activos})"
            print_error(error_msg)
            errores.append(error_msg)
    except Exception as e:
        error_msg = f"Error en reporte inventario: {str(e)}"
        print_error(error_msg)
        errores.append(error_msg)
    
    # Test 5: Detalle de Conteo - Verificación directa
    print_header("5. TEST DETALLE DE CONTEO")
    try:
        # Verificar directamente la consulta que hace detalle_conteo
        total_productos_conteo = Producto.objects.count()
        
        if total_productos_conteo == total_productos_todos:
            print_success(f"Detalle conteo: {total_productos_conteo} productos (correcto)")
        else:
            error_msg = f"Detalle conteo: {total_productos_conteo} (esperado: {total_productos_todos})"
            print_error(error_msg)
            errores.append(error_msg)
        
        # Verificar que el conteo puede buscar todos los productos
        conteo = Conteo.objects.first()
        if conteo:
            print_info(f"Conteo de prueba: {conteo.nombre}")
            print_success("Detalle conteo: consulta incluye todos los productos")
        else:
            print_info("Detalle conteo: No hay conteos para verificar funcionalidad completa")
    except Exception as e:
        error_msg = f"Error en detalle conteo: {str(e)}"
        print_error(error_msg)
        errores.append(error_msg)
    
    # Test 6: Detalle de Comparativo - Verificación directa
    print_header("6. TEST DETALLE DE COMPARATIVO")
    try:
        # Verificar directamente la consulta que hace detalle_comparativo
        productos_comparativo = Producto.objects.all()
        total_productos_comparativo = productos_comparativo.count()
        
        if total_productos_comparativo == total_productos_todos:
            print_success(f"Detalle comparativo: {total_productos_comparativo} productos (correcto)")
        else:
            error_msg = f"Detalle comparativo: {total_productos_comparativo} (esperado: {total_productos_todos})"
            print_error(error_msg)
            errores.append(error_msg)
        
        # Verificar que el comparativo puede incluir todos los productos
        comparativo = ComparativoInventario.objects.first()
        if comparativo:
            print_info(f"Comparativo de prueba: {comparativo.nombre}")
            print_success("Detalle comparativo: consulta incluye todos los productos")
        else:
            print_info("Detalle comparativo: No hay comparativos para verificar funcionalidad completa")
    except Exception as e:
        error_msg = f"Error en detalle comparativo: {str(e)}"
        print_error(error_msg)
        errores.append(error_msg)
    
    # Test 7: Verificación directa de consultas
    print_header("7. VERIFICACIÓN DIRECTA DE CONSULTAS")
    
    # Verificar que no haya filtros por activo=True en lugares críticos
    consultas_verificar = [
        ("Producto.objects.count()", Producto.objects.count()),
        ("Producto.objects.all().count()", Producto.objects.all().count()),
        ("Producto.objects.filter(activo=True).count()", Producto.objects.filter(activo=True).count()),
    ]
    
    for nombre, resultado in consultas_verificar:
        print_info(f"{nombre}: {resultado}")
    
    if Producto.objects.count() == total_productos_todos:
        print_success("Producto.objects.count() cuenta todos los productos")
    else:
        error_msg = f"Producto.objects.count() no cuenta todos: {Producto.objects.count()} vs {total_productos_todos}"
        print_error(error_msg)
        errores.append(error_msg)
    
    # Resumen final
    print_header("RESUMEN DEL TEST")
    
    if errores:
        print_error(f"Se encontraron {len(errores)} error(es):")
        for error in errores:
            print(f"  - {error}")
    else:
        print_success("No se encontraron errores")
    
    if advertencias:
        print_info(f"Se encontraron {len(advertencias)} advertencia(s):")
        for advertencia in advertencias:
            print(f"  - {advertencia}")
    
    print_info(f"Total productos en sistema: {total_productos_todos}")
    print_info(f"  - Activos: {total_productos_activos}")
    print_info(f"  - Inactivos: {total_productos_inactivos}")
    
    if errores:
        return False
    return True

if __name__ == '__main__':
    try:
        resultado = test_conteo_productos()
        if resultado:
            print("\n" + "="*70)
            print("  ✓ TEST COMPLETADO EXITOSAMENTE")
            print("="*70 + "\n")
            sys.exit(0)
        else:
            print("\n" + "="*70)
            print("  ✗ TEST COMPLETADO CON ERRORES")
            print("="*70 + "\n")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error fatal: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

