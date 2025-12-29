"""
Script para actualizar los PINs en los perfiles de usuario
Genera PINs nuevos y los guarda en el perfil
"""
import os
import sys
import django
import io
import secrets

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configurar Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megaInventario.settings')
django.setup()

from django.contrib.auth.models import User
from usuarios.models import PerfilUsuario
from django.db import transaction

def generar_pin():
    """Genera un PIN de 4 dígitos"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(4)])

def main():
    print("="*70)
    print("ACTUALIZACIÓN DE PINS EN PERFILES")
    print("="*70)
    print()
    
    usuarios = User.objects.all()
    pins_usados = set()
    actualizados = 0
    creados = 0
    
    with transaction.atomic():
        for usuario in usuarios:
            # Obtener o crear perfil
            perfil, creado = PerfilUsuario.objects.get_or_create(user=usuario)
            
            # Si el perfil no tiene PIN o se creó nuevo, generar uno
            if not perfil.pin or creado:
                # Generar PIN único
                pin = generar_pin()
                while pin in pins_usados:
                    pin = generar_pin()
                pins_usados.add(pin)
                
                perfil.pin = pin
                perfil.save()
                
                # Actualizar contraseña del usuario con el PIN
                usuario.set_password(pin)
                usuario.save()
                
                if creado:
                    creados += 1
                    print(f"  Perfil creado y PIN asignado: {usuario.username} -> PIN: {pin}")
                else:
                    actualizados += 1
                    print(f"  PIN actualizado: {usuario.username} -> PIN: {pin}")
            else:
                print(f"  PIN existente mantenido: {usuario.username} -> PIN: {perfil.pin}")
    
    print()
    print("="*70)
    print("ACTUALIZACIÓN COMPLETADA")
    print("="*70)
    print(f"Perfiles creados: {creados}")
    print(f"PINs actualizados: {actualizados}")
    print(f"Total usuarios: {usuarios.count()}")

if __name__ == '__main__':
    main()

