from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import resolve, reverse

# 1. IMPORTAÇÕES ATUALIZADAS: Substituindo Board, Post, Topic por Professor, Avaliacao, Comentario
from ..models import Professor, Avaliacao, Comentario
from ..views import reply_avaliacao
from ..forms import ComentarioForm

class ReplyAvaliacaoTestCase(TestCase):
    """
    Classe base que configura o cenário de testes para a view `reply_avaliacao`.
    Todas as outras classes herdam estes dados automaticamente.
    """
    def setUp(self):
        # 2. SETUP ATUALIZADO: Criação do professor do Instituto de Física e da sua avaliação
        self.professor = Professor.objects.create(nome='Professor de Teste', descricao='Instituto de Física')
        self.username = 'john'
        self.password = '123'
        self.user = User.objects.create_user(username=self.username, email='john@doe.com', password=self.password)
        
        self.avaliacao = Avaliacao.objects.create(titulo='Avaliação do Semestre', professor=self.professor, starter=self.user)
        Comentario.objects.create(texto='Comentário inicial estruturado', avaliacao=self.avaliacao, created_by=self.user)
        
        # 3. ROTA ATUALIZADA
        self.url = reverse('reply_avaliacao', kwargs={'pk': self.professor.pk, 'avaliacao_pk': self.avaliacao.pk})


class LoginRequiredReplyAvaliacaoTests(ReplyAvaliacaoTestCase):
    """
    Testa se utilizadores anónimos são barrados e redirecionados para a página de login.
    """
    def test_redirection(self):
        login_url = reverse('login')
        expected_url = f'{login_url}?next={self.url}'
        response = self.client.get(self.url)
        self.assertRedirects(response, expected_url)


class ReplyAvaliacaoTests(ReplyAvaliacaoTestCase):
    """
    Testa acessos básicos de um utilizador devidamente logado.
    """
    def setUp(self):
        super().setUp()
        # Efetua o login para permitir o acesso à view protegida
        self.client.login(username=self.username, password=self.password)
        self.response = self.client.get(self.url)

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_view_function(self):
        # 4. RESOLVE ATUALIZADO: URL física aponta agora para a secção de professores
        view = resolve(f'/professores/{self.professor.pk}/avaliacoes/{self.avaliacao.pk}/reply/')
        self.assertEqual(view.func, reply_avaliacao)

    def test_csrf(self):
        self.assertContains(self.response, 'csrfmiddlewaretoken')

    def test_contains_form(self):
        form = self.response.context.get('form')
        self.assertIsInstance(form, ComentarioForm)


class SuccessfulReplyAvaliacaoTests(ReplyAvaliacaoTestCase):
    """
    Testa o envio de dados válidos através do formulário de resposta.
    """
    def setUp(self):
        super().setUp()
        self.client.login(username=self.username, password=self.password)
        # 5. POST ATUALIZADO: Usando a chave 'texto' em vez de 'message'
        self.response = self.client.post(self.url, {'texto': 'Concordo plenamente com esta perspetiva!'})

    def test_redirection(self):
        '''
        Uma submissão válida deve redirecionar o utilizador 
        para a view avaliacao_comentarios, na última página, 
        e fixar a âncora no comentário recém-criado usando o ID real.
        '''
        url = reverse('avaliacao_comentarios', kwargs={'pk': self.professor.pk, 'avaliacao_pk': self.avaliacao.pk})
        
        # BUSCA DINÂMICA: Vai ao banco de dados e pega o último comentário criado
        novo_comentario = Comentario.objects.last()
        
        # Monta a URL injetando a Chave Primária (pk) real que o banco gerou
        expected_url = f"{url}?page=1#{novo_comentario.pk}" 
        
        self.assertRedirects(self.response, expected_url)

    def test_reply_created(self):
        """
        A base de dados deve agora conter 2 comentários (o original do setUp e o novo enviado pelo POST).
        """
        self.assertEqual(Comentario.objects.count(), 2)


class InvalidReplyAvaliacaoTests(ReplyAvaliacaoTestCase):
    """
    Testa o envio de dados inválidos (como um campo de texto vazio).
    """
    def setUp(self):
        super().setUp()
        self.client.login(username=self.username, password=self.password)
        # Envia um POST com o 'texto' vazio para forçar o erro
        self.response = self.client.post(self.url, {'texto': ''})

    def test_status_code(self):
        """
        Dados inválidos não devem redirecionar (302). Devem retornar 200 para exibir os erros.
        """
        self.assertEqual(self.response.status_code, 200)

    def test_form_errors(self):
        form = self.response.context.get('form')
        self.assertTrue(form.errors)

    def test_reply_not_created(self):
        """
        Como o formulário era inválido, nenhum comentário novo deve ter sido inserido na base de dados.
        """
        self.assertEqual(Comentario.objects.count(), 1)