"""
Script para eliminar todas las imágenes de productos excepto las actuales
Mantiene solo las imágenes que están asignadas a productos en la base de datos
"""

import os
import sys
import django
import io
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megaInventario.settings')
django.setup()

from django.conf import settings
from productos.models import Producto
from django.core.files.storage import default_storage

def main():
    print("="*70)
    print("LIMPIEZA DE IMÁGENES DE PRODUCTOS")
    print("="*70)
    print()
    print("Este script eliminará todas las imágenes de productos")
    print("excepto las que están actualmente asignadas a productos.")
    print()
    
    # Obtener todas las imágenes que están en uso
    productos_con_imagen = Producto.objects.exclude(imagen__isnull=True).exclude(imagen='')
    imagenes_en_uso = set()
    
    print("Obteniendo imágenes en uso...")
    for producto in productos_con_imagen:
        if producto.imagen:
            # Obtener la ruta relativa de la imagen
            imagen_path = producto.imagen.name
            imagenes_en_uso.add(imagen_path)
            # También agregar el nombre del archivo por si acaso
            if os.path.basename(imagen_path):
                imagenes_en_uso.add(os.path.basename(imagen_path))
    
    print(f"  Imágenes en uso: {len(imagenes_en_uso)}")
    print()
    
    # Obtener todas las imágenes en el directorio
    media_root = settings.MEDIA_ROOT
    productos_dir = os.path.join(media_root, 'productos')
    
    if not os.path.exists(productos_dir):
        print("No existe el directorio de productos.")
        return
    
    print("Escaneando directorio de imágenes...")
    todas_las_imagenes = []
    for root, dirs, files in os.walk(productos_dir):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, media_root)
            todas_las_imagenes.append((file_path, rel_path, file))
    
    print(f"  Total de imágenes encontradas: {len(todas_las_imagenes)}")
    print()
    
    # Identificar imágenes a eliminar
    imagenes_a_eliminar = []
    imagenes_a_mantener = []
    
    for file_path, rel_path, file_name in todas_las_imagenes:
        # Verificar si la imagen está en uso
        en_uso = False
        
        # Verificar por ruta relativa completa
        if rel_path in imagenes_en_uso:
            en_uso = True
        # Verificar por nombre de archivo
        elif file_name in imagenes_en_uso:
            en_uso = True
        # Verificar si algún producto tiene esta imagen
        else:
            for producto in productos_con_imagen:
                if producto.imagen and (producto.imagen.name == rel_path or os.path.basename(producto.imagen.name) == file_name):
                    en_uso = True
                    break
        
        if en_uso:
            imagenes_a_mantener.append((file_path, rel_path, file_name))
        else:
            imagenes_a_eliminar.append((file_path, rel_path, file_name))
    
    print("="*70)
    print("RESUMEN")
    print("="*70)
    print(f"Imágenes a mantener: {len(imagenes_a_mantener)}")
    print(f"Imágenes a eliminar: {len(imagenes_a_eliminar)}")
    print()
    
    if len(imagenes_a_eliminar) == 0:
        print("No hay imágenes para eliminar.")
        return
    
    # Mostrar algunas imágenes que se eliminarán
    print("Ejemplos de imágenes a eliminar (primeras 10):")
    for file_path, rel_path, file_name in imagenes_a_eliminar[:10]:
        print(f"  - {file_name}")
    if len(imagenes_a_eliminar) > 10:
        print(f"  ... y {len(imagenes_a_eliminar) - 10} más")
    print()
    
    # Verificar si se pasó el argumento --confirmar
    confirmar = '--confirmar' in sys.argv
    
    if not confirmar:
        try:
            respuesta = input(f"¿Desea eliminar {len(imagenes_a_eliminar)} imágenes? (s/n): ")
            if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
                print("Operación cancelada.")
                return
        except EOFError:
            print("Error: No se puede leer entrada. Use --confirmar para ejecutar sin confirmación.")
            sys.exit(1)
    
    print()
    print("Eliminando imágenes...")
    
    eliminadas = 0
    errores = 0
    
    for file_path, rel_path, file_name in imagenes_a_eliminar:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                eliminadas += 1
                if eliminadas % 100 == 0:
                    print(f"  Eliminadas: {eliminadas}/{len(imagenes_a_eliminar)}")
        except Exception as e:
            errores += 1
            print(f"  Error al eliminar {file_name}: {str(e)}")
    
    print()
    print("="*70)
    print("LIMPIEZA COMPLETADA")
    print("="*70)
    print(f"Imágenes eliminadas: {eliminadas}")
    print(f"Imágenes mantenidas: {len(imagenes_a_mantener)}")
    if errores > 0:
        print(f"Errores: {errores}")
    print()

if __name__ == '__main__':
    main()

