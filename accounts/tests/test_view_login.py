from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from ..forms import EmailOrUsernameAuthenticationForm


class LoginViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alunoteste',
            email='aluno@usp.br',
            password='senha_forte_123'
        )
        self.url = reverse('login')

    def test_login_usa_form_customizado(self):
        response = self.client.get(self.url)
        self.assertIsInstance(response.context.get('form'), EmailOrUsernameAuthenticationForm)

    def test_rotulo_do_campo_menciona_email(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Usuário ou e-mail')

    def test_login_com_username(self):
        response = self.client.post(self.url, {
            'username': 'alunoteste',
            'password': 'senha_forte_123',
        })
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_com_email(self):
        response = self.client.post(self.url, {
            'username': 'aluno@usp.br',
            'password': 'senha_forte_123',
        })
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_com_senha_errada_nao_autentica(self):
        response = self.client.post(self.url, {
            'username': 'aluno@usp.br',
            'password': 'senha_errada',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
