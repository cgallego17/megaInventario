"""
Test completo para verificar la congruencia entre movimientos y conteos.
Verifica que:
1. Los movimientos reflejen correctamente los cambios en los conteos
2. Las cantidades en items coincidan con los movimientos
3. Las estadísticas sean correctas
4. No haya inconsistencias entre movimientos y items
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
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megaInventario.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from productos.models import Producto
from conteo.models import Conteo, ItemConteo
from movimientos.models import MovimientoConteo
import json

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

def print_warning(text):
    print(f"  ⚠ {text}")

class TestCongruenciaMovimientosConteos:
    """Test completo para verificar congruencia entre movimientos y conteos"""
    
    def __init__(self):
        self.client = Client()
        self.admin_user = None
        self.normal_user = None
        self.conteo = None
        self.productos = []
        self.items = []
        
    def setup(self):
        """Configurar datos de prueba"""
        print_header("Configurando datos de prueba")
        
        # Crear o obtener usuarios
        self.admin_user, created = User.objects.get_or_create(
            username='admin_congruencia',
            defaults={
                'is_superuser': True,
                'is_staff': True
            }
        )
        if created:
            self.admin_user.set_password('testpass123')
            self.admin_user.save()
        print_success(f"Usuario administrador {'creado' if created else 'obtenido'}: {self.admin_user.username}")
        
        self.normal_user, created = User.objects.get_or_create(
            username='normal_congruencia',
            defaults={
                'is_superuser': False,
                'is_staff': False
            }
        )
        if created:
            self.normal_user.set_password('testpass123')
            self.normal_user.save()
        print_success(f"Usuario normal {'creado' if created else 'obtenido'}: {self.normal_user.username}")
        
        # Crear productos
        for i in range(5):
            producto, created = Producto.objects.get_or_create(
                codigo_barras=f'CONG{i+1:05d}',
                defaults={
                    'nombre': f'Producto Congruencia {i+1}',
                    'precio': 100.00 * (i+1),
                    'activo': True
                }
            )
            self.productos.append(producto)
        print_success(f"{len(self.productos)} productos listos")
        
        # Crear conteo
        self.conteo, created = Conteo.objects.get_or_create(
            nombre='Conteo Congruencia Test',
            numero_conteo=1,
            defaults={
                'estado': 'en_proceso',
                'usuario_creador': self.admin_user
            }
        )
        print_success(f"Conteo {'creado' if created else 'obtenido'}: {self.conteo.nombre}")
        
        # Limpiar items y movimientos existentes del conteo
        ItemConteo.objects.filter(conteo=self.conteo).delete()
        MovimientoConteo.objects.filter(conteo=self.conteo).delete()
        
        print_success("Configuración completada")
        
    def test_1_agregar_items_y_verificar_movimientos(self):
        """Verificar que al agregar items se crean movimientos correctos"""
        print_header("Test 1: Agregar items y verificar movimientos")
        
        self.client.force_login(self.normal_user)
        
        cantidades_iniciales = [10, 20, 30, 40, 50]
        
        for i, producto in enumerate(self.productos):
            cantidad = cantidades_iniciales[i]
            
            # Agregar item
            response = self.client.post(
                f'/conteo/{self.conteo.id}/agregar-item/',
                {
                    'producto_id': producto.id,
                    'cantidad': cantidad
                },
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            assert response.status_code == 200, f"Error al agregar item {i+1}"
            data = json.loads(response.content)
            assert data['success'], f"Fallo al agregar item {i+1}: {data.get('error', '')}"
            
            # Verificar que se creó el item
            item = ItemConteo.objects.filter(conteo=self.conteo, producto=producto).first()
            assert item is not None, f"Item no fue creado para producto {producto.nombre}"
            assert item.cantidad == cantidad, f"Cantidad incorrecta en item: {item.cantidad} != {cantidad}"
            
            # Verificar que se creó el movimiento
            movimiento = MovimientoConteo.objects.filter(
                conteo=self.conteo,
                producto=producto,
                tipo='agregar'
            ).order_by('-fecha_movimiento').first()
            
            assert movimiento is not None, f"Movimiento no fue creado para producto {producto.nombre}"
            assert movimiento.cantidad_anterior == 0, f"Cantidad anterior incorrecta: {movimiento.cantidad_anterior}"
            assert movimiento.cantidad_nueva == cantidad, f"Cantidad nueva incorrecta: {movimiento.cantidad_nueva}"
            assert movimiento.cantidad_cambiada == cantidad, f"Cantidad cambiada incorrecta: {movimiento.cantidad_cambiada}"
            assert movimiento.usuario == self.normal_user, f"Usuario incorrecto en movimiento"
            
            print_success(f"Producto {i+1}: Item y movimiento creados correctamente")
        
        # Guardar items para siguientes tests
        self.items = list(ItemConteo.objects.filter(conteo=self.conteo))
        print_success(f"Total items creados: {len(self.items)}")
        print_success(f"Total movimientos creados: {MovimientoConteo.objects.filter(conteo=self.conteo, tipo='agregar').count()}")
        
    def test_2_verificar_congruencia_agregar(self):
        """Verificar que las cantidades de items coinciden con los movimientos"""
        print_header("Test 2: Verificar congruencia después de agregar")
        
        # Calcular total desde items
        total_items = ItemConteo.objects.filter(conteo=self.conteo).aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        
        # Calcular total desde movimientos de agregar
        total_movimientos = MovimientoConteo.objects.filter(
            conteo=self.conteo,
            tipo='agregar'
        ).aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
        
        print_info(f"Total desde items: {total_items}")
        print_info(f"Total desde movimientos agregar: {total_movimientos}")
        
        assert total_items == total_movimientos, f"Incongruencia: items={total_items}, movimientos={total_movimientos}"
        print_success("Cantidades coinciden entre items y movimientos")
        
        # Verificar cada item individualmente
        for item in self.items:
            movimientos_item = MovimientoConteo.objects.filter(
                conteo=self.conteo,
                producto=item.producto,
                tipo='agregar'
            )
            
            suma_movimientos = movimientos_item.aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
            
            # Si hay múltiples movimientos de agregar (suma), la cantidad del item debe ser igual a la suma
            # Si solo hay uno, debe ser igual
            assert item.cantidad == suma_movimientos, \
                f"Incongruencia para {item.producto.nombre}: item={item.cantidad}, movimientos={suma_movimientos}"
            
            print_success(f"{item.producto.nombre}: Item={item.cantidad}, Movimientos={suma_movimientos}")
        
    def test_3_editar_items_y_verificar_movimientos(self):
        """Verificar que al editar items se crean movimientos correctos"""
        print_header("Test 3: Editar items y verificar movimientos")
        
        self.client.force_login(self.admin_user)
        
        ediciones = [
            (self.items[0], 15),  # 10 -> 15 (+5)
            (self.items[1], 25),  # 20 -> 25 (+5)
            (self.items[2], 20),  # 30 -> 20 (-10)
        ]
        
        for item, nueva_cantidad in ediciones:
            cantidad_anterior = item.cantidad
            
            # Editar item
            response = self.client.post(
                f'/conteo/item/{item.id}/editar/',
                {'cantidad': nueva_cantidad},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            assert response.status_code == 200, f"Error al editar item {item.id}"
            data = json.loads(response.content)
            assert data['success'], f"Fallo al editar item {item.id}: {data.get('error', '')}"
            
            # Verificar que el item se actualizó
            item.refresh_from_db()
            assert item.cantidad == nueva_cantidad, f"Cantidad no actualizada: {item.cantidad} != {nueva_cantidad}"
            
            # Verificar que se creó el movimiento de modificar
            movimiento = MovimientoConteo.objects.filter(
                conteo=self.conteo,
                producto=item.producto,
                tipo='modificar',
                item_conteo=item
            ).order_by('-fecha_movimiento').first()
            
            assert movimiento is not None, f"Movimiento de modificar no fue creado"
            assert movimiento.cantidad_anterior == cantidad_anterior, \
                f"Cantidad anterior incorrecta: {movimiento.cantidad_anterior} != {cantidad_anterior}"
            assert movimiento.cantidad_nueva == nueva_cantidad, \
                f"Cantidad nueva incorrecta: {movimiento.cantidad_nueva} != {nueva_cantidad}"
            assert movimiento.cantidad_cambiada == (nueva_cantidad - cantidad_anterior), \
                f"Cantidad cambiada incorrecta: {movimiento.cantidad_cambiada} != {nueva_cantidad - cantidad_anterior}"
            
            print_success(f"{item.producto.nombre}: {cantidad_anterior} -> {nueva_cantidad} (movimiento: {movimiento.cantidad_cambiada:+})")
        
    def test_4_verificar_congruencia_despues_de_editar(self):
        """Verificar congruencia después de editar"""
        print_header("Test 4: Verificar congruencia después de editar")
        
        # Calcular total desde items
        total_items = ItemConteo.objects.filter(conteo=self.conteo).aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        
        # Calcular total desde movimientos
        # Total = suma de todos los movimientos de agregar + suma de cambios de modificar
        movimientos_agregar = MovimientoConteo.objects.filter(
            conteo=self.conteo,
            tipo='agregar'
        ).aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
        
        movimientos_modificar = MovimientoConteo.objects.filter(
            conteo=self.conteo,
            tipo='modificar'
        ).aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
        
        total_movimientos = movimientos_agregar + movimientos_modificar
        
        print_info(f"Total desde items: {total_items}")
        print_info(f"Total desde movimientos agregar: {movimientos_agregar}")
        print_info(f"Total desde movimientos modificar: {movimientos_modificar}")
        print_info(f"Total desde movimientos (agregar + modificar): {total_movimientos}")
        
        # El total de items debe ser igual a la suma de movimientos de agregar más los cambios de modificar
        assert total_items == total_movimientos, \
            f"Incongruencia: items={total_items}, movimientos={total_movimientos}"
        print_success("Cantidades coinciden después de editar")
        
        # Verificar cada item individualmente
        for item in ItemConteo.objects.filter(conteo=self.conteo):
            # Sumar todos los movimientos de agregar para este producto
            movimientos_agregar_item = MovimientoConteo.objects.filter(
                conteo=self.conteo,
                producto=item.producto,
                tipo='agregar'
            ).aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
            
            # Sumar todos los cambios de modificar para este producto
            movimientos_modificar_item = MovimientoConteo.objects.filter(
                conteo=self.conteo,
                producto=item.producto,
                tipo='modificar'
            ).aggregate(Sum('cantidad_cambiada'))['cantidad_cambiada__sum'] or 0
            
            cantidad_calculada = movimientos_agregar_item + movimientos_modificar_item
            
            assert item.cantidad == cantidad_calculada, \
                f"Incongruencia para {item.producto.nombre}: item={item.cantidad}, calculado={cantidad_calculada} (agregar={movimientos_agregar_item}, modificar={movimientos_modificar_item})"
            
            print_success(f"{item.producto.nombre}: Item={item.cantidad}, Calculado={cantidad_calculada}")
        
    def test_5_verificar_estadisticas_conteo(self):
        """Verificar que las estadísticas del conteo son correctas"""
        print_header("Test 5: Verificar estadísticas del conteo")
        
        # Estadísticas desde items
        total_items_count = ItemConteo.objects.filter(conteo=self.conteo).count()
        total_cantidad_items = ItemConteo.objects.filter(conteo=self.conteo).aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        
        # Estadísticas desde movimientos
        total_movimientos_count = MovimientoConteo.objects.filter(conteo=self.conteo).count()
        movimientos_agregar_count = MovimientoConteo.objects.filter(conteo=self.conteo, tipo='agregar').count()
        movimientos_modificar_count = MovimientoConteo.objects.filter(conteo=self.conteo, tipo='modificar').count()
        
        print_info(f"Total items: {total_items_count}")
        print_info(f"Total cantidad items: {total_cantidad_items}")
        print_info(f"Total movimientos: {total_movimientos_count}")
        print_info(f"Movimientos agregar: {movimientos_agregar_count}")
        print_info(f"Movimientos modificar: {movimientos_modificar_count}")
        
        # Verificar que hay al menos un movimiento por item agregado
        assert movimientos_agregar_count >= total_items_count, \
            f"Debe haber al menos un movimiento de agregar por item"
        
        print_success("Estadísticas del conteo son correctas")
        
    def test_6_verificar_historial_completo(self):
        """Verificar que el historial de movimientos refleja correctamente el estado actual"""
        print_header("Test 6: Verificar historial completo")
        
        # Para cada item, reconstruir su cantidad desde el historial de movimientos
        for item in ItemConteo.objects.filter(conteo=self.conteo):
            movimientos = MovimientoConteo.objects.filter(
                conteo=self.conteo,
                producto=item.producto
            ).order_by('fecha_movimiento')
            
            cantidad_reconstruida = 0
            for movimiento in movimientos:
                if movimiento.tipo == 'agregar':
                    cantidad_reconstruida += movimiento.cantidad_cambiada
                elif movimiento.tipo == 'modificar':
                    cantidad_reconstruida += movimiento.cantidad_cambiada
                elif movimiento.tipo == 'eliminar':
                    cantidad_reconstruida = 0  # Si se elimina, vuelve a 0
            
            assert item.cantidad == cantidad_reconstruida, \
                f"Historial inconsistente para {item.producto.nombre}: item={item.cantidad}, reconstruido={cantidad_reconstruida}"
            
            print_success(f"{item.producto.nombre}: Item={item.cantidad}, Reconstruido={cantidad_reconstruida} (movimientos: {movimientos.count()})")
        
    def test_7_verificar_eliminar_item(self):
        """Verificar que al eliminar un item se crea el movimiento correcto"""
        print_header("Test 7: Eliminar item y verificar movimiento")
        
        if not self.items:
            print_warning("No hay items para eliminar, saltando test")
            return
        
        item_a_eliminar = self.items[-1]  # Último item
        cantidad_eliminada = item_a_eliminar.cantidad
        producto_eliminado = item_a_eliminar.producto
        
        self.client.force_login(self.normal_user)
        
        # Eliminar item
        response = self.client.post(
            f'/conteo/item/{item_a_eliminar.id}/eliminar/',
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            follow=True
        )
        
        # Verificar que el item fue eliminado
        assert not ItemConteo.objects.filter(id=item_a_eliminar.id).exists(), "Item no fue eliminado"
        
        # Verificar que se creó el movimiento de eliminar
        movimiento = MovimientoConteo.objects.filter(
            conteo=self.conteo,
            producto=producto_eliminado,
            tipo='eliminar'
        ).order_by('-fecha_movimiento').first()
        
        assert movimiento is not None, "Movimiento de eliminar no fue creado"
        assert movimiento.cantidad_anterior == cantidad_eliminada, \
            f"Cantidad anterior incorrecta: {movimiento.cantidad_anterior} != {cantidad_eliminada}"
        assert movimiento.cantidad_nueva == 0, \
            f"Cantidad nueva debe ser 0: {movimiento.cantidad_nueva}"
        assert movimiento.cantidad_cambiada == -cantidad_eliminada, \
            f"Cantidad cambiada incorrecta: {movimiento.cantidad_cambiada} != {-cantidad_eliminada}"
        
        print_success(f"Item eliminado correctamente: {producto_eliminado.nombre} (cantidad: {cantidad_eliminada})")
        
    def test_8_verificar_integridad_final(self):
        """Verificar integridad final de todos los datos"""
        print_header("Test 8: Verificar integridad final")
        
        # Verificar que todos los movimientos tienen datos válidos
        movimientos = MovimientoConteo.objects.filter(conteo=self.conteo)
        
        for movimiento in movimientos:
            assert movimiento.conteo is not None, "Movimiento sin conteo"
            assert movimiento.producto is not None, "Movimiento sin producto"
            assert movimiento.usuario is not None, "Movimiento sin usuario"
            assert movimiento.tipo in ['agregar', 'modificar', 'eliminar'], f"Tipo inválido: {movimiento.tipo}"
            assert movimiento.cantidad_cambiada == (movimiento.cantidad_nueva - movimiento.cantidad_anterior), \
                f"Cantidad cambiada inconsistente: {movimiento.cantidad_cambiada} != {movimiento.cantidad_nueva - movimiento.cantidad_anterior}"
        
        print_success(f"Todos los {movimientos.count()} movimientos tienen datos válidos")
        
        # Verificar que todos los items tienen datos válidos
        items = ItemConteo.objects.filter(conteo=self.conteo)
        
        for item in items:
            assert item.conteo is not None, "Item sin conteo"
            assert item.producto is not None, "Item sin producto"
            assert item.cantidad >= 0, f"Cantidad negativa: {item.cantidad}"
        
        print_success(f"Todos los {items.count()} items tienen datos válidos")
        
        # Verificar que no hay items huérfanos (sin movimientos)
        items_sin_movimientos = []
        for item in items:
            if not MovimientoConteo.objects.filter(conteo=self.conteo, producto=item.producto).exists():
                items_sin_movimientos.append(item)
        
        if items_sin_movimientos:
            print_warning(f"Items sin movimientos: {len(items_sin_movimientos)}")
            for item in items_sin_movimientos:
                print_warning(f"  - {item.producto.nombre}")
        else:
            print_success("Todos los items tienen movimientos asociados")
        
    def cleanup(self):
        """Limpiar datos de prueba"""
        print_header("Limpiando datos de prueba")
        
        try:
            if self.conteo:
                MovimientoConteo.objects.filter(conteo=self.conteo).delete()
                ItemConteo.objects.filter(conteo=self.conteo).delete()
                # No eliminar el conteo para no afectar otros tests
                # Conteo.objects.filter(id=self.conteo.id).delete()
            
            # No eliminar productos ni usuarios para no afectar otros tests
            print_success("Datos limpiados (conteo mantenido para referencia)")
        except Exception as e:
            print_error(f"Error al limpiar: {str(e)}")
        
    def run_all_tests(self):
        """Ejecutar todos los tests"""
        try:
            self.setup()
            self.test_1_agregar_items_y_verificar_movimientos()
            self.test_2_verificar_congruencia_agregar()
            self.test_3_editar_items_y_verificar_movimientos()
            self.test_4_verificar_congruencia_despues_de_editar()
            self.test_5_verificar_estadisticas_conteo()
            self.test_6_verificar_historial_completo()
            self.test_7_verificar_eliminar_item()
            self.test_8_verificar_integridad_final()
            
            print_header("TODOS LOS TESTS DE CONGRUENCIA PASARON EXITOSAMENTE")
            print_success("Los movimientos y conteos son completamente congruentes")
            print_success("Todas las operaciones funcionan correctamente")
            
        except AssertionError as e:
            print_error(f"Test falló: {str(e)}")
            raise
        except Exception as e:
            print_error(f"Error inesperado: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            self.cleanup()

if __name__ == '__main__':
    test = TestCongruenciaMovimientosConteos()
    test.run_all_tests()

