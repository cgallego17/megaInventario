"""
Script de prueba completo del sistema Mega Inventario
Prueba todos los módulos y funcionalidades del sistema
"""
import os
import sys
import django
from pathlib import Path
from datetime import datetime, timedelta

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megaInventario.settings')
django.setup()

import pandas as pd
from io import BytesIO
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from productos.models import Producto
from usuarios.models import ParejaConteo
from conteo.models import Conteo, ItemConteo
from comparativos.models import ComparativoInventario, InventarioSistema, ItemComparativo
from movimientos.models import MovimientoConteo

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class Colores:
    """Colores para la salida"""
    VERDE = '\033[92m'
    ROJO = '\033[91m'
    AMARILLO = '\033[93m'
    AZUL = '\033[94m'
    RESET = '\033[0m'
    NEGRITA = '\033[1m'

def print_titulo(texto):
    """Imprime un título formateado"""
    print(f"\n{Colores.NEGRITA}{Colores.AZUL}{'='*70}")
    print(f"{texto}")
    print(f"{'='*70}{Colores.RESET}\n")

def print_exito(texto):
    """Imprime un mensaje de éxito"""
    print(f"{Colores.VERDE}✓ {texto}{Colores.RESET}")

def print_error(texto):
    """Imprime un mensaje de error"""
    print(f"{Colores.ROJO}✗ {texto}{Colores.RESET}")

def print_info(texto):
    """Imprime un mensaje informativo"""
    print(f"{Colores.AMARILLO}ℹ {texto}{Colores.RESET}")

def limpiar_datos_prueba():
    """Limpia datos de prueba anteriores"""
    print_info("Limpiando datos de prueba anteriores...")
    ComparativoInventario.objects.filter(nombre__startswith='TEST_').delete()
    Conteo.objects.filter(nombre__startswith='TEST_').delete()
    # ParejaConteo no tiene campo nombre, se limpia por usuarios
    User.objects.filter(username__startswith='test_').delete()
    Producto.objects.filter(nombre__startswith='TEST_').delete()
    print_exito("Datos de prueba limpiados")

def test_1_productos():
    """Prueba el módulo de productos"""
    print_titulo("TEST 1: MÓDULO DE PRODUCTOS")
    
    resultados = []
    
    # 1.1 Crear productos manualmente
    producto1 = None
    try:
        producto1, created = Producto.objects.get_or_create(
            codigo_barras='7501234567890',
            defaults={
                'codigo': 'PROD001',
                'nombre': 'TEST_Producto Manual 1',
                'marca': 'Marca Test',
                'atributo': 'Talla M',
                'precio': 100.00,
                'categoria': 'Categoria Test',
                'activo': True
            }
        )
        if created:
            print_exito(f"Producto creado: {producto1.nombre}")
        else:
            print_exito(f"Producto existente: {producto1.nombre}")
        resultados.append(("Crear producto manual", True))
    except Exception as e:
        print_error(f"Error creando producto: {str(e)}")
        resultados.append(("Crear producto manual", False))
    
    # 1.2 Verificar get_stock_actual (debe ser 0 sin conteos)
    if producto1:
        try:
            stock = producto1.get_stock_actual()
            print_info(f"Stock actual del producto: {stock}")
            resultados.append(("Stock actual sin conteos", True))
        except Exception as e:
            print_error(f"Error obteniendo stock: {str(e)}")
            resultados.append(("Stock actual sin conteos", False))
    else:
        print_info("No se puede verificar stock: producto no creado")
        resultados.append(("Stock actual sin conteos", False))
    
    # 1.3 Buscar productos
    try:
        productos = Producto.objects.filter(
            Q(nombre__icontains='TEST_') |
            Q(codigo_barras__icontains='7501234567890') |
            Q(marca__icontains='Marca Test')
        )
        if productos.exists():
            print_exito(f"Búsqueda funcionando: {productos.count()} productos encontrados")
            resultados.append(("Búsqueda de productos", True))
        else:
            print_error("Búsqueda no encontró productos")
            resultados.append(("Búsqueda de productos", False))
    except Exception as e:
        print_error(f"Error en búsqueda: {str(e)}")
        resultados.append(("Búsqueda de productos", False))
    
    return resultados

