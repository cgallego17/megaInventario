# Scripts de Utilidad

Esta carpeta contiene scripts de utilidad para el sistema de inventario.

## Scripts Disponibles

### Gestión de Usuarios
- **`crear_usuarios_parejas.py`** - Crea usuarios y sus parejas de conteo
- **`crear_usuarios_administrativos.py`** - Crea usuarios administrativos y de gerencia
- **`generar_pins_acceso.py`** - Genera PINs de 4 dígitos para todos los usuarios
- **`actualizar_pins_perfiles.py`** - Actualiza los PINs en los perfiles de usuario
- **`actualizar_pins_especificos.py`** - Actualiza PINs específicos de usuarios

### Gestión de Parejas
- **`asignar_colores_parejas.py`** - Asigna colores únicos a cada pareja de conteo

### Gestión de Productos
- **`importar_api_directo.py`** - Importa productos directamente desde la API
- **`importar_productos_api.py`** - Importa productos desde la API con sincronización
- **`sincronizar_productos_api.py`** - Sincroniza productos con la API (elimina los que no están en la API)
- **`eliminar_duplicados_productos.py`** - Elimina productos duplicados basados en `id_api`
- **`migrar_id_api.py`** - Migra IDs de API desde el campo `codigo` al campo `id_api`
- **`limpiar_imagenes_productos.py`** - Elimina imágenes de productos no referenciadas

### Limpieza de Datos
- **`borrar_todos_datos.py`** - Elimina todos los datos del sistema (preserva superusuarios)
- **`limpiar_registros_excepto_productos_usuarios.py`** - Limpia registros excepto productos, usuarios y parejas

## Uso

Todos los scripts deben ejecutarse desde la raíz del proyecto:

```bash
python scripts/nombre_del_script.py
```

Algunos scripts requieren argumentos adicionales. Consulta la documentación dentro de cada script para más detalles.





