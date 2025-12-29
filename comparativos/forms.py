from django import forms
from .models import ComparativoInventario, InventarioSistema
from conteo.models import Conteo
import pandas as pd
import io


class ComparativoInventarioForm(forms.ModelForm):
    class Meta:
        model = ComparativoInventario
        fields = ['nombre', 'nombre_sistema1', 'nombre_sistema2', 'observaciones']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_sistema1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: SAP, Oracle, etc.'}),
            'nombre_sistema2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: SAP, Oracle, etc.'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        help_texts = {
            'nombre_sistema1': 'Nombre personalizado para el primer sistema (ej: SAP, Oracle, etc.)',
            'nombre_sistema2': 'Nombre personalizado para el segundo sistema (ej: SAP, Oracle, etc.)',
            'nombre': 'El conteo físico se calculará automáticamente sumando todos los conteos finalizados.',
        }


class InventarioSistemaForm(forms.ModelForm):
    archivo = forms.FileField(
        label="Archivo de Inventario",
        help_text="Sube un archivo Excel (.xlsx, .xls) o CSV con las columnas: codigo_barras (o codigo) y cantidad (o stock)",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls,.csv'})
    )
    
    class Meta:
        model = InventarioSistema
        fields = ['sistema', 'archivo']
        widgets = {
            'sistema': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def procesar_archivo(self, archivo, sistema=None):
        """Procesa el archivo y retorna un diccionario {codigo_barras: cantidad} y el nombre del sistema
        
        Args:
            archivo: Archivo a procesar
            sistema: Sistema para el cual se está procesando ('sistema1' o 'sistema2')
                     Si se proporciona, buscará primero la columna específica del sistema
        
        Returns:
            tuple: (inventario_dict, nombre_sistema) donde inventario_dict es {codigo_barras: cantidad}
                   y nombre_sistema es el nombre extraído del archivo o None
        """
        nombre_sistema = None
        try:
            # Leer el archivo según su extensión
            if archivo.name.endswith('.csv'):
                df = pd.read_csv(archivo)
            else:
                # Intentar leer la hoja de configuración primero
                try:
                    df_config = pd.read_excel(archivo, sheet_name='Configuración')
                    # Buscar el nombre del sistema en la hoja de configuración
                    if 'Parámetro' in df_config.columns and 'Valor' in df_config.columns:
                        nombre_idx = df_config[df_config['Parámetro'].str.contains('Nombre del Sistema', case=False, na=False)].index
                        if len(nombre_idx) > 0:
                            nombre_sistema = str(df_config.loc[nombre_idx[0], 'Valor']).strip()
                            if nombre_sistema and nombre_sistema.lower() not in ['nan', 'none', '']:
                                nombre_sistema = nombre_sistema
                            else:
                                nombre_sistema = None
                except:
                    # Si no hay hoja de configuración, continuar
                    pass
                
                # Leer la hoja de inventario (o la primera hoja si no existe 'Inventario')
                try:
                    df = pd.read_excel(archivo, sheet_name='Inventario')
                except:
                    df = pd.read_excel(archivo)
            
            # Normalizar nombres de columnas
            df.columns = df.columns.str.lower().str.strip()
            
            # Encontrar columna de código
            codigo_col = None
            for col in df.columns:
                if col in ['codigo_barras', 'codigo', 'barcode', 'codigo de barras']:
                    codigo_col = col
                    break
            
            if not codigo_col:
                raise forms.ValidationError("No se encontró columna de código de barras")
            
            # Encontrar columna de cantidad - priorizar columna específica del sistema si existe
            cantidad_col = None
            
            # Si se especificó el sistema, buscar primero la columna específica
            if sistema:
                columna_sistema = f'cantidad_{sistema}'
                if columna_sistema in df.columns:
                    cantidad_col = columna_sistema
            
            # Si no se encontró columna específica, buscar genérica
            if not cantidad_col:
                for col in df.columns:
                    if col in ['cantidad', 'cantidad_sistema1', 'cantidad_sistema2', 'stock', 'stock_actual', 'inventario']:
                        cantidad_col = col
                        break
            
            if not cantidad_col:
                raise forms.ValidationError(
                    f"No se encontró columna de cantidad. "
                    f"Busque columnas como: cantidad, cantidad_{sistema}, stock, stock_actual"
                )
            
            # Crear diccionario
            inventario = {}
            productos_procesados = 0
            productos_sin_cantidad = 0
            
            for index, row in df.iterrows():
                try:
                    codigo = str(row[codigo_col]).strip()
                    # Filtrar valores nulos, vacíos o 'nan'
                    if codigo and codigo.lower() != 'nan' and codigo != '':
                        # Manejar valores vacíos o NaN en cantidad
                        cantidad_val = row[cantidad_col]
                        if pd.isna(cantidad_val) or cantidad_val == '' or str(cantidad_val).strip() == '':
                            cantidad = 0
                            productos_sin_cantidad += 1
                        else:
                            try:
                                # Convertir a float primero para manejar decimales, luego a int
                                cantidad = int(float(cantidad_val))
                                # Asegurar que no sea negativo
                                if cantidad < 0:
                                    cantidad = 0
                            except (ValueError, TypeError, OverflowError):
                                cantidad = 0
                                productos_sin_cantidad += 1
                        
                        # Solo agregar si el código es válido
                        inventario[codigo] = cantidad
                        productos_procesados += 1
                except (KeyError, IndexError) as e:
                    # Si hay un error al acceder a la fila, continuar con la siguiente
                    continue
                except Exception as e:
                    # Otros errores, continuar con la siguiente fila
                    continue
            
            return inventario, nombre_sistema
            
        except forms.ValidationError:
            raise
        except Exception as e:
            raise forms.ValidationError(f"Error al procesar el archivo: {str(e)}")

