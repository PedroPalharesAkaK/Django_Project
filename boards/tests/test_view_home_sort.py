from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Professor, Avaliacao

class HomeSortTests(TestCase):
    def setUp(self):
        # 1. Cria um utilizador base para ser o "dono" das avaliações
        self.user = User.objects.create_user(username='testuser', password='123')

        # 2. Cria a Zélia (Muitas views, 0 avaliações, última no alfabeto)
        self.prof_zelia = Professor.objects.create(nome='Zélia', visualizacoes=100)

        # 3. Cria a Ana (Poucas views, 1 avaliação média, primeira no alfabeto)
        self.prof_ana = Professor.objects.create(nome='Ana', visualizacoes=10)
        Avaliacao.objects.create(
            titulo='Mediana', nota_geral=3, nota_didatica=3, nota_empenho=3, 
            nota_relacao=3, nota_dificuldade=3, professor=self.prof_ana, starter=self.user
        )

        # 4. Cria o Carlos (Views médias, 2 avaliações ótimas, meio do alfabeto)
        self.prof_carlos = Professor.objects.create(nome='Carlos', visualizacoes=50)
        Avaliacao.objects.create(
            titulo='Ótimo', nota_geral=5, nota_didatica=5, nota_empenho=5, 
            nota_relacao=5, nota_dificuldade=5, professor=self.prof_carlos, starter=self.user
        )
        Avaliacao.objects.create(
            titulo='Incrível', nota_geral=5, nota_didatica=5, nota_empenho=5, 
            nota_relacao=5, nota_dificuldade=5, professor=self.prof_carlos, starter=self.user
        )

        self.url = reverse('home')

    def test_sort_default_alfabetico(self):
        """Se o utilizador não clicar em nada, deve vir em ordem alfabética."""
        response = self.client.get(self.url)
        professores = list(response.context.get('professors'))
        
        self.assertEqual(professores, [self.prof_ana, self.prof_carlos, self.prof_zelia])

    def test_sort_visualizacoes(self):
        """Filtro de visualizações deve trazer a Zélia em primeiro."""
        response = self.client.get(f"{self.url}?sort=visualizacoes")
        professores = list(response.context.get('professors'))
        
        self.assertEqual(professores, [self.prof_zelia, self.prof_carlos, self.prof_ana])

    def test_sort_avaliacoes_quantidade(self):
        """Filtro de total de avaliações deve trazer o Carlos (2), Ana (1), Zélia (0)."""
        response = self.client.get(f"{self.url}?sort=avaliacoes")
        professores = list(response.context.get('professors'))
        
        self.assertEqual(professores, [self.prof_carlos, self.prof_ana, self.prof_zelia])

    def test_sort_maior_nota(self):
        """
        Filtro de nota. O Carlos tem média 5.0, a Ana tem 3.0.
        A Zélia não tem nota (NULL), por isso o nosso 'nulls_last=True'
        tem de garantir que ela seja empurrada para o final da lista.
        """
        response = self.client.get(f"{self.url}?sort=nota")
        professores = list(response.context.get('professors'))
        
        self.assertEqual(professores, [self.prof_carlos, self.prof_ana, self.prof_zelia])