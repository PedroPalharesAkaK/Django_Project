from django.test import TestCase
from django.contrib.auth import authenticate
from django.contrib.auth.models import User


class EmailOrUsernameBackendTests(TestCase):
    """Testa o backend accounts.backends.EmailOrUsernameModelBackend."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='alunoteste',
            email='aluno@usp.br',
            password='senha_forte_123'
        )

    def test_autentica_com_username(self):
        user = authenticate(username='alunoteste', password='senha_forte_123')
        self.assertEqual(user, self.user)

    def test_autentica_com_email(self):
        user = authenticate(username='aluno@usp.br', password='senha_forte_123')
        self.assertEqual(user, self.user)

    def test_autentica_com_email_ignora_maiusculas_minusculas(self):
        user = authenticate(username='ALUNO@usp.br', password='senha_forte_123')
        self.assertEqual(user, self.user)

    def test_senha_errada_nao_autentica(self):
        user = authenticate(username='aluno@usp.br', password='senha_errada')
        self.assertIsNone(user)

    def test_email_inexistente_nao_autentica(self):
        user = authenticate(username='ninguem@usp.br', password='senha_forte_123')
        self.assertIsNone(user)

    def test_usuario_inativo_nao_autentica(self):
        self.user.is_active = False
        self.user.save()
        user = authenticate(username='aluno@usp.br', password='senha_forte_123')
        self.assertIsNone(user)

    def test_email_duplicado_nao_autentica_ninguem(self):
        """
        Se duas contas (criadas antes da validação existir, ou via admin)
        compartilham o mesmo e-mail, o login por e-mail deve falhar de forma
        segura em vez de logar arbitrariamente numa das duas.
        """
        User.objects.create_user(
            username='outroaluno',
            email='aluno@usp.br',
            password='outra_senha_123'
        )
        user = authenticate(username='aluno@usp.br', password='senha_forte_123')
        self.assertIsNone(user)
        user = authenticate(username='aluno@usp.br', password='outra_senha_123')
        self.assertIsNone(user)
