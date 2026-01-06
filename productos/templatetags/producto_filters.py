from django import template

register = template.Library()

@register.filter(name='formato_precio')
def formato_precio(value):
    """
    Formatea un precio con puntos como separadores de miles y coma para decimales.
    Ejemplo: 1234567.89 -> 1.234.567,89
    """
    if value is None:
        return "0,00"
    
    try:
        # Convertir a float
        precio = float(value)
        
        # Formatear con 2 decimales
        precio_str = f"{precio:,.2f}"
        
        # Reemplazar comas por puntos (separadores de miles)
        # y el punto decimal por coma
        precio_str = precio_str.replace(',', 'X')  # Temporal
        precio_str = precio_str.replace('.', ',')  # Decimal
        precio_str = precio_str.replace('X', '.')   # Miles
        
        return precio_str
    except (ValueError, TypeError):
        return "0,00"










