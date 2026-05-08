from django.urls import reverse, resolve
from django.test import TestCase
from .views import home, board_topics
from .models import Board

class HomeTests(TestCase):
    # Teste 1: Verifica se a página carrega com sucesso (Código 200)
    def test_home_view_status_code(self):
        url = reverse('home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    # Teste 2: Verifica se o link '/' chama a função 'home' correta
    def test_home_url_resolves_home_view(self):
        view = resolve('/')
        self.assertEqual(view.func, home)

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