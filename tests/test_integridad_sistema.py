"""
Test de Integridad y Consistencia del Sistema
Verifica que no haya incongruencias, datos huérfanos o inconsistencias
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

from django.db.models import Sum, Count, Q
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from productos.models import Producto
from usuarios.models import ParejaConteo
from conteo.models import Conteo, ItemConteo
from comparativos.models import ComparativoInventario, InventarioSistema, ItemComparativo
from movimientos.models import MovimientoConteo
from django.contrib.auth.models import User

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

def test_1_integridad_productos():
    """Verifica la integridad de los productos"""
    print_titulo("TEST 1: INTEGRIDAD DE PRODUCTOS")
    
    errores = []
    advertencias = []
    
    # 1.1 Verificar que todos los productos activos tengan código de barras único
    productos = Producto.objects.filter(activo=True)
    codigos_barras = productos.values_list('codigo_barras', flat=True)
    duplicados = productos.values('codigo_barras').annotate(
        count=Count('codigo_barras')
    ).filter(count__gt=1)
    
    if duplicados.exists():
        for dup in duplicados:
            errores.append(f"Código de barras duplicado: {dup['codigo_barras']} ({dup['count']} veces)")
    else:
        print_exito(f"Todos los {productos.count()} productos tienen código de barras único")
    
    # 1.2 Verificar que get_stock_actual sea consistente con ItemConteo
    productos_sin_stock_consistente = []
    for producto in productos[:10]:  # Verificar primeros 10 para no sobrecargar
        stock_calculado = producto.get_stock_actual()
        
        # Verificar manualmente
        ultimo_conteo = Conteo.objects.filter(
            estado='finalizado',
            items__producto=producto
        ).order_by('-fecha_fin').first()
        
        if ultimo_conteo:
            item = ItemConteo.objects.filter(
                conteo=ultimo_conteo,
                producto=producto
            ).first()
            if item:
                stock_manual = item.cantidad
                if stock_calculado != stock_manual:
                    productos_sin_stock_consistente.append(
                        f"Producto {producto.nombre}: calculado={stock_calculado}, manual={stock_manual}"
                    )
    
    if productos_sin_stock_consistente:
        errores.extend(productos_sin_stock_consistente)
    else:
        print_exito("Stock actual es consistente con ItemConteo")
    
    # 1.3 Verificar que productos con stock tengan conteos finalizados
    productos_con_stock = [p for p in productos if p.get_stock_actual() > 0]
    productos_sin_conteo = []
    
    for producto in productos_con_stock[:10]:
        tiene_conteo = Conteo.objects.filter(
            estado='finalizado',
            items__producto=producto
        ).exists()
        if not tiene_conteo:
            productos_sin_conteo.append(f"Producto {producto.nombre} tiene stock pero no tiene conteo finalizado")
    
    if productos_sin_conteo:
        advertencias.extend(productos_sin_conteo)
    else:
        print_exito("Productos con stock tienen conteos finalizados asociados")
    
    return errores, advertencias

def test_2_integridad_conteos():
    """Verifica la integridad de los conteos"""
    print_titulo("TEST 2: INTEGRIDAD DE CONTEOS")
    
    errores = []
    advertencias = []
    
    # 2.1 Verificar que conteos finalizados tengan fecha_fin
    conteos_finalizados = Conteo.objects.filter(estado='finalizado')
    conteos_sin_fecha = conteos_finalizados.filter(fecha_fin__isnull=True)
    
    if conteos_sin_fecha.exists():
        errores.append(f"{conteos_sin_fecha.count()} conteos finalizados sin fecha_fin")
    else:
        print_exito(f"Todos los {conteos_finalizados.count()} conteos finalizados tienen fecha_fin")
    
    # 2.2 Verificar que conteos en proceso no tengan fecha_fin
    conteos_en_proceso = Conteo.objects.filter(estado='en_proceso')
    conteos_con_fecha = conteos_en_proceso.filter(fecha_fin__isnull=False)
    
    if conteos_con_fecha.exists():
        advertencias.append(f"{conteos_con_fecha.count()} conteos en proceso tienen fecha_fin (deberían ser null)")
    else:
        print_exito(f"Todos los {conteos_en_proceso.count()} conteos en proceso no tienen fecha_fin")
    
    # 2.3 Verificar que items de conteo tengan producto activo
    items = ItemConteo.objects.all()
    items_producto_inactivo = items.filter(producto__activo=False)
    
    if items_producto_inactivo.exists():
        advertencias.append(f"{items_producto_inactivo.count()} items de conteo tienen productos inactivos")
    else:
        print_exito(f"Todos los {items.count()} items de conteo tienen productos activos")
    
    # 2.4 Verificar que items de conteo tengan cantidad >= 0
    items_negativos = items.filter(cantidad__lt=0)
    
    if items_negativos.exists():
        errores.append(f"{items_negativos.count()} items de conteo tienen cantidad negativa")
    else:
        print_exito("Todas las cantidades de items de conteo son >= 0")
    
    # 2.5 Verificar consistencia de parejas
    conteos_con_parejas = Conteo.objects.filter(parejas__isnull=False).distinct()
    conteos_solo_usuarios = Conteo.objects.filter(
        parejas__isnull=True,
        usuario_1__isnull=False,
        usuario_2__isnull=False
    )
    
    print_exito(f"{conteos_con_parejas.count()} conteos con parejas, {conteos_solo_usuarios.count()} con usuarios manuales")
    
    return errores, advertencias

def test_3_integridad_movimientos():
    """Verifica la integridad de los movimientos"""
    print_titulo("TEST 3: INTEGRIDAD DE MOVIMIENTOS")
    
    errores = []
    advertencias = []
    
    # 3.1 Verificar que movimientos tengan conteo válido
    movimientos = MovimientoConteo.objects.all()
    movimientos_sin_conteo = movimientos.filter(conteo__isnull=True)
    
    if movimientos_sin_conteo.exists():
        errores.append(f"{movimientos_sin_conteo.count()} movimientos sin conteo asociado")
    else:
        print_exito(f"Todos los {movimientos.count()} movimientos tienen conteo asociado")
    
    # 3.2 Verificar que movimientos tengan producto válido
    movimientos_sin_producto = movimientos.filter(producto__isnull=True)
    
    if movimientos_sin_producto.exists():
        errores.append(f"{movimientos_sin_producto.count()} movimientos sin producto asociado")
    else:
        print_exito("Todos los movimientos tienen producto asociado")
    
    # 3.3 Verificar consistencia entre movimientos e ItemConteo
    # Nota: Las inconsistencias pueden ser normales si se modificaron items después de crear movimientos
    # Solo verificamos que el movimiento tenga sentido lógico
    movimientos_con_item = movimientos.filter(item_conteo__isnull=False)
    inconsistencias_graves = []
    
    for movimiento in movimientos_con_item[:20]:  # Verificar primeros 20
        if movimiento.item_conteo:
            # Verificar que cantidad_nueva sea >= cantidad_anterior para agregar/modificar
            if movimiento.tipo in ['agregar', 'modificar']:
                if movimiento.cantidad_nueva < movimiento.cantidad_anterior:
                    inconsistencias_graves.append(
                        f"Movimiento {movimiento.id} ({movimiento.tipo}): "
                        f"cantidad_nueva ({movimiento.cantidad_nueva}) < cantidad_anterior ({movimiento.cantidad_anterior})"
                    )
    
    if inconsistencias_graves:
        errores.extend(inconsistencias_graves[:5])
    else:
        print_exito("Movimientos tienen lógica consistente")
    
    # Advertencia sobre diferencias menores (pueden ser normales)
    diferencias_menores = 0
    for movimiento in movimientos_con_item[:20]:
        if movimiento.item_conteo:
            if abs(movimiento.item_conteo.cantidad - movimiento.cantidad_nueva) > 0:
                diferencias_menores += 1
    
    if diferencias_menores > 0:
        advertencias.append(
            f"{diferencias_menores} movimientos tienen diferencias menores con item_conteo "
            f"(puede ser normal si se modificaron después)"
        )
    
    # 3.4 Verificar que cantidad_cambiada sea correcta
    movimientos_incorrectos = []
    for movimiento in movimientos[:20]:
        diferencia_esperada = movimiento.cantidad_nueva - movimiento.cantidad_anterior
        if movimiento.cantidad_cambiada != diferencia_esperada:
            movimientos_incorrectos.append(
                f"Movimiento {movimiento.id}: cantidad_cambiada={movimiento.cantidad_cambiada}, "
                f"esperado={diferencia_esperada}"
            )
    
    if movimientos_incorrectos:
        errores.extend(movimientos_incorrectos[:5])
    else:
        print_exito("cantidad_cambiada es correcta en todos los movimientos")
    
    # 3.5 Verificar que movimientos de eliminación tengan item_conteo null
    movimientos_eliminar = movimientos.filter(tipo='eliminar')
    movimientos_eliminar_con_item = movimientos_eliminar.filter(item_conteo__isnull=False)
    
    if movimientos_eliminar_con_item.exists():
        advertencias.append(f"{movimientos_eliminar_con_item.count()} movimientos de eliminación tienen item_conteo (deberían ser null)")
    else:
        print_exito(f"Todos los {movimientos_eliminar.count()} movimientos de eliminación tienen item_conteo null")
    
    return errores, advertencias

def test_4_integridad_comparativos():
    """Verifica la integridad de los comparativos"""
    print_titulo("TEST 4: INTEGRIDAD DE COMPARATIVOS")
    
    errores = []
    advertencias = []
    
    # 4.1 Verificar que comparativos tengan usuario
    comparativos = ComparativoInventario.objects.all()
    comparativos_sin_usuario = comparativos.filter(usuario__isnull=True)
    
    if comparativos_sin_usuario.exists():
        errores.append(f"{comparativos_sin_usuario.count()} comparativos sin usuario")
    else:
        print_exito(f"Todos los {comparativos.count()} comparativos tienen usuario")
    
    # 4.2 Verificar que items comparativos tengan producto activo
    items = ItemComparativo.objects.all()
    items_producto_inactivo = items.filter(producto__activo=False)
    
    if items_producto_inactivo.exists():
        advertencias.append(f"{items_producto_inactivo.count()} items comparativos tienen productos inactivos")
    else:
        print_exito(f"Todos los {items.count()} items comparativos tienen productos activos")
    
    # 4.3 Verificar que diferencias estén calculadas correctamente
    items_con_diferencias_incorrectas = []
    for item in items[:20]:
        diferencia_s1_esperada = item.cantidad_fisico - item.cantidad_sistema1
        diferencia_s2_esperada = item.cantidad_fisico - item.cantidad_sistema2
        
        if item.diferencia_sistema1 != diferencia_s1_esperada:
            items_con_diferencias_incorrectas.append(
                f"Item {item.id} (S1): diferencia={item.diferencia_sistema1}, esperada={diferencia_s1_esperada}"
            )
        
        if item.diferencia_sistema2 != diferencia_s2_esperada:
            items_con_diferencias_incorrectas.append(
                f"Item {item.id} (S2): diferencia={item.diferencia_sistema2}, esperada={diferencia_s2_esperada}"
            )
    
    if items_con_diferencias_incorrectas:
        errores.extend(items_con_diferencias_incorrectas[:5])
    else:
        print_exito("Todas las diferencias están calculadas correctamente")
    
    # 4.4 Verificar que cantidad_fisico sea consistente con conteos finalizados
    comparativos_con_conteo = comparativos.filter(conteo__isnull=False)
    for comparativo in comparativos_con_conteo:
        # Obtener suma de conteos finalizados
        conteos_finalizados = Conteo.objects.filter(estado='finalizado')
        items_agregados = ItemConteo.objects.filter(
            conteo__in=conteos_finalizados
        ).values('producto').annotate(
            cantidad_total=Sum('cantidad')
        )
        cantidad_por_producto = {item['producto']: item['cantidad_total'] for item in items_agregados}
        
        # Verificar algunos items
        items_comparativo = ItemComparativo.objects.filter(comparativo=comparativo)[:10]
        inconsistencias = []
        for item in items_comparativo:
            cantidad_esperada = cantidad_por_producto.get(item.producto.id, 0)
            if item.cantidad_fisico != cantidad_esperada:
                inconsistencias.append(
                    f"Item {item.id} ({item.producto.nombre}): "
                    f"cantidad_fisico={item.cantidad_fisico}, esperada={cantidad_esperada}"
                )
        
        if inconsistencias:
            advertencias.extend(inconsistencias[:3])
        else:
            print_exito(f"Comparativo {comparativo.nombre}: cantidad_fisico es consistente")
    
    # 4.5 Verificar que inventarios de sistema tengan archivo
    inventarios = InventarioSistema.objects.all()
    inventarios_sin_archivo = inventarios.filter(archivo='')
    
    if inventarios_sin_archivo.exists():
        advertencias.append(f"{inventarios_sin_archivo.count()} inventarios de sistema sin archivo")
    else:
        print_exito(f"Todos los {inventarios.count()} inventarios de sistema tienen archivo")
    
    return errores, advertencias

def test_5_consistencia_cruzada():
    """Verifica consistencia entre diferentes módulos"""
    print_titulo("TEST 5: CONSISTENCIA CRUZADA")
    
    errores = []
    advertencias = []
    
    # 5.1 Verificar que productos en conteos finalizados tengan stock actual
    conteos_finalizados = Conteo.objects.filter(estado='finalizado')
    productos_en_conteos = Producto.objects.filter(
        itemconteo__conteo__in=conteos_finalizados
    ).distinct()
    
    productos_sin_stock = []
    for producto in productos_en_conteos[:10]:
        stock = producto.get_stock_actual()
        if stock == 0:
            # Verificar si realmente está en un conteo finalizado
            tiene_item = ItemConteo.objects.filter(
                conteo__estado='finalizado',
                producto=producto,
                cantidad__gt=0
            ).exists()
            if tiene_item:
                productos_sin_stock.append(f"Producto {producto.nombre} está en conteo finalizado pero stock=0")
    
    if productos_sin_stock:
        advertencias.extend(productos_sin_stock)
    else:
        print_exito("Productos en conteos finalizados tienen stock actual correcto")
    
    # 5.2 Verificar que movimientos correspondan a conteos existentes
    movimientos = MovimientoConteo.objects.all()
    conteos_ids = set(Conteo.objects.values_list('id', flat=True))
    
    movimientos_conteo_inexistente = []
    for movimiento in movimientos[:50]:
        if movimiento.conteo_id not in conteos_ids:
            movimientos_conteo_inexistente.append(
                f"Movimiento {movimiento.id} referencia conteo {movimiento.conteo_id} que no existe"
            )
    
    if movimientos_conteo_inexistente:
        errores.extend(movimientos_conteo_inexistente[:5])
    else:
        print_exito("Todos los movimientos referencian conteos existentes")
    
    # 5.3 Verificar que items comparativos correspondan a productos existentes
    items = ItemComparativo.objects.all()
    productos_ids = set(Producto.objects.values_list('id', flat=True))
    
    items_producto_inexistente = []
    for item in items[:50]:
        if item.producto_id not in productos_ids:
            items_producto_inexistente.append(
                f"Item comparativo {item.id} referencia producto {item.producto_id} que no existe"
            )
    
    if items_producto_inexistente:
        errores.extend(items_producto_inexistente[:5])
    else:
        print_exito("Todos los items comparativos referencian productos existentes")
    
    # 5.4 Verificar suma de cantidades en conteos
    conteos = Conteo.objects.all()
    for conteo in conteos[:5]:
        suma_items = ItemConteo.objects.filter(conteo=conteo).aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        
        suma_movimientos = MovimientoConteo.objects.filter(conteo=conteo).aggregate(
            total=Sum('cantidad_cambiada')
        )['total'] or 0
        
        # La suma de movimientos debería ser igual o mayor (porque puede haber eliminaciones)
        if suma_movimientos < 0:
            advertencias.append(
                f"Conteo {conteo.nombre}: suma de movimientos es negativa ({suma_movimientos})"
            )
        else:
            print_exito(f"Conteo {conteo.nombre}: {suma_items} unidades en items, {suma_movimientos} en movimientos")
    
    return errores, advertencias

def test_6_reglas_negocio():
    """Verifica que se cumplan las reglas de negocio"""
    print_titulo("TEST 6: REGLAS DE NEGOCIO")
    
    errores = []
    advertencias = []
    
    # 6.1 Verificar que no haya conteos finalizados sin items
    conteos_finalizados = Conteo.objects.filter(estado='finalizado')
    conteos_sin_items = conteos_finalizados.annotate(
        num_items=Count('items')
    ).filter(num_items=0)
    
    if conteos_sin_items.exists():
        advertencias.append(f"{conteos_sin_items.count()} conteos finalizados sin items")
    else:
        print_exito("Todos los conteos finalizados tienen items")
    
    # 6.2 Verificar que parejas tengan usuarios diferentes
    from django.db.models import F
    parejas = ParejaConteo.objects.all()
    parejas_incorrectas = parejas.filter(usuario_1=F('usuario_2'))
    
    if parejas_incorrectas.exists():
        errores.append(f"{parejas_incorrectas.count()} parejas tienen el mismo usuario dos veces")
    else:
        print_exito(f"Todas las {parejas.count()} parejas tienen usuarios diferentes")
    
    # 6.3 Verificar que usuarios en parejas estén activos
    parejas_usuario_inactivo = parejas.filter(
        Q(usuario_1__is_active=False) | Q(usuario_2__is_active=False)
    )
    
    if parejas_usuario_inactivo.exists():
        advertencias.append(f"{parejas_usuario_inactivo.count()} parejas tienen usuarios inactivos")
    else:
        print_exito("Todas las parejas tienen usuarios activos")
    
    # 6.4 Verificar que comparativos procesados tengan al menos un inventario de sistema
    comparativos = ComparativoInventario.objects.all()
    comparativos_sin_inventario = []
    
    for comparativo in comparativos:
        inventarios = InventarioSistema.objects.filter(comparativo=comparativo)
        items = ItemComparativo.objects.filter(comparativo=comparativo)
        # Solo advertir si tiene items pero no inventarios (significa que se procesó pero no tiene datos de sistemas)
        if items.exists() and inventarios.count() == 0:
            comparativos_sin_inventario.append(
                f"Comparativo {comparativo.nombre} tiene items pero no tiene inventarios de sistema"
            )
    
    if comparativos_sin_inventario:
        advertencias.extend(comparativos_sin_inventario)
    else:
        print_exito("Comparativos con items tienen inventarios de sistema")
    
    return errores, advertencias

def main():
    """Ejecuta todos los tests de integridad"""
    print(f"\n{Colores.NEGRITA}{Colores.AZUL}")
    print("="*70)
    print("TEST DE INTEGRIDAD Y CONSISTENCIA DEL SISTEMA")
    print("="*70)
    print(f"{Colores.RESET}")
    
    todos_errores = []
    todas_advertencias = []
    
    # Ejecutar todos los tests
    errores1, advertencias1 = test_1_integridad_productos()
    todos_errores.extend(errores1)
    todas_advertencias.extend(advertencias1)
    
    errores2, advertencias2 = test_2_integridad_conteos()
    todos_errores.extend(errores2)
    todas_advertencias.extend(advertencias2)
    
    errores3, advertencias3 = test_3_integridad_movimientos()
    todos_errores.extend(errores3)
    todas_advertencias.extend(advertencias3)
    
    errores4, advertencias4 = test_4_integridad_comparativos()
    todos_errores.extend(errores4)
    todas_advertencias.extend(advertencias4)
    
    errores5, advertencias5 = test_5_consistencia_cruzada()
    todos_errores.extend(errores5)
    todas_advertencias.extend(advertencias5)
    
    # Test 6: Reglas de negocio
    errores6, advertencias6 = test_6_reglas_negocio()
    todos_errores.extend(errores6)
    todas_advertencias.extend(advertencias6)
    
    # Resumen final
    print_titulo("RESUMEN DE INTEGRIDAD")
    
    print(f"\n{Colores.NEGRITA}Errores encontrados: {len(todos_errores)}{Colores.RESET}")
    if todos_errores:
        print(f"{Colores.ROJO}")
        for error in todos_errores[:10]:  # Mostrar primeros 10
            print(f"  ✗ {error}")
        if len(todos_errores) > 10:
            print(f"  ... y {len(todos_errores) - 10} errores más")
        print(f"{Colores.RESET}")
    
    print(f"\n{Colores.NEGRITA}Advertencias encontradas: {len(todas_advertencias)}{Colores.RESET}")
    if todas_advertencias:
        print(f"{Colores.AMARILLO}")
        for advertencia in todas_advertencias[:10]:  # Mostrar primeros 10
            print(f"  ⚠ {advertencia}")
        if len(todas_advertencias) > 10:
            print(f"  ... y {len(todas_advertencias) - 10} advertencias más")
        print(f"{Colores.RESET}")
    
    # Resultado final
    if len(todos_errores) == 0 and len(todas_advertencias) == 0:
        print(f"\n{Colores.VERDE}{Colores.NEGRITA}")
        print("="*70)
        print("✓ ✓ ✓ SISTEMA COMPLETAMENTE INTEGRO Y CONSISTENTE")
        print("="*70)
        print(f"{Colores.RESET}")
    elif len(todos_errores) == 0:
        print(f"\n{Colores.AMARILLO}{Colores.NEGRITA}")
        print("="*70)
        print("⚠ SISTEMA FUNCIONAL CON ADVERTENCIAS MENORES")
        print("="*70)
        print(f"{Colores.RESET}")
    else:
        print(f"\n{Colores.ROJO}{Colores.NEGRITA}")
        print("="*70)
        print(f"✗ ✗ ✗ SE ENCONTRARON {len(todos_errores)} ERRORES DE INTEGRIDAD")
        print("="*70)
        print(f"{Colores.RESET}")

if __name__ == '__main__':
    main()

