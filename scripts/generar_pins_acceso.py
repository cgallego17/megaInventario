"""
Script para generar PINs de acceso para todos los usuarios
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

def generar_pin():
    """Genera un PIN numérico de 4 dígitos"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(4)])

def generar_pins_todos_usuarios():
    """Genera PINs únicos para todos los usuarios del sistema"""
    print("="*70)
    print("GENERANDO PINS DE ACCESO PARA TODOS LOS USUARIOS")
    print("="*70)
    print()
    
    # Obtener todos los usuarios activos (excepto superusuarios del sistema)
    usuarios = User.objects.filter(is_active=True).order_by('username')
    
    credenciales = {}
    pins_usados = set()
    
    try:
        with transaction.atomic():
            usuarios_actualizados = 0
            
            for usuario in usuarios:
                # Generar PIN único
                pin = generar_pin()
                while pin in pins_usados:
                    pin = generar_pin()
                pins_usados.add(pin)
                
                # Actualizar contraseña con el PIN
                usuario.set_password(pin)
                usuario.save()
                usuarios_actualizados += 1
                
                # Determinar tipo de usuario
                tipo = "Superusuario" if usuario.is_superuser else ("Staff" if usuario.is_staff else "Usuario")
                
                credenciales[usuario.username] = {
                    'nombre': f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username,
                    'pin': pin,
                    'tipo': tipo,
                    'is_staff': usuario.is_staff,
                    'is_superuser': usuario.is_superuser
                }
            
            print(f"Total usuarios actualizados: {usuarios_actualizados}")
            print()
            print("="*70)
            print("CREDENCIALES DE ACCESO CON PIN")
            print("="*70)
            print()
            
            # Agrupar por tipo
            parejas = []
            administrativos = []
            gerencia = []
            otros = []
            
            for username, info in credenciales.items():
                if info['is_superuser'] and info['is_staff']:
                    if 'claudia' in username or 'carmenza' in username:
                        gerencia.append((username, info))
                    elif username == 'cristian':
                        administrativos.append((username, info))
                    else:
                        otros.append((username, info))
                elif info['is_staff']:
                    administrativos.append((username, info))
                else:
                    parejas.append((username, info))
            
            # Mostrar parejas de conteo
            if parejas:
                print("PAREJAS DE CONTEO:")
                print("-" * 70)
                # Agrupar por parejas conocidas
                parejas_ordenadas = [
                    ('beto', 'dina'),
                    ('juan_pablo', 'alejandro'),
                    ('isabel', 'hernán'),
                    ('walter', 'andrés'),
                    ('jaiber', 'mauricio'),
                ]
                
                for user1, user2 in parejas_ordenadas:
                    if user1 in credenciales and user2 in credenciales:
                        info1 = credenciales[user1]
                        info2 = credenciales[user2]
                        print(f"  Pareja: {info1['nombre']} y {info2['nombre']}")
                        print(f"    - Usuario: {user1:20} | PIN: {info1['pin']}")
                        print(f"    - Usuario: {user2:20} | PIN: {info2['pin']}")
                        print()
                
                # Mostrar otros usuarios que no están en parejas conocidas
                usuarios_parejas = set()
                for user1, user2 in parejas_ordenadas:
                    usuarios_parejas.add(user1)
                    usuarios_parejas.add(user2)
                
                otros_parejas = [(u, i) for u, i in parejas if u not in usuarios_parejas]
                if otros_parejas:
                    for username, info in otros_parejas:
                        print(f"  - Usuario: {username:20} | PIN: {info['pin']} | Nombre: {info['nombre']}")
                    print()
            
            # Mostrar administrativos
            if administrativos:
                print("ADMINISTRATIVOS (Soporte en sistema):")
                print("-" * 70)
                for username, info in sorted(administrativos):
                    superuser_text = "Si" if info['is_superuser'] else "No"
                    print(f"  - Usuario: {username:20} | PIN: {info['pin']:6} | Staff: Si | Superuser: {superuser_text} | Nombre: {info['nombre']}")
                print()
            
            # Mostrar gerencia
            if gerencia:
                print("GERENCIA (Supervision):")
                print("-" * 70)
                for username, info in sorted(gerencia):
                    print(f"  - Usuario: {username:20} | PIN: {info['pin']:6} | Staff: Si | Superuser: Si | Nombre: {info['nombre']}")
                print()
            
            # Mostrar otros usuarios
            if otros:
                print("OTROS USUARIOS:")
                print("-" * 70)
                for username, info in sorted(otros):
                    tipo_text = "Superuser" if info['is_superuser'] else ("Staff" if info['is_staff'] else "Usuario")
                    print(f"  - Usuario: {username:20} | PIN: {info['pin']:6} | Tipo: {tipo_text} | Nombre: {info['nombre']}")
                print()
            
            print("="*70)
            print("RESUMEN")
            print("="*70)
            print(f"  - Total usuarios con PIN: {len(credenciales)}")
            print(f"  - Parejas de conteo: {len([u for u in credenciales.keys() if u in usuarios_parejas])}")
            print(f"  - Administrativos: {len(administrativos)}")
            print(f"  - Gerencia: {len(gerencia)}")
            print()
            print("="*70)
            print("NOTA: Los usuarios ahora ingresan con su PIN de 4 digitos")
            print("      Guarde estas credenciales de forma segura.")
            print("="*70)
            
    except Exception as e:
        print()
        print("="*70)
        print("ERROR AL GENERAR PINS")
        print("="*70)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    generar_pins_todos_usuarios()

