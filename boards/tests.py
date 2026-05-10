from django.urls import reverse, resolve
from django.test import TestCase
from .views import home, board_topics
from .models import Board

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

class BoardTopicsTests(TestCase):
    def setUp(self):
        # Cria um board para os testes
        Board.objects.create(name='Django', description='Django board.')

    def test_board_topics_view_success_status_code(self):
        url = reverse('board_topics', kwargs={'pk': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_board_topics_view_not_found_status_code(self):
        url = reverse('board_topics', kwargs={'pk': 99})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_board_topics_url_resolves_board_topics_view(self):
        view = resolve('/boards/1/')
        self.assertEqual(view.func, board_topics)

    def test_board_topics_view_contains_link_back_to_homepage(self):
        board_topics_url = reverse('board_topics', kwargs={'pk': 1})
        response = self.client.get(board_topics_url)
        homepage_url = reverse('home')
        # Usando f-string em vez de .format()
        self.assertContains(response, f'href="{homepage_url}"')