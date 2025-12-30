"""
Test del flujo completo de reconteo desde comparativos
"""
import os
import django
import sys

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megaInventario.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.db import transaction
from productos.models import Producto
from conteo.models import Conteo, ItemConteo
from comparativos.models import ComparativoInventario, ItemComparativo
from usuarios.models import ParejaConteo, PerfilUsuario


class TestFlujoReconteo(TestCase):
    """Test del flujo completo de reconteo desde comparativos"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        # Crear usuarios
        self.usuario1, _ = User.objects.get_or_create(
            username='test_usuario1',
            defaults={'first_name': 'Usuario', 'last_name': 'Uno'}
        )
        self.usuario1.set_password('test123')
        self.usuario1.save()
        
        self.usuario2, _ = User.objects.get_or_create(
            username='test_usuario2',
            defaults={'first_name': 'Usuario', 'last_name': 'Dos'}
        )
        self.usuario2.set_password('test123')
        self.usuario2.save()
        
        # Crear perfil de usuario si no existe
        PerfilUsuario.objects.get_or_create(user=self.usuario1)
        PerfilUsuario.objects.get_or_create(user=self.usuario2)
        
        # Crear pareja de conteo
        self.pareja, _ = ParejaConteo.objects.get_or_create(
            usuario_1=self.usuario1,
            usuario_2=self.usuario2,
            defaults={'activa': True, 'color': 'primary'}
        )
        
        # Crear productos de prueba
        self.productos = []
        for i in range(5):
            producto, _ = Producto.objects.get_or_create(
                codigo_barras=f'TEST-RECONTE-{i:03d}',
                defaults={
                    'nombre': f'Producto Test Reconteo {i}',
                    'marca': 'Test',
                    'precio': 100.00 + (i * 10),
                    'activo': True
                }
            )
            self.productos.append(producto)
        
        # Crear comparativo
        self.comparativo, _ = ComparativoInventario.objects.get_or_create(
            nombre='Test Comparativo Reconteo',
            defaults={
                'usuario': self.usuario1,
                'nombre_sistema1': 'Sistema 1',
                'nombre_sistema2': 'Sistema 2'
            }
        )
        
        # Crear items del comparativo con diferencias
        for producto in self.productos:
            ItemComparativo.objects.get_or_create(
                comparativo=self.comparativo,
                producto=producto,
                defaults={
                    'cantidad_sistema1': 10,
                    'cantidad_sistema2': 12,
                    'cantidad_fisico': 15,  # Diferencia para que necesite reconteo
                    'diferencia_sistema1': 5,
                    'diferencia_sistema2': 3
                }
            )
        
        # Cliente para hacer requests
        self.client = Client()
        self.client.login(username='test_usuario1', password='test123')
    
    def test_1_crear_conteo_desde_comparativo(self):
        """Test 1: Crear un conteo desde el comparativo con productos seleccionados"""
        print("\n" + "="*80)
        print("TEST 1: Crear Conteo desde Comparativo")
        print("="*80)
        
        # Seleccionar 3 productos para reconteo
        productos_seleccionados = self.productos[:3]
        producto_ids = [str(p.id) for p in productos_seleccionados]
        
        # Datos para crear el conteo
        data = {
            'productos[]': producto_ids,
            'nombre_conteo': 'Conteo Reconteo Test',
            'numero_conteo': '1'
        }
        
        # Hacer la petición POST
        response = self.client.post(
            f'/comparativos/{self.comparativo.pk}/asignar-recontar/',
            data=data
        )
        
        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertTrue(json_response.get('success'), "La respuesta debería indicar éxito")
        
        # Verificar que el conteo fue creado
        conteo = Conteo.objects.filter(
            nombre__startswith='Conteo Reconteo Test',
            numero_conteo=1,
            estado='en_proceso'
        ).first()
        
        self.assertIsNotNone(conteo, "El conteo debería haber sido creado")
        print(f"[OK] Conteo creado: {conteo.nombre} (ID: {conteo.pk})")
        
        # Verificar que las observaciones contienen los IDs de productos
        self.assertIn('Productos:', conteo.observaciones)
        productos_ids_str = conteo.observaciones.split('Productos:')[1].strip()
        productos_ids_guardados = [int(pid.strip()) for pid in productos_ids_str.split(',')]
        
        self.assertEqual(len(productos_ids_guardados), 3, "Deberian guardarse 3 productos")
        for producto in productos_seleccionados:
            self.assertIn(producto.id, productos_ids_guardados, f"El producto {producto.id} deberia estar guardado")
        
        print(f"[OK] Productos guardados en observaciones: {productos_ids_guardados}")
        
        # Verificar que el conteo NO tiene parejas asignadas
        self.assertEqual(conteo.parejas.count(), 0, "El conteo no deberia tener parejas asignadas")
        print("[OK] Conteo creado sin parejas asignadas (correcto)")
        
        return conteo
    
    def test_2_filtrar_productos_por_conteo(self):
        """Test 2: Filtrar productos por conteo en asignación múltiple"""
        print("\n" + "="*80)
        print("TEST 2: Filtrar Productos por Conteo")
        print("="*80)
        
        # Crear un conteo primero
        conteo = self.test_1_crear_conteo_desde_comparativo()
        
        # Obtener los IDs de productos del conteo
        productos_ids_str = conteo.observaciones.split('Productos:')[1].strip()
        productos_ids_esperados = [int(pid.strip()) for pid in productos_ids_str.split(',')]
        
        # Hacer petición GET a asignación múltiple con filtro de conteo
        response = self.client.get(
            '/productos/asignar-multiples-parejas/',
            {'conteo': conteo.pk}
        )
        
        self.assertEqual(response.status_code, 200)
        print(f"[OK] Pagina de asignacion multiple cargada correctamente")
        
        # Verificar que el conteo aparece en el contexto (usar context_data si está disponible)
        context = getattr(response, 'context', None) or getattr(response, 'context_data', None)
        if context:
            self.assertIn('conteos_recontar', context)
            conteos_recontar = context['conteos_recontar']
            self.assertIn(conteo, conteos_recontar, "El conteo deberia aparecer en la lista de conteos para recontar")
            print(f"[OK] Conteo aparece en la lista de conteos para recontar")
            
            # Verificar que los productos filtrados son correctos
            if 'page_obj' in context:
                productos_filtrados = context['page_obj'].object_list
                productos_ids_filtrados = [p.id for p in productos_filtrados]
                
                # Todos los productos filtrados deberían estar en la lista esperada
                for producto_id in productos_ids_filtrados:
                    self.assertIn(producto_id, productos_ids_esperados, 
                                f"El producto {producto_id} deberia estar en el conteo")
                
                print(f"[OK] Productos filtrados correctamente: {len(productos_filtrados)} productos")
        else:
            # Si no hay contexto, al menos verificar que la respuesta es exitosa
            print(f"[OK] Respuesta exitosa (contexto no disponible en este tipo de respuesta)")
    
    def test_3_asignar_productos_a_pareja(self):
        """Test 3: Asignar productos del conteo a una pareja"""
        print("\n" + "="*80)
        print("TEST 3: Asignar Productos a Pareja")
        print("="*80)
        
        # Crear un conteo primero
        conteo = self.test_1_crear_conteo_desde_comparativo()
        
        # Obtener los IDs de productos del conteo
        productos_ids_str = conteo.observaciones.split('Productos:')[1].strip()
        productos_ids = [int(pid.strip()) for pid in productos_ids_str.split(',')]
        productos = Producto.objects.filter(id__in=productos_ids)
        
        # Verificar que los productos NO tienen parejas asignadas inicialmente
        for producto in productos:
            self.assertEqual(producto.parejas_asignadas.count(), 0, 
                           f"El producto {producto.nombre} no debería tener parejas asignadas")
        
        print("[OK] Productos sin parejas asignadas inicialmente")
        
        # Asignar productos a la pareja
        data = {
            'productos': [str(p.id) for p in productos],
            'parejas': [str(self.pareja.pk)],
            'accion': 'asignar'
        }
        
        response = self.client.post(
            '/productos/asignar-multiples-parejas/',
            data=data
        )
        
        self.assertEqual(response.status_code, 200)
        print("[OK] Productos asignados a pareja")
        
        # Verificar que los productos ahora tienen la pareja asignada
        for producto in productos:
            producto.refresh_from_db()
            self.assertIn(self.pareja, producto.parejas_asignadas.all(),
                         f"El producto {producto.nombre} deberia tener la pareja asignada")
        
        print(f"[OK] {len(productos)} productos asignados correctamente a la pareja")
    
    def test_4_flujo_completo(self):
        """Test 4: Flujo completo de reconteo"""
        print("\n" + "="*80)
        print("TEST 4: Flujo Completo de Reconteo")
        print("="*80)
        
        # Paso 1: Crear conteo desde comparativo
        print("\n1. Creando conteo desde comparativo...")
        productos_seleccionados = self.productos[:3]
        producto_ids = [str(p.id) for p in productos_seleccionados]
        
        data = {
            'productos[]': producto_ids,
            'nombre_conteo': 'Flujo Completo Test',
            'numero_conteo': '2'
        }
        
        response = self.client.post(
            f'/comparativos/{self.comparativo.pk}/asignar-recontar/',
            data=data
        )
        
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertTrue(json_response['success'])
        print(f"   [OK] {json_response['message']}")
        
        # Obtener el conteo creado
        conteo = Conteo.objects.filter(
            nombre__startswith='Flujo Completo Test',
            numero_conteo=2
        ).first()
        self.assertIsNotNone(conteo)
        print(f"   [OK] Conteo ID: {conteo.pk}")
        
        # Paso 2: Verificar que el conteo aparece en la lista de conteos para recontar
        print("\n2. Verificando que el conteo aparece en asignacion multiple...")
        response = self.client.get('/productos/asignar-multiples-parejas/')
        self.assertEqual(response.status_code, 200)
        context = getattr(response, 'context', None) or getattr(response, 'context_data', None)
        if context and 'conteos_recontar' in context:
            self.assertIn(conteo, context['conteos_recontar'])
            print(f"   [OK] Conteo aparece en la lista")
        else:
            print(f"   [OK] Respuesta exitosa")
        
        # Paso 3: Filtrar productos por conteo
        print("\n3. Filtrando productos por conteo...")
        productos_ids_str = conteo.observaciones.split('Productos:')[1].strip()
        productos_ids_esperados = [int(pid.strip()) for pid in productos_ids_str.split(',')]
        
        response = self.client.get(
            '/productos/asignar-multiples-parejas/',
            {'conteo': conteo.pk}
        )
        self.assertEqual(response.status_code, 200)
        
        context = getattr(response, 'context', None) or getattr(response, 'context_data', None)
        if context and 'page_obj' in context:
            productos_filtrados = context['page_obj'].object_list
            productos_ids_filtrados = [p.id for p in productos_filtrados]
            self.assertEqual(len(productos_ids_filtrados), len(productos_ids_esperados))
            print(f"   [OK] {len(productos_filtrados)} productos filtrados correctamente")
        else:
            print(f"   [OK] Filtro aplicado (verificacion de contexto no disponible)")
        
        # Paso 4: Asignar productos a pareja
        print("\n4. Asignando productos a pareja...")
        productos = Producto.objects.filter(id__in=productos_ids_esperados)
        
        data = {
            'productos': [str(p.id) for p in productos],
            'parejas': [str(self.pareja.pk)],
            'accion': 'asignar'
        }
        
        response = self.client.post(
            '/productos/asignar-multiples-parejas/',
            data=data
        )
        self.assertEqual(response.status_code, 200)
        print(f"   [OK] Productos asignados a pareja {self.pareja}")
        
        # Paso 5: Verificar que los productos están asignados
        print("\n5. Verificando asignacion...")
        for producto in productos:
            producto.refresh_from_db()
            self.assertIn(self.pareja, producto.parejas_asignadas.all())
        print(f"   [OK] Todos los productos estan asignados correctamente")
        
        print("\n" + "="*80)
        print("[OK] FLUJO COMPLETO EXITOSO")
        print("="*80 + "\n")
    
    def test_5_crear_conteo_con_nombre_duplicado(self):
        """Test 5: Crear conteo con nombre duplicado (debe ajustar el nombre)"""
        print("\n" + "="*80)
        print("TEST 5: Crear Conteo con Nombre Duplicado")
        print("="*80)
        
        # Crear primer conteo
        producto_ids = [str(self.productos[0].id)]
        data = {
            'productos[]': producto_ids,
            'nombre_conteo': 'Conteo Duplicado',
            'numero_conteo': '1'
        }
        
        response1 = self.client.post(
            f'/comparativos/{self.comparativo.pk}/asignar-recontar/',
            data=data
        )
        self.assertEqual(response1.status_code, 200)
        json_response1 = response1.json()
        self.assertTrue(json_response1['success'])
        
        conteo1 = Conteo.objects.filter(nombre='Conteo Duplicado', numero_conteo=1).first()
        self.assertIsNotNone(conteo1)
        print(f"[OK] Primer conteo creado: {conteo1.nombre}")
        
        # Intentar crear segundo conteo con mismo nombre y número
        data2 = {
            'productos[]': producto_ids,
            'nombre_conteo': 'Conteo Duplicado',
            'numero_conteo': '1'
        }
        
        response2 = self.client.post(
            f'/comparativos/{self.comparativo.pk}/asignar-recontar/',
            data=data2
        )
        self.assertEqual(response2.status_code, 200)
        json_response2 = response2.json()
        self.assertTrue(json_response2['success'])
        
        # Verificar que se creó con nombre ajustado
        conteo2 = Conteo.objects.filter(nombre='Conteo Duplicado (1)', numero_conteo=1).first()
        self.assertIsNotNone(conteo2, "Deberia crearse con nombre ajustado")
        print(f"[OK] Segundo conteo creado con nombre ajustado: {conteo2.nombre}")
        
        # Verificar que el mensaje indica el ajuste
        self.assertIn('ajust', json_response2['message'].lower())
        print(f"[OK] Mensaje indica ajuste del nombre")


def run_tests():
    """Ejecutar todos los tests"""
    print("\n" + "="*80)
    print("TESTS DEL FLUJO DE RECONTEO")
    print("="*80)
    
    # Crear instancia del test
    test = TestFlujoReconteo()
    
    try:
        # Configurar
        test.setUp()
        
        # Ejecutar tests
        test.test_1_crear_conteo_desde_comparativo()
        test.test_2_filtrar_productos_por_conteo()
        test.test_3_asignar_productos_a_pareja()
        test.test_4_flujo_completo()
        test.test_5_crear_conteo_con_nombre_duplicado()
        
        print("\n" + "="*80)
        print("[OK] TODOS LOS TESTS PASARON EXITOSAMENTE")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\nERROR EN TESTS: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    run_tests()

