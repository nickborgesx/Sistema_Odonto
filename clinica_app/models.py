from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        (1, 'Gerente'),
        (2, 'Dentista'),
        (3, 'Paciente'),
    )
    user_type = models.CharField(default=1, choices=USER_TYPE_CHOICES, max_length=1)

class Gerente(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Dentista(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    especialidade = models.CharField(max_length=255)
    cro = models.CharField(max_length=50) # Registro profissional
    address = models.TextField()

class Paciente(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    genero = models.CharField(max_length=50)
    address = models.TextField()
    historico_medico = models.TextField()

class Procedimento(models.Model):
    nome = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

class Consulta(models.Model):
    paciente_id = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    dentista_id = models.ForeignKey(Dentista, on_delete=models.CASCADE)
    procedimento_id = models.ForeignKey(Procedimento, on_delete=models.CASCADE)
    data_consulta = models.DateTimeField()
    status = models.BooleanField(default=False) # False = Pendente, True = Realizada

# Signals para criar o perfil automaticamente ao criar um usuário
@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type == 1:
            Gerente.objects.create(admin=instance)
        if instance.user_type == 2:
            Dentista.objects.create(admin=instance)
        if instance.user_type == 3:
            Paciente.objects.create(admin=instance)