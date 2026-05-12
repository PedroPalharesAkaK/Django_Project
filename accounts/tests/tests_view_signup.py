from django.urls import reverse, resolve
from django.test import TestCase
from django.contrib.auth.forms import UserCreationForm
from ..views import signup #.. é tipo cd .. ; voltar uma pasta
from ..forms import SignUpForm
from django.contrib.auth.models import User


class SignUpTests(TestCase):
    def setUp(self):
        url = reverse('signup')
        self.response = self.client.get(url)

    def test_signup_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_signup_url_resolves_signup_view(self):
        view = resolve('/signup/')
        self.assertEqual(view.func, signup)

    def test_csrf(self):
        self.assertContains(self.response, 'csrfmiddlewaretoken')

    def test_contains_form(self):
        form = self.response.context.get('form')
        self.assertIsInstance(form, UserCreationForm)
    def test_form_inputs(self):
        '''
        The view must contain five inputs: csrf, username, email,
        password1, password2
        '''
        self.assertContains(self.response, '<input', 5)
        self.assertContains(self.response, 'type="text"', 1)
        self.assertContains(self.response, 'type="email"', 1)
        self.assertContains(self.response, 'type="password"', 2)

class SuccessfulSignUpTests(TestCase):
    def setUp(self):
        url = reverse('signup')
        self.data = {
            'username': 'john',
            'email': 'john@doe.com',
            'password1': 'abcdef123456',
            'password2': 'abcdef123456'
        }
        self.response = self.client.post(url, self.data)
        self.home_url = reverse('home')

    def test_redirection(self):
        # Verifica se o cadastro redireciona corretamente para a home
        self.assertRedirects(self.response, self.home_url)

    def test_user_creation(self):
        # Verifica se o usuário foi realmente criado no banco de dados
        self.assertTrue(User.objects.filter(username='john').exists())

    def test_user_authentication(self):
        # Verifica se o usuário recém-criado já está logado na sessão
        # Usamos o client do próprio teste para checar o ID da sessão
        from django.contrib.auth import get_user
        user = get_user(self.client)
        self.assertTrue(user.is_authenticated)

class InvalidSignUpTests(TestCase):
    def setUp(self):
        url = reverse('signup')
        # Simulando o envio de um formulário vazio
        self.response = self.client.post(url, {})

    def test_signup_status_code(self):
        # Deve recarregar a mesma página (200)
        self.assertEqual(self.response.status_code, 200)

    def test_form_errors(self):
        form = self.response.context.get('form')
        self.assertTrue(form.errors)

    def test_dont_create_user(self):
        # Garante que o banco de dados continua vazio
        self.assertFalse(User.objects.exists())