from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import resolve, reverse

# 1. IMPORTAÇÕES ATUALIZADAS: Trazendo os novos Modelos e a Class-Based View correta
from ..models import Professor, Avaliacao, Comentario
from ..views import ComentarioListView 

class AvaliacaoComentariosTests(TestCase):
    def setUp(self):
        # 2. SETUP DINÂMICO: Guardando o professor, a avaliação e o comentário em variáveis 'self.' 
        self.professor = Professor.objects.create(nome='Professor de Teste', descricao='Instituto de Física')
        self.user = User.objects.create_user(username='john', email='john@doe.com', password='123')
        
        # O 'subject' passa a 'titulo' e 'board' passa a 'professor'
        self.avaliacao = Avaliacao.objects.create(titulo='Didática excelente', professor=self.professor, starter=self.user)
        # A 'message' passa a 'texto' e 'topic' passa a 'avaliacao'
        self.comentario = Comentario.objects.create(texto='Concordo com os pontos apresentados.', avaliacao=self.avaliacao, created_by=self.user)
        
        # 3. URL DINÂMICA: Usando as chaves (PKs) reais da base de dados de testes
        self.url = reverse('avaliacao_comentarios', kwargs={'pk': self.professor.pk, 'avaliacao_pk': self.avaliacao.pk})
        self.response = self.client.get(self.url)

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_view_class(self):
        # 4. RESOLVE ATUALIZADO: Rota correspondente à listagem de comentários
        view = resolve(f'/professores/{self.professor.pk}/avaliacoes/{self.avaliacao.pk}/')
        # Validamos se o Django está a direcionar para a nossa nova ComentarioListView!
        self.assertEqual(view.func.view_class, ComentarioListView)

    def test_contains_navigation_links(self):
        # 5. LINKS DE NAVEGAÇÃO: Garantir que as migalhas de pão (breadcrumb) funcionam
        homepage_url = reverse('home')
        professor_avaliacoes_url = reverse('professor_avaliacoes', kwargs={'pk': self.professor.pk})
        
        # Verifica se o HTML contém os links corretos de volta para a Home e para o Perfil do Professor
        self.assertContains(self.response, f'href="{homepage_url}"')
        self.assertContains(self.response, f'href="{professor_avaliacoes_url}"')