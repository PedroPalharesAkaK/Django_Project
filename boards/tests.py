from django.urls import reverse, resolve  # Ambos vêm de django.urls agora
from django.test import TestCase
from .views import home

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