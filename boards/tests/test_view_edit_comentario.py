from django.forms import ModelForm
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import resolve, reverse

# 1. IMPORTAÇÕES ATUALIZADAS: Chamando os novos Modelos e a nova View
from ..models import Professor, Avaliacao, Comentario
from ..views import ComentarioUpdateView


class ComentarioUpdateViewTestCase(TestCase):
    """
    Base test case to be used in all `ComentarioUpdateView` view tests
    """
    def setUp(self):
        # 2. SETUP ATUALIZADO: Criando Professor, Avaliação e Comentário
        self.professor = Professor.objects.create(nome='Professor de Teste', descricao='Instituto de Física')
        self.username = 'john'
        self.password = '123'
        user = User.objects.create_user(username=self.username, email='john@doe.com', password=self.password)
        
        self.avaliacao = Avaliacao.objects.create(titulo='Avaliação Teste', professor=self.professor, starter=user)
        self.comentario = Comentario.objects.create(texto='Comentário original', avaliacao=self.avaliacao, created_by=user)
        
        # 3. ROTA ATUALIZADA: Usando os novos kwargs
        self.url = reverse('edit_comentario', kwargs={
            'pk': self.professor.pk,
            'avaliacao_pk': self.avaliacao.pk,
            'comentario_pk': self.comentario.pk
        })


class LoginRequiredComentarioUpdateViewTests(ComentarioUpdateViewTestCase):
    def test_redirection(self):
        login_url = reverse('login')
        response = self.client.get(self.url)
        self.assertRedirects(response, '{login_url}?next={url}'.format(login_url=login_url, url=self.url))


class UnauthorizedComentarioUpdateViewTests(ComentarioUpdateViewTestCase):
    def setUp(self):
        super().setUp()
        username = 'jane'
        password = '321'
        User.objects.create_user(username=username, email='jane@doe.com', password=password)
        self.client.login(username=username, password=password)
        self.response = self.client.get(self.url)

    def test_status_code(self):
        """
        A topic should be edited only by the owner.
        Unauthorized users should get a 404 response (Page Not Found)
        """
        self.assertEqual(self.response.status_code, 404)


class ComentarioUpdateViewTests(ComentarioUpdateViewTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username=self.username, password=self.password)
        self.response = self.client.get(self.url)

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_view_class(self):
        # 4. ROTA DE RESOLVE ATUALIZADA: Adequada ao urls.py
        dynamic_url = f'/professores/{self.professor.pk}/avaliacoes/{self.avaliacao.pk}/comentarios/{self.comentario.pk}/edit/'
        view = resolve(dynamic_url)
        self.assertEqual(view.func.view_class, ComentarioUpdateView)

    def test_csrf(self):
        self.assertContains(self.response, 'csrfmiddlewaretoken')

    def test_contains_form(self):
        form = self.response.context.get('form')
        self.assertIsInstance(form, ModelForm)

    def test_form_inputs(self):
        """
        The view must contain the message textarea
        """
        self.assertContains(self.response, '<textarea', 1)


class SuccessfulComentarioUpdateViewTests(ComentarioUpdateViewTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username=self.username, password=self.password)
        # 5. ATUALIZAÇÃO DE CAMPO: Enviando 'texto' em vez de 'message'
        self.response = self.client.post(self.url, {'texto': 'texto editado'})

    def test_redirection(self):
        """
        A valid form submission should redirect the user
        """
        # 6. REDIRECIONAMENTO ATUALIZADO: Apontando para os comentários da avaliação
        avaliacao_comentarios_url = reverse('avaliacao_comentarios', kwargs={'pk': self.professor.pk, 'avaliacao_pk': self.avaliacao.pk})
        self.assertRedirects(self.response, avaliacao_comentarios_url)

    def test_post_changed(self):
        self.comentario.refresh_from_db()
        self.assertEqual(self.comentario.texto, 'texto editado')


class InvalidComentarioUpdateViewTests(ComentarioUpdateViewTestCase):
    def setUp(self):
        """
        Submit an empty dictionary to the view
        """
        super().setUp()
        self.client.login(username=self.username, password=self.password)
        self.response = self.client.post(self.url, {})

    def test_status_code(self):
        """
        An invalid form submission should return to the same page
        """
        self.assertEqual(self.response.status_code, 200)

    def test_form_errors(self):
        form = self.response.context.get('form')
        self.assertTrue(form.errors)