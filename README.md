# Mega Inventario - Sistema de Gestión de Inventario

Sistema completo de gestión de inventario desarrollado con Django que incluye módulos para productos, conteo físico con scanner de código de barras, usuarios, reportes y comparativos.

## Características

### 📦 Módulo de Productos
- Gestión completa de productos (crear, editar, eliminar)
- Importación masiva desde archivos Excel o CSV
- Búsqueda y filtrado de productos
- Gestión de stock y precios

### 📷 Módulo de Conteo
- Scanner de código de barras usando cámara del celular
- Conteo por parejas de usuarios
- Suma automática de cantidades por producto
- Sesiones de conteo con seguimiento de estado

### 👥 Módulo de Usuarios
- Sistema de autenticación
- Gestión de perfiles de usuario
- Creación de parejas para conteo
- Control de acceso

### 📊 Módulo de Reportes
- Reporte de sesiones de conteo
- Reporte de inventario actual
- Reporte de diferencias entre sistema y físico
- Exportación a CSV

### 🔄 Módulo de Comparativos
- Carga de inventarios de dos sistemas diferentes
- Comparación con conteo físico
- Visualización de diferencias
- Exportación de resultados

## Requisitos

- Python 3.8 o superior
- Django 4.2
- Navegador web moderno con soporte para cámara (para el scanner)

## Instalación

1. Clonar o descargar el proyecto

2. Crear un entorno virtual (recomendado):
```bash
python -m venv venv
```

3. Activar el entorno virtual:
- Windows:
```bash
venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```

4. Instalar dependencias:
```bash
pip install -r requirements.txt
```

5. Ejecutar migraciones:
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Crear un superusuario:
```bash
python manage.py createsuperuser
```

7. Ejecutar el servidor de desarrollo:
```bash
python manage.py runserver
```

8. Acceder a la aplicación en: http://127.0.0.1:8000

## Uso del Scanner de Código de Barras

1. Crear una sesión de conteo con dos usuarios
2. Abrir la sesión de conteo
3. Hacer clic en "Activar Cámara"
4. Permitir el acceso a la cámara cuando el navegador lo solicite
5. Apuntar la cámara al código de barras del producto
6. El sistema detectará automáticamente el código y agregará el producto
7. También puedes ingresar el código manualmente en el campo de texto

## Formato de Importación de Productos

El archivo Excel o CSV debe contener las siguientes columnas:

- **codigo_barras** o **codigo** (requerido)
- **nombre** o **producto** (requerido)
- **descripcion** (opcional)
- **categoria** (opcional)
- **precio** (opcional, default: 0)
- **stock_actual** o **stock** (opcional, default: 0)
- **unidad_medida** o **unidad** (opcional, default: UN)

## Estructura del Proyecto

```
megaInventario/
├── megaInventario/          # Configuración del proyecto
├── productos/               # Módulo de productos
├── conteo/                  # Módulo de conteo
├── usuarios/                # Módulo de usuarios
├── reportes/                # Módulo de reportes
├── comparativos/            # Módulo de comparativos
├── templates/               # Plantillas HTML
├── static/                  # Archivos estáticos
└── media/                   # Archivos subidos
```

## Notas Importantes

- El scanner de código de barras requiere acceso a la cámara del dispositivo
- Funciona mejor en dispositivos móviles con cámara trasera
- Los archivos de importación deben estar en formato Excel (.xlsx, .xls) o CSV
- Se recomienda usar HTTPS en producción para acceso a la cámara

## Desarrollo

Para desarrollo, el proyecto incluye:
- Django Admin para gestión administrativa
- Interfaz responsive con Bootstrap 5
- Sistema de autenticación integrado
- API REST básica para algunas funcionalidades

## Licencia

Este proyecto es de uso interno.

