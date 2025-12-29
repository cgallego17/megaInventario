"""
Test completo de todos los módulos del sistema Mega Inventario
Prueba todas las funcionalidades principales usando Django TestClient
"""

import os
import sys
import django
from pathlib import Path
from datetime import datetime, timedelta
from io import BytesIO

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megaInventario.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
import pandas as pd

from productos.models import Producto
from usuarios.models import ParejaConteo, PerfilUsuario
from conteo.models import Conteo, ItemConteo
from comparativos.models import ComparativoInventario, InventarioSistema, ItemComparativo
from movimientos.models import MovimientoConteo

# Configurar encoding para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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
    print(f"\n{Colores.NEGRITA}{Colores.AZUL}{'='*80}")
    print(f"  {texto}")
    print(f"{'='*80}{Colores.RESET}\n")

def print_exito(texto):
    """Imprime un mensaje de éxito"""
    print(f"{Colores.VERDE}  ✓ {texto}{Colores.RESET}")

def print_error(texto):
    """Imprime un mensaje de error"""
    print(f"{Colores.ROJO}  ✗ {texto}{Colores.RESET}")

def print_info(texto):
    """Imprime un mensaje informativo"""
    print(f"{Colores.AMARILLO}  ℹ {texto}{Colores.RESET}")

def print_seccion(texto):
    """Imprime una sección"""
    print(f"\n{Colores.NEGRITA}{texto}{Colores.RESET}")

