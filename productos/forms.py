from django import forms
from .models import Producto
import pandas as pd
import io
import requests
import json


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['codigo_barras', 'codigo', 'nombre', 'marca', 'descripcion', 'categoria', 'atributo', 'imagen', 'precio', 'unidad_medida']
        widgets = {
            'codigo_barras': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'categoria': forms.TextInput(attrs={'class': 'form-control'}),
            'atributo': forms.TextInput(attrs={'class': 'form-control'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ImportarProductosForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo Excel o CSV",
        help_text="Sube un archivo Excel (.xlsx, .xls) o CSV con las columnas: codigo_barras, codigo, nombre, marca, descripcion, categoria, atributo, precio, unidad_medida",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls,.csv'})
    )

    def procesar_archivo(self, archivo):
        """Procesa el archivo y retorna una lista de productos con todos los campos necesarios"""
        try:
            # Leer el archivo según su extensión
            if archivo.name.endswith('.csv'):
                df = pd.read_csv(archivo, encoding='utf-8-sig')  # utf-8-sig para manejar BOM
            else:
                df = pd.read_excel(archivo)
            
            productos = []
            errores = []
            
            # Validar que el DataFrame no esté vacío
            if df.empty:
                raise forms.ValidationError("El archivo está vacío")
            
            # Normalizar nombres de columnas (minúsculas y sin espacios)
            df.columns = df.columns.str.lower().str.strip()
            
            # Mapear columnas posibles (más variantes para mayor flexibilidad)
            columnas_mapeo = {
                'codigo_barras': ['codigo_barras', 'barcode', 'codigo de barras', 'código de barras', 'codigo_barras', 'ean', 'upc'],
                'codigo': ['codigo', 'cod', 'code', 'código', 'sku', 'codigo_interno'],
                'nombre': ['nombre', 'producto', 'name', 'descripcion', 'description', 'producto_nombre'],
                'marca': ['marca', 'brand', 'fabricante', 'manufacturer', 'marca_producto'],
                'descripcion': ['descripcion', 'detalle', 'description', 'detalles', 'observaciones', 'notas'],
                'categoria': ['categoria', 'category', 'categ', 'categoría', 'tipo', 'grupo'],
                'atributo': ['atributo', 'attribute', 'attr', 'caracteristica', 'característica', 'variante'],
                'precio': ['precio', 'price', 'precio_unitario', 'precio unitario', 'cost', 'costo', 'valor'],
                'unidad_medida': ['unidad_medida', 'unidad', 'um', 'unit', 'unidad de medida', 'medida'],
                'activo': ['activo', 'active', 'habilitado', 'enabled', 'estado']  # Campo adicional
            }
            
            # Encontrar las columnas correctas
            columnas_encontradas = {}
            for col_objetivo, posibles_nombres in columnas_mapeo.items():
                for nombre_posible in posibles_nombres:
                    if nombre_posible in df.columns:
                        columnas_encontradas[col_objetivo] = nombre_posible
                        break
            
            # Validar que al menos codigo_barras y nombre existan
            if 'codigo_barras' not in columnas_encontradas:
                raise forms.ValidationError(
                    "No se encontró la columna 'codigo_barras' en el archivo. "
                    "Asegúrese de que el archivo tenga una columna con código de barras."
                )
            if 'nombre' not in columnas_encontradas:
                raise forms.ValidationError(
                    "No se encontró la columna 'nombre' en el archivo. "
                    "Asegúrese de que el archivo tenga una columna con el nombre del producto."
                )
            
            # Procesar cada fila
            for index, row in df.iterrows():
                try:
                    # Función auxiliar para limpiar valores
                    def limpiar_valor(valor, default=''):
                        """Limpia y normaliza valores del DataFrame"""
                        if pd.isna(valor) or valor is None:
                            return default
                        valor_str = str(valor).strip()
                        if valor_str.lower() in ['nan', 'none', 'null', '']:
                            return default
                        return valor_str
                    
                    # Función auxiliar para convertir a float de forma segura
                    def convertir_precio(valor, default=0.0):
                        """Convierte un valor a float de forma segura"""
                        if pd.isna(valor) or valor is None:
                            return default
                        try:
                            valor_float = float(valor)
                            # Validar que no sea negativo
                            if valor_float < 0:
                                return default
                            return valor_float
                        except (ValueError, TypeError):
                            return default
                    
                    # Extraer y limpiar codigo_barras
                    codigo_barras = limpiar_valor(row[columnas_encontradas['codigo_barras']])
                    if not codigo_barras:
                        errores.append(f"Fila {index + 2}: Código de barras vacío o inválido")
                        continue
                    
                    # Extraer y limpiar nombre
                    nombre = limpiar_valor(row[columnas_encontradas['nombre']])
                    if not nombre:
                        errores.append(f"Fila {index + 2}: Nombre vacío o inválido")
                        continue
                    
                    # Construir diccionario de datos del producto
                    producto_data = {
                        'codigo_barras': codigo_barras,
                        'codigo': limpiar_valor(row[columnas_encontradas.get('codigo', '')]) if 'codigo' in columnas_encontradas else '',
                        'nombre': nombre,
                        'marca': limpiar_valor(row[columnas_encontradas.get('marca', '')]) if 'marca' in columnas_encontradas else '',
                        'descripcion': limpiar_valor(row[columnas_encontradas.get('descripcion', '')]) if 'descripcion' in columnas_encontradas else '',
                        'categoria': limpiar_valor(row[columnas_encontradas.get('categoria', '')]) if 'categoria' in columnas_encontradas else '',
                        'atributo': limpiar_valor(row[columnas_encontradas.get('atributo', '')]) if 'atributo' in columnas_encontradas else '',
                        'precio': convertir_precio(row[columnas_encontradas.get('precio', 0)]) if 'precio' in columnas_encontradas else 0.0,
                        'unidad_medida': limpiar_valor(row[columnas_encontradas.get('unidad_medida', 'UN')]) if 'unidad_medida' in columnas_encontradas else 'UN',
                    }
                    
                    # Procesar campo activo si existe
                    if 'activo' in columnas_encontradas:
                        activo_val = row[columnas_encontradas['activo']]
                        if pd.isna(activo_val) or activo_val is None:
                            producto_data['activo'] = True  # Por defecto activo
                        else:
                            # Aceptar varios formatos: True/False, Sí/No, 1/0, S/N, etc.
                            activo_str = str(activo_val).strip().lower()
                            producto_data['activo'] = activo_str in ['true', '1', 'sí', 'si', 's', 'yes', 'y', 'verdadero', 'habilitado', 'enabled']
                    else:
                        producto_data['activo'] = True  # Por defecto activo
                    
                    # Validaciones adicionales
                    # Validar longitud de codigo_barras
                    if len(producto_data['codigo_barras']) > 100:
                        errores.append(f"Fila {index + 2}: Código de barras demasiado largo (máximo 100 caracteres)")
                        continue
                    
                    # Validar longitud de nombre
                    if len(producto_data['nombre']) > 200:
                        errores.append(f"Fila {index + 2}: Nombre demasiado largo (máximo 200 caracteres)")
                        continue
                    
                    # Validar que unidad_medida no esté vacía
                    if not producto_data['unidad_medida']:
                        producto_data['unidad_medida'] = 'UN'
                    
                    productos.append(producto_data)
                    
                except KeyError as e:
                    errores.append(f"Fila {index + 2}: Error al acceder a columna: {str(e)}")
                except Exception as e:
                    errores.append(f"Fila {index + 2}: Error inesperado: {str(e)}")
            
            # Validar que se hayan procesado al menos algunos productos
            if not productos and not errores:
                raise forms.ValidationError("No se pudo procesar ningún producto del archivo. Verifique el formato.")
            
            return productos, errores
            
        except forms.ValidationError:
            raise  # Re-lanzar errores de validación
        except pd.errors.EmptyDataError:
            raise forms.ValidationError("El archivo está vacío o no tiene datos válidos")
        except pd.errors.ParserError as e:
            raise forms.ValidationError(f"Error al leer el archivo: {str(e)}")
        except Exception as e:
            raise forms.ValidationError(f"Error al procesar el archivo: {str(e)}")


class ImportarProductosAPIForm(forms.Form):
    """Formulario para importar productos desde una API"""
    url_api = forms.URLField(
        label="URL de la API",
        help_text="Ingrese la URL completa de la API que devuelve los productos",
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://api.ejemplo.com/productos'})
    )
    
    headers_json = forms.CharField(
        label="Headers (JSON opcional)",
        required=False,
        help_text="Headers en formato JSON para autenticación (ej: {\"Authorization\": \"Bearer token\"})",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '{"Authorization": "Bearer token"}'})
    )
    
    metodo = forms.ChoiceField(
        label="Método HTTP",
        choices=[('GET', 'GET'), ('POST', 'POST')],
        initial='GET',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    mapeo_personalizado_json = forms.CharField(
        label="Mapeo Personalizado (JSON opcional)",
        required=False,
        help_text="Mapeo de campos de la API a campos del sistema (ej: {\"codigo_barras\": \"barcode\", \"nombre\": \"product_name\"})",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '{"codigo_barras": "barcode", "nombre": "product_name"}'})
    )
    
    def clean_headers_json(self):
        """Valida que headers_json sea JSON válido si se proporciona"""
        headers_json = self.cleaned_data.get('headers_json', '').strip()
        if headers_json:
            try:
                return json.loads(headers_json)
            except json.JSONDecodeError:
                raise forms.ValidationError("El formato de headers no es JSON válido")
        return None
    
    def clean_mapeo_personalizado_json(self):
        """Valida que mapeo_personalizado_json sea JSON válido si se proporciona"""
        mapeo_json = self.cleaned_data.get('mapeo_personalizado_json', '').strip()
        if mapeo_json:
            try:
                return json.loads(mapeo_json)
            except json.JSONDecodeError:
                raise forms.ValidationError("El formato de mapeo personalizado no es JSON válido")
        return None

