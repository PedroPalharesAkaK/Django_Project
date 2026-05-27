from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Perfil

@receiver(post_save, sender=User)
def gerir_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        # Se o usuário acabou de se cadastrar, cria o perfil.
        Perfil.objects.create(user=instance)
    else:
        # Se o usuário já existe (ex: login), garante que o perfil existe
        perfil, is_new = Perfil.objects.get_or_create(user=instance)
        
        # Só tenta salvar se o perfil já existia antes
        if not is_new:
            perfil.save()