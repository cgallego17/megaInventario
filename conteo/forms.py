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
        parejas = cleaned_data.get('parejas')
        usuario_1 = cleaned_data.get('usuario_1')
        usuario_2 = cleaned_data.get('usuario_2')
        
        # Si no hay parejas ni usuarios, mostrar error
        if not parejas and not usuario_1 and not usuario_2:
            raise forms.ValidationError('Debe seleccionar al menos una pareja o dos usuarios.')
        
        return cleaned_data


class ItemConteoForm(forms.ModelForm):
    class Meta:
        model = ItemConteo
        fields = ['producto', 'cantidad']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mostrar todos los productos (activos e inactivos)
        self.fields['producto'].queryset = Producto.objects.all().order_by('nombre')
    
    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad < 0:
            raise forms.ValidationError('La cantidad no puede ser negativa.')
        return cantidad
    
    def save(self, commit=True):
        item = super().save(commit=False)
        if commit:
            item.save()
        return item


class CompararConteosForm(forms.Form):
    """Formulario para seleccionar conteos a comparar"""
    conteos = forms.ModelMultipleChoiceField(
        queryset=Conteo.objects.filter(estado='finalizado').order_by('numero_conteo', '-fecha_fin'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Seleccionar Conteos',
        help_text='Seleccione al menos 2 conteos finalizados para comparar. Puede seleccionar múltiples conteos.',
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo conteos finalizados
        self.fields['conteos'].queryset = Conteo.objects.filter(estado='finalizado').order_by('numero_conteo', '-fecha_fin')
    
    def clean_conteos(self):
        conteos = self.cleaned_data.get('conteos')
        if len(conteos) < 2:
            raise forms.ValidationError('Debe seleccionar al menos 2 conteos para comparar.')
        return conteos
