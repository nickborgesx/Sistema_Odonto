from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Gerente, Dentista, Paciente, Procedimento, Consulta

# Configuração para o Usuário Personalizado aparecer com os campos certos
class UserModel(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('user_type',)}),
    )

admin.site.register(CustomUser, UserModel)
admin.site.register(Gerente)
admin.site.register(Dentista)
admin.site.register(Paciente)
admin.site.register(Procedimento)
admin.site.register(Consulta)