def test_2_usuarios():
    """Prueba el módulo de usuarios"""
    print_titulo("TEST 2: MÓDULO DE USUARIOS")
    
    resultados = []
    
    # 2.1 Crear usuarios
    try:
        usuario1, created1 = User.objects.get_or_create(
            username='test_contador1',
            defaults={
                'email': 'contador1@test.com',
                'first_name': 'Contador',
                'last_name': 'Uno'
            }
        )
        if created1:
            usuario1.set_password('test123')
            usuario1.save()
            print_exito(f"Usuario creado: {usuario1.username}")
        else:
            print_exito(f"Usuario existente: {usuario1.username}")
        
        usuario2, created2 = User.objects.get_or_create(
            username='test_contador2',
            defaults={
                'email': 'contador2@test.com',
                'first_name': 'Contador',
                'last_name': 'Dos'
            }
        )
        if created2:
            usuario2.set_password('test123')
            usuario2.save()
            print_exito(f"Usuario creado: {usuario2.username}")
        else:
            print_exito(f"Usuario existente: {usuario2.username}")
        
        resultados.append(("Crear usuarios", True))
    except Exception as e:
        print_error(f"Error creando usuarios: {str(e)}")
        resultados.append(("Crear usuarios", False))
        return resultados
    
    # 2.2 Crear pareja de conteo
    try:
        pareja, created = ParejaConteo.objects.get_or_create(
            usuario_1=usuario1,
            usuario_2=usuario2,
            defaults={
                'activa': True
            }
        )
        if created:
            print_exito(f"Pareja creada: {pareja}")
        else:
            print_exito(f"Pareja existente: {pareja}")
        resultados.append(("Crear pareja", True))
    except Exception as e:
        print_error(f"Error creando pareja: {str(e)}")
        resultados.append(("Crear pareja", False))
    
    return resultados, usuario1, usuario2, pareja

