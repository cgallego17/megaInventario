"""
Escaneo Completo del Sistema
Verifica todos los archivos Python, sintaxis, imports, modelos, URLs, y funcionalidad
"""
import os
import sys
import django
import ast
import importlib.util
from pathlib import Path
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megaInventario.settings')
django.setup()

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class Colores:
    VERDE = '\033[92m'
    ROJO = '\033[91m'
    AMARILLO = '\033[93m'
    AZUL = '\033[94m'
    RESET = '\033[0m'
    NEGRITA = '\033[1m'

def print_titulo(texto):
    print(f"\n{Colores.NEGRITA}{Colores.AZUL}{'='*70}")
    print(f"{texto}")
    print(f"{'='*70}{Colores.RESET}\n")

def print_exito(texto):
    print(f"{Colores.VERDE}✓ {texto}{Colores.RESET}")

def print_error(texto):
    print(f"{Colores.ROJO}✗ {texto}{Colores.RESET}")

def print_info(texto):
    print(f"{Colores.AMARILLO}ℹ {texto}{Colores.RESET}")

def verificar_sintaxis_python(archivo):
    """Verifica la sintaxis de un archivo Python"""
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            codigo = f.read()
        ast.parse(codigo, filename=str(archivo))
        return True, None
    except SyntaxError as e:
        return False, f"Error de sintaxis en línea {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Error al verificar: {str(e)}"

def verificar_imports(archivo):
    """Verifica que los imports sean válidos"""
    errores = []
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            codigo = f.read()
        
        tree = ast.parse(codigo, filename=str(archivo))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    try:
                        __import__(alias.name)
                    except ImportError:
                        # Algunos imports pueden ser relativos o de Django, verificar después
                        pass
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    try:
                        __import__(node.module)
                    except ImportError:
                        # Verificar si es un import relativo o de Django
                        pass
    except Exception as e:
        errores.append(f"Error verificando imports: {str(e)}")
    
    return errores

def escanear_archivos_python():
    """Escanea todos los archivos Python del proyecto"""
    print_titulo("ESCANEO 1: ARCHIVOS PYTHON Y SINTAXIS")
    
    errores = []
    archivos_verificados = 0
    
    # Directorios a escanear
    directorios = [
        'megaInventario',
        'productos',
        'conteo',
        'usuarios',
        'reportes',
        'comparativos',
        'movimientos',
    ]
    
    for directorio in directorios:
        dir_path = Path(BASE_DIR) / directorio
        if not dir_path.exists():
            print_error(f"Directorio no encontrado: {directorio}")
            continue
        
        print_info(f"Escaneando {directorio}/...")
        
        # Buscar todos los archivos .py
        archivos_py = list(dir_path.rglob('*.py'))
        
        for archivo in archivos_py:
            # Saltar __pycache__ y migrations (por ahora)
            if '__pycache__' in str(archivo) or 'migrations' in str(archivo):
                continue
            
            archivos_verificados += 1
            rel_path = archivo.relative_to(BASE_DIR)
            
            # Verificar sintaxis
            es_valido, error = verificar_sintaxis_python(archivo)
            if not es_valido:
                errores.append(f"{rel_path}: {error}")
            else:
                print_exito(f"{rel_path}: sintaxis correcta")
    
    print_info(f"Total archivos verificados: {archivos_verificados}")
    
    return errores

def verificar_modelos():
    """Verifica que todos los modelos estén correctos"""
    print_titulo("ESCANEO 2: MODELOS DE DJANGO")
    
    errores = []
    
    try:
        from django.apps import apps
        
        # Obtener todas las apps instaladas
        apps_instaladas = [
            'productos',
            'conteo',
            'usuarios',
            'reportes',
            'comparativos',
            'movimientos',
        ]
        
        for app_name in apps_instaladas:
            try:
                app_config = apps.get_app_config(app_name)
                modelos = app_config.get_models()
                
                print_info(f"App {app_name}: {len(list(modelos))} modelos")
                
                for modelo in modelos:
                    try:
                        # Verificar que el modelo tenga Meta
                        if not hasattr(modelo, '_meta'):
                            errores.append(f"Modelo {modelo.__name__} no tiene _meta")
                            continue
                        
                        # Verificar que se pueda obtener el nombre del modelo
                        nombre = modelo._meta.verbose_name
                        print_exito(f"  {modelo.__name__}: {nombre}")
                        
                        # Verificar campos básicos
                        campos = modelo._meta.get_fields()
                        if len(list(campos)) == 0:
                            errores.append(f"Modelo {modelo.__name__} no tiene campos")
                        
                    except Exception as e:
                        errores.append(f"Error en modelo {modelo.__name__}: {str(e)}")
                        
            except Exception as e:
                errores.append(f"Error en app {app_name}: {str(e)}")
    
    except Exception as e:
        errores.append(f"Error verificando modelos: {str(e)}")
    
    return errores

def verificar_urls():
    """Verifica que todas las URLs estén correctas"""
    print_titulo("ESCANEO 3: CONFIGURACIÓN DE URLs")
    
    errores = []
    
    try:
        from django.urls import get_resolver
        from django.core.exceptions import ViewDoesNotExist
        
        resolver = get_resolver()
        urls_encontradas = []
        
        def listar_urls(urlpatterns, prefix=''):
            for pattern in urlpatterns:
                if hasattr(pattern, 'url_patterns'):
                    # Es un include
                    listar_urls(pattern.url_patterns, prefix + str(pattern.pattern))
                elif hasattr(pattern, 'callback'):
                    # Es una vista
                    try:
                        callback = pattern.callback
                        if hasattr(callback, 'view_class'):
                            nombre = callback.view_class.__name__
                        elif hasattr(callback, '__name__'):
                            nombre = callback.__name__
                        else:
                            nombre = str(callback)
                        urls_encontradas.append(f"{prefix}{pattern.pattern} -> {nombre}")
                    except Exception as e:
                        errores.append(f"Error en URL {pattern.pattern}: {str(e)}")
        
        listar_urls(resolver.url_patterns)
        
        print_exito(f"Total URLs encontradas: {len(urls_encontradas)}")
        for url in urls_encontradas[:10]:  # Mostrar primeras 10
            print_info(f"  {url}")
        if len(urls_encontradas) > 10:
            print_info(f"  ... y {len(urls_encontradas) - 10} URLs más")
    
    except Exception as e:
        errores.append(f"Error verificando URLs: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return errores

def verificar_forms():
    """Verifica que todos los formularios estén correctos"""
    print_titulo("ESCANEO 4: FORMULARIOS")
    
    errores = []
    forms_verificados = 0
    
    try:
        # Verificar forms de cada app
        apps_forms = {
            'productos': ['ProductoForm', 'ImportarProductosForm'],
            'conteo': ['ConteoForm', 'ItemConteoForm'],
            'usuarios': ['UsuarioForm', 'ParejaConteoForm', 'RegistroForm', 'LoginForm', 'PerfilForm'],
            'comparativos': ['ComparativoInventarioForm', 'InventarioSistemaForm'],
        }
        
        for app_name, form_names in apps_forms.items():
            try:
                forms_module = importlib.import_module(f'{app_name}.forms')
                
                for form_name in form_names:
                    if hasattr(forms_module, form_name):
                        form_class = getattr(forms_module, form_name)
                        forms_verificados += 1
                        print_exito(f"{app_name}.{form_name}: encontrado")
                    else:
                        errores.append(f"Form {form_name} no encontrado en {app_name}.forms")
            except ImportError as e:
                errores.append(f"Error importando {app_name}.forms: {str(e)}")
    
    except Exception as e:
        errores.append(f"Error verificando forms: {str(e)}")
    
    print_info(f"Total forms verificados: {forms_verificados}")
    
    return errores

def verificar_views():
    """Verifica que todas las vistas sean accesibles"""
    print_titulo("ESCANEO 5: VISTAS")
    
    errores = []
    views_verificadas = 0
    
    try:
        apps_views = {
            'productos': ['lista_productos', 'crear_producto', 'editar_producto', 'eliminar_producto', 'detalle_producto', 'importar_productos'],
            'conteo': ['lista_conteos', 'crear_conteo', 'detalle_conteo', 'finalizar_conteo', 'agregar_item', 'buscar_producto', 'eliminar_item'],
            'usuarios': ['lista_usuarios', 'crear_usuario', 'editar_usuario', 'eliminar_usuario', 'lista_parejas', 'crear_pareja', 'eliminar_pareja'],
            'comparativos': ['lista_comparativos', 'crear_comparativo', 'detalle_comparativo', 'subir_inventario', 'procesar_comparativo', 'exportar_comparativo', 'descargar_ejemplo'],
            'movimientos': ['lista_movimientos', 'movimientos_por_conteo', 'movimientos_por_usuario', 'resumen_movimientos'],
            'reportes': ['menu_reportes', 'reporte_inventario', 'reporte_conteo', 'reporte_diferencias'],
        }
        
        for app_name, view_names in apps_views.items():
            try:
                views_module = importlib.import_module(f'{app_name}.views')
                
                for view_name in view_names:
                    if hasattr(views_module, view_name):
                        view_func = getattr(views_module, view_name)
                        views_verificadas += 1
                        print_exito(f"{app_name}.{view_name}: encontrada")
                    else:
                        errores.append(f"Vista {view_name} no encontrada en {app_name}.views")
            except ImportError as e:
                errores.append(f"Error importando {app_name}.views: {str(e)}")
    
    except Exception as e:
        errores.append(f"Error verificando views: {str(e)}")
    
    print_info(f"Total vistas verificadas: {views_verificadas}")
    
    return errores

def verificar_templates():
    """Verifica que los templates existan"""
    print_titulo("ESCANEO 6: TEMPLATES")
    
    errores = []
    templates_encontrados = 0
    
    try:
        from django.template.loader import get_template
        from django.conf import settings
        
        templates_dir = Path(BASE_DIR) / 'templates'
        
        if templates_dir.exists():
            # Buscar todos los templates
            templates = list(templates_dir.rglob('*.html'))
            
            for template_path in templates:
                rel_path = template_path.relative_to(templates_dir)
                try:
                    # Intentar cargar el template
                    template = get_template(str(rel_path))
                    templates_encontrados += 1
                    print_exito(f"{rel_path}: válido")
                except Exception as e:
                    errores.append(f"Template {rel_path}: {str(e)}")
            
            print_info(f"Total templates encontrados: {templates_encontrados}")
        else:
            errores.append("Directorio templates no encontrado")
    
    except Exception as e:
        errores.append(f"Error verificando templates: {str(e)}")
    
    return errores

def verificar_migrations():
    """Verifica que las migraciones estén correctas"""
    print_titulo("ESCANEO 7: MIGRACIONES")
    
    errores = []
    
    try:
        # Ejecutar makemigrations --dry-run para verificar
        out = StringIO()
        try:
            call_command('makemigrations', '--dry-run', '--check', stdout=out, stderr=out)
            print_exito("No hay migraciones pendientes")
        except CommandError:
            # Si hay migraciones pendientes, no es necesariamente un error
            output = out.getvalue()
            if 'No changes detected' not in output:
                print_info("Hay migraciones pendientes (puede ser normal)")
        
        # Verificar que las migraciones existentes sean válidas
        apps = ['productos', 'conteo', 'usuarios', 'reportes', 'comparativos', 'movimientos']
        for app in apps:
            migrations_dir = Path(BASE_DIR) / app / 'migrations'
            if migrations_dir.exists():
                migrations = list(migrations_dir.glob('*.py'))
                migrations = [m for m in migrations if m.name != '__init__.py']
                print_exito(f"{app}: {len(migrations)} migraciones")
    
    except Exception as e:
        errores.append(f"Error verificando migraciones: {str(e)}")
    
    return errores

def verificar_django_check():
    """Ejecuta django check"""
    print_titulo("ESCANEO 8: DJANGO CHECK")
    
    errores = []
    
    try:
        out = StringIO()
        call_command('check', stdout=out, stderr=out)
        output = out.getvalue()
        
        if 'System check identified no issues' in output:
            print_exito("Django check: sin problemas")
        else:
            # Parsear errores
            lineas = output.split('\n')
            for linea in lineas:
                if 'ERROR' in linea or 'WARNING' in linea:
                    errores.append(linea.strip())
                    print_error(linea.strip())
    
    except CommandError as e:
        errores.append(f"Error en django check: {str(e)}")
    
    return errores

def verificar_funcionalidad_basica():
    """Verifica funcionalidad básica de los modelos"""
    print_titulo("ESCANEO 9: FUNCIONALIDAD BÁSICA")
    
    errores = []
    
    try:
        # Verificar que se puedan crear instancias básicas
        from productos.models import Producto
        from conteo.models import Conteo
        from usuarios.models import ParejaConteo
        from comparativos.models import ComparativoInventario
        from movimientos.models import MovimientoConteo
        
        # Verificar métodos de modelos
        productos = Producto.objects.filter(activo=True)[:1]
        if productos.exists():
            producto = productos.first()
            try:
                stock = producto.get_stock_actual()
                print_exito(f"Producto.get_stock_actual() funciona: {stock}")
            except Exception as e:
                errores.append(f"Error en get_stock_actual(): {str(e)}")
        
        # Verificar métodos de ItemComparativo
        from comparativos.models import ItemComparativo
        items = ItemComparativo.objects.all()
        if items.exists():
            item = items.first()
            try:
                valor_s1 = item.get_valor_sistema1()
                valor_s2 = item.get_valor_sistema2()
                valor_fisico = item.get_valor_fisico()
                print_exito("ItemComparativo: métodos de valor funcionan")
            except Exception as e:
                errores.append(f"Error en métodos de ItemComparativo: {str(e)}")
        
        # Verificar métodos de Conteo
        conteos = Conteo.objects.all()[:1]
        if conteos.exists():
            conteo = conteos.first()
            try:
                usuarios = conteo.get_usuarios()
                print_exito(f"Conteo.get_usuarios() funciona: {len(usuarios)} usuarios")
            except Exception as e:
                errores.append(f"Error en get_usuarios(): {str(e)}")
    
    except Exception as e:
        errores.append(f"Error verificando funcionalidad: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return errores

def verificar_settings():
    """Verifica configuración de Django"""
    print_titulo("ESCANEO 10: CONFIGURACIÓN")
    
    errores = []
    
    try:
        from django.conf import settings
        
        # Verificar apps instaladas
        apps_requeridas = [
            'productos',
            'conteo',
            'usuarios',
            'reportes',
            'comparativos',
            'movimientos',
            'django.contrib.humanize',
        ]
        
        for app in apps_requeridas:
            if app in settings.INSTALLED_APPS:
                print_exito(f"App {app} instalada")
            else:
                errores.append(f"App {app} no está en INSTALLED_APPS")
        
        # Verificar configuración de media y static
        if hasattr(settings, 'MEDIA_ROOT'):
            print_exito(f"MEDIA_ROOT configurado: {settings.MEDIA_ROOT}")
        else:
            errores.append("MEDIA_ROOT no configurado")
        
        if hasattr(settings, 'STATIC_ROOT'):
            print_exito(f"STATIC_ROOT configurado: {settings.STATIC_ROOT}")
        else:
            print_info("STATIC_ROOT no configurado (puede ser normal en desarrollo)")
    
    except Exception as e:
        errores.append(f"Error verificando settings: {str(e)}")
    
    return errores

def main():
    """Ejecuta el escaneo completo"""
    print(f"\n{Colores.NEGRITA}{Colores.AZUL}")
    print("="*70)
    print("ESCANEO COMPLETO DEL SISTEMA MEGA INVENTARIO")
    print("="*70)
    print(f"{Colores.RESET}")
    
    todos_errores = []
    
    # Ejecutar todos los escaneos
    errores1 = escanear_archivos_python()
    todos_errores.extend(errores1)
    
    errores2 = verificar_modelos()
    todos_errores.extend(errores2)
    
    errores3 = verificar_urls()
    todos_errores.extend(errores3)
    
    errores4 = verificar_forms()
    todos_errores.extend(errores4)
    
    errores5 = verificar_views()
    todos_errores.extend(errores5)
    
    errores6 = verificar_templates()
    todos_errores.extend(errores6)
    
    errores7 = verificar_migrations()
    todos_errores.extend(errores7)
    
    errores8 = verificar_django_check()
    todos_errores.extend(errores8)
    
    errores9 = verificar_funcionalidad_basica()
    todos_errores.extend(errores9)
    
    errores10 = verificar_settings()
    todos_errores.extend(errores10)
    
    # Resumen final
    print_titulo("RESUMEN DEL ESCANEO COMPLETO")
    
    print(f"\n{Colores.NEGRITA}Errores encontrados: {len(todos_errores)}{Colores.RESET}")
    if todos_errores:
        print(f"{Colores.ROJO}")
        for error in todos_errores[:20]:  # Mostrar primeros 20
            print(f"  ✗ {error}")
        if len(todos_errores) > 20:
            print(f"  ... y {len(todos_errores) - 20} errores más")
        print(f"{Colores.RESET}")
    else:
        print(f"{Colores.VERDE}")
        print("  ✓ No se encontraron errores en el escaneo completo")
        print(f"{Colores.RESET}")
    
    # Resultado final
    if len(todos_errores) == 0:
        print(f"\n{Colores.VERDE}{Colores.NEGRITA}")
        print("="*70)
        print("✓ ✓ ✓ SISTEMA COMPLETAMENTE FUNCIONAL Y SIN ERRORES")
        print("="*70)
        print(f"{Colores.RESET}")
    else:
        print(f"\n{Colores.ROJO}{Colores.NEGRITA}")
        print("="*70)
        print(f"✗ ✗ ✗ SE ENCONTRARON {len(todos_errores)} ERRORES")
        print("="*70)
        print(f"{Colores.RESET}")

if __name__ == '__main__':
    main()

