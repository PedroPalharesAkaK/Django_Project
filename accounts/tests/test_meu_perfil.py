from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

class PerfilViewTests(TestCase):
    def setUp(self):
        # Cria um usuário falso para os testes
        self.user = User.objects.create_user(
            username='alunoteste', 
            email='aluno@usp.br', 
            password='senha_forte_123'
        )

    def test_editar_perfil_exige_login(self):
        """
        Garante que se alguém não logado tentar aceder,
        é redirecionado para a página de login (status 302).
        """
        url = reverse('editar_perfil')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302) 

    def test_editar_perfil_acesso_permitido(self):
        """
        Garante que um usuário logado consegue abrir a página
        e recebe um status 200 (OK).
        """
        self.client.login(username='alunoteste', password='senha_forte_123')
        url = reverse('editar_perfil')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Verifica se o HTML da página correta foi carregado
        self.assertTemplateUsed(response, 'editar_perfil.html')