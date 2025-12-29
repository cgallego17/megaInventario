"""
Test completo para verificar que la edición de items en conteo
no daña los cálculos y mantiene la integridad de los datos.
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

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.db.models import Sum
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

class TestEditarItemConteo:
    """Test completo para verificar la edición de items en conteo"""
    
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
            username='admin_test',
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
            username='normal_test',
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
            producto = Producto.objects.create(
                nombre=f'Producto Test {i+1}',
                codigo_barras=f'1234567890{i+1}',
                precio=100.00 * (i+1),
                activo=True
            )
            self.productos.append(producto)
        print_success(f"{len(self.productos)} productos creados")
        
        # Crear conteo
        self.conteo = Conteo.objects.create(
            nombre='Conteo Test Edición',
            numero_conteo=1,
            estado='en_proceso',
            usuario_creador=self.admin_user
        )
        print_success(f"Conteo creado: {self.conteo.nombre}")
        
        # Crear items iniciales
        cantidades_iniciales = [10, 20, 30, 40, 50]
        for i, producto in enumerate(self.productos):
            item = ItemConteo.objects.create(
                conteo=self.conteo,
                producto=producto,
                cantidad=cantidades_iniciales[i],
                usuario_conteo=self.normal_user
            )
            self.items.append(item)
        print_success(f"{len(self.items)} items creados con cantidades iniciales")
        
        print_success("Configuración completada")
        
    def test_1_verificar_calculos_iniciales(self):
        """Verificar que los cálculos iniciales son correctos"""
        print_header("Test 1: Verificar cálculos iniciales")
        
        # Calcular totales esperados
        total_items_esperado = len(self.items)
        total_cantidad_esperado = sum([item.cantidad for item in self.items])
        
        # Obtener totales del conteo
        total_items_real = self.conteo.items.count()
        total_cantidad_real = self.conteo.items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        
        print_info(f"Total items esperado: {total_items_esperado}, real: {total_items_real}")
        print_info(f"Total cantidad esperado: {total_cantidad_esperado}, real: {total_cantidad_real}")
        
        assert total_items_esperado == total_items_real, f"Total items incorrecto: {total_items_esperado} != {total_items_real}"
        assert total_cantidad_esperado == total_cantidad_real, f"Total cantidad incorrecto: {total_cantidad_esperado} != {total_cantidad_real}"
        
        print_success("Cálculos iniciales correctos")
        
    def test_2_usuario_normal_no_puede_editar(self):
        """Verificar que usuarios normales no pueden editar"""
        print_header("Test 2: Usuario normal no puede editar")
        
        self.client.force_login(self.normal_user)
        
        # Intentar editar un item
        item = self.items[0]
        response = self.client.post(
            f'/conteo/item/{item.id}/editar/',
            {'cantidad': 999},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        assert response.status_code == 200, f"Status code incorrecto: {response.status_code}"
        
        data = json.loads(response.content)
        assert not data['success'], "Usuario normal no debería poder editar"
        assert 'permisos' in data['error'].lower() or 'administrador' in data['error'].lower()
        
        print_success("Usuario normal correctamente bloqueado")
        
        # Verificar que la cantidad no cambió
        item.refresh_from_db()
        assert item.cantidad == 10, f"Cantidad no debería haber cambiado: {item.cantidad}"
        print_success("Cantidad no fue modificada por usuario normal")
        
    def test_3_admin_puede_editar(self):
        """Verificar que administradores pueden editar"""
        print_header("Test 3: Administrador puede editar")
        
        self.client.force_login(self.admin_user)
        
        # Editar un item
        item = self.items[0]
        cantidad_anterior = item.cantidad
        nueva_cantidad = 25
        
        response = self.client.post(
            f'/conteo/item/{item.id}/editar/',
            {'cantidad': nueva_cantidad},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        assert response.status_code == 200, f"Status code incorrecto: {response.status_code}"
        
        data = json.loads(response.content)
        assert data['success'], f"Edición falló: {data.get('error', '')}"
        assert data['cantidad'] == nueva_cantidad, f"Cantidad incorrecta en respuesta: {data['cantidad']}"
        
        print_success("Edición exitosa")
        
        # Verificar que la cantidad se actualizó en la BD
        item.refresh_from_db()
        assert item.cantidad == nueva_cantidad, f"Cantidad no se actualizó: {item.cantidad} != {nueva_cantidad}"
        print_success(f"Cantidad actualizada correctamente: {cantidad_anterior} -> {nueva_cantidad}")
        
        # Verificar que se registró el movimiento
        movimiento = MovimientoConteo.objects.filter(
            item_conteo=item,
            tipo='modificar'
        ).order_by('-id').first()
        
        assert movimiento is not None, "Movimiento no fue registrado"
        assert movimiento.cantidad_anterior == cantidad_anterior, f"Cantidad anterior incorrecta: {movimiento.cantidad_anterior}"
        assert movimiento.cantidad_nueva == nueva_cantidad, f"Cantidad nueva incorrecta: {movimiento.cantidad_nueva}"
        assert movimiento.cantidad_cambiada == (nueva_cantidad - cantidad_anterior), f"Cantidad cambiada incorrecta: {movimiento.cantidad_cambiada}"
        assert movimiento.usuario == self.admin_user, "Usuario del movimiento incorrecto"
        
        print_success("Movimiento registrado correctamente")
        
    def test_4_calculos_despues_de_editar(self):
        """Verificar que los cálculos se mantienen correctos después de editar"""
        print_header("Test 4: Verificar cálculos después de editar")
        
        # Obtener totales antes de editar
        total_items_antes = self.conteo.items.count()
        total_cantidad_antes = self.conteo.items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        
        print_info(f"Antes de editar - Items: {total_items_antes}, Cantidad: {total_cantidad_antes}")
        
        # Editar varios items
        self.client.force_login(self.admin_user)
        
        ediciones = [
            (self.items[1], 35),  # 20 -> 35 (+15)
            (self.items[2], 25),  # 30 -> 25 (-5)
            (self.items[3], 45),  # 40 -> 45 (+5)
        ]
        
        for item, nueva_cantidad in ediciones:
            cantidad_anterior = item.cantidad
            response = self.client.post(
                f'/conteo/item/{item.id}/editar/',
                {'cantidad': nueva_cantidad},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            assert response.status_code == 200, f"Error al editar item {item.id}"
            data = json.loads(response.content)
            assert data['success'], f"Edición falló para item {item.id}: {data.get('error', '')}"
            
            item.refresh_from_db()
            assert item.cantidad == nueva_cantidad, f"Cantidad no actualizada para item {item.id}"
            
            print_info(f"Item {item.id}: {cantidad_anterior} -> {nueva_cantidad}")
        
        # Verificar totales después de editar
        total_items_despues = self.conteo.items.count()
        total_cantidad_despues = self.conteo.items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        
        print_info(f"Después de editar - Items: {total_items_despues}, Cantidad: {total_cantidad_despues}")
        
        # El número de items no debe cambiar
        assert total_items_antes == total_items_despues, f"Total items cambió: {total_items_antes} != {total_items_despues}"
        print_success("Total items se mantiene correcto")
        
        # Calcular cantidad esperada manualmente
        cantidad_esperada = sum([item.cantidad for item in self.items])
        assert total_cantidad_despues == cantidad_esperada, f"Total cantidad incorrecto: {total_cantidad_despues} != {cantidad_esperada}"
        print_success(f"Total cantidad correcto: {total_cantidad_despues}")
        
    def test_5_editar_a_cero(self):
        """Verificar que se puede editar a cantidad 0"""
        print_header("Test 5: Editar a cantidad 0")
        
        self.client.force_login(self.admin_user)
        
        item = self.items[4]  # Último item
        cantidad_anterior = item.cantidad
        
        response = self.client.post(
            f'/conteo/item/{item.id}/editar/',
            {'cantidad': 0},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        assert response.status_code == 200, f"Status code incorrecto: {response.status_code}"
        data = json.loads(response.content)
        assert data['success'], f"Edición a 0 falló: {data.get('error', '')}"
        
        item.refresh_from_db()
        assert item.cantidad == 0, f"Cantidad no se actualizó a 0: {item.cantidad}"
        print_success(f"Cantidad editada a 0 correctamente: {cantidad_anterior} -> 0")
        
        # Verificar que el item sigue existiendo
        assert ItemConteo.objects.filter(id=item.id).exists(), "Item fue eliminado incorrectamente"
        print_success("Item sigue existiendo después de editar a 0")
        
    def test_6_validacion_cantidad_negativa(self):
        """Verificar que no se puede editar a cantidad negativa"""
        print_header("Test 6: Validación cantidad negativa")
        
        self.client.force_login(self.admin_user)
        
        item = self.items[0]
        cantidad_original = item.cantidad
        
        response = self.client.post(
            f'/conteo/item/{item.id}/editar/',
            {'cantidad': -10},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        assert response.status_code == 200, f"Status code incorrecto: {response.status_code}"
        data = json.loads(response.content)
        assert not data['success'], "No debería permitir cantidad negativa"
        assert 'negativa' in data['error'].lower() or 'negativo' in data['error'].lower()
        
        # Verificar que la cantidad no cambió
        item.refresh_from_db()
        assert item.cantidad == cantidad_original, f"Cantidad no debería haber cambiado: {item.cantidad}"
        print_success("Cantidad negativa correctamente rechazada")
        
    def test_7_movimientos_registrados_correctamente(self):
        """Verificar que todos los movimientos se registran correctamente"""
        print_header("Test 7: Verificar movimientos registrados")
        
        # Contar movimientos antes
        movimientos_antes = MovimientoConteo.objects.filter(conteo=self.conteo).count()
        print_info(f"Movimientos antes: {movimientos_antes}")
        
        # Hacer varias ediciones
        self.client.force_login(self.admin_user)
        
        for i, item in enumerate(self.items[:3]):
            nueva_cantidad = item.cantidad + 5
            response = self.client.post(
                f'/conteo/item/{item.id}/editar/',
                {'cantidad': nueva_cantidad},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            assert response.status_code == 200
            data = json.loads(response.content)
            assert data['success']
        
        # Verificar que se crearon los movimientos
        movimientos_despues = MovimientoConteo.objects.filter(conteo=self.conteo).count()
        movimientos_nuevos = movimientos_despues - movimientos_antes
        
        print_info(f"Movimientos después: {movimientos_despues}")
        print_info(f"Movimientos nuevos: {movimientos_nuevos}")
        
        # Deberían haberse creado 3 movimientos nuevos (uno por cada edición)
        assert movimientos_nuevos >= 3, f"Se esperaban al menos 3 movimientos nuevos, se crearon {movimientos_nuevos}"
        print_success(f"Se registraron {movimientos_nuevos} movimientos correctamente")
        
        # Verificar que todos los movimientos tienen los datos correctos
        movimientos_modificar = MovimientoConteo.objects.filter(
            conteo=self.conteo,
            tipo='modificar'
        ).order_by('-id')[:3]
        
        for movimiento in movimientos_modificar:
            assert movimiento.cantidad_anterior is not None, "Cantidad anterior es None"
            assert movimiento.cantidad_nueva is not None, "Cantidad nueva es None"
            assert movimiento.cantidad_cambiada == (movimiento.cantidad_nueva - movimiento.cantidad_anterior), \
                f"Cantidad cambiada incorrecta: {movimiento.cantidad_cambiada}"
            assert movimiento.usuario == self.admin_user, "Usuario incorrecto"
            print_success(f"Movimiento {movimiento.id} correcto: {movimiento.cantidad_anterior} -> {movimiento.cantidad_nueva}")
        
    def test_8_estadisticas_finales(self):
        """Verificar estadísticas finales del conteo"""
        print_header("Test 8: Verificar estadísticas finales")
        
        # Calcular estadísticas manualmente
        items = ItemConteo.objects.filter(conteo=self.conteo)
        total_items_manual = items.count()
        total_cantidad_manual = sum([item.cantidad for item in items])
        
        # Obtener estadísticas del modelo
        total_items_modelo = self.conteo.items.count()
        total_cantidad_modelo = self.conteo.items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        
        print_info(f"Total items - Manual: {total_items_manual}, Modelo: {total_items_modelo}")
        print_info(f"Total cantidad - Manual: {total_cantidad_manual}, Modelo: {total_cantidad_modelo}")
        
        assert total_items_manual == total_items_modelo, f"Total items inconsistente"
        assert total_cantidad_manual == total_cantidad_modelo, f"Total cantidad inconsistente"
        
        print_success("Estadísticas finales correctas")
        print_success(f"Total items: {total_items_manual}")
        print_success(f"Total cantidad: {total_cantidad_manual}")
        
    def cleanup(self):
        """Limpiar datos de prueba"""
        print_header("Limpiando datos de prueba")
        
        try:
            # Eliminar en orden inverso de dependencias
            if self.conteo:
                MovimientoConteo.objects.filter(conteo=self.conteo).delete()
                ItemConteo.objects.filter(conteo=self.conteo).delete()
                Conteo.objects.filter(id=self.conteo.id).delete()
            
            if self.productos:
                Producto.objects.filter(id__in=[p.id for p in self.productos]).delete()
            
            User.objects.filter(username__in=['admin_test', 'normal_test']).delete()
            
            print_success("Datos limpiados")
        except Exception as e:
            print_error(f"Error al limpiar: {str(e)}")
        
    def run_all_tests(self):
        """Ejecutar todos los tests"""
        try:
            self.setup()
            self.test_1_verificar_calculos_iniciales()
            self.test_2_usuario_normal_no_puede_editar()
            self.test_3_admin_puede_editar()
            self.test_4_calculos_despues_de_editar()
            self.test_5_editar_a_cero()
            self.test_6_validacion_cantidad_negativa()
            self.test_7_movimientos_registrados_correctamente()
            self.test_8_estadisticas_finales()
            
            print_header("TODOS LOS TESTS PASARON EXITOSAMENTE")
            print_success("La funcionalidad de editar items funciona correctamente")
            print_success("Los cálculos se mantienen íntegros después de editar")
            
        except AssertionError as e:
            print_error(f"Test falló: {str(e)}")
            raise
        except Exception as e:
            print_error(f"Error inesperado: {str(e)}")
            raise
        finally:
            self.cleanup()

if __name__ == '__main__':
    test = TestEditarItemConteo()
    test.run_all_tests()

