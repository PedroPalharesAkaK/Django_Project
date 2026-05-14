from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth import views as auth_views
from django.urls import reverse, resolve  # Corrigido para Django 6
from django.test import TestCase

class PasswordChangeTests(TestCase):
    def setUp(self):
        username = 'john'
        password = 'secret123'
        self.user = User.objects.create_user(username=username, email='john@doe.com', password=password)
        self.client.login(username=username, password=password)
        url = reverse('password_change')
        self.response = self.client.get(url)

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_url_resolves_correct_view(self):
        view = resolve('/settings/password/')
        self.assertEqual(view.func.view_class, auth_views.PasswordChangeView)

    def test_csrf(self):
        self.assertContains(self.response, 'csrfmiddlewaretoken')

    def test_contains_form(self):
        form = self.response.context.get('form')
        self.assertIsInstance(form, PasswordChangeForm)

    def test_form_inputs(self):
        """
        A view deve conter quatro inputs: csrf, old_password, new_password1, new_password2
        """
        self.assertContains(self.response, '<input', 5)
        self.assertContains(self.response, 'type="password"', 3)


class LoginRequiredPasswordChangeTests(TestCase):
    def test_redirection(self):
        url = reverse('password_change')
        login_url = reverse('login')
        response = self.client.get(url)
        # O Django redireciona utilizadores não logados para a página de login
        self.assertRedirects(response, f'{login_url}?next={url}')


class PasswordChangeTestCase(TestCase):
    """
    Classe base para processamento de formulários
    """
    def create_user_and_post(self, data):
        self.user = User.objects.create_user(username='john', email='john@doe.com', password='old_password')
        self.url = reverse('password_change')
        self.client.login(username='john', password='old_password')
        return self.client.post(self.url, data)


class SuccessfulPasswordChangeTests(PasswordChangeTestCase):
    def setUp(self):
        self.response = self.create_user_and_post({
            'old_password': 'old_password',
            'new_password1': 'new_password',
            'new_password2': 'new_password',
        })

    def test_redirection(self):
        self.assertRedirects(self.response, reverse('password_change_done'))

    def test_password_changed(self):
        self.user.refresh_from_db()  # Atualiza os dados do banco [cite: 6]
        self.assertTrue(self.user.check_password('new_password'))

    def test_user_authentication(self):
        """
        Verifica se o utilizador continua autenticado após mudar a senha
        """
        response = self.client.get(reverse('home'))
        user = response.context.get('user')
        self.assertTrue(user.is_authenticated)


class InvalidPasswordChangeTests(PasswordChangeTestCase):
    def setUp(self):
        self.response = self.create_user_and_post({
            'old_password': 'wrong_password',
            'new_password1': 'new_password',
            'new_password2': 'mismatch_password',
        })

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_form_errors(self):
        form = self.response.context.get('form')
        self.assertTrue(form.errors)

    def test_didnt_change_password(self):
        self.user.refresh_from_db()  # Garante que temos os dados mais recentes [cite: 10]
        self.assertTrue(self.user.check_password('old_password'))