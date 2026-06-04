from django.urls import reverse, resolve
from django.test import TestCase
from django.contrib.auth.models import User
from django.core import mail # NOVO IMPORT: Ferramenta de testes de e-mail do Django
from ..views import signup
from ..forms import SignUpForm

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
        # Atualizado para garantir que estamos usando o seu form customizado
        self.assertIsInstance(form, SignUpForm) 
        
    def test_form_inputs(self):
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

    def test_redirection_and_template(self):
        # Agora o status deve ser 200 (sucesso) e renderizar a tela de aviso de e-mail
        self.assertEqual(self.response.status_code, 200)
        self.assertTemplateUsed(self.response, 'email_confirmation_sent.html')

    def test_user_creation_is_inactive(self):
        # Verifica se foi criado, mas exige que a conta esteja "congelada" (is_active=False)
        self.assertTrue(User.objects.filter(username='john').exists())
        user = User.objects.get(username='john')
        self.assertFalse(user.is_active)

    def test_user_not_authenticated(self):
        # O usuário NÃO deve estar logado no sistema ainda
        from django.contrib.auth import get_user
        user = get_user(self.client)
        self.assertFalse(user.is_authenticated)

    def test_email_sent(self):
        # Verifica se o Django gerou e colocou exatamente 1 e-mail na caixa de saída
        self.assertEqual(len(mail.outbox), 1)
        # Verifica se o destinatário e o assunto estão corretos
        self.assertEqual(mail.outbox[0].to, ['john@doe.com'])
        self.assertEqual(mail.outbox[0].subject, 'Ative a sua conta no Avalia Professor')

class InvalidSignUpTests(TestCase):
    def setUp(self):
        url = reverse('signup')
        self.response = self.client.post(url, {})

    def test_signup_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_form_errors(self):
        form = self.response.context.get('form')
        self.assertTrue(form.errors)

    def test_dont_create_user(self):
        self.assertFalse(User.objects.exists())