from django.urls import reverse, resolve
from django.test import TestCase

# IMPORTAÇÕES ATUALIZADAS: Chamando os novos Models, Views e Forms
from ..views import new_avaliacao
from ..models import Professor, Avaliacao, Comentario
from django.contrib.auth.models import User
from ..forms import NewAvaliacaoForm


class NewAvaliacaoTests(TestCase):
    def setUp(self):
        # 1. Cria o professor em vez do board
        self.professor = Professor.objects.create(nome='Professor de Teste', descricao='Departamento de Física')
        self.username = 'john'
        self.password = '1234abcd'
        self.user = User.objects.create_user(username=self.username, email='john@doe.com', password=self.password)
        
        # 2. URL aponta para a nova rota de criação de avaliação
        self.url = reverse('new_avaliacao', kwargs={'pk': self.professor.pk})
        
        self.client.login(username=self.username, password=self.password)
        self.response = self.client.get(self.url)

    def test_new_avaliacao_view_success_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_new_avaliacao_view_not_found_status_code(self):
        # Passa um ID que não existe com certeza
        url = reverse('new_avaliacao', kwargs={'pk': self.professor.pk + 99})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_new_avaliacao_url_resolves_new_avaliacao_view(self):
        # Rota física do url dinâmica
        view = resolve(f'/professores/{self.professor.pk}/new/')
        self.assertEqual(view.func, new_avaliacao)

    def test_new_avaliacao_view_contains_link_back_to_professor_avaliacoes_view(self):
        professor_avaliacoes_url = reverse('professor_avaliacoes', kwargs={'pk': self.professor.pk})
        self.assertContains(self.response, f'href="{professor_avaliacoes_url}"')

    def test_csrf(self):
        # Verifica se o token de segurança CSRF está presente no formulário
        self.assertContains(self.response, 'csrfmiddlewaretoken')

    def test_new_avaliacao_valid_post_data(self):
        # DICIONÁRIO ATUALIZADO: Agora enviamos o pacote completo com as notas!
        data = {
            'titulo': 'Excelente didática',
            'texto': 'As aulas são muito bem estruturadas.',
            'nota_geral': 5,
            'nota_didatica': 5,
            'nota_empenho': 4,
            'nota_relacao': 5,
            'nota_dificuldade': 3
        }
        response = self.client.post(self.url, data)
        
        # Verifica se a avaliação e o comentário inicial foram criados na base de dados
        self.assertTrue(Avaliacao.objects.exists())
        self.assertTrue(Comentario.objects.exists())

    def test_new_avaliacao_invalid_post_data(self):
        '''
        Dados inválidos (vazio) não devem redirecionar.
        O comportamento esperado é mostrar o formulário novamente com status 200 e erros.
        '''
        # (Juntei os dois testes repetidos que você tinha num só, muito mais limpo!)
        response = self.client.post(self.url, {})
        form = response.context.get('form')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(form.errors)

    def test_new_avaliacao_invalid_post_data_empty_fields(self):
        '''
        Campos enviados mas vazios também devem ser rejeitados e não salvar na BD.
        '''
        data = {
            'titulo': '',
            'texto': ''
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Avaliacao.objects.exists())
        self.assertFalse(Comentario.objects.exists()) 
        
    def test_contains_form(self):
        form = self.response.context.get('form')
        self.assertIsInstance(form, NewAvaliacaoForm)


class LoginRequiredNewAvaliacaoTests(TestCase):
    def setUp(self):
        # 1. Criação do cenário de teste para utilizadores não logados
        self.professor = Professor.objects.create(nome='Django', descricao='Django Professor.')
        self.url = reverse('new_avaliacao', kwargs={'pk': self.professor.pk})
        # 2. Fazemos uma requisição sem estar logados para testar a proteção
        self.response = self.client.get(self.url)

    def test_redirection(self):
        """
        Garante que usuários não autenticados sejam redirecionados para o login
        """
        login_url = reverse('login')
        expected_url = f'{login_url}?next={self.url}'
        self.assertRedirects(self.response, expected_url)