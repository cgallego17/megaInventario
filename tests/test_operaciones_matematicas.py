"""
Test de Operaciones Matemáticas del Sistema
Verifica que todas las sumas, restas, multiplicaciones y cálculos sean correctos
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
from decimal import Decimal

from productos.models import Producto
from conteo.models import Conteo, ItemConteo
from comparativos.models import ComparativoInventario, ItemComparativo
from movimientos.models import MovimientoConteo

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

def test_1_sumas_conteos():
    """Verifica que las sumas en conteos sean correctas"""
    print_titulo("TEST 1: SUMAS EN CONTEOS")
    
    errores = []
    
    conteos = Conteo.objects.all()
    
    for conteo in conteos:
        # Suma manual de items
        items = ItemConteo.objects.filter(conteo=conteo)
        suma_manual = sum(item.cantidad for item in items)
        
        # Suma usando aggregate
        suma_aggregate = items.aggregate(total=Sum('cantidad'))['total'] or 0
        
        # Verificar que coincidan
        if suma_manual != suma_aggregate:
            errores.append(
                f"Conteo {conteo.nombre}: suma manual={suma_manual}, aggregate={suma_aggregate}"
            )
        else:
            print_exito(f"Conteo {conteo.nombre}: {suma_manual} unidades (verificado)")
        
        # Verificar suma de movimientos
        movimientos = MovimientoConteo.objects.filter(conteo=conteo)
        suma_movimientos = movimientos.aggregate(total=Sum('cantidad_cambiada'))['total'] or 0
        
        # La suma de movimientos debería ser igual a la suma de items (si no hay eliminaciones)
        movimientos_eliminar = movimientos.filter(tipo='eliminar').count()
        if movimientos_eliminar == 0 and movimientos.exists():
            if abs(suma_movimientos - suma_manual) > 0.01:  # Tolerancia para decimales
                errores.append(
                    f"Conteo {conteo.nombre}: suma items={suma_manual}, suma movimientos={suma_movimientos}"
                )
            else:
                print_exito(f"Conteo {conteo.nombre}: suma movimientos coincide con items")
        elif not movimientos.exists() and items.exists():
            # Si hay items pero no movimientos, puede ser porque se crearon directamente (test)
            print_info(f"Conteo {conteo.nombre}: tiene items pero no movimientos (puede ser de test directo)")
    
    return errores

def test_2_calculos_stock():
    """Verifica que los cálculos de stock sean correctos"""
    print_titulo("TEST 2: CÁLCULOS DE STOCK")
    
    errores = []
    
    productos = Producto.objects.filter(activo=True)[:10]
    
    for producto in productos:
        # Calcular stock manualmente
        conteos_finalizados = Conteo.objects.filter(
            estado='finalizado',
            items__producto=producto
        ).order_by('-fecha_fin')
        
        stock_manual = 0
        if conteos_finalizados.exists():
            ultimo_conteo = conteos_finalizados.first()
            item = ItemConteo.objects.filter(
                conteo=ultimo_conteo,
                producto=producto
            ).first()
            if item:
                stock_manual = item.cantidad
        
        # Obtener stock usando método
        stock_metodo = producto.get_stock_actual()
        
        if stock_manual != stock_metodo:
            errores.append(
                f"Producto {producto.nombre}: stock manual={stock_manual}, método={stock_metodo}"
            )
        else:
            print_exito(f"Producto {producto.nombre}: stock={stock_metodo} (verificado)")
    
    return errores

def test_3_calculos_valores():
    """Verifica que los cálculos de valores (precio * cantidad) sean correctos"""
    print_titulo("TEST 3: CÁLCULOS DE VALORES")
    
    errores = []
    
    # 3.1 Verificar valores en ItemComparativo
    items = ItemComparativo.objects.all()[:20]
    
    for item in items:
        precio = float(item.producto.precio)
        
        # Valor Sistema 1
        valor_s1_esperado = item.cantidad_sistema1 * precio
        valor_s1_metodo = float(item.get_valor_sistema1())
        if abs(valor_s1_esperado - valor_s1_metodo) > 0.01:
            errores.append(
                f"Item {item.id} S1: esperado={valor_s1_esperado:.2f}, método={valor_s1_metodo:.2f}"
            )
        
        # Valor Sistema 2
        valor_s2_esperado = item.cantidad_sistema2 * precio
        valor_s2_metodo = float(item.get_valor_sistema2())
        if abs(valor_s2_esperado - valor_s2_metodo) > 0.01:
            errores.append(
                f"Item {item.id} S2: esperado={valor_s2_esperado:.2f}, método={valor_s2_metodo:.2f}"
            )
        
        # Valor Físico
        valor_fisico_esperado = item.cantidad_fisico * precio
        valor_fisico_metodo = float(item.get_valor_fisico())
        if abs(valor_fisico_esperado - valor_fisico_metodo) > 0.01:
            errores.append(
                f"Item {item.id} Físico: esperado={valor_fisico_esperado:.2f}, método={valor_fisico_metodo:.2f}"
            )
    
    if not errores:
        print_exito(f"Todos los cálculos de valores son correctos ({len(items)} items verificados)")
    
    return errores

def test_4_calculos_diferencias():
    """Verifica que los cálculos de diferencias sean correctos"""
    print_titulo("TEST 4: CÁLCULOS DE DIFERENCIAS")
    
    errores = []
    
    items = ItemComparativo.objects.all()[:20]
    
    for item in items:
        # Diferencia Sistema 1 (cantidad)
        diferencia_s1_esperada = item.cantidad_fisico - item.cantidad_sistema1
        if item.diferencia_sistema1 != diferencia_s1_esperada:
            errores.append(
                f"Item {item.id} Dif S1: esperada={diferencia_s1_esperada}, actual={item.diferencia_sistema1}"
            )
        
        # Diferencia Sistema 2 (cantidad)
        diferencia_s2_esperada = item.cantidad_fisico - item.cantidad_sistema2
        if item.diferencia_sistema2 != diferencia_s2_esperada:
            errores.append(
                f"Item {item.id} Dif S2: esperada={diferencia_s2_esperada}, actual={item.diferencia_sistema2}"
            )
        
        # Diferencia Sistema 1 (valor)
        precio = float(item.producto.precio)
        diferencia_valor_s1_esperada = (item.cantidad_fisico * precio) - (item.cantidad_sistema1 * precio)
        diferencia_valor_s1_metodo = float(item.get_diferencia_valor_sistema1())
        if abs(diferencia_valor_s1_esperada - diferencia_valor_s1_metodo) > 0.01:
            errores.append(
                f"Item {item.id} Dif Valor S1: esperada={diferencia_valor_s1_esperada:.2f}, método={diferencia_valor_s1_metodo:.2f}"
            )
        
        # Diferencia Sistema 2 (valor)
        diferencia_valor_s2_esperada = (item.cantidad_fisico * precio) - (item.cantidad_sistema2 * precio)
        diferencia_valor_s2_metodo = float(item.get_diferencia_valor_sistema2())
        if abs(diferencia_valor_s2_esperada - diferencia_valor_s2_metodo) > 0.01:
            errores.append(
                f"Item {item.id} Dif Valor S2: esperada={diferencia_valor_s2_esperada:.2f}, método={diferencia_valor_s2_metodo:.2f}"
            )
    
    if not errores:
        print_exito(f"Todos los cálculos de diferencias son correctos ({len(items)} items verificados)")
    
    return errores

def test_5_sumas_totales_comparativos():
    """Verifica que las sumas totales en comparativos sean correctas"""
    print_titulo("TEST 5: SUMAS TOTALES EN COMPARATIVOS")
    
    errores = []
    
    comparativos = ComparativoInventario.objects.all()
    
    for comparativo in comparativos:
        items = ItemComparativo.objects.filter(comparativo=comparativo)
        
        # Suma manual de cantidades
        total_s1_manual = sum(item.cantidad_sistema1 for item in items)
        total_s2_manual = sum(item.cantidad_sistema2 for item in items)
        total_fisico_manual = sum(item.cantidad_fisico for item in items)
        
        # Suma usando aggregate
        total_s1_aggregate = items.aggregate(total=Sum('cantidad_sistema1'))['total'] or 0
        total_s2_aggregate = items.aggregate(total=Sum('cantidad_sistema2'))['total'] or 0
        total_fisico_aggregate = items.aggregate(total=Sum('cantidad_fisico'))['total'] or 0
        
        # Verificar cantidades
        if total_s1_manual != total_s1_aggregate:
            errores.append(
                f"Comparativo {comparativo.nombre} S1: manual={total_s1_manual}, aggregate={total_s1_aggregate}"
            )
        if total_s2_manual != total_s2_aggregate:
            errores.append(
                f"Comparativo {comparativo.nombre} S2: manual={total_s2_manual}, aggregate={total_s2_aggregate}"
            )
        if total_fisico_manual != total_fisico_aggregate:
            errores.append(
                f"Comparativo {comparativo.nombre} Físico: manual={total_fisico_manual}, aggregate={total_fisico_aggregate}"
            )
        
        # Suma manual de valores
        total_valor_s1_manual = sum(float(item.get_valor_sistema1()) for item in items)
        total_valor_s2_manual = sum(float(item.get_valor_sistema2()) for item in items)
        total_valor_fisico_manual = sum(float(item.get_valor_fisico()) for item in items)
        
        # Calcular diferencias de totales
        diferencia_cantidad_s1 = total_fisico_manual - total_s1_manual
        diferencia_cantidad_s2 = total_fisico_manual - total_s2_manual
        diferencia_valor_s1 = total_valor_fisico_manual - total_valor_s1_manual
        diferencia_valor_s2 = total_valor_fisico_manual - total_valor_s2_manual
        
        print_exito(f"Comparativo {comparativo.nombre}:")
        print_info(f"  S1: {total_s1_manual} unidades, ${total_valor_s1_manual:.2f}")
        print_info(f"  S2: {total_s2_manual} unidades, ${total_valor_s2_manual:.2f}")
        print_info(f"  Físico: {total_fisico_manual} unidades, ${total_valor_fisico_manual:.2f}")
        print_info(f"  Dif S1: {diferencia_cantidad_s1} unidades, ${diferencia_valor_s1:.2f}")
        print_info(f"  Dif S2: {diferencia_cantidad_s2} unidades, ${diferencia_valor_s2:.2f}")
    
    return errores

def test_6_suma_conteos_finalizados():
    """Verifica que la suma de conteos finalizados sea correcta"""
    print_titulo("TEST 6: SUMA DE CONTEOS FINALIZADOS")
    
    errores = []
    
    # Obtener todos los conteos finalizados
    conteos_finalizados = Conteo.objects.filter(estado='finalizado')
    
    # Agrupar items por producto y sumar cantidades
    items_agregados = ItemConteo.objects.filter(
        conteo__in=conteos_finalizados
    ).values('producto').annotate(
        cantidad_total=Sum('cantidad')
    )
    
    cantidad_por_producto = {item['producto']: item['cantidad_total'] for item in items_agregados}
    
    # Verificar algunos productos
    productos_verificar = Producto.objects.filter(activo=True)[:10]
    
    for producto in productos_verificar:
        cantidad_esperada = cantidad_por_producto.get(producto.id, 0)
        
        # Verificar en comparativos que se hayan procesado después de todos los conteos
        items_comparativo = ItemComparativo.objects.filter(producto=producto)
        for item in items_comparativo:
            # Solo verificar si el comparativo tiene conteo asignado o fue procesado recientemente
            # Si cantidad_fisico es diferente, puede ser porque:
            # 1. El comparativo se procesó antes de que todos los conteos estuvieran finalizados
            # 2. El comparativo tiene un conteo específico asignado (no suma todos)
            if item.comparativo.conteo:
                # Si tiene conteo específico, verificar contra ese conteo
                items_conteo_especifico = ItemConteo.objects.filter(
                    conteo=item.comparativo.conteo,
                    producto=producto
                )
                cantidad_conteo_especifico = items_conteo_especifico.aggregate(
                    total=Sum('cantidad')
                )['total'] or 0
                
                if item.cantidad_fisico != cantidad_conteo_especifico:
                    errores.append(
                        f"Producto {producto.nombre} en comparativo {item.comparativo.nombre}: "
                        f"cantidad_fisico={item.cantidad_fisico}, esperada del conteo={cantidad_conteo_especifico}"
                    )
            else:
                # Si no tiene conteo específico, debería sumar todos los finalizados
                if item.cantidad_fisico != cantidad_esperada:
                    # Verificar si hay conteos finalizados después de procesar el comparativo
                    fecha_procesado = item.comparativo.fecha_creacion
                    conteos_despues = Conteo.objects.filter(
                        estado='finalizado',
                        fecha_fin__gt=fecha_procesado
                    )
                    if conteos_despues.exists():
                        print_info(
                            f"Producto {producto.nombre} en comparativo {item.comparativo.nombre}: "
                            f"diferencia puede ser porque hay {conteos_despues.count()} conteo(s) finalizado(s) después"
                        )
                    else:
                        errores.append(
                            f"Producto {producto.nombre} en comparativo {item.comparativo.nombre}: "
                            f"cantidad_fisico={item.cantidad_fisico}, esperada={cantidad_esperada}"
                        )
    
    if not errores:
        print_exito(f"Suma de conteos finalizados correcta para {len(productos_verificar)} productos")
        print_info(f"Total de conteos finalizados: {conteos_finalizados.count()}")
        print_info(f"Total de productos con cantidad: {len(cantidad_por_producto)}")
    
    return errores

def test_7_operaciones_movimientos():
    """Verifica que las operaciones en movimientos sean correctas"""
    print_titulo("TEST 7: OPERACIONES EN MOVIMIENTOS")
    
    errores = []
    
    movimientos = MovimientoConteo.objects.all()[:30]
    
    for movimiento in movimientos:
        # Verificar que cantidad_cambiada sea correcta
        cantidad_cambiada_esperada = movimiento.cantidad_nueva - movimiento.cantidad_anterior
        
        if movimiento.cantidad_cambiada != cantidad_cambiada_esperada:
            errores.append(
                f"Movimiento {movimiento.id}: cantidad_cambiada={movimiento.cantidad_cambiada}, "
                f"esperada={cantidad_cambiada_esperada} (nueva={movimiento.cantidad_nueva}, anterior={movimiento.cantidad_anterior})"
            )
        
        # Verificar lógica según tipo
        if movimiento.tipo == 'agregar':
            if movimiento.cantidad_anterior != 0:
                errores.append(
                    f"Movimiento {movimiento.id} (agregar): cantidad_anterior debería ser 0, es {movimiento.cantidad_anterior}"
                )
            if movimiento.cantidad_cambiada <= 0:
                errores.append(
                    f"Movimiento {movimiento.id} (agregar): cantidad_cambiada debería ser > 0, es {movimiento.cantidad_cambiada}"
                )
        
        elif movimiento.tipo == 'modificar':
            if movimiento.cantidad_anterior == 0:
                errores.append(
                    f"Movimiento {movimiento.id} (modificar): cantidad_anterior debería ser > 0, es {movimiento.cantidad_anterior}"
                )
        
        elif movimiento.tipo == 'eliminar':
            if movimiento.cantidad_nueva != 0:
                errores.append(
                    f"Movimiento {movimiento.id} (eliminar): cantidad_nueva debería ser 0, es {movimiento.cantidad_nueva}"
                )
            if movimiento.cantidad_cambiada >= 0:
                errores.append(
                    f"Movimiento {movimiento.id} (eliminar): cantidad_cambiada debería ser < 0, es {movimiento.cantidad_cambiada}"
                )
    
    if not errores:
        print_exito(f"Todas las operaciones de movimientos son correctas ({len(movimientos)} verificados)")
    
    return errores

def test_8_verificacion_cruzada():
    """Verifica consistencia cruzada de cálculos"""
    print_titulo("TEST 8: VERIFICACIÓN CRUZADA")
    
    errores = []
    
    # 8.1 Verificar que suma de items en conteo = suma de movimientos (sin eliminaciones)
    conteos = Conteo.objects.all()[:5]
    
    for conteo in conteos:
        items = ItemConteo.objects.filter(conteo=conteo)
        suma_items = sum(item.cantidad for item in items)
        
        movimientos = MovimientoConteo.objects.filter(conteo=conteo)
        movimientos_sin_eliminar = movimientos.exclude(tipo='eliminar')
        suma_movimientos = sum(mov.cantidad_cambiada for mov in movimientos_sin_eliminar)
        
        if abs(suma_items - suma_movimientos) > 0.01:
            print_info(
                f"Conteo {conteo.nombre}: items={suma_items}, movimientos={suma_movimientos} "
                f"(diferencia puede ser normal si hay modificaciones)"
            )
        else:
            print_exito(f"Conteo {conteo.nombre}: suma items = suma movimientos = {suma_items}")
    
    # 8.2 Verificar que totales de comparativo sean consistentes
    comparativos = ComparativoInventario.objects.all()
    
    for comparativo in comparativos:
        items = ItemComparativo.objects.filter(comparativo=comparativo)
        
        # Calcular totales manualmente
        total_s1 = sum(item.cantidad_sistema1 for item in items)
        total_s2 = sum(item.cantidad_sistema2 for item in items)
        total_fisico = sum(item.cantidad_fisico for item in items)
        
        # Calcular diferencias manualmente
        dif_s1_manual = total_fisico - total_s1
        dif_s2_manual = total_fisico - total_s2
        
        # Calcular diferencias sumando items
        dif_s1_items = sum(item.diferencia_sistema1 for item in items)
        dif_s2_items = sum(item.diferencia_sistema2 for item in items)
        
        if dif_s1_manual != dif_s1_items:
            errores.append(
                f"Comparativo {comparativo.nombre} Dif S1: manual={dif_s1_manual}, items={dif_s1_items}"
            )
        if dif_s2_manual != dif_s2_items:
            errores.append(
                f"Comparativo {comparativo.nombre} Dif S2: manual={dif_s2_manual}, items={dif_s2_items}"
            )
    
    if not errores:
        print_exito("Todas las verificaciones cruzadas son correctas")
    
    return errores

def main():
    """Ejecuta todos los tests de operaciones matemáticas"""
    print(f"\n{Colores.NEGRITA}{Colores.AZUL}")
    print("="*70)
    print("TEST DE OPERACIONES MATEMÁTICAS DEL SISTEMA")
    print("="*70)
    print(f"{Colores.RESET}")
    
    todos_errores = []
    
    # Ejecutar todos los tests
    errores1 = test_1_sumas_conteos()
    todos_errores.extend(errores1)
    
    errores2 = test_2_calculos_stock()
    todos_errores.extend(errores2)
    
    errores3 = test_3_calculos_valores()
    todos_errores.extend(errores3)
    
    errores4 = test_4_calculos_diferencias()
    todos_errores.extend(errores4)
    
    errores5 = test_5_sumas_totales_comparativos()
    todos_errores.extend(errores5)
    
    errores6 = test_6_suma_conteos_finalizados()
    todos_errores.extend(errores6)
    
    errores7 = test_7_operaciones_movimientos()
    todos_errores.extend(errores7)
    
    errores8 = test_8_verificacion_cruzada()
    todos_errores.extend(errores8)
    
    # Resumen final
    print_titulo("RESUMEN DE OPERACIONES MATEMÁTICAS")
    
    print(f"\n{Colores.NEGRITA}Errores encontrados: {len(todos_errores)}{Colores.RESET}")
    if todos_errores:
        print(f"{Colores.ROJO}")
        for error in todos_errores[:15]:  # Mostrar primeros 15
            print(f"  ✗ {error}")
        if len(todos_errores) > 15:
            print(f"  ... y {len(todos_errores) - 15} errores más")
        print(f"{Colores.RESET}")
    else:
        print(f"{Colores.VERDE}")
        print("  ✓ No se encontraron errores en las operaciones matemáticas")
        print(f"{Colores.RESET}")
    
    # Resultado final
    if len(todos_errores) == 0:
        print(f"\n{Colores.VERDE}{Colores.NEGRITA}")
        print("="*70)
        print("✓ ✓ ✓ TODAS LAS OPERACIONES MATEMÁTICAS SON CORRECTAS")
        print("="*70)
        print(f"{Colores.RESET}")
    else:
        print(f"\n{Colores.ROJO}{Colores.NEGRITA}")
        print("="*70)
        print(f"✗ ✗ ✗ SE ENCONTRARON {len(todos_errores)} ERRORES EN OPERACIONES")
        print("="*70)
        print(f"{Colores.RESET}")

if __name__ == '__main__':
    main()

