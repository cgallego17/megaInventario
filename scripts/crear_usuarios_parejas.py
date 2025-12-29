"""
Script para crear usuarios y parejas de conteo
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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megaInventario.settings')
django.setup()

from django.contrib.auth.models import User
from usuarios.models import ParejaConteo
from django.db import transaction
import secrets
import string

def generar_contrasena_segura():
    """Genera una contraseña segura de 8 caracteres"""
    # Usar letras mayúsculas, minúsculas y números
    caracteres = string.ascii_letters + string.digits
    # Excluir caracteres confusos: 0, O, I, l
    caracteres = caracteres.replace('0', '').replace('O', '').replace('I', '').replace('l', '')
    return ''.join(secrets.choice(caracteres) for _ in range(8))

def crear_usuarios_y_parejas():
    """Crea usuarios y parejas de conteo con contraseñas únicas"""
    print("="*70)
    print("CREANDO USUARIOS Y PAREJAS DE CONTEO")
    print("="*70)
    print()
    
    # Definir parejas
    parejas_data = [
        ('Beto', 'Dina'),
        ('Juan Pablo', 'Alejandro'),
        ('Isabel', 'Hernán'),
        ('Walter', 'Andrés'),
        ('Jaiber', 'Mauricio'),
    ]
    
    # Diccionario para almacenar credenciales
    credenciales = {}
    
    try:
        with transaction.atomic():
            parejas_creadas = 0
            usuarios_creados = 0
            
            for usuario1_nombre, usuario2_nombre in parejas_data:
                # Crear usuario 1
                username1 = usuario1_nombre.lower().replace(' ', '_')
                password1 = generar_contrasena_segura()
                
                usuario1, created1 = User.objects.get_or_create(
                    username=username1,
                    defaults={
                        'first_name': usuario1_nombre.split()[0] if ' ' in usuario1_nombre else usuario1_nombre,
                        'last_name': usuario1_nombre.split()[1] if ' ' in usuario1_nombre else '',
                        'email': f'{username1}@megaInventario.com',
                        'is_active': True,
                        'is_staff': False,
                        'is_superuser': False,
                    }
                )
                if created1:
                    usuario1.set_password(password1)
                    usuario1.save()
                    usuarios_creados += 1
                    credenciales[username1] = {
                        'nombre': usuario1_nombre,
                        'password': password1
                    }
                    print(f"  Usuario creado: {username1} ({usuario1_nombre})")
                else:
                    # Si el usuario ya existe, actualizar contraseña
                    password1 = generar_contrasena_segura()
                    usuario1.set_password(password1)
                    usuario1.save()
                    credenciales[username1] = {
                        'nombre': usuario1_nombre,
                        'password': password1
                    }
                    print(f"  Usuario actualizado: {username1} ({usuario1_nombre}) - Contrasena regenerada")
                
                # Crear usuario 2
                username2 = usuario2_nombre.lower().replace(' ', '_')
                password2 = generar_contrasena_segura()
                
                usuario2, created2 = User.objects.get_or_create(
                    username=username2,
                    defaults={
                        'first_name': usuario2_nombre.split()[0] if ' ' in usuario2_nombre else usuario2_nombre,
                        'last_name': usuario2_nombre.split()[1] if ' ' in usuario2_nombre else '',
                        'email': f'{username2}@megaInventario.com',
                        'is_active': True,
                        'is_staff': False,
                        'is_superuser': False,
                    }
                )
                if created2:
                    usuario2.set_password(password2)
                    usuario2.save()
                    usuarios_creados += 1
                    credenciales[username2] = {
                        'nombre': usuario2_nombre,
                        'password': password2
                    }
                    print(f"  Usuario creado: {username2} ({usuario2_nombre})")
                else:
                    # Si el usuario ya existe, actualizar contraseña
                    password2 = generar_contrasena_segura()
                    usuario2.set_password(password2)
                    usuario2.save()
                    credenciales[username2] = {
                        'nombre': usuario2_nombre,
                        'password': password2
                    }
                    print(f"  Usuario actualizado: {username2} ({usuario2_nombre}) - Contrasena regenerada")
                
                # Crear pareja
                pareja, created_pareja = ParejaConteo.objects.get_or_create(
                    usuario_1=usuario1,
                    usuario_2=usuario2,
                    defaults={
                        'activa': True,
                        'observaciones': f'Pareja: {usuario1_nombre} y {usuario2_nombre}',
                    }
                )
                
                if created_pareja:
                    parejas_creadas += 1
                    print(f"  Pareja creada: {usuario1_nombre} y {usuario2_nombre}")
                else:
                    print(f"  Pareja ya existe: {usuario1_nombre} y {usuario2_nombre}")
                
                print()
            
            print("="*70)
            print("PROCESO COMPLETADO EXITOSAMENTE")
            print("="*70)
            print()
            print(f"Resumen:")
            print(f"  - Usuarios nuevos creados: {usuarios_creados}")
            print(f"  - Parejas nuevas creadas: {parejas_creadas}")
            print(f"  - Total parejas: {len(parejas_data)}")
            print()
            print("="*70)
            print("CREDENCIALES DE ACCESO")
            print("="*70)
            print()
            
            # Mostrar credenciales por parejas
            for i, (usuario1_nombre, usuario2_nombre) in enumerate(parejas_data, 1):
                username1 = usuario1_nombre.lower().replace(' ', '_')
                username2 = usuario2_nombre.lower().replace(' ', '_')
                
                print(f"Pareja {i}: {usuario1_nombre} y {usuario2_nombre}")
                print(f"  - Usuario: {username1:20} | Contrasena: {credenciales[username1]['password']}")
                print(f"  - Usuario: {username2:20} | Contrasena: {credenciales[username2]['password']}")
                print()
            
            print("="*70)
            print("NOTA: Guarde estas credenciales de forma segura.")
            print("="*70)
            
    except Exception as e:
        print()
        print("="*70)
        print("ERROR AL CREAR USUARIOS Y PAREJAS")
        print("="*70)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    crear_usuarios_y_parejas()

