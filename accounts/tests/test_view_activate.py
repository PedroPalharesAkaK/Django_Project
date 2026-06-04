from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

class ActivateAccountTests(TestCase):
    def setUp(self):
        # 1. Cria um usuário "congelado" para o teste
        self.user = User.objects.create_user(
            username='alunoteste',
            email='alunoteste@usp.br',
            password='senha_forte123'
        )
        self.user.is_active = False
        self.user.save()

        # 2. Gera o UID e o Token válidos (exatamente como a sua View faz)
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)

    def test_activation_success(self):
        # Cenário 1: Link perfeito
        url = reverse('activate', kwargs={'uidb64': self.uid, 'token': self.token})
        response = self.client.get(url)

        # Verifica se carregou a página de sucesso
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'email_confirmed.html')

        # Recarrega o usuário do banco de dados e verifica se a conta foi ativada
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        
        # Verifica se o Django fez o login automático após a confirmação
        from django.contrib.auth import get_user
        logged_user = get_user(self.client)
        self.assertTrue(logged_user.is_authenticated)

    def test_activation_invalid_token(self):
        # Cenário 2: Token falso ou expirado
        url = reverse('activate', kwargs={'uidb64': self.uid, 'token': 'token-falso-123'})
        response = self.client.get(url)

        # Verifica se carregou a página de erro
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'email_confirmation_invalid.html')

        # Garante que o usuário continua bloqueado (is_active=False)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_activation_invalid_uid(self):
        # Cenário 3: ID de usuário alterado/forjado (ex: 'MTIz' é '123' em base64)
        url = reverse('activate', kwargs={'uidb64': 'MTIz', 'token': self.token})
        response = self.client.get(url)

        # Deve barrar do mesmo jeito
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'email_confirmation_invalid.html')