from django.test import TestCase
from django.contrib.auth.models import User
from ..forms import SignUpForm

class SignUpFormTest(TestCase):
    def test_form_has_fields(self):
        form = SignUpForm()
        expected = ['username', 'email', 'password1', 'password2',]
        actual = list(form.fields)
        self.assertSequenceEqual(expected, actual)


class SignUpFormUniqueEmailTest(TestCase):
    """Garante que não é possível existir mais de uma conta com o mesmo e-mail."""

    def setUp(self):
        User.objects.create_user(
            username='jasexistente',
            email='ocupado@usp.br',
            password='senha_forte_123'
        )
        self.dados_validos = {
            'username': 'novoaluno',
            'password1': 'abcdef123456',
            'password2': 'abcdef123456',
        }

    def test_rejeita_email_ja_cadastrado(self):
        form = SignUpForm(data={**self.dados_validos, 'email': 'ocupado@usp.br'})
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_rejeita_email_ja_cadastrado_ignorando_maiusculas(self):
        form = SignUpForm(data={**self.dados_validos, 'email': 'OCUPADO@usp.br'})
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_aceita_email_novo(self):
        form = SignUpForm(data={**self.dados_validos, 'email': 'livre@usp.br'})
        self.assertTrue(form.is_valid())