from django.test import TestCase
from django.contrib.auth.models import User
from ..forms import UserUpdateForm


class UserUpdateFormUniqueEmailTest(TestCase):
    """Garante que editar o perfil não permite roubar o e-mail de outra conta."""

    def setUp(self):
        self.outro_usuario = User.objects.create_user(
            username='outroaluno',
            email='ocupado@usp.br',
            password='senha_forte_123'
        )
        self.usuario = User.objects.create_user(
            username='meuusuario',
            email='meu@usp.br',
            password='senha_forte_123'
        )

    def test_rejeita_trocar_para_email_de_outra_conta(self):
        form = UserUpdateForm(
            data={'first_name': '', 'last_name': '', 'email': 'ocupado@usp.br'},
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_rejeita_ignorando_maiusculas_minusculas(self):
        form = UserUpdateForm(
            data={'first_name': '', 'last_name': '', 'email': 'OCUPADO@usp.br'},
            instance=self.usuario
        )
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_permite_manter_o_proprio_email(self):
        form = UserUpdateForm(
            data={'first_name': 'Nome', 'last_name': '', 'email': 'meu@usp.br'},
            instance=self.usuario
        )
        self.assertTrue(form.is_valid())

    def test_permite_trocar_para_email_novo(self):
        form = UserUpdateForm(
            data={'first_name': '', 'last_name': '', 'email': 'novo@usp.br'},
            instance=self.usuario
        )
        self.assertTrue(form.is_valid())
