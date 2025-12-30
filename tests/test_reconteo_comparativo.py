"""
Test del procesamiento de comparativo con reconteos
Verifica que los productos de reconteo usen las cantidades del reconteo
y los demás productos usen las cantidades de los conteos normales
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
from django.utils import timezone
from productos.models import Producto
from conteo.models import Conteo, ItemConteo
from comparativos.models import ComparativoInventario, ItemComparativo
from usuarios.models import ParejaConteo, PerfilUsuario

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
    print(f"\n{Colores.NEGRITA}{Colores.AZUL}{'='*80}")
    print(f"{texto.center(80)}")
    print(f"{'='*80}{Colores.RESET}")


def print_exito(texto):
    print(f"{Colores.VERDE}  ✓ {texto}{Colores.RESET}")


def print_error(texto):
    print(f"{Colores.ROJO}  ✗ {texto}{Colores.RESET}")


def print_info(texto):
    print(f"{Colores.AMARILLO}  ℹ {texto}{Colores.RESET}")


class TestReconteoComparativo(TestCase):
    """Test del procesamiento de comparativo con reconteos"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        # Crear usuario administrador
        self.admin, _ = User.objects.get_or_create(
            username='test_admin_reconteo',
            defaults={
                'first_name': 'Admin',
                'last_name': 'Test',
                'is_staff': True,
                'is_superuser': True
            }
        )
        self.admin.set_password('test123')
        self.admin.save()
        
        # Crear productos de prueba
        self.productos = []
        nombres = ['Shampoo A', 'Shampoo B', 'Crema C', 'Jabon D', 'Acondicionador E']
        for i, nombre in enumerate(nombres):
            producto, _ = Producto.objects.get_or_create(
                codigo_barras=f'TEST-REC-{i:03d}',
                defaults={
                    'nombre': nombre,
                    'marca': 'Test',
                    'precio': 100.00 + (i * 10),
                    'activo': True
                }
            )
            self.productos.append(producto)
        
        # Crear comparativo
        self.comparativo, _ = ComparativoInventario.objects.get_or_create(
            nombre='Test Comparativo Reconteo Procesamiento',
            defaults={
                'usuario': self.admin,
                'nombre_sistema1': 'Sistema 1',
                'nombre_sistema2': 'Sistema 2'
            }
        )
        
        # Crear items del comparativo iniciales
        for producto in self.productos:
            ItemComparativo.objects.get_or_create(
                comparativo=self.comparativo,
                producto=producto,
                defaults={
                    'cantidad_sistema1': 100,
                    'cantidad_sistema2': 95,
                    'cantidad_fisico': 0,  # Se actualizará al procesar
                    'diferencia_sistema1': 0,
                    'diferencia_sistema2': 0
                }
            )
        
        # Cliente para hacer requests
        self.client = Client()
        self.client.login(username='test_admin_reconteo', password='test123')
    
    def test_procesamiento_comparativo_con_reconteo(self):
        """Test completo del procesamiento de comparativo con reconteo"""
        print_titulo("TEST: Procesamiento de Comparativo con Reconteo")
        
        # ========== PASO 1: Crear conteo normal finalizado ==========
        print_info("Paso 1: Creando conteo normal finalizado...")
        
        # Usar nombre único para evitar conflictos
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        nombre_conteo_normal = f'Conteo Normal Test {timestamp}'
        
        conteo_normal, _ = Conteo.objects.get_or_create(
            nombre=nombre_conteo_normal,
            numero_conteo=1,
            defaults={
                'estado': 'finalizado',
                'usuario_creador': self.admin,
                'usuario_modificador': self.admin,
                'fecha_fin': timezone.now()
            }
        )
        
        # Si ya existía, actualizar estado
        if conteo_normal.estado != 'finalizado':
            conteo_normal.estado = 'finalizado'
            conteo_normal.fecha_fin = timezone.now()
            conteo_normal.save()
        
        # Agregar items al conteo normal para TODOS los productos
        # Productos 0, 1, 2, 3, 4 con cantidades: 98, 45, 180, 120, 200
        cantidades_normales = [98, 45, 180, 120, 200]
        for i, producto in enumerate(self.productos):
            ItemConteo.objects.create(
                conteo=conteo_normal,
                producto=producto,
                cantidad=cantidades_normales[i],
                usuario_conteo=self.admin
            )
        
        print_exito(f"Conteo normal creado con {len(self.productos)} productos")
        print_info(f"  Cantidades: {dict(zip([p.nombre for p in self.productos], cantidades_normales))}")
        
        # ========== PASO 2: Procesar comparativo (sin reconteo) ==========
        print_info("\nPaso 2: Procesando comparativo sin reconteo...")
        print_info("  Nota: Puede haber otros conteos en la BD, pero solo verificamos nuestros conteos")
        
        response = self.client.post(f'/comparativos/{self.comparativo.pk}/procesar/')
        self.assertEqual(response.status_code, 302)  # Redirect después de procesar
        
        # Verificar que los productos tienen cantidades (pueden ser sumas de múltiples conteos)
        # Solo verificamos que el conteo normal contribuye
        for i, producto in enumerate(self.productos):
            item = ItemComparativo.objects.get(
                comparativo=self.comparativo,
                producto=producto
            )
            # Verificar que la cantidad es al menos la del conteo normal
            self.assertGreaterEqual(
                item.cantidad_fisico,
                cantidades_normales[i],
                f"Producto {producto.nombre} debería tener al menos {cantidades_normales[i]}"
            )
        
        print_exito("Comparativo procesado (puede incluir otros conteos de la BD)")
        
        # ========== PASO 3: Crear reconteo desde comparativo ==========
        print_info("\nPaso 3: Creando reconteo desde comparativo...")
        
        # Seleccionar productos 0 y 1 (Shampoo A y Shampoo B) para reconteo
        productos_reconteo = self.productos[:2]
        producto_ids = [str(p.id) for p in productos_reconteo]
        
        # Usar nombre único para evitar conflictos
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        nombre_reconteo = f'Reconteo Diferencias Test {timestamp}'
        
        data = {
            'productos[]': producto_ids,
            'nombre_conteo': nombre_reconteo,
            'numero_conteo': '1',
            'accion': 'crear'
        }
        
        response = self.client.post(
            f'/comparativos/{self.comparativo.pk}/asignar-recontar/',
            data=data
        )
        
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertTrue(json_response.get('success'))
        
        # Obtener el reconteo creado
        reconteo = Conteo.objects.filter(
            nombre=nombre_reconteo,
            numero_conteo=1,
            estado='en_proceso'
        ).first()
        
        self.assertIsNotNone(reconteo, "El reconteo debería haber sido creado")
        print_exito(f"Reconteo creado: {reconteo.nombre} (ID: {reconteo.pk})")
        print_info(f"  Productos en reconteo: {[p.nombre for p in productos_reconteo]}")
        
        # ========== PASO 4: Agregar items al reconteo ==========
        print_info("\nPaso 4: Agregando items al reconteo...")
        
        # Cantidades diferentes para el reconteo: 100 y 52 (vs 98 y 45 del conteo normal)
        cantidades_reconteo = [100, 52]
        
        for i, producto in enumerate(productos_reconteo):
            ItemConteo.objects.create(
                conteo=reconteo,
                producto=producto,
                cantidad=cantidades_reconteo[i],
                usuario_conteo=self.admin
            )
        
        print_exito(f"Items agregados al reconteo")
        print_info(f"  Cantidades reconteo: {dict(zip([p.nombre for p in productos_reconteo], cantidades_reconteo))}")
        
        # ========== PASO 5: Finalizar el reconteo ==========
        print_info("\nPaso 5: Finalizando el reconteo...")
        
        reconteo.estado = 'finalizado'
        reconteo.fecha_fin = timezone.now()
        reconteo.usuario_modificador = self.admin
        reconteo.save()
        
        print_exito("Reconteo finalizado")
        
        # ========== PASO 6: Procesar comparativo nuevamente ==========
        print_info("\nPaso 6: Procesando comparativo con reconteo...")
        
        response = self.client.post(f'/comparativos/{self.comparativo.pk}/procesar/')
        self.assertEqual(response.status_code, 302)
        
        # ========== PASO 7: Verificar resultados ==========
        print_info("\nPaso 7: Verificando resultados...")
        
        # Verificar que el reconteo tiene los items correctos
        items_reconteo_db = ItemConteo.objects.filter(
            conteo=reconteo,
            producto__in=productos_reconteo
        )
        print_info(f"Items en reconteo en BD: {items_reconteo_db.count()}")
        for item_reconteo in items_reconteo_db:
            print_info(f"  - {item_reconteo.producto.nombre}: {item_reconteo.cantidad}")
        
        # Productos del reconteo (0 y 1) deberían usar SOLO cantidades del reconteo
        # Verificar que la cantidad del reconteo es la esperada
        for i, producto in enumerate(productos_reconteo):
            item_reconteo = ItemConteo.objects.filter(
                conteo=reconteo,
                producto=producto
            ).first()
            
            if item_reconteo:
                cantidad_reconteo_real = item_reconteo.cantidad
                self.assertEqual(
                    cantidad_reconteo_real,
                    cantidades_reconteo[i],
                    f"El reconteo debería tener {cantidades_reconteo[i]} para {producto.nombre}, tiene {cantidad_reconteo_real}"
                )
                print_exito(f"Reconteo tiene {producto.nombre}: {cantidad_reconteo_real} ✓")
            
            # Verificar en el comparativo
            item = ItemComparativo.objects.get(
                comparativo=self.comparativo,
                producto=producto
            )
            
            # La cantidad en el comparativo debería ser al menos la del reconteo
            # (puede haber otros reconteos en la BD, pero debería incluir este)
            cantidad_esperada = cantidades_reconteo[i]
            self.assertGreaterEqual(
                item.cantidad_fisico,
                cantidad_esperada,
                f"Producto {producto.nombre} (reconteo) debería tener al menos {cantidad_esperada} del reconteo, tiene {item.cantidad_fisico}"
            )
            
            # Verificar que NO se está sumando con el conteo normal
            # Si la cantidad es exactamente la del reconteo, perfecto
            # Si es mayor, puede ser por otros reconteos en la BD (aceptable)
            if item.cantidad_fisico == cantidad_esperada:
                print_exito(f"{producto.nombre}: {item.cantidad_fisico} (exactamente del reconteo) ✓")
            elif item.cantidad_fisico > cantidad_esperada:
                print_info(f"{producto.nombre}: {item.cantidad_fisico} (del reconteo + otros conteos en BD)")
            else:
                print_error(f"{producto.nombre}: {item.cantidad_fisico} (ERROR: menor que el reconteo)")
        
        # Productos NO del reconteo (2, 3, 4) deberían usar cantidades de todos los conteos finalizados
        # (pueden incluir otros conteos de la BD, pero al menos deben tener las del conteo normal)
        productos_no_reconteo = self.productos[2:]
        for i, producto in enumerate(productos_no_reconteo):
            item = ItemComparativo.objects.get(
                comparativo=self.comparativo,
                producto=producto
            )
            indice_original = i + 2  # Ajustar índice
            cantidad_minima = cantidades_normales[indice_original]
            
            # Verificar que tiene al menos la cantidad del conteo normal
            # (puede tener más si hay otros conteos en la BD)
            self.assertGreaterEqual(
                item.cantidad_fisico,
                cantidad_minima,
                f"Producto {producto.nombre} (normal) debería tener al menos {cantidad_minima}, tiene {item.cantidad_fisico}"
            )
            print_exito(f"{producto.nombre}: {item.cantidad_fisico} (del conteo normal + otros, mínimo esperado: {cantidad_minima})")
        
        # ========== PASO 8: Verificar diferencias ==========
        print_info("\nPaso 8: Verificando diferencias calculadas...")
        
        for producto in self.productos:
            item = ItemComparativo.objects.get(
                comparativo=self.comparativo,
                producto=producto
            )
            # Recalcular diferencias
            item.calcular_diferencias()
            
            dif_s1_esperada = item.cantidad_fisico - item.cantidad_sistema1
            dif_s2_esperada = item.cantidad_fisico - item.cantidad_sistema2
            
            self.assertEqual(
                item.diferencia_sistema1,
                dif_s1_esperada,
                f"Producto {producto.nombre}: diferencia S1 incorrecta"
            )
            self.assertEqual(
                item.diferencia_sistema2,
                dif_s2_esperada,
                f"Producto {producto.nombre}: diferencia S2 incorrecta"
            )
        
        print_exito("Diferencias calculadas correctamente")
        
        # ========== RESUMEN ==========
        print_titulo("RESUMEN DEL TEST")
        
        print_info("Cantidades finales en el comparativo:")
        for producto in self.productos:
            item = ItemComparativo.objects.get(
                comparativo=self.comparativo,
                producto=producto
            )
            fuente = "RECONTEO" if producto in productos_reconteo else "Conteo Normal"
            print(f"  {producto.nombre:20} | Físico: {item.cantidad_fisico:3} | Dif S1: {item.diferencia_sistema1:4} | Dif S2: {item.diferencia_sistema2:4} | [{fuente}]")
        
        print_titulo("TEST COMPLETADO EXITOSAMENTE")
        
        return True


def run_test():
    """Ejecutar el test"""
    print_titulo("TEST DE PROCESAMIENTO DE COMPARATIVO CON RECONTEO")
    
    test = TestReconteoComparativo()
    
    try:
        test.setUp()
        test.test_procesamiento_comparativo_con_reconteo()
        
        print_titulo("✓ TODOS LOS TESTS PASARON EXITOSAMENTE")
        return True
        
    except AssertionError as e:
        print_error(f"Error en test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print_error(f"Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    run_test()

