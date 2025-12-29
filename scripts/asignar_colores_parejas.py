"""
Script para asignar colores diferentes a cada pareja
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

from usuarios.models import ParejaConteo

# Colores disponibles en orden
COLORES = ['primary', 'success', 'danger', 'warning', 'info', 'secondary', 'dark', 'light']

def main():
    print("="*70)
    print("ASIGNACIÓN DE COLORES A PAREJAS")
    print("="*70)
    print()
    
    parejas = ParejaConteo.objects.all().order_by('id')
    total_parejas = parejas.count()
    
    print(f"Total de parejas: {total_parejas}")
    print()
    
    if total_parejas == 0:
        print("No hay parejas para asignar colores.")
        return
    
    # Asignar colores
    for idx, pareja in enumerate(parejas):
        # Usar módulo para ciclar los colores si hay más parejas que colores
        color = COLORES[idx % len(COLORES)]
        pareja.color = color
        pareja.save()
        print(f"  Pareja {idx + 1}: {pareja.usuario_1.username} & {pareja.usuario_2.username} -> Color: {color}")
    
    print()
    print("="*70)
    print("COLORES ASIGNADOS EXITOSAMENTE")
    print("="*70)
    print()
    
    # Mostrar resumen
    print("Resumen por color:")
    for color in COLORES:
        count = ParejaConteo.objects.filter(color=color).count()
        if count > 0:
            print(f"  {color}: {count} pareja(s)")

if __name__ == '__main__':
    main()

