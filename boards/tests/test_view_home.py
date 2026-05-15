from django.urls import reverse, resolve
from django.test import TestCase
from ..views import home, board_topics, new_topic
from ..models import Board, Topic, Post
from django.contrib.auth.models import User
from ..forms import NewTopicForm

class HomeTests(TestCase):
    def setUp(self):
        # Cria um board de teste para garantir que a home tenha o que listar
        self.board = Board.objects.create(name='Django', description='Django board.')
        url = reverse('home')
        self.response = self.client.get(url)

    def test_home_view_status_code(self):
        # Verifica se a página carrega (Status 200)
        self.assertEqual(self.response.status_code, 200)

    def test_home_url_resolves_home_view(self):
        # Verifica se a URL '/' chama a função 'home'
        view = resolve('/')
        self.assertEqual(view.func, home)

    def test_home_view_contains_link_to_topics_page(self):
        # Verifica se o link para os tópicos do board específico está no HTML
        board_topics_url = reverse('board_topics', kwargs={'pk': self.board.pk})
        self.assertContains(self.response, f'href="{board_topics_url}"')




    
    
    