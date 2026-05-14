from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core import mail
from django.urls import reverse, resolve  # 1. Importação corrigida
from django.test import TestCase

class PasswordResetTests(TestCase):
    def setUp(self):
        url = reverse('password_reset')
        self.response = self.client.get(url)

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_view_function(self):
        view = resolve('/reset/')
        # 2. Verificação de CBVs atualizada
        self.assertEqual(view.func.view_class, auth_views.PasswordResetView)

    def test_csrf(self):
        self.assertContains(self.response, 'csrfmiddlewaretoken')

    def test_contains_form(self):
        form = self.response.context.get('form')
        self.assertIsInstance(form, PasswordResetForm)

    def test_form_inputs(self):
        """
        A view deve conter dois inputs: csrf e email
        """
        self.assertContains(self.response, '<input', 2)
        self.assertContains(self.response, 'type="email"', 1)


class SuccessfulPasswordResetTests(TestCase):
    def setUp(self):
        self.email = 'john@doe.com'
        User.objects.create_user(username='john', email=self.email, password='123abcdef')
        self.url = reverse('password_reset')
        self.response = self.client.post(self.url, {'email': self.email})

    def test_redirection(self):
        """
        Um envio válido deve redirecionar para password_reset_done
        """
        # 3. No Django 6, o redirecionamento é padrão para segurança
        url = reverse('password_reset_done')
        self.assertRedirects(self.response, url)

    def test_send_password_reset_email(self):
        # Verifica se o e-mail foi "enviado" para a caixa de saída (mail.outbox)
        self.assertEqual(1, len(mail.outbox))


class InvalidPasswordResetTests(TestCase):
    def setUp(self):
        url = reverse('password_reset')
        # E-mail que não existe no banco de dados
        self.response = self.client.post(url, {'email': 'donotexist@email.com'})

    def test_redirection(self):
        """
        Mesmo e-mails inexistentes redirecionam para 'done' por segurança (evita enumeração de usuários)
        """
        url = reverse('password_reset_done')
        self.assertRedirects(self.response, url)

    def test_no_reset_email_sent(self):
        # Não deve enviar e-mail se o usuário não existe
        self.assertEqual(0, len(mail.outbox))



class PasswordResetDoneTests(TestCase):
    def setUp(self):
        url = reverse('password_reset_done')
        self.response = self.client.get(url)

    def test_status_code(self):
        # Corrigido: assertEqual em vez de assertEquals
        self.assertEqual(self.response.status_code, 200)

    def test_view_function(self):
        view = resolve('/reset/done/')
        # Corrigido: assertEqual e verificação da View Class
        self.assertEqual(view.func.view_class, auth_views.PasswordResetDoneView)



class PasswordResetConfirmTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='john', email='john@doe.com', password='123')
        self.uid = urlsafe_base64_encode(force_bytes(user.pk))
        self.token = default_token_generator.make_token(user)
        
        url = reverse('password_reset_confirm', kwargs={'uidb64': self.uid, 'token': self.token})
        self.response = self.client.get(url, follow=True)

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_view_function(self):
        view = resolve(f'/reset/{self.uid}/{self.token}/')
        self.assertEqual(view.func.view_class, auth_views.PasswordResetConfirmView)

    def test_csrf(self):
        self.assertContains(self.response, 'csrfmiddlewaretoken')

    def test_contains_form(self):
        form = self.response.context.get('form')
        self.assertIsInstance(form, SetPasswordForm)

    def test_form_inputs(self):
        # O formulário de nova senha contém: CSRF, senha1 e senha2
        self.assertContains(self.response, '<input', 3)


class InvalidPasswordResetConfirmTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='john', email='john@doe.com', password='123')
        self.uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        # Invalida o token mudando a senha ANTES de usar o link
        user.set_password('abcdef123')
        user.save()

        url = reverse('password_reset_confirm', kwargs={'uidb64': self.uid, 'token': token})
        self.response = self.client.get(url)

    def test_status_code(self):
        # Mesmo com link inválido, o Django renderiza a página avisando o erro (status 200)
        self.assertEqual(self.response.status_code, 200)

    def test_html(self):
        password_reset_url = reverse('password_reset')
        self.assertContains(self.response, 'It looks like you clicked on an invalid password reset link')
        self.assertContains(self.response, f'href="{password_reset_url}"')



class PasswordResetCompleteTests(TestCase):
    def setUp(self):
        url = reverse('password_reset_complete')
        self.response = self.client.get(url)

    def test_status_code(self):
        # Corrigido para o padrão atual
        self.assertEqual(self.response.status_code, 200)

    def test_view_function(self):
        view = resolve('/reset/complete/')
        # Verifica se a URL está a usar a Class-Based View correta
        self.assertEqual(view.func.view_class, auth_views.PasswordResetCompleteView)