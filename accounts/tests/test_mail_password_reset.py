from django.core import mail
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase

class PasswordResetMailTests(TestCase):
    def setUp(self):
        User.objects.create_user(username='john', email='john@doe.com', password='123')
        self.response = self.client.post(reverse('password_reset'), {'email': 'john@doe.com'})
        self.email = mail.outbox[0]

    def test_email_subject(self):
        # Garanta que o assunto bate exatamente com o seu password_reset_subject.txt
        self.assertEqual('[Django Boards] Please reset your password', self.email.subject)

    def test_email_body(self):
        context = self.response.context
        token = context.get('token')
        uid = context.get('uid')
        password_reset_token_url = reverse('password_reset_confirm', kwargs={
            'uidb64': uid,
            'token': token
        })
        
        # No Django 6, acessamos o corpo do e-mail assim para evitar erros de encoding:
        email_body = self.email.body
        
        self.assertIn(password_reset_token_url, email_body)
        self.assertIn('john', email_body)
        self.assertIn('john@doe.com', email_body)

    def test_email_to(self):
        self.assertEqual(['john@doe.com'], self.email.to)