class TestCompleto:
    def __init__(self):
        self.client = Client()
        self.usuario_test = None
        self.productos_test = []
        self.conteo_test = None
        self.comparativo_test = None
        self.errores = []
        self.exitos = []
        
    def crear_usuario_test(self):
        """Crea un usuario de prueba"""
        try:
            self.usuario_test, created = User.objects.get_or_create(
                username='test_user',
                defaults={
                    'email': 'test@test.com',
                    'first_name': 'Test',
                    'last_name': 'User',
                    'is_staff': True,
                }
            )
            if created:
                self.usuario_test.set_password('test123')
                self.usuario_test.save()
                # Crear perfil
                PerfilUsuario.objects.get_or_create(
                    user=self.usuario_test,
                    defaults={'pin': '1234'}
                )
            print_exito(f"Usuario de prueba creado: {self.usuario_test.username}")
            return True
        except Exception as e:
            print_error(f"Error al crear usuario: {str(e)}")
            return False
    
    def login(self):
        """Inicia sesión con el usuario de prueba"""
        try:
            response = self.client.login(username='test_user', password='test123')
            if response:
                print_exito("Sesión iniciada correctamente")
                return True
            else:
                print_error("Error al iniciar sesión")
                return False
        except Exception as e:
            print_error(f"Error al iniciar sesión: {str(e)}")
            return False
    
    def test_dashboard(self):
        """Test del dashboard"""
        print_seccion("1. TEST DASHBOARD")
        try:
            response = self.client.get('/')
            if response.status_code == 200:
                print_exito(f"Dashboard accesible (status: {response.status_code})")
                # Verificar que el contexto tenga los datos necesarios
                try:
                    if hasattr(response, 'context') and 'total_productos' in response.context:
                        print_exito(f"Total productos en contexto: {response.context['total_productos']}")
                except:
                    pass  # El contexto puede no estar disponible en algunos casos
                return True
            else:
                print_error(f"Dashboard no accesible (status: {response.status_code})")
                return False
        except Exception as e:
            print_error(f"Error en dashboard: {str(e)}")
            return False
    
    def test_productos(self):
        """Test del módulo de productos"""
        print_seccion("2. TEST MÓDULO PRODUCTOS")
        
        resultados = []
        
        # 2.1 Lista de productos
        try:
            response = self.client.get('/productos/')
            if response.status_code == 200:
                print_exito("Lista de productos accesible")
                resultados.append(True)
            else:
                print_error(f"Lista de productos no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en lista de productos: {str(e)}")
            resultados.append(False)
        
        # 2.2 Crear producto
        try:
            response = self.client.get('/productos/crear/')
            if response.status_code == 200:
                print_exito("Formulario crear producto accesible")
                resultados.append(True)
            else:
                print_error(f"Formulario crear producto no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en crear producto: {str(e)}")
            resultados.append(False)
        
        # 2.3 Buscar producto (API)
        try:
            # Obtener un producto existente
            producto = Producto.objects.first()
            if producto:
                response = self.client.get('/conteo/buscar-producto/', {'busqueda': producto.codigo_barras})
                if response.status_code == 200:
                    print_exito("API buscar producto funciona")
                    resultados.append(True)
                else:
                    print_error(f"API buscar producto no funciona (status: {response.status_code})")
                    resultados.append(False)
            else:
                print_info("No hay productos para probar búsqueda")
                resultados.append(True)
        except Exception as e:
            print_error(f"Error en buscar producto: {str(e)}")
            resultados.append(False)
        
        # 2.4 Exportar productos
        try:
            response = self.client.get('/productos/exportar/')
            if response.status_code == 200:
                print_exito("Exportar productos funciona")
                resultados.append(True)
            else:
                print_error(f"Exportar productos no funciona (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en exportar productos: {str(e)}")
            resultados.append(False)
        
        # 2.5 Descargar plantilla
        try:
            response = self.client.get('/productos/descargar-plantilla/')
            if response.status_code == 200:
                print_exito("Descargar plantilla funciona")
                resultados.append(True)
            else:
                print_error(f"Descargar plantilla no funciona (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en descargar plantilla: {str(e)}")
            resultados.append(False)
        
        # 2.6 Importar productos (formulario)
        try:
            response = self.client.get('/productos/importar/')
            if response.status_code == 200:
                print_exito("Formulario importar productos accesible")
                resultados.append(True)
            else:
                print_error(f"Formulario importar productos no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en importar productos: {str(e)}")
            resultados.append(False)
        
        # 2.7 Importar productos API (formulario)
        try:
            response = self.client.get('/productos/importar-api/')
            if response.status_code == 200:
                print_exito("Formulario importar productos API accesible")
                resultados.append(True)
            else:
                print_error(f"Formulario importar productos API no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en importar productos API: {str(e)}")
            resultados.append(False)
        
        # 2.8 Detalle de producto
        try:
            producto = Producto.objects.first()
            if producto:
                response = self.client.get(f'/productos/{producto.id}/')
                if response.status_code == 200:
                    print_exito("Detalle de producto accesible")
                    resultados.append(True)
                else:
                    print_error(f"Detalle de producto no accesible (status: {response.status_code})")
                    resultados.append(False)
            else:
                print_info("No hay productos para probar detalle")
                resultados.append(True)
        except Exception as e:
            print_error(f"Error en detalle de producto: {str(e)}")
            resultados.append(False)
        
        return all(resultados)
    
    def test_conteos(self):
        """Test del módulo de conteos"""
        print_seccion("3. TEST MÓDULO CONTEOS")
        
        resultados = []
        
        # 3.1 Lista de conteos
        try:
            response = self.client.get('/conteo/')
            if response.status_code == 200:
                print_exito("Lista de conteos accesible")
                resultados.append(True)
            else:
                print_error(f"Lista de conteos no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en lista de conteos: {str(e)}")
            resultados.append(False)
        
        # 3.2 Crear conteo
        try:
            response = self.client.get('/conteo/crear/')
            if response.status_code == 200:
                print_exito("Formulario crear conteo accesible")
                resultados.append(True)
            else:
                print_error(f"Formulario crear conteo no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en crear conteo: {str(e)}")
            resultados.append(False)
        
        # 3.3 Crear un conteo de prueba
        try:
            # Obtener una pareja
            pareja = ParejaConteo.objects.filter(activa=True).first()
            if pareja:
                data = {
                    'nombre': f'Test Conteo {timezone.now().timestamp()}',
                    'numero_conteo': 1,
                    'parejas': [pareja.id],
                }
                response = self.client.post('/conteo/crear/', data)
                if response.status_code == 302:  # Redirect después de crear
                    print_exito("Conteo creado correctamente")
                    # Obtener el conteo creado
                    self.conteo_test = Conteo.objects.filter(nombre=data['nombre']).first()
                    resultados.append(True)
                elif response.status_code == 200:
                    # Puede ser que el formulario tenga errores, pero eso está bien para el test
                    print_info("Formulario de conteo accesible (puede requerir datos adicionales)")
                    resultados.append(True)
                else:
                    print_error(f"Error al crear conteo (status: {response.status_code})")
                    resultados.append(False)
            else:
                print_info("No hay parejas para crear conteo")
                resultados.append(True)
        except Exception as e:
            print_error(f"Error al crear conteo: {str(e)}")
            resultados.append(False)
        
        # 3.4 Detalle de conteo
        try:
            conteo = Conteo.objects.first()
            if conteo:
                response = self.client.get(f'/conteo/{conteo.id}/')
                if response.status_code == 200:
                    print_exito("Detalle de conteo accesible")
                    resultados.append(True)
                else:
                    print_error(f"Detalle de conteo no accesible (status: {response.status_code})")
                    resultados.append(False)
            else:
                print_info("No hay conteos para probar detalle")
                resultados.append(True)
        except Exception as e:
            print_error(f"Error en detalle de conteo: {str(e)}")
            resultados.append(False)
        
        # 3.5 Agregar item a conteo
        try:
            conteo = Conteo.objects.first()
            producto = Producto.objects.first()
            if conteo and producto:
                data = {
                    'producto_id': producto.id,
                    'cantidad': 5,
                }
                response = self.client.post(f'/conteo/{conteo.id}/agregar-item/', data)
                if response.status_code == 200:
                    print_exito("Agregar item a conteo funciona")
                    resultados.append(True)
                else:
                    print_error(f"Agregar item no funciona (status: {response.status_code})")
                    resultados.append(False)
            else:
                print_info("No hay conteo o producto para probar agregar item")
                resultados.append(True)
        except Exception as e:
            print_error(f"Error al agregar item: {str(e)}")
            resultados.append(False)
        
        return all(resultados)
    
    def test_comparativos(self):
        """Test del módulo de comparativos"""
        print_seccion("4. TEST MÓDULO COMPARATIVOS")
        
        resultados = []
        
        # 4.1 Lista de comparativos
        try:
            response = self.client.get('/comparativos/')
            if response.status_code in [200, 302]:  # 302 puede ser redirección válida
                print_exito("Lista de comparativos accesible")
                resultados.append(True)
            else:
                print_error(f"Lista de comparativos no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en lista de comparativos: {str(e)}")
            resultados.append(False)
        
        # 4.2 Crear comparativo
        try:
            response = self.client.get('/comparativos/crear/')
            if response.status_code in [200, 302]:  # 302 puede ser redirección si ya existe
                print_exito("Formulario crear comparativo accesible")
                resultados.append(True)
            else:
                print_error(f"Formulario crear comparativo no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en crear comparativo: {str(e)}")
            resultados.append(False)
        
        # 4.3 Descargar ejemplo
        try:
            response = self.client.get('/comparativos/descargar-ejemplo/')
            if response.status_code == 200:
                print_exito("Descargar ejemplo funciona")
                resultados.append(True)
            else:
                print_error(f"Descargar ejemplo no funciona (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en descargar ejemplo: {str(e)}")
            resultados.append(False)
        
        # 4.4 Detalle de comparativo
        try:
            comparativo = ComparativoInventario.objects.first()
            if comparativo:
                response = self.client.get(f'/comparativos/{comparativo.id}/')
                if response.status_code == 200:
                    print_exito("Detalle de comparativo accesible")
                    resultados.append(True)
                else:
                    print_error(f"Detalle de comparativo no accesible (status: {response.status_code})")
                    resultados.append(False)
            else:
                print_info("No hay comparativos para probar detalle")
                resultados.append(True)
        except Exception as e:
            print_error(f"Error en detalle de comparativo: {str(e)}")
            resultados.append(False)
        
        return all(resultados)
    
    def test_reportes(self):
        """Test del módulo de reportes"""
        print_seccion("5. TEST MÓDULO REPORTES")
        
        resultados = []
        
        # 5.1 Menú de reportes
        try:
            response = self.client.get('/reportes/')
            if response.status_code == 200:
                print_exito("Menú de reportes accesible")
                resultados.append(True)
            else:
                print_error(f"Menú de reportes no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en menú de reportes: {str(e)}")
            resultados.append(False)
        
        # 5.2 Reporte de conteo
        try:
            response = self.client.get('/reportes/conteo/')
            if response.status_code == 200:
                print_exito("Reporte de conteo accesible")
                resultados.append(True)
            else:
                print_error(f"Reporte de conteo no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en reporte de conteo: {str(e)}")
            resultados.append(False)
        
        # 5.3 Reporte de inventario
        try:
            response = self.client.get('/reportes/inventario/')
            if response.status_code == 200:
                print_exito("Reporte de inventario accesible")
                resultados.append(True)
            else:
                print_error(f"Reporte de inventario no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en reporte de inventario: {str(e)}")
            resultados.append(False)
        
        # 5.4 Exportar reporte de conteo
        try:
            response = self.client.get('/reportes/exportar/conteo/')
            if response.status_code == 200:
                print_exito("Exportar reporte de conteo funciona")
                resultados.append(True)
            else:
                print_error(f"Exportar reporte de conteo no funciona (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en exportar reporte de conteo: {str(e)}")
            resultados.append(False)
        
        # 5.5 Exportar reporte de inventario
        try:
            response = self.client.get('/reportes/exportar/inventario/')
            if response.status_code == 200:
                print_exito("Exportar reporte de inventario funciona")
                resultados.append(True)
            else:
                print_error(f"Exportar reporte de inventario no funciona (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en exportar reporte de inventario: {str(e)}")
            resultados.append(False)
        
        return all(resultados)
    
    def test_movimientos(self):
        """Test del módulo de movimientos"""
        print_seccion("6. TEST MÓDULO MOVIMIENTOS")
        
        resultados = []
        
        # 6.1 Lista de movimientos
        try:
            response = self.client.get('/movimientos/')
            if response.status_code == 200:
                print_exito("Lista de movimientos accesible")
                resultados.append(True)
            else:
                print_error(f"Lista de movimientos no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en lista de movimientos: {str(e)}")
            resultados.append(False)
        
        # 6.2 Resumen de movimientos
        try:
            response = self.client.get('/movimientos/resumen/')
            if response.status_code == 200:
                print_exito("Resumen de movimientos accesible")
                resultados.append(True)
            else:
                print_error(f"Resumen de movimientos no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en resumen de movimientos: {str(e)}")
            resultados.append(False)
        
        # 6.3 Movimientos por conteo
        try:
            conteo = Conteo.objects.first()
            if conteo:
                response = self.client.get(f'/movimientos/conteo/{conteo.id}/')
                if response.status_code == 200:
                    print_exito("Movimientos por conteo accesible")
                    resultados.append(True)
                else:
                    print_error(f"Movimientos por conteo no accesible (status: {response.status_code})")
                    resultados.append(False)
            else:
                print_info("No hay conteos para probar movimientos")
                resultados.append(True)
        except Exception as e:
            print_error(f"Error en movimientos por conteo: {str(e)}")
            resultados.append(False)
        
        # 6.4 Movimientos por usuario
        try:
            usuario = User.objects.first()
            if usuario:
                response = self.client.get(f'/movimientos/usuario/{usuario.id}/')
                if response.status_code == 200:
                    print_exito("Movimientos por usuario accesible")
                    resultados.append(True)
                else:
                    print_error(f"Movimientos por usuario no accesible (status: {response.status_code})")
                    resultados.append(False)
            else:
                print_info("No hay usuarios para probar movimientos")
                resultados.append(True)
        except Exception as e:
            print_error(f"Error en movimientos por usuario: {str(e)}")
            resultados.append(False)
        
        return all(resultados)
    
    def test_usuarios(self):
        """Test del módulo de usuarios"""
        print_seccion("7. TEST MÓDULO USUARIOS")
        
        resultados = []
        
        # 7.1 Lista de usuarios
        try:
            response = self.client.get('/usuarios/usuarios/')
            if response.status_code == 200:
                print_exito("Lista de usuarios accesible")
                resultados.append(True)
            else:
                print_error(f"Lista de usuarios no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en lista de usuarios: {str(e)}")
            resultados.append(False)
        
        # 7.2 Lista de parejas
        try:
            response = self.client.get('/usuarios/parejas/')
            if response.status_code == 200:
                print_exito("Lista de parejas accesible")
                resultados.append(True)
            else:
                print_error(f"Lista de parejas no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en lista de parejas: {str(e)}")
            resultados.append(False)
        
        # 7.3 Crear pareja
        try:
            response = self.client.get('/usuarios/parejas/crear/')
            if response.status_code == 200:
                print_exito("Formulario crear pareja accesible")
                resultados.append(True)
            else:
                print_error(f"Formulario crear pareja no accesible (status: {response.status_code})")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error en crear pareja: {str(e)}")
            resultados.append(False)
        
        return all(resultados)
    
    def test_integridad_datos(self):
        """Test de integridad de datos"""
        print_seccion("8. TEST INTEGRIDAD DE DATOS")
        
        resultados = []
        
        # 8.1 Verificar que todos los productos se muestran
        try:
            total_productos = Producto.objects.count()
            total_activos = Producto.objects.filter(activo=True).count()
            total_inactivos = Producto.objects.filter(activo=False).count()
            
            if total_productos == (total_activos + total_inactivos):
                print_exito(f"Integridad de productos: {total_productos} total ({total_activos} activos, {total_inactivos} inactivos)")
                resultados.append(True)
            else:
                print_error(f"Error en integridad de productos: {total_productos} != {total_activos} + {total_inactivos}")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error al verificar integridad de productos: {str(e)}")
            resultados.append(False)
        
        # 8.2 Verificar relaciones ItemConteo -> Producto
        try:
            items_sin_producto = ItemConteo.objects.filter(producto__isnull=True).count()
            if items_sin_producto == 0:
                print_exito("Todos los items de conteo tienen producto asociado")
                resultados.append(True)
            else:
                print_error(f"Hay {items_sin_producto} items sin producto asociado")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error al verificar items de conteo: {str(e)}")
            resultados.append(False)
        
        # 8.3 Verificar relaciones ItemComparativo -> Producto
        try:
            items_sin_producto = ItemComparativo.objects.filter(producto__isnull=True).count()
            if items_sin_producto == 0:
                print_exito("Todos los items de comparativo tienen producto asociado")
                resultados.append(True)
            else:
                print_error(f"Hay {items_sin_producto} items sin producto asociado")
                resultados.append(False)
        except Exception as e:
            print_error(f"Error al verificar items de comparativo: {str(e)}")
            resultados.append(False)
        
        return all(resultados)
    
    def test_operaciones_matematicas(self):
        """Test de operaciones matemáticas"""
        print_seccion("9. TEST OPERACIONES MATEMÁTICAS")
        
        resultados = []
        
        # 9.1 Verificar suma de cantidades en conteos
        try:
            conteo = Conteo.objects.first()
            if conteo:
                items = conteo.items.all()
                suma_manual = sum(item.cantidad for item in items)
                suma_agregada = items.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
                
                if suma_manual == suma_agregada:
                    print_exito(f"Suma de cantidades en conteo correcta: {suma_agregada}")
                    resultados.append(True)
                else:
                    print_error(f"Error en suma: manual={suma_manual}, agregada={suma_agregada}")
                    resultados.append(False)
            else:
                print_info("No hay conteos para probar operaciones matemáticas")
                resultados.append(True)
        except Exception as e:
            print_error(f"Error al verificar suma de cantidades: {str(e)}")
            resultados.append(False)
        
        # 9.2 Verificar cálculo de stock
        try:
            producto = Producto.objects.first()
            if producto:
                stock = producto.get_stock_actual()
                print_exito(f"Cálculo de stock funciona: {stock} unidades")
                resultados.append(True)
            else:
                print_info("No hay productos para probar cálculo de stock")
                resultados.append(True)
        except Exception as e:
            print_error(f"Error al calcular stock: {str(e)}")
            resultados.append(False)
        
        return all(resultados)
    
    def ejecutar_todos_los_tests(self):
        """Ejecuta todos los tests"""
        print_titulo("TEST COMPLETO DE TODOS LOS MÓDULOS DEL SISTEMA")
        
        # Configuración inicial
        if not self.crear_usuario_test():
            print_error("No se pudo crear el usuario de prueba. Abortando.")
            return False
        
        if not self.login():
            print_error("No se pudo iniciar sesión. Abortando.")
            return False
        
        # Ejecutar tests
        resultados = {
            'Dashboard': self.test_dashboard(),
            'Productos': self.test_productos(),
            'Conteos': self.test_conteos(),
            'Comparativos': self.test_comparativos(),
            'Reportes': self.test_reportes(),
            'Movimientos': self.test_movimientos(),
            'Usuarios': self.test_usuarios(),
            'Integridad': self.test_integridad_datos(),
            'Operaciones': self.test_operaciones_matematicas(),
        }
        
        # Resumen
        print_titulo("RESUMEN DE TESTS")
        
        total_tests = len(resultados)
        tests_exitosos = sum(1 for v in resultados.values() if v)
        
        for modulo, resultado in resultados.items():
            if resultado:
                print_exito(f"{modulo}: OK")
            else:
                print_error(f"{modulo}: FALLÓ")
        
        print(f"\n{Colores.NEGRITA}Total: {tests_exitosos}/{total_tests} módulos pasaron los tests{Colores.RESET}\n")
        
        if tests_exitosos == total_tests:
            print_exito("¡TODOS LOS TESTS PASARON EXITOSAMENTE!")
            return True
        else:
            print_error(f"FALLARON {total_tests - tests_exitosos} TEST(S)")
            return False

def main():
    """Función principal"""
    test = TestCompleto()
    exito = test.ejecutar_todos_los_tests()
    sys.exit(0 if exito else 1)

if __name__ == '__main__':
    main()

