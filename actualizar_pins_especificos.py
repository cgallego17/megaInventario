"""
Script para actualizar los PINs específicos de los usuarios según la lista proporcionada
"""
import os
import sys
import django
import io

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

# PINs específicos según la lista
PINS_USUARIOS = {
    'beto': '7534',
    'dina': '2122',
    'juan_pablo': '4835',
    'alejandro': '0302',
    'isabel': '1528',
    'hernán': '8176',
    'walter': '5271',
    'andrés': '2526',
    'jaiber': '7804',
    'mauricio': '2767',
    'cristian': '7426',
    'melisa': '8736',
    'yessica': '0706',
    'carmenza': '5394',
    'claudia_arenas': '9252',
    'claudia_ríos': '0916',
}

def main():
    print("="*70)
    print("ACTUALIZACIÓN DE PINS ESPECÍFICOS")
    print("="*70)
    print()
    
    actualizados = 0
    no_encontrados = []
    
    with transaction.atomic():
        for username, pin in PINS_USUARIOS.items():
            try:
                usuario = User.objects.get(username=username)
                
                # Obtener o crear perfil
                perfil, creado = PerfilUsuario.objects.get_or_create(user=usuario)
                
                # Actualizar PIN
                perfil.pin = pin
                perfil.save()
                
                # Actualizar contraseña del usuario con el PIN
                usuario.set_password(pin)
                usuario.save()
                
                actualizados += 1
                print(f"  ✓ {username:20} -> PIN: {pin}")
                
            except User.DoesNotExist:
                no_encontrados.append(username)
                print(f"  ✗ {username:20} -> NO ENCONTRADO")
    
    print()
    print("="*70)
    print("ACTUALIZACIÓN COMPLETADA")
    print("="*70)
    print(f"Usuarios actualizados: {actualizados}")
    if no_encontrados:
        print(f"Usuarios no encontrados: {len(no_encontrados)}")
        print(f"  {', '.join(no_encontrados)}")
    
    print()
    print("Verificación de PINs:")
    for username, pin_esperado in PINS_USUARIOS.items():
        try:
            usuario = User.objects.get(username=username)
            pin_actual = usuario.perfilusuario.pin if hasattr(usuario, 'perfilusuario') and usuario.perfilusuario else None
            if pin_actual == pin_esperado:
                print(f"  ✓ {username}: {pin_actual}")
            else:
                print(f"  ✗ {username}: Esperado {pin_esperado}, Actual {pin_actual}")
        except User.DoesNotExist:
            print(f"  ✗ {username}: Usuario no existe")

if __name__ == '__main__':
    main()

