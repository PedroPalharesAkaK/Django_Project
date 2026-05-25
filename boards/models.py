from django.db import models
from django.contrib.auth.models import User
from django.db.models import F
from django.utils.html import mark_safe
from markdown import markdown
import math

class Professor(models.Model): # Antigo Board
    nome = models.CharField(max_length=30, unique=True) # Antigo name
    descricao = models.CharField(max_length=100) # Antigo description

    def __str__(self):
        return self.nome

    # 1. Contagem de Comentários
    def get_comentarios_count(self):
        return Comentario.objects.filter(avaliacao__professor=self).count()

    # 2. Contagem de Avaliações
    def get_avaliacoes_count(self):
        return self.avaliacoes.count()

    # 3. Dados do Último Comentário
    def get_last_comentario(self):
        return Comentario.objects.filter(avaliacao__professor=self).order_by('-created_at').first()


class Avaliacao(models.Model): # Antigo Topic
    titulo = models.CharField(max_length=255) # Antigo subject
    last_updated = models.DateTimeField(auto_now_add=True)
    
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, related_name='avaliacoes') # Antigo board
    starter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='avaliacoes_criadas')
    views = models.PositiveIntegerField(default=0) 

    def __str__(self):
        return self.titulo

    def get_page_count(self):
        count = self.comentarios.count()
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
        
    def get_last_ten_comentarios(self):
        # Puxa os posts ordenados do mais recente para o mais antigo, limitando a 10
        return self.comentarios.order_by('-created_at')[:10]


class Comentario(models.Model): # Antigo Post
    texto = models.TextField(max_length=4000) # Antigo message
    avaliacao = models.ForeignKey(Avaliacao, related_name='comentarios', on_delete=models.CASCADE) # Antigo topic
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(User, related_name='comentarios_feitos', on_delete=models.CASCADE)
    updated_by = models.ForeignKey(User, null=True, related_name='+', on_delete=models.CASCADE)

    def get_texto_as_markdown(self):
        return mark_safe(markdown(self.texto))