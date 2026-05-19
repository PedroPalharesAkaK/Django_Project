from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import resolve, reverse
from ..models import Board, Post, Topic
from ..views import reply_topic
from ..forms import PostForm

class ReplyTopicTestCase(TestCase):
    """
    Classe base que configura o cenário de testes para a view `reply_topic`.
    Todas as outras classes herdam estes dados automaticamente.
    """
    def setUp(self):
        self.board = Board.objects.create(name='Django', description='Django board.')
        self.username = 'john'
        self.password = '123'
        self.user = User.objects.create_user(username=self.username, email='john@doe.com', password=self.password)
        self.topic = Topic.objects.create(subject='Hello, world', board=self.board, starter=self.user)
        Post.objects.create(message='Lorem ipsum dolor sit amet', topic=self.topic, created_by=self.user)
        self.url = reverse('reply_topic', kwargs={'pk': self.board.pk, 'topic_pk': self.topic.pk})


class LoginRequiredReplyTopicTests(ReplyTopicTestCase):
    """
    Testa se usuários anônimos são barrados e redirecionados para a página de login.
    """
    def test_redirection(self):
        login_url = reverse('login')
        expected_url = f'{login_url}?next={self.url}'
        response = self.client.get(self.url)
        self.assertRedirects(response, expected_url)


class ReplyTopicTests(ReplyTopicTestCase):
    """
    Testas acessos básicos de um usuário devidamente logado.
    """
    def setUp(self):
        super().setUp()
        # Efetua o login para permitir o acesso à view protegida
        self.client.login(username=self.username, password=self.password)
        self.response = self.client.get(self.url)

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_view_function(self):
        view = resolve(f'/boards/{self.board.pk}/topics/{self.topic.pk}/reply/')
        self.assertEqual(view.func, reply_topic)

    def test_csrf(self):
        self.assertContains(self.response, 'csrfmiddlewaretoken')

    def test_contains_form(self):
        form = self.response.context.get('form')
        self.assertIsInstance(form, PostForm)


class SuccessfulReplyTopicTests(ReplyTopicTestCase):
    """
    Testa o envio de dados válidos através do formulário de resposta.
    """
    def setUp(self):
        super().setUp()
        self.client.login(username=self.username, password=self.password)
        # Envia um POST com uma mensagem válida
        self.response = self.client.post(self.url, {'message': 'hello world!'})

    def test_redirection(self):
        '''
        A valid form submission should redirect the user 
        to the topic_posts view, to the last page, 
        and anchor to the newly created post.
        '''
        # 1. Gera a URL base usando o reverse
        url = reverse('topic_posts', kwargs={'pk': self.board.pk, 'topic_pk': self.topic.pk})
        
        # 2. Constrói a URL esperada exatamente como na view
        # Nota: assumindo que o novo post é o segundo (ID 2), como sugere o exemplo da imagem
        expected_url = f"{url}?page=1#2" 
        
        # 3. Verifica se o redirecionamento aponta para esta URL específica
        self.assertRedirects(self.response, expected_url)

    def test_reply_created(self):
        """
        O banco de dados deve agora conter 2 posts (o original do setUp e o novo enviado pelo POST).
        """
        self.assertEqual(Post.objects.count(), 2)


class InvalidReplyTopicTests(ReplyTopicTestCase):
    """
    Testa o envio de dados inválidos (como um campo de texto vazio).
    """
    def setUp(self):
        super().setUp()
        self.client.login(username=self.username, password=self.password)
        # Envia um POST vazio para forçar o erro de validação
        self.response = self.client.post(self.url, {'message': ''})

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
        Como o formulário era inválido, nenhum post novo deve ter sido inserido no banco.
        """
        self.assertEqual(Post.objects.count(), 1)