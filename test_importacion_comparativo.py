"""
Script de prueba para verificar la funcionalidad de importación de comparativos
"""
import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megaInventario.settings')
django.setup()

import pandas as pd
from io import BytesIO
from django.contrib.auth.models import User
from productos.models import Producto
from comparativos.models import ComparativoInventario, InventarioSistema, ItemComparativo
from comparativos.forms import InventarioSistemaForm
from conteo.models import Conteo, ItemConteo
from django.core.files.uploadedfile import SimpleUploadedFile

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def crear_datos_prueba():
    """Crea datos de prueba si no existen"""
    print("=" * 60)
    print("CREANDO DATOS DE PRUEBA")
    print("=" * 60)
    
    # Crear usuario si no existe
    usuario, created = User.objects.get_or_create(
        username='test_user',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    if created:
        usuario.set_password('test123')
        usuario.save()
        print(f"✓ Usuario creado: {usuario.username}")
    else:
        print(f"✓ Usuario existente: {usuario.username}")
    
    # Crear productos de prueba si no existen
    productos_data = [
        {'codigo_barras': '1234567890123', 'codigo': 'PROD001', 'nombre': 'Producto Test 1', 'marca': 'Marca A', 'atributo': 'Talla M', 'precio': 100.00},
        {'codigo_barras': '9876543210987', 'codigo': 'PROD002', 'nombre': 'Producto Test 2', 'marca': 'Marca B', 'atributo': 'Talla L', 'precio': 200.00},
        {'codigo_barras': '5555555555555', 'codigo': 'PROD003', 'nombre': 'Producto Test 3', 'marca': 'Marca C', 'atributo': 'Color Rojo', 'precio': 150.00},
    ]
    
    productos_creados = 0
    for prod_data in productos_data:
        producto, created = Producto.objects.get_or_create(
            codigo_barras=prod_data['codigo_barras'],
            defaults=prod_data
        )
        if created:
            productos_creados += 1
            print(f"✓ Producto creado: {producto.nombre}")
    
    if productos_creados == 0:
        print("✓ Productos ya existen")
    else:
        print(f"✓ Total productos creados: {productos_creados}")
    
    return usuario

def crear_archivo_excel_prueba(nombre_sistema="SAP", sistema_numero=1):
    """Crea un archivo Excel de prueba con la estructura correcta"""
    print(f"\n{'=' * 60}")
    print(f"CREANDO ARCHIVO EXCEL DE PRUEBA - {nombre_sistema}")
    print(f"{'=' * 60}")
    
    # Obtener productos activos
    productos = Producto.objects.filter(activo=True)[:5]  # Limitar a 5 para prueba
    
    # ===== HOJA 1: CONFIGURACIÓN =====
    config_data = {
        'Parámetro': ['Nombre del Sistema', 'Fecha de Inventario', 'Notas'],
        'Valor': [nombre_sistema, '2024-01-15', 'Archivo de prueba generado automáticamente'],
        'Descripción': [
            'Ingrese el nombre de este sistema (ej: SAP, Oracle, Sistema Legacy, etc.)',
            'Fecha del inventario (opcional)',
            'Notas adicionales (opcional)'
        ]
    }
    df_config = pd.DataFrame(config_data)
    
    # ===== HOJA 2: INVENTARIO =====
    datos_inventario = []
    for idx, producto in enumerate(productos):
        # Asignar cantidades de prueba
        cantidad = (idx + 1) * 10  # 10, 20, 30, 40, 50
        datos_inventario.append({
            'codigo_barras': producto.codigo_barras,
            'codigo': producto.codigo or '',
            'nombre': producto.nombre,
            'marca': producto.marca or '',
            'atributo': producto.atributo or '',
            'cantidad': cantidad,
        })
    
    df_inventario = pd.DataFrame(datos_inventario)
    
    # Crear archivo Excel en memoria
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Hoja de configuración
        df_config.to_excel(writer, sheet_name='Configuración', index=False)
        
        # Hoja de inventario
        df_inventario.to_excel(writer, sheet_name='Inventario', index=False)
    
    output.seek(0)
    
    print(f"✓ Archivo Excel creado con {len(df_config)} filas en Configuración")
    print(f"✓ Archivo Excel creado con {len(df_inventario)} filas en Inventario")
    print(f"✓ Nombre del sistema configurado: {nombre_sistema}")
    
    return output.getvalue()

def probar_extraccion_nombre_sistema():
    """Prueba la extracción del nombre del sistema desde el archivo"""
    print(f"\n{'=' * 60}")
    print("PRUEBA 1: EXTRACCIÓN DEL NOMBRE DEL SISTEMA")
    print(f"{'=' * 60}")
    
    # Crear archivo de prueba
    archivo_bytes = crear_archivo_excel_prueba("Oracle ERP", 1)
    
    # Crear archivo subido simulado
    archivo = SimpleUploadedFile(
        "test_inventario.xlsx",
        archivo_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # Probar el formulario
    form = InventarioSistemaForm()
    try:
        inventario_data, nombre_sistema = form.procesar_archivo(archivo, sistema='sistema1')
        
        print(f"✓ Archivo procesado correctamente")
        print(f"✓ Nombre del sistema extraído: {nombre_sistema}")
        print(f"✓ Productos en inventario: {len(inventario_data)}")
        
        if nombre_sistema == "Oracle ERP":
            print("✓ ✓ ✓ NOMBRE DEL SISTEMA EXTRAÍDO CORRECTAMENTE")
        else:
            print(f"✗ ✗ ✗ ERROR: Se esperaba 'Oracle ERP' pero se obtuvo '{nombre_sistema}'")
            return False
        
        # Mostrar algunos datos
        print("\nPrimeros 3 productos del inventario:")
        for idx, (codigo, cantidad) in enumerate(list(inventario_data.items())[:3]):
            print(f"  - {codigo}: {cantidad} unidades")
        
        return True
        
    except Exception as e:
        print(f"✗ ✗ ✗ ERROR al procesar archivo: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def probar_importacion_completa():
    """Prueba la importación completa de un comparativo"""
    print(f"\n{'=' * 60}")
    print("PRUEBA 2: IMPORTACIÓN COMPLETA")
    print(f"{'=' * 60}")
    
    # Crear comparativo
    usuario = User.objects.filter(username='test_user').first()
    if not usuario:
        usuario = crear_datos_prueba()
    
    # Limpiar comparativos de prueba anteriores
    ComparativoInventario.objects.filter(nombre__startswith='TEST_').delete()
    
    comparativo = ComparativoInventario.objects.create(
        nombre='TEST_Comparativo Importación',
        nombre_sistema1='Sistema 1',
        nombre_sistema2='Sistema 2',
        usuario=usuario
    )
    print(f"✓ Comparativo creado: {comparativo.nombre}")
    
    # Crear archivos de prueba para ambos sistemas
    archivo_sistema1_bytes = crear_archivo_excel_prueba("SAP", 1)
    archivo_sistema2_bytes = crear_archivo_excel_prueba("Oracle", 2)
    
    # Procesar Sistema 1
    print(f"\n--- Procesando Sistema 1 (SAP) ---")
    archivo1 = SimpleUploadedFile(
        "test_sistema1.xlsx",
        archivo_sistema1_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    form1 = InventarioSistemaForm()
    try:
        inventario1, nombre1 = form1.procesar_archivo(archivo1, sistema='sistema1')
        
        # Actualizar nombre del sistema
        if nombre1:
            comparativo.nombre_sistema1 = nombre1
            comparativo.save()
            print(f"✓ Nombre del sistema 1 actualizado: {nombre1}")
        
        # Guardar inventario
        inventario_sistema1, created = InventarioSistema.objects.update_or_create(
            comparativo=comparativo,
            sistema='sistema1',
            defaults={'archivo': archivo1}
        )
        print(f"✓ Inventario Sistema 1 guardado")
        
        # Procesar items
        from django.db.models import Q
        productos_procesados = 0
        for codigo_barras, cantidad in inventario1.items():
            producto = Producto.objects.filter(
                activo=True
            ).filter(
                Q(codigo_barras=codigo_barras) | Q(codigo=codigo_barras)
            ).first()
            
            if producto:
                item, item_created = ItemComparativo.objects.get_or_create(
                    comparativo=comparativo,
                    producto=producto
                )
                item.cantidad_sistema1 = cantidad
                item.save()
                productos_procesados += 1
        
        print(f"✓ {productos_procesados} productos procesados para Sistema 1")
        
    except Exception as e:
        print(f"✗ ERROR procesando Sistema 1: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Procesar Sistema 2
    print(f"\n--- Procesando Sistema 2 (Oracle) ---")
    archivo2 = SimpleUploadedFile(
        "test_sistema2.xlsx",
        archivo_sistema2_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    form2 = InventarioSistemaForm()
    try:
        inventario2, nombre2 = form2.procesar_archivo(archivo2, sistema='sistema2')
        
        # Actualizar nombre del sistema
        if nombre2:
            comparativo.nombre_sistema2 = nombre2
            comparativo.save()
            print(f"✓ Nombre del sistema 2 actualizado: {nombre2}")
        
        # Guardar inventario
        inventario_sistema2, created = InventarioSistema.objects.update_or_create(
            comparativo=comparativo,
            sistema='sistema2',
            defaults={'archivo': archivo2}
        )
        print(f"✓ Inventario Sistema 2 guardado")
        
        # Procesar items
        from django.db.models import Q
        productos_procesados = 0
        for codigo_barras, cantidad in inventario2.items():
            producto = Producto.objects.filter(
                activo=True
            ).filter(
                Q(codigo_barras=codigo_barras) | Q(codigo=codigo_barras)
            ).first()
            
            if producto:
                item, item_created = ItemComparativo.objects.get_or_create(
                    comparativo=comparativo,
                    producto=producto
                )
                item.cantidad_sistema2 = cantidad
                item.save()
                productos_procesados += 1
        
        print(f"✓ {productos_procesados} productos procesados para Sistema 2")
        
    except Exception as e:
        print(f"✗ ERROR procesando Sistema 2: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Verificar resultados
    print(f"\n--- Verificando Resultados ---")
    comparativo.refresh_from_db()
    
    print(f"✓ Nombre Sistema 1: {comparativo.nombre_sistema1}")
    print(f"✓ Nombre Sistema 2: {comparativo.nombre_sistema2}")
    
    items_count = ItemComparativo.objects.filter(comparativo=comparativo).count()
    print(f"✓ Total items en comparativo: {items_count}")
    
    items_sistema1 = ItemComparativo.objects.filter(comparativo=comparativo).exclude(cantidad_sistema1=0).count()
    items_sistema2 = ItemComparativo.objects.filter(comparativo=comparativo).exclude(cantidad_sistema2=0).count()
    
    print(f"✓ Items con cantidad en Sistema 1: {items_sistema1}")
    print(f"✓ Items con cantidad en Sistema 2: {items_sistema2}")
    
    # Verificar que los nombres se actualizaron correctamente
    if comparativo.nombre_sistema1 == "SAP" and comparativo.nombre_sistema2 == "Oracle":
        print("✓ ✓ ✓ NOMBRES DE SISTEMAS ACTUALIZADOS CORRECTAMENTE")
    else:
        print(f"✗ ✗ ✗ ERROR: Nombres no coinciden. S1: {comparativo.nombre_sistema1}, S2: {comparativo.nombre_sistema2}")
        return False
    
    return True

def probar_archivo_sin_configuracion():
    """Prueba que funcione con archivos sin hoja de configuración"""
    print(f"\n{'=' * 60}")
    print("PRUEBA 3: ARCHIVO SIN HOJA DE CONFIGURACIÓN")
    print(f"{'=' * 60}")
    
    # Crear archivo simple sin hoja de configuración
    productos = Producto.objects.filter(activo=True)[:3]
    datos = []
    for producto in productos:
        datos.append({
            'codigo_barras': producto.codigo_barras,
            'cantidad': 15
        })
    
    df = pd.DataFrame(datos)
    output = BytesIO()
    df.to_excel(output, engine='openpyxl', index=False)
    output.seek(0)
    
    archivo = SimpleUploadedFile(
        "test_simple.xlsx",
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    form = InventarioSistemaForm()
    try:
        inventario_data, nombre_sistema = form.procesar_archivo(archivo, sistema='sistema1')
        
        print(f"✓ Archivo sin configuración procesado correctamente")
        print(f"✓ Nombre del sistema: {nombre_sistema} (debe ser None)")
        print(f"✓ Productos en inventario: {len(inventario_data)}")
        
        if nombre_sistema is None:
            print("✓ ✓ ✓ MANEJO CORRECTO DE ARCHIVOS SIN CONFIGURACIÓN")
        else:
            print(f"✗ ✗ ✗ ERROR: Se esperaba None pero se obtuvo '{nombre_sistema}'")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ ✗ ✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecuta todas las pruebas"""
    print("\n" + "=" * 60)
    print("INICIANDO PRUEBAS DE IMPORTACIÓN DE COMPARATIVOS")
    print("=" * 60)
    
    # Crear datos de prueba
    crear_datos_prueba()
    
    resultados = []
    
    # Prueba 1: Extracción del nombre del sistema
    try:
        resultado1 = probar_extraccion_nombre_sistema()
        resultados.append(("Extracción nombre sistema", resultado1))
    except Exception as e:
        print(f"✗ ERROR en Prueba 1: {str(e)}")
        resultados.append(("Extracción nombre sistema", False))
    
    # Prueba 2: Importación completa
    try:
        resultado2 = probar_importacion_completa()
        resultados.append(("Importación completa", resultado2))
    except Exception as e:
        print(f"✗ ERROR en Prueba 2: {str(e)}")
        import traceback
        traceback.print_exc()
        resultados.append(("Importación completa", False))
    
    # Prueba 3: Archivo sin configuración
    try:
        resultado3 = probar_archivo_sin_configuracion()
        resultados.append(("Archivo sin configuración", resultado3))
    except Exception as e:
        print(f"✗ ERROR en Prueba 3: {str(e)}")
        resultados.append(("Archivo sin configuración", False))
    
    # Resumen
    print(f"\n{'=' * 60}")
    print("RESUMEN DE PRUEBAS")
    print(f"{'=' * 60}")
    
    for nombre, resultado in resultados:
        estado = "✓ PASÓ" if resultado else "✗ FALLÓ"
        print(f"{estado}: {nombre}")
    
    total_pruebas = len(resultados)
    pruebas_pasadas = sum(1 for _, resultado in resultados if resultado)
    
    print(f"\nTotal: {pruebas_pasadas}/{total_pruebas} pruebas pasadas")
    
    if pruebas_pasadas == total_pruebas:
        print("\n✓ ✓ ✓ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
    else:
        print(f"\n✗ ✗ ✗ {total_pruebas - pruebas_pasadas} PRUEBA(S) FALLARON")

if __name__ == '__main__':
    main()