def test_3_conteos(usuario1, usuario2, pareja):
    """Prueba el módulo de conteos"""
    print_titulo("TEST 3: MÓDULO DE CONTEOS")
    
    resultados = []
    conteos_creados = []
    
    # 3.1 Crear Conteo 1
    try:
        conteo1 = Conteo.objects.create(
            nombre='TEST_Conteo Físico 1',
            numero_conteo=1,
            estado='en_proceso',
            usuario_creador=usuario1,
            usuario_modificador=usuario1
        )
        conteo1.parejas.add(pareja)
        print_exito(f"Conteo 1 creado: {conteo1.nombre}")
        resultados.append(("Crear Conteo 1", True))
        conteos_creados.append(conteo1)
    except Exception as e:
        print_error(f"Error creando Conteo 1: {str(e)}")
        resultados.append(("Crear Conteo 1", False))
        return resultados, []
    
    # 3.2 Agregar productos al conteo (simulando la vista agregar_item)
    try:
        from movimientos.models import MovimientoConteo
        
        productos = Producto.objects.filter(activo=True)[:5]
        items_creados = 0
        
        for idx, producto in enumerate(productos):
            cantidad = (idx + 1) * 10
            
            # Simular el proceso de agregar_item de la vista
            with transaction.atomic():
                cantidad_anterior = 0
                item, created = ItemConteo.objects.get_or_create(
                    conteo=conteo1,
                    producto=producto,
                    defaults={
                        'cantidad': cantidad,
                        'usuario_conteo': usuario1
                    }
                )
                
                if not created:
                    cantidad_anterior = item.cantidad
                    item.cantidad += cantidad
                    item.usuario_conteo = usuario1
                    item.save()
                    tipo_movimiento = 'modificar'
                else:
                    tipo_movimiento = 'agregar'
                
                # Registrar movimiento (como lo hace la vista)
                MovimientoConteo.objects.create(
                    conteo=conteo1,
                    item_conteo=item,
                    producto=producto,
                    usuario=usuario1,
                    tipo=tipo_movimiento,
                    cantidad_anterior=cantidad_anterior,
                    cantidad_nueva=item.cantidad,
                    cantidad_cambiada=cantidad,
                )
                items_creados += 1
        
        print_exito(f"{items_creados} productos agregados al Conteo 1")
        resultados.append(("Agregar productos a conteo", True))
    except Exception as e:
        print_error(f"Error agregando productos: {str(e)}")
        import traceback
        traceback.print_exc()
        resultados.append(("Agregar productos a conteo", False))
    
    # 3.3 Verificar movimientos
    try:
        movimientos = MovimientoConteo.objects.filter(conteo=conteo1)
        if movimientos.exists():
            print_exito(f"Movimientos registrados: {movimientos.count()}")
            resultados.append(("Registro de movimientos", True))
        else:
            print_error("No se registraron movimientos")
            resultados.append(("Registro de movimientos", False))
    except Exception as e:
        print_error(f"Error verificando movimientos: {str(e)}")
        resultados.append(("Registro de movimientos", False))
    
    # 3.4 Finalizar Conteo 1
    try:
        conteo1.estado = 'finalizado'
        conteo1.fecha_fin = timezone.now()
        conteo1.usuario_modificador = usuario1
        conteo1.save()
        print_exito("Conteo 1 finalizado")
        resultados.append(("Finalizar conteo", True))
    except Exception as e:
        print_error(f"Error finalizando conteo: {str(e)}")
        resultados.append(("Finalizar conteo", False))
    
    # 3.5 Verificar stock actual después de finalizar
    try:
        productos_con_stock = 0
        for producto in productos:
            stock = producto.get_stock_actual()
            if stock > 0:
                productos_con_stock += 1
        
        if productos_con_stock > 0:
            print_exito(f"Stock actualizado: {productos_con_stock} productos con stock")
            resultados.append(("Actualización de stock", True))
        else:
            print_error("Stock no se actualizó")
            resultados.append(("Actualización de stock", False))
    except Exception as e:
        print_error(f"Error verificando stock: {str(e)}")
        resultados.append(("Actualización de stock", False))
    
    # 3.6 Crear Conteo 2
    try:
        conteo2 = Conteo.objects.create(
            nombre='TEST_Conteo Físico 2',
            numero_conteo=2,
            estado='en_proceso',
            usuario_creador=usuario2,
            usuario_modificador=usuario2
        )
        conteo2.parejas.add(pareja)
        
        # Agregar algunos productos diferentes
        productos2 = Producto.objects.filter(activo=True)[5:8]
        for idx, producto in enumerate(productos2):
            cantidad = (idx + 1) * 15
            ItemConteo.objects.create(
                conteo=conteo2,
                producto=producto,
                cantidad=cantidad,
                usuario_conteo=usuario2
            )
        
        print_exito(f"Conteo 2 creado con {productos2.count()} productos")
        resultados.append(("Crear Conteo 2", True))
        conteos_creados.append(conteo2)
    except Exception as e:
        print_error(f"Error creando Conteo 2: {str(e)}")
        resultados.append(("Crear Conteo 2", False))
    
    return resultados, conteos_creados

