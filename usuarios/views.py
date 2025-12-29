from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .forms import RegistroForm, LoginForm, PerfilForm, ParejaConteoForm, UsuarioForm
from .models import PerfilUsuario, ParejaConteo


def registro(request):
    """Registro de nuevos usuarios"""
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Crear perfil
            PerfilUsuario.objects.create(user=user)
            messages.success(request, 'Usuario registrado exitosamente. Por favor inicia sesión.')
            return redirect('usuarios:login')
    else:
        form = RegistroForm()
    
    return render(request, 'usuarios/registro.html', {'form': form})


def login_view(request):
    """Vista de login"""
    if request.user.is_authenticated:
        return redirect('productos:lista')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bienvenido, {user.username}!')
            return redirect('productos:lista')
    else:
        form = LoginForm()
    
    return render(request, 'usuarios/login.html', {'form': form})


@login_required
def logout_view(request):
    """Cerrar sesión"""
    logout(request)
    messages.success(request, 'Sesión cerrada exitosamente.')
    return redirect('usuarios:login')


@login_required
def perfil(request):
    """Ver y editar perfil de usuario"""
    perfil_usuario, created = PerfilUsuario.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=perfil_usuario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado exitosamente.')
            return redirect('usuarios:perfil')
    else:
        form = PerfilForm(instance=perfil_usuario)
    
    return render(request, 'usuarios/perfil.html', {'form': form, 'perfil': perfil_usuario})


@login_required
def lista_parejas(request):
    """Lista todas las parejas de conteo"""
    parejas = ParejaConteo.objects.all()
    return render(request, 'usuarios/lista_parejas.html', {'parejas': parejas})


@login_required
def crear_pareja(request):
    """Crea una nueva pareja de conteo"""
    if request.method == 'POST':
        form = ParejaConteoForm(request.POST)
        if form.is_valid():
            pareja = form.save(commit=False)
            # Si no se especificó un color, asignar uno automáticamente
            if not pareja.color:
                COLORES = ['primary', 'success', 'danger', 'warning', 'info', 'secondary', 'dark', 'light']
                parejas_existentes = ParejaConteo.objects.exclude(id=pareja.id if pareja.id else None)
                colores_usados = set(p.color for p in parejas_existentes if p.color)
                # Encontrar el primer color disponible
                color_disponible = None
                for color in COLORES:
                    if color not in colores_usados:
                        color_disponible = color
                        break
                # Si todos los colores están usados, usar el siguiente en la lista
                if not color_disponible:
                    total_parejas = parejas_existentes.count()
                    color_disponible = COLORES[total_parejas % len(COLORES)]
                pareja.color = color_disponible
            pareja.save()
            messages.success(request, 'Pareja de conteo creada exitosamente.')
            return redirect('usuarios:lista_parejas')
    else:
        form = ParejaConteoForm()
    
    return render(request, 'usuarios/form_pareja.html', {'form': form, 'titulo': 'Crear Pareja de Conteo'})


@login_required
def editar_pareja(request, pk):
    """Edita una pareja de conteo"""
    pareja = get_object_or_404(ParejaConteo, pk=pk)
    
    if request.method == 'POST':
        form = ParejaConteoForm(request.POST, instance=pareja)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pareja actualizada exitosamente.')
            return redirect('usuarios:lista_parejas')
    else:
        form = ParejaConteoForm(instance=pareja)
    
    return render(request, 'usuarios/form_pareja.html', {'form': form, 'pareja': pareja, 'titulo': 'Editar Pareja'})


@login_required
def desactivar_pareja(request, pk):
    """Desactiva una pareja de conteo"""
    pareja = get_object_or_404(ParejaConteo, pk=pk)
    
    if request.method == 'POST':
        pareja.activa = False
        pareja.save()
        messages.success(request, 'Pareja desactivada exitosamente.')
        return redirect('usuarios:lista_parejas')
    
    return render(request, 'usuarios/desactivar_pareja.html', {'pareja': pareja})


@login_required
def eliminar_pareja(request, pk):
    """Elimina una pareja de conteo"""
    pareja = get_object_or_404(ParejaConteo, pk=pk)
    
    if request.method == 'POST':
        pareja.delete()
        messages.success(request, 'Pareja eliminada exitosamente.')
        return redirect('usuarios:lista_parejas')
    
    return render(request, 'usuarios/eliminar_pareja.html', {'pareja': pareja})


@login_required
def lista_usuarios(request):
    """Lista todos los usuarios"""
    usuarios = User.objects.all().select_related('perfilusuario')
    
    # Búsqueda
    busqueda = request.GET.get('busqueda', '').strip()
    if busqueda:
        usuarios = usuarios.filter(
            Q(username__icontains=busqueda) |
            Q(first_name__icontains=busqueda) |
            Q(last_name__icontains=busqueda) |
            Q(email__icontains=busqueda)
        )
    
    # Paginación
    usuarios = usuarios.order_by('username')
    paginator = Paginator(usuarios, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'usuarios/lista_usuarios.html', {
        'page_obj': page_obj,
        'busqueda': busqueda
    })


@login_required
def crear_usuario(request):
    """Crea un nuevo usuario"""
    if request.method == 'POST':
        form = UsuarioForm(request.POST, is_creating=True)
        if form.is_valid():
            user = form.save()
            # Crear perfil si no existe
            PerfilUsuario.objects.get_or_create(user=user)
            messages.success(request, 'Usuario creado exitosamente.')
            return redirect('usuarios:lista_usuarios')
    else:
        form = UsuarioForm(is_creating=True)
    
    return render(request, 'usuarios/form_usuario.html', {'form': form, 'titulo': 'Crear Usuario'})


@login_required
def editar_usuario(request, pk):
    """Edita un usuario existente"""
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=user, is_creating=False)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario actualizado exitosamente.')
            return redirect('usuarios:lista_usuarios')
    else:
        form = UsuarioForm(instance=user, is_creating=False)
    
    return render(request, 'usuarios/form_usuario.html', {
        'form': form,
        'usuario': user,
        'titulo': 'Editar Usuario'
    })


@login_required
def eliminar_usuario(request, pk):
    """Elimina un usuario"""
    user = get_object_or_404(User, pk=pk)
    
    # No permitir eliminar al usuario actual
    if user == request.user:
        messages.error(request, 'No puedes eliminar tu propio usuario.')
        return redirect('usuarios:lista_usuarios')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Usuario {username} eliminado exitosamente.')
        return redirect('usuarios:lista_usuarios')
    
    return render(request, 'usuarios/eliminar_usuario.html', {'usuario': user})


@login_required
def obtener_usuarios_pareja(request, pk):
    """API endpoint para obtener los usuarios de una pareja"""
    from django.http import JsonResponse
    pareja = get_object_or_404(ParejaConteo, pk=pk)
    return JsonResponse({
        'success': True,
        'usuario_1_id': pareja.usuario_1.id,
        'usuario_2_id': pareja.usuario_2.id,
        'usuario_1_username': pareja.usuario_1.username,
        'usuario_2_username': pareja.usuario_2.username,
    })

