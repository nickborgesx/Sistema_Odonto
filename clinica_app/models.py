from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('1', 'Gerente'),
        ('2', 'Dentista'),
        ('3', 'Paciente'),
        ('4', 'Recepcionista'),
    )
    # Garante que o email seja obrigatório e único
    email = models.EmailField(unique=True) 
    user_type = models.CharField(default='1', choices=USER_TYPE_CHOICES, max_length=1)
    # Reaproveitamos `first_name` como "Nome completo" no sistema.
    first_name = models.CharField("Nome completo", max_length=150, blank=True)

    # Mantemos o fluxo padrão do Django (USERNAME_FIELD = "username").
    # O login do projeto já usa o e-mail no campo `username` (views.py),
    # o que evita quebrar `createsuperuser` sem um manager customizado.
    REQUIRED_FIELDS = ['email', 'first_name']

    def __str__(self):
        return self.email

class Gerente(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Dentista(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    # Estes campos são preenchidos logo após a criação do usuário (signal + views).
    # Se forem obrigatórios aqui, o signal falha ao criar o perfil.
    especialidade = models.CharField(max_length=255, null=True, blank=True)
    cro = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    cpf = models.CharField(max_length=14, null=True, blank=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)

class Paciente(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    genero = models.CharField(max_length=50, null=True, blank=True)
    cpf = models.CharField(max_length=14, null=True, blank=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    historico_medico = models.TextField(null=True, blank=True)

class Procedimento(models.Model):
    nome = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

class Consulta(models.Model):
    paciente_id = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    dentista_id = models.ForeignKey(Dentista, on_delete=models.CASCADE)
    procedimento_id = models.ForeignKey(Procedimento, on_delete=models.CASCADE)
    data_consulta = models.DateTimeField()
    status = models.BooleanField(default=False)

class Recepcionista(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    cpf = models.CharField(max_length=14, null=True, blank=True, unique=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    endereco = models.TextField(null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.admin.first_name

# Atualize o Signal
@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type == '1':
            Gerente.objects.create(admin=instance)
        elif instance.user_type == '2':
            Dentista.objects.create(admin=instance)
        elif instance.user_type == '3':
            Paciente.objects.create(admin=instance)
        elif instance.user_type == '4':
            Recepcionista.objects.create(admin=instance) # Novo perfil
