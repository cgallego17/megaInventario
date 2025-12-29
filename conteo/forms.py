from django import forms
from .models import Conteo, ItemConteo
from productos.models import Producto
from usuarios.models import ParejaConteo


class ConteoForm(forms.ModelForm):
    class Meta:
        model = Conteo
        fields = ['nombre', 'numero_conteo', 'parejas', 'usuario_1', 'usuario_2', 'observaciones']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_conteo': forms.Select(attrs={'class': 'form-control'}),
            'parejas': forms.SelectMultiple(attrs={'class': 'form-control', 'id': 'id_parejas', 'size': '5'}),
            'usuario_1': forms.Select(attrs={'class': 'form-control', 'id': 'id_usuario_1'}),
            'usuario_2': forms.Select(attrs={'class': 'form-control', 'id': 'id_usuario_2'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'parejas': 'Parejas de Conteo',
        }
        help_texts = {
            'parejas': 'Seleccione una o más parejas para este conteo. Puede mantener presionada la tecla Ctrl (o Cmd en Mac) para seleccionar múltiples parejas.',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo parejas activas
        self.fields['parejas'].queryset = ParejaConteo.objects.filter(activa=True)
        # Reordenar campos
        field_order = ['nombre', 'numero_conteo', 'parejas', 'usuario_1', 'usuario_2', 'observaciones']
        self.fields = {k: self.fields[k] for k in field_order if k in self.fields}
    
    def clean(self):
        cleaned_data = super().clean()
        parejas = cleaned_data.get('parejas', [])
        usuario_1 = cleaned_data.get('usuario_1')
        usuario_2 = cleaned_data.get('usuario_2')
        
        # Validar que se haya seleccionado al menos una pareja o usuarios manuales
        if not parejas and (not usuario_1 or not usuario_2):
            raise forms.ValidationError("Debe seleccionar al menos una pareja o ambos usuarios manualmente.")
        
        # Validar que los usuarios sean diferentes si se proporcionan manualmente
        if usuario_1 and usuario_2 and usuario_1 == usuario_2:
            raise forms.ValidationError("Los usuarios deben ser diferentes.")
        
        return cleaned_data
    
    def save(self, commit=True, usuario=None):
        conteo = super().save(commit=False)
        if commit:
            # Si es una edición y hay usuario, actualizar usuario_modificador
            if self.instance.pk and usuario:
                conteo.usuario_modificador = usuario
            conteo.save()
            # Guardar las parejas (ManyToMany necesita guardarse después del objeto)
            self.save_m2m()
        return conteo


class ItemConteoForm(forms.ModelForm):
    codigo_barras = forms.CharField(
        label="Código de Barras",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autofocus': True,
            'placeholder': 'Escanee o ingrese el código de barras'
        })
    )
    
    class Meta:
        model = ItemConteo
        fields = ['cantidad']
        widgets = {
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'value': '1'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.sesion = kwargs.pop('sesion', None)
        super().__init__(*args, **kwargs)
    
    def clean_codigo_barras(self):
        codigo_barras = self.cleaned_data.get('codigo_barras')
        if codigo_barras:
            try:
                # Buscar todos los productos (activos e inactivos)
                producto = Producto.objects.get(codigo_barras=codigo_barras)
                return producto
            except Producto.DoesNotExist:
                raise forms.ValidationError(f"Producto con código {codigo_barras} no encontrado")
        return None
    
    def save(self, commit=True):
        item = super().save(commit=False)
        producto = self.cleaned_data.get('codigo_barras')
        if producto:
            item.producto = producto
        if self.sesion:
            item.sesion = self.sesion
        if commit:
            item.save()
        return item

