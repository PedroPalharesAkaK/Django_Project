from django.urls import reverse, resolve
from django.test import TestCase
from ..views import home, board_topics, new_topic
from ..models import Board, Topic, Post
from django.contrib.auth.models import User
from ..forms import NewTopicForm


class NewTopicTests(TestCase):
    def setUp(self):
        # Cria um Board de teste para ser usado em todos os métodos abaixo
        Board.objects.create(name='Django', description='Django board.')

    def test_new_topic_view_success_status_code(self):
        url = reverse('new_topic', kwargs={'pk': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_new_topic_view_not_found_status_code(self):
        url = reverse('new_topic', kwargs={'pk': 99})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_new_topic_url_resolves_new_topic_view(self):
        view = resolve('/boards/1/new/')
        self.assertEqual(view.func, new_topic)

    def test_new_topic_view_contains_link_back_to_board_topics_view(self):
        new_topic_url = reverse('new_topic', kwargs={'pk': 1})
        board_topics_url = reverse('board_topics', kwargs={'pk': 1})
        response = self.client.get(new_topic_url)
        # Usando f-string em vez de .format() para um código mais limpo
        self.assertContains(response, f'href="{board_topics_url}"')
    def setUp(self):
        # Cria um board e um usuário para os testes
        Board.objects.create(name='Django', description='Django board.')
        User.objects.create_user(username='john', email='john@doe.com', password='123')

    def test_csrf(self):
        url = reverse('new_topic', kwargs={'pk': 1})
        response = self.client.get(url)
        # Verifica se o token de segurança CSRF está presente no formulário
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_new_topic_valid_post_data(self):
        url = reverse('new_topic', kwargs={'pk': 1})
        data = {
            'subject': 'Test title',
            'message': 'Lorem ipsum dolor sit amet'
        }
        response = self.client.post(url, data)
        # Verifica se o tópico e o post foram criados no banco
        self.assertTrue(Topic.objects.exists())
        self.assertTrue(Post.objects.exists())

    def test_new_topic_invalid_post_data(self):
        '''
        Dados inválidos (vazio) não devem redirecionar.
        O comportamento esperado é mostrar o formulário novamente com status 200.
        '''
        url = reverse('new_topic', kwargs={'pk': 1})
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 200)
    def test_new_topic_invalid_post_data_empty_fields(self):
        '''
        Campos enviados mas vazios também devem ser rejeitados.
        '''
        url = reverse('new_topic', kwargs={'pk': 1})
        data = {
            'subject': '',
            'message': ''
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Topic.objects.exists())
        self.assertFalse(Post.objects.exists()) 
        
    def test_contains_form(self):
        url = reverse('new_topic', kwargs={'pk': 1})
        response = self.client.get(url)
        form = response.context.get('form')
        self.assertIsInstance(form, NewTopicForm)
    def test_new_topic_invalid_post_data(self):
        url = reverse('new_topic', kwargs={'pk': 1})
        response = self.client.post(url, {})
        form = response.context.get('form')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(form.errors)
    

class LoginRequiredNewTopicTests(TestCase):
    def setUp(self):
        # 1. Criação do cenário de teste
        Board.objects.create(name='Django', description='Django board.')
        self.url = reverse('new_topic', kwargs={'pk': 1})
        # 2. Fazemos uma requisição sem estar logados para testar a proteção
        self.response = self.client.get(self.url)

    def test_redirection(self):
        """
        Garante que usuários não autenticados sejam redirecionados para o login
        """
        login_url = reverse('login')
        # 3. No Django 6, prefira f-strings para construir a URL de redirecionamento
        expected_url = f'{login_url}?next={self.url}'
        self.assertRedirects(self.response, expected_url)
    