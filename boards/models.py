from django.db import models
from django.contrib.auth.models import User
from django.db.models import F
from django.utils.html import mark_safe
from markdown import markdown
import math
from django.db.models import Avg

# IMPORTANTE: Importamos os validadores para garantir que a nota não passa de 5 nem desce de 0
from django.core.validators import MinValueValidator, MaxValueValidator

class Universidade(models.Model):
    nome = models.CharField(max_length=150, unique=True)
    sigla = models.CharField(max_length=15, unique=True) # Ex: USP, UNICAMP

    def __str__(self):
        return self.sigla

class Instituto(models.Model):
    nome = models.CharField(max_length=150) # Ex: Instituto de Física
    sigla = models.CharField(max_length=15) # Ex: IFUSP
    
    universidade = models.ForeignKey(Universidade, on_delete=models.CASCADE, related_name='institutos')

    def __str__(self):
        return self.sigla

class Professor(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.CharField(max_length=100)
    
    biografia = models.TextField(max_length=2000, blank=True, null=True) 
    
    foto_url = models.URLField(max_length=500, blank=True, null=True)
    universidade = models.ForeignKey(Universidade, on_delete=models.SET_NULL, null=True, blank=True, related_name='professores')
    instituto = models.ForeignKey(Instituto, on_delete=models.SET_NULL, null=True, blank=True, related_name='professores')
    visualizacoes = models.PositiveIntegerField(default=0)
    

    def __str__(self):
        return self.nome

    def get_comentarios_count(self):
        return Comentario.objects.filter(avaliacao__professor=self).count()

    def get_avaliacoes_count(self):
        return self.avaliacoes.count()

    def get_last_comentario(self):
        return Comentario.objects.filter(avaliacao__professor=self).order_by('-created_at').first()
    # Certifique-se de que este import está no topo do seu models.py

    def _get_avg(self, field_name):
        """Método auxiliar interno para calcular a média de um quesito"""
        avg = self.avaliacoes.aggregate(Avg(field_name))[f'{field_name}__avg']
        return round(avg, 1) if avg else 0

    # Métodos que devolvem a nota decimal (Ex: 4.3)
    def get_media_geral(self): return self._get_avg('nota_geral')
    def get_media_didatica(self): return self._get_avg('nota_didatica')
    def get_media_empenho(self): return self._get_avg('nota_empenho')
    def get_media_relacao(self): return self._get_avg('nota_relacao')
    def get_media_dificuldade(self): return self._get_avg('nota_dificuldade')

    # Métodos que convertem a nota em percentagem para preencher a barra de progresso (0 a 100%)
    # Métodos que convertem a nota em percentagem para preencher a barra de progresso (0 a 100%)
    def get_percent_geral(self): 
        return int((self.get_media_geral() / 5) * 100)
        
    def get_percent_didatica(self): 
        return int((self.get_media_didatica() / 5) * 100)
        
    def get_percent_empenho(self): 
        return int((self.get_media_empenho() / 5) * 100)
        
    def get_percent_relacao(self): 
        return int((self.get_media_relacao() / 5) * 100)
        
    def get_percent_dificuldade(self): 
        return int((self.get_media_dificuldade() / 5) * 100)


class Avaliacao(models.Model):
    titulo = models.CharField(max_length=255)
    last_updated = models.DateTimeField(auto_now_add=True)
    
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, related_name='avaliacoes')
    starter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='avaliacoes_criadas')
    views = models.PositiveIntegerField(default=0) 

    # NOVOS CAMPOS DE NOTAS (De 0 a 5)
    # Colocamos default=0 para que as avaliações antigas não quebrem a base de dados
    nota_geral = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    nota_didatica = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    nota_empenho = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    nota_relacao = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    nota_dificuldade = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])

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
        return self.comentarios.order_by('-created_at')[:10]


class Comentario(models.Model):
    texto = models.TextField(max_length=4000)
    avaliacao = models.ForeignKey(Avaliacao, related_name='comentarios', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(User, related_name='comentarios_feitos', on_delete=models.CASCADE)
    updated_by = models.ForeignKey(User, null=True, related_name='+', on_delete=models.CASCADE)

    def get_texto_as_markdown(self):
        return mark_safe(markdown(self.texto))
    

class Contato(models.Model):
    nome = models.CharField(max_length=100)
    sobrenome = models.CharField(max_length=100)
    email = models.EmailField()
    mensagem = models.TextField(max_length=2000)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mensagem de {self.nome} - {self.email}"