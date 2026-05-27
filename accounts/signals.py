from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Perfil

# Este sinal escuta quando um User é salvo. Se for "criado" (created=True), ele cria o Perfil.
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance)

# Este sinal garante que se você salvar o User, o Perfil também é salvo.
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.perfil.save()