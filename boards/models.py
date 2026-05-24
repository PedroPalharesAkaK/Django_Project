from django.db import models
from django.contrib.auth.models import User
from django.db.models import F  # <-- ADICIONE ESSE IMPORT!
from django.utils.html import mark_safe  # <-- ADICIONE ESTA LINHA NO TOPO
from markdown import markdown
import math
class Board(models.Model):
    name = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    # 1. Contagem de Posts (Exatamente como na imagem)
    def get_posts_count(self):
        return Post.objects.filter(topic__board=self).count() #tabela post, veja class post

    # 2. O QUE FALTOU NA IMAGEM: Contagem de Tópicos do Board
    def get_topics_count(self):
        return self.topics.count()  # Usa o related_name de Topic para contar direto!

    # 3. Dados do Último Post (Exatamente como na imagem)
    def get_last_post(self):
        return Post.objects.filter(topic__board=self).order_by('-created_at').first()

class Topic(models.Model):
    subject = models.CharField(max_length=255)
    last_updated = models.DateTimeField(auto_now_add=True)
    # ADICIONADO: on_delete=models.CASCADE
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='topics')
    #, the board field is a ForeignKey to the Board model. It is telling Django that a Topic instance relates to only one Board instance
    #The related_name parameter will be used to create a reverse relationship where the Board instances will have access a list of Topic instances that belong to it.
    starter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topics')
    views = models.PositiveIntegerField(default=0) #topico nasce com 0 views
    def __str__(self):
        return self.subject

    def get_page_count(self):
        count = self.posts.count()
        pages = count / 20
        return math.ceil(pages)

    def has_many_pages(self, count=None):
        if count is None:
            count = self.get_page_count()
        return count > 6

    def get_page_range(self):
        count = self.get_page_count()
        if self.has_many_pages(count):
            return range(1, 5)
        return range(1, count + 1)
    def get_last_ten_posts(self):
        # Puxa os posts ordenados do mais recente para o mais antigo, limitando a 10
        return self.posts.order_by('-created_at')[:10]

class Post(models.Model):
    message = models.TextField(max_length=4000)
    topic = models.ForeignKey(Topic, related_name='posts', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(User, related_name='posts', on_delete=models.CASCADE)
    updated_by = models.ForeignKey(User, null=True, related_name='+', on_delete=models.CASCADE)

    # <-- ADICIONE ESTE BLOCO NO FINAL DA CLASSE POST -->
    def get_message_as_markdown(self):
        # Versão moderna e corrigida: sem o safe_mode
        return mark_safe(markdown(self.message))
    

