from django.db import models
from django.contrib.auth.models import User

class Perfil(models.Model):
    # A mágica acontece aqui: uma relação 1 para 1 com o User
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    
    # Campos específicos do estudante
    curso = models.CharField(max_length=100, blank=True, null=True, help_text="Ex: Bacharelado em Física")
    instituto = models.CharField(max_length=50, blank=True, null=True, help_text="Ex: IFUSP")
    semestre_ingresso = models.PositiveIntegerField(blank=True, null=True, help_text="Ex: 2023")
    # NOVO CAMPO AQUI:
    email_institucional = models.EmailField(max_length=255, blank=True, null=True, help_text="Ex: aluno@usp.br")
    
    # Opcional: Uma pequena bio para o aluno se descrever
    bio = models.TextField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"