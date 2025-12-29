from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import PerfilUsuario, ParejaConteo


class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = 'Perfil'


class UserAdmin(BaseUserAdmin):
    inlines = (PerfilUsuarioInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(ParejaConteo)
class ParejaConteoAdmin(admin.ModelAdmin):
    list_display = ['usuario_1', 'usuario_2', 'color', 'activa', 'fecha_creacion']
    list_filter = ['activa', 'color', 'fecha_creacion']
    search_fields = ['usuario_1__username', 'usuario_2__username']
    readonly_fields = ['fecha_creacion']