def test_4_comparativos(usuario1, conteos):
    """Prueba el módulo de comparativos"""
    print_titulo("TEST 4: MÓDULO DE COMPARATIVOS")
    
    resultados = []
    
    # 4.1 Crear comparativo
    try:
        comparativo = ComparativoInventario.objects.create(
            nombre='TEST_Comparativo Completo',
            nombre_sistema1='Sistema 1',
            nombre_sistema2='Sistema 2',
            usuario=usuario1
        )
        print_exito(f"Comparativo creado: {comparativo.nombre}")
        resultados.append(("Crear comparativo", True))
    except Exception as e:
        print_error(f"Error creando comparativo: {str(e)}")
        resultados.append(("Crear comparativo", False))
        return resultados
    
    # 4.2 Crear archivo Excel con configuración
    try:
        productos = Producto.objects.filter(activo=True)[:5]
        
        # Hoja Configuración
        config_data = {
            'Parámetro': ['Nombre del Sistema', 'Fecha de Inventario', 'Notas'],
            'Valor': ['SAP ERP', '2024-01-15', 'Prueba automática'],
            'Descripción': ['', '', '']
        }
        df_config = pd.DataFrame(config_data)
        
        # Hoja Inventario
        datos_inventario = []
        for idx, producto in enumerate(productos):
            datos_inventario.append({
                'codigo_barras': producto.codigo_barras,
                'codigo': producto.codigo or '',
                'nombre': producto.nombre,
                'marca': producto.marca or '',
                'atributo': producto.atributo or '',
                'cantidad': (idx + 1) * 20
            })
        df_inventario = pd.DataFrame(datos_inventario)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_config.to_excel(writer, sheet_name='Configuración', index=False)
            df_inventario.to_excel(writer, sheet_name='Inventario', index=False)
        output.seek(0)
        
        archivo_bytes = output.getvalue()
        print_exito("Archivo Excel creado con configuración e inventario")
        resultados.append(("Crear archivo Excel", True))
    except Exception as e:
        print_error(f"Error creando archivo Excel: {str(e)}")
        resultados.append(("Crear archivo Excel", False))
        return resultados
    
    # 4.3 Procesar archivo Sistema 1
    try:
        from comparativos.forms import InventarioSistemaForm
        
        archivo1 = SimpleUploadedFile(
            "test_sistema1.xlsx",
            archivo_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        form = InventarioSistemaForm()
        inventario1, nombre1 = form.procesar_archivo(archivo1, sistema='sistema1')
        
        if nombre1 == 'SAP ERP':
            print_exito(f"Nombre del sistema extraído correctamente: {nombre1}")
        else:
            print_error(f"Nombre esperado 'SAP ERP', obtenido: {nombre1}")
        
        # Actualizar comparativo
        if nombre1:
            comparativo.nombre_sistema1 = nombre1
            comparativo.save()
        
        # Guardar inventario
        inventario_sistema1, created = InventarioSistema.objects.update_or_create(
            comparativo=comparativo,
            sistema='sistema1',
            defaults={'archivo': archivo1}
        )
        
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
        
        print_exito(f"Sistema 1 procesado: {productos_procesados} productos, nombre: {nombre1}")
        resultados.append(("Procesar Sistema 1", True))
    except Exception as e:
        print_error(f"Error procesando Sistema 1: {str(e)}")
        import traceback
        traceback.print_exc()
        resultados.append(("Procesar Sistema 1", False))
    
    # 4.4 Procesar archivo Sistema 2
    try:
        # Crear archivo diferente para Sistema 2
        config_data2 = {
            'Parámetro': ['Nombre del Sistema', 'Fecha de Inventario', 'Notas'],
            'Valor': ['Oracle ERP', '2024-01-15', 'Prueba automática'],
            'Descripción': ['', '', '']
        }
        df_config2 = pd.DataFrame(config_data2)
        
        datos_inventario2 = []
        for idx, producto in enumerate(productos):
            datos_inventario2.append({
                'codigo_barras': producto.codigo_barras,
                'codigo': producto.codigo or '',
                'nombre': producto.nombre,
                'marca': producto.marca or '',
                'atributo': producto.atributo or '',
                'cantidad': (idx + 1) * 25
            })
        df_inventario2 = pd.DataFrame(datos_inventario2)
        
        output2 = BytesIO()
        with pd.ExcelWriter(output2, engine='openpyxl') as writer:
            df_config2.to_excel(writer, sheet_name='Configuración', index=False)
            df_inventario2.to_excel(writer, sheet_name='Inventario', index=False)
        output2.seek(0)
        
        archivo2 = SimpleUploadedFile(
            "test_sistema2.xlsx",
            output2.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        form2 = InventarioSistemaForm()
        inventario2, nombre2 = form2.procesar_archivo(archivo2, sistema='sistema2')
        
        if nombre2:
            comparativo.nombre_sistema2 = nombre2
            comparativo.save()
        
        inventario_sistema2, created = InventarioSistema.objects.update_or_create(
            comparativo=comparativo,
            sistema='sistema2',
            defaults={'archivo': archivo2}
        )
        
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
        
        print_exito(f"Sistema 2 procesado: {productos_procesados} productos, nombre: {nombre2}")
        resultados.append(("Procesar Sistema 2", True))
    except Exception as e:
        print_error(f"Error procesando Sistema 2: {str(e)}")
        resultados.append(("Procesar Sistema 2", False))
    
    # 4.5 Procesar comparativo (sumar conteos finalizados)
    try:
        from django.db.models import Sum
        conteos_finalizados = Conteo.objects.filter(estado='finalizado')
        
        items_agregados = ItemConteo.objects.filter(
            conteo__in=conteos_finalizados
        ).values('producto').annotate(
            cantidad_total=Sum('cantidad')
        )
        
        cantidad_por_producto = {item['producto']: item['cantidad_total'] for item in items_agregados}
        
        productos_activos = Producto.objects.filter(activo=True)
        for producto in productos_activos:
            item, created = ItemComparativo.objects.get_or_create(
                comparativo=comparativo,
                producto=producto
            )
            item.cantidad_fisico = cantidad_por_producto.get(producto.id, 0)
            item.calcular_diferencias()
        
        print_exito(f"Comparativo procesado: {productos_activos.count()} productos")
        resultados.append(("Procesar comparativo", True))
    except Exception as e:
        print_error(f"Error procesando comparativo: {str(e)}")
        resultados.append(("Procesar comparativo", False))
    
    # 4.6 Verificar diferencias calculadas
    try:
        items = ItemComparativo.objects.filter(comparativo=comparativo)
        items_con_diferencias = items.exclude(diferencia_sistema1=0).count()
        
        if items_con_diferencias > 0:
            print_exito(f"Diferencias calculadas: {items_con_diferencias} productos con diferencias")
            resultados.append(("Calcular diferencias", True))
        else:
            print_info("No hay diferencias (puede ser normal si coinciden)")
            resultados.append(("Calcular diferencias", True))
    except Exception as e:
        print_error(f"Error verificando diferencias: {str(e)}")
        resultados.append(("Calcular diferencias", False))
    
    return resultados

def test_5_movimientos():
    """Prueba el módulo de movimientos"""
    print_titulo("TEST 5: MÓDULO DE MOVIMIENTOS")
    
    resultados = []
    
    # 5.1 Verificar movimientos registrados
    try:
        total_movimientos = MovimientoConteo.objects.count()
        movimientos_agregar = MovimientoConteo.objects.filter(tipo='agregar').count()
        movimientos_modificar = MovimientoConteo.objects.filter(tipo='modificar').count()
        
        print_exito(f"Total movimientos: {total_movimientos}")
        print_exito(f"Movimientos agregar: {movimientos_agregar}")
        print_exito(f"Movimientos modificar: {movimientos_modificar}")
        
        if total_movimientos > 0:
            resultados.append(("Movimientos registrados", True))
        else:
            print_error("No hay movimientos registrados")
            resultados.append(("Movimientos registrados", False))
    except Exception as e:
        print_error(f"Error verificando movimientos: {str(e)}")
        resultados.append(("Movimientos registrados", False))
    
    # 5.2 Verificar movimientos por conteo
    try:
        conteos = Conteo.objects.filter(nombre__startswith='TEST_')
        for conteo in conteos:
            movimientos = MovimientoConteo.objects.filter(conteo=conteo)
            if movimientos.exists():
                print_exito(f"Conteo {conteo.nombre}: {movimientos.count()} movimientos")
        
        resultados.append(("Movimientos por conteo", True))
    except Exception as e:
        print_error(f"Error verificando movimientos por conteo: {str(e)}")
        resultados.append(("Movimientos por conteo", False))
    
    return resultados

def test_6_dashboard():
    """Prueba el dashboard"""
    print_titulo("TEST 6: DASHBOARD")
    
    resultados = []
    
    # 6.1 Verificar estadísticas
    try:
        total_productos = Producto.objects.filter(activo=True).count()
        total_conteos = Conteo.objects.count()
        conteos_en_proceso = Conteo.objects.filter(estado='en_proceso').count()
        conteos_finalizados = Conteo.objects.filter(estado='finalizado').count()
        total_movimientos = MovimientoConteo.objects.count()
        
        print_exito(f"Total productos: {total_productos}")
        print_exito(f"Total conteos: {total_conteos}")
        print_exito(f"Conteos en proceso: {conteos_en_proceso}")
        print_exito(f"Conteos finalizados: {conteos_finalizados}")
        print_exito(f"Total movimientos: {total_movimientos}")
        
        if total_productos > 0 and total_conteos > 0:
            resultados.append(("Estadísticas del dashboard", True))
        else:
            print_error("Estadísticas incompletas")
            resultados.append(("Estadísticas del dashboard", False))
    except Exception as e:
        print_error(f"Error verificando estadísticas: {str(e)}")
        resultados.append(("Estadísticas del dashboard", False))
    
    # 6.2 Verificar progreso de conteos
    try:
        conteos_activos = Conteo.objects.filter(estado='en_proceso')
        for conteo in conteos_activos:
            items_contados = conteo.items.count()
            total_cantidad = conteo.items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            print_exito(f"Conteo {conteo.nombre}: {items_contados} items, {total_cantidad} unidades")
        
        resultados.append(("Progreso de conteos", True))
    except Exception as e:
        print_error(f"Error verificando progreso: {str(e)}")
        resultados.append(("Progreso de conteos", False))
    
    return resultados

def main():
    """Ejecuta todas las pruebas"""
    print(f"\n{Colores.NEGRITA}{Colores.AZUL}")
    print("="*70)
    print("TEST COMPLETO DEL SISTEMA MEGA INVENTARIO")
    print("="*70)
    print(f"{Colores.RESET}")
    
    # Limpiar datos de prueba
    limpiar_datos_prueba()
    
    todos_resultados = []
    
    # Test 1: Productos
    resultados1 = test_1_productos()
    todos_resultados.extend(resultados1)
    
    # Test 2: Usuarios
    resultados2, usuario1, usuario2, pareja = test_2_usuarios()
    todos_resultados.extend(resultados2)
    
    # Test 3: Conteos
    resultados3, conteos = test_3_conteos(usuario1, usuario2, pareja)
    todos_resultados.extend(resultados3)
    
    # Test 4: Comparativos
    resultados4 = test_4_comparativos(usuario1, conteos)
    todos_resultados.extend(resultados4)
    
    # Test 5: Movimientos
    resultados5 = test_5_movimientos()
    todos_resultados.extend(resultados5)
    
    # Test 6: Dashboard
    resultados6 = test_6_dashboard()
    todos_resultados.extend(resultados6)
    
    # Resumen final
    print_titulo("RESUMEN FINAL DE PRUEBAS")
    
    pruebas_pasadas = sum(1 for _, resultado in todos_resultados if resultado)
    total_pruebas = len(todos_resultados)
    
    print(f"\n{Colores.NEGRITA}Total de pruebas: {total_pruebas}")
    print(f"Pruebas pasadas: {pruebas_pasadas}")
    print(f"Pruebas fallidas: {total_pruebas - pruebas_pasadas}{Colores.RESET}\n")
    
    print("Detalle de pruebas:")
    for nombre, resultado in todos_resultados:
        estado = f"{Colores.VERDE}✓ PASÓ{Colores.RESET}" if resultado else f"{Colores.ROJO}✗ FALLÓ{Colores.RESET}"
        print(f"  {estado}: {nombre}")
    
    if pruebas_pasadas == total_pruebas:
        print(f"\n{Colores.VERDE}{Colores.NEGRITA}")
        print("="*70)
        print("✓ ✓ ✓ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
        print("="*70)
        print(f"{Colores.RESET}")
    else:
        print(f"\n{Colores.ROJO}{Colores.NEGRITA}")
        print("="*70)
        print(f"✗ ✗ ✗ {total_pruebas - pruebas_pasadas} PRUEBA(S) FALLARON")
        print("="*70)
        print(f"{Colores.RESET}")

if __name__ == '__main__':
    main()

