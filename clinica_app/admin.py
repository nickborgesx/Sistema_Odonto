from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Gerente, Dentista, Paciente, Procedimento, Consulta, Recepcionista

# Configuração para o Usuário Personalizado aparecer com os campos certos
class UserModel(UserAdmin):
    # Campos que aparecem na lista
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'is_staff')
    
    # Ordenação (opcional, ajuda a organizar)
    ordering = ('email',)

    # Campos que aparecem na tela de edição
    fieldsets = UserAdmin.fieldsets + (
        ('Tipo de Usuário', {'fields': ('user_type',)}),
    )

    # ESSENCIAL: Campos que aparecem na tela de CRIAÇÃO (Botão "Adicionar Usuário")
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'user_type', 'is_staff', 'is_active'),
        }),
    )

admin.site.register(CustomUser, UserModel)
admin.site.register(Gerente)
admin.site.register(Dentista)
admin.site.register(Paciente)
admin.site.register(Procedimento)
admin.site.register(Consulta)
admin.site.register(Recepcionista)
