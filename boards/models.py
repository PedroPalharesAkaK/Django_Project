from django.db import models
from django.contrib.auth.models import User

class Board(models.Model):
    name = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Topic(models.Model):
    subject = models.CharField(max_length=255)
    last_updated = models.DateTimeField(auto_now_add=True)
    # ADICIONADO: on_delete=models.CASCADE
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='topics')
    #, the board field is a ForeignKey to the Board model. It is telling Django that a Topic instance relates to only one Board instance
    #The related_name parameter will be used to create a reverse relationship where the Board instances will have access a list of Topic instances that belong to it.
    starter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topics')

class Post(models.Model):
    message = models.TextField(max_length=4000)
    # ADICIONADO: on_delete=models.CASCADE
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    # ADICIONADO: on_delete=models.SET_NULL (para não perder o post se o user sumir)
    updated_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='+') #esse related name diz para nao fazer a reserve relationship