"""
Script para crear usuarios administrativos y de gerencia
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

def crear_usuarios_administrativos():
    """Crea usuarios administrativos y de gerencia"""
    print("="*70)
    print("CREANDO USUARIOS ADMINISTRATIVOS Y DE GERENCIA")
    print("="*70)
    print()
    
    # Usuarios administrativos (Soporte en sistema)
    administrativos = [
        ('Melisa', 'Administrativo'),
        ('Yessica', 'Administrativo'),
        # Cristian ya existe, no se crea
    ]
    
    # Usuarios de gerencia (Supervisión)
    gerencia = [
        ('Claudia Ríos', 'Gerencia'),
        ('Carmenza', 'Gerencia'),
        ('Claudia Arenas', 'Gerencia'),
    ]
    
    credenciales = {}
    
    try:
        with transaction.atomic():
            usuarios_creados = 0
            usuarios_actualizados = 0
            
            # Crear usuarios administrativos
            print("USUARIOS ADMINISTRATIVOS (Soporte en sistema):")
            print("-" * 70)
            for nombre, tipo in administrativos:
                username = nombre.lower().replace(' ', '_')
                password = generar_contrasena_segura()
                
                usuario, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'first_name': nombre.split()[0] if ' ' in nombre else nombre,
                        'last_name': nombre.split()[1] if ' ' in nombre else '',
                        'email': f'{username}@megaInventario.com',
                        'is_active': True,
                        'is_staff': True,  # Acceso al admin
                        'is_superuser': False,
                    }
                )
                
                if created:
                    usuario.set_password(password)
                    usuario.save()
                    usuarios_creados += 1
                    credenciales[username] = {
                        'nombre': nombre,
                        'password': password,
                        'tipo': tipo,
                        'is_staff': True
                    }
                    print(f"  Usuario creado: {username} ({nombre}) - Staff: Si")
                else:
                    # Si el usuario ya existe, actualizar contraseña y permisos
                    password = generar_contrasena_segura()
                    usuario.set_password(password)
                    usuario.is_staff = True
                    usuario.is_superuser = False
                    usuario.save()
                    usuarios_actualizados += 1
                    credenciales[username] = {
                        'nombre': nombre,
                        'password': password,
                        'tipo': tipo,
                        'is_staff': True
                    }
                    print(f"  Usuario actualizado: {username} ({nombre}) - Staff: Si - Contrasena regenerada")
            
            print()
            
            # Verificar si Cristian existe
            cristian = User.objects.filter(username='cristian').first()
            if cristian:
                password_cristian = generar_contrasena_segura()
                cristian.set_password(password_cristian)
                cristian.is_staff = True
                cristian.is_superuser = True  # Mantener superusuario
                cristian.save()
                credenciales['cristian'] = {
                    'nombre': 'Cristian',
                    'password': password_cristian,
                    'tipo': 'Administrativo',
                    'is_staff': True,
                    'is_superuser': True
                }
                print("  Usuario existente actualizado: cristian (Cristian) - Staff: Si, Superuser: Si - Contrasena regenerada")
                usuarios_actualizados += 1
            else:
                # Si no existe, crearlo
                password_cristian = generar_contrasena_segura()
                cristian = User.objects.create_user(
                    username='cristian',
                    first_name='Cristian',
                    email='cristian@megaInventario.com',
                    password=password_cristian,
                    is_active=True,
                    is_staff=True,
                    is_superuser=True
                )
                credenciales['cristian'] = {
                    'nombre': 'Cristian',
                    'password': password_cristian,
                    'tipo': 'Administrativo',
                    'is_staff': True,
                    'is_superuser': True
                }
                usuarios_creados += 1
                print(f"  Usuario creado: cristian (Cristian) - Staff: Si, Superuser: Si")
            
            print()
            
            # Crear usuarios de gerencia
            print("USUARIOS DE GERENCIA (Supervision):")
            print("-" * 70)
            for nombre, tipo in gerencia:
                username = nombre.lower().replace(' ', '_')
                password = generar_contrasena_segura()
                
                usuario, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'first_name': nombre.split()[0] if ' ' in nombre else nombre,
                        'last_name': ' '.join(nombre.split()[1:]) if ' ' in nombre else '',
                        'email': f'{username}@megaInventario.com',
                        'is_active': True,
                        'is_staff': True,  # Acceso al admin
                        'is_superuser': True,  # Supervisión completa
                    }
                )
                
                if created:
                    usuario.set_password(password)
                    usuario.save()
                    usuarios_creados += 1
                    credenciales[username] = {
                        'nombre': nombre,
                        'password': password,
                        'tipo': tipo,
                        'is_staff': True,
                        'is_superuser': True
                    }
                    print(f"  Usuario creado: {username} ({nombre}) - Staff: Si, Superuser: Si")
                else:
                    # Si el usuario ya existe, actualizar contraseña y permisos
                    password = generar_contrasena_segura()
                    usuario.set_password(password)
                    usuario.is_staff = True
                    usuario.is_superuser = True
                    usuario.save()
                    usuarios_actualizados += 1
                    credenciales[username] = {
                        'nombre': nombre,
                        'password': password,
                        'tipo': tipo,
                        'is_staff': True,
                        'is_superuser': True
                    }
                    print(f"  Usuario actualizado: {username} ({nombre}) - Staff: Si, Superuser: Si - Contrasena regenerada")
            
            print()
            print("="*70)
            print("PROCESO COMPLETADO EXITOSAMENTE")
            print("="*70)
            print()
            print(f"Resumen:")
            print(f"  - Usuarios nuevos creados: {usuarios_creados}")
            print(f"  - Usuarios actualizados: {usuarios_actualizados}")
            print(f"  - Total usuarios procesados: {len(credenciales)}")
            print()
            print("="*70)
            print("CREDENCIALES DE ACCESO")
            print("="*70)
            print()
            
            # Mostrar credenciales por tipo
            print("ADMINISTRATIVOS (Soporte en sistema):")
            print("-" * 70)
            for username, info in credenciales.items():
                if info['tipo'] == 'Administrativo':
                    superuser_text = "Si" if info.get('is_superuser', False) else "No"
                    print(f"  - Usuario: {username:20} | Contrasena: {info['password']:12} | Staff: Si | Superuser: {superuser_text}")
            
            print()
            print("GERENCIA (Supervision):")
            print("-" * 70)
            for username, info in credenciales.items():
                if info['tipo'] == 'Gerencia':
                    print(f"  - Usuario: {username:20} | Contrasena: {info['password']:12} | Staff: Si | Superuser: Si")
            
            print()
            print("="*70)
            print("NOTA: Guarde estas credenciales de forma segura.")
            print("="*70)
            
    except Exception as e:
        print()
        print("="*70)
        print("ERROR AL CREAR USUARIOS")
        print("="*70)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    crear_usuarios_administrativos()

