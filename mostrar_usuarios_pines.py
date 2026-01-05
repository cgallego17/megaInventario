#!/usr/bin/env python
"""
Script para mostrar todos los usuarios y sus PINs
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megaInventario.settings')
django.setup()

from django.contrib.auth.models import User
from usuarios.models import PerfilUsuario

def main():
    print("\n" + "="*80)
    print("USUARIOS Y PINES DEL SISTEMA")
    print("="*80 + "\n")
    
    usuarios = User.objects.all().order_by('username')
    
    # Encabezado
    print(f"{'Usuario':<25} {'PIN':<8} {'Staff':<8} {'Superuser':<12} {'Nombre Completo':<30}")
    print("-" * 80)
    
    usuarios_con_pin = 0
    usuarios_sin_pin = 0
    
    for usuario in usuarios:
        # Obtener perfil
        try:
            perfil = usuario.perfilusuario
            pin = perfil.pin if perfil.pin else 'Sin PIN'
        except PerfilUsuario.DoesNotExist:
            pin = 'Sin PIN'
            perfil = None
        
        if pin and pin != 'Sin PIN':
            usuarios_con_pin += 1
        else:
            usuarios_sin_pin += 1
        
        staff = 'Sí' if usuario.is_staff else 'No'
        superuser = 'Sí' if usuario.is_superuser else 'No'
        nombre_completo = usuario.get_full_name() or usuario.first_name or usuario.last_name or '-'
        
        print(f"{usuario.username:<25} {pin:<8} {staff:<8} {superuser:<12} {nombre_completo:<30}")
    
    print("-" * 80)
    print(f"\nTotal usuarios: {usuarios.count()}")
    print(f"Usuarios con PIN: {usuarios_con_pin}")
    print(f"Usuarios sin PIN: {usuarios_sin_pin}")
    print("\n" + "="*80 + "\n")
    
    # Mostrar parejas si existen
    from usuarios.models import ParejaConteo
    parejas = ParejaConteo.objects.filter(activa=True).select_related('usuario_1', 'usuario_2')
    
    if parejas.exists():
        print("\nPAREJAS DE CONTEO ACTIVAS:")
        print("-" * 80)
        for pareja in parejas:
            pin1 = pareja.usuario_1.perfilusuario.pin if hasattr(pareja.usuario_1, 'perfilusuario') and pareja.usuario_1.perfilusuario.pin else 'Sin PIN'
            pin2 = pareja.usuario_2.perfilusuario.pin if hasattr(pareja.usuario_2, 'perfilusuario') and pareja.usuario_2.perfilusuario.pin else 'Sin PIN'
            print(f"  {pareja.usuario_1.username} (PIN: {pin1}) & {pareja.usuario_2.username} (PIN: {pin2}) - Color: {pareja.get_color_display()}")
        print("-" * 80 + "\n")

if __name__ == '__main__':
    main()



