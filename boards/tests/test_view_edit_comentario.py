from django.forms import ModelForm
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import resolve, reverse

# 1. IMPORTAÇÕES ATUALIZADAS: Chamando os novos Modelos e a nova View
from ..models import Professor, Avaliacao, Comentario
from ..views import ComentarioUpdateView
from ..forms import NewAvaliacaoForm, ComentarioForm


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
        
        # ATUALIZAÇÃO: Como estamos a testar a edição do primeiro comentário,
        # o nosso Camaleão exige o pacote completo (Título, Texto e as 5 Notas).
        data = {
            'titulo': 'Avaliação Teste Editada',
            'texto': 'texto editado',
            'nota_geral': 5,
            'nota_didatica': 4,
            'nota_empenho': 5,
            'nota_relacao': 4,
            'nota_dificuldade': 3
        }
        self.response = self.client.post(self.url, data)


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

class EditComentarioSegurancaTests(TestCase):
    def setUp(self):
        # 1. Cria o Professor e dois Alunos
        self.professor = Professor.objects.create(nome='Prof Teste', descricao='Física')
        self.user_autor = User.objects.create_user(username='autor', password='123')
        self.user_aluno = User.objects.create_user(username='aluno2', password='123')

        # 2. Cria a Avaliação e as Notas (O Tópico Pai)
        self.avaliacao = Avaliacao.objects.create(
            titulo='Review Original', professor=self.professor, starter=self.user_autor,
            nota_geral=3, nota_didatica=3, nota_empenho=3, nota_relacao=3, nota_dificuldade=3
        )
        
        # 3. Cria o 1º Comentário (A Review Original feita pelo autor)
        self.primeiro_comentario = Comentario.objects.create(
            texto='Texto original', avaliacao=self.avaliacao, created_by=self.user_autor
        )

        # 4. Cria o 2º Comentário (O próprio autor a responder ao seu tópico)
        self.segundo_comentario = Comentario.objects.create(
            texto='Esqueci-me de dizer algo...', avaliacao=self.avaliacao, created_by=self.user_autor
        )

        # 5. Cria o 3º Comentário (O outro aluno a responder)
        self.terceiro_comentario = Comentario.objects.create(
            texto='Concordo contigo!', avaliacao=self.avaliacao, created_by=self.user_aluno
        )

    def test_form_class_for_original_review(self):
        """O autor a editar a avaliação original DEVE ver as Notas."""
        self.client.login(username='autor', password='123')
        url = reverse('edit_comentario', kwargs={
            'pk': self.professor.pk,
            'avaliacao_pk': self.avaliacao.pk,
            'comentario_pk': self.primeiro_comentario.pk
        })
        response = self.client.get(url)
        # Verifica se o Django enviou o formulário grande (com notas)
        self.assertIsInstance(response.context.get('form'), NewAvaliacaoForm)

    def test_form_class_for_reply_same_author(self):
        """O autor a editar a sua própria resposta NÃO DEVE ver as Notas."""
        self.client.login(username='autor', password='123')
        url = reverse('edit_comentario', kwargs={
            'pk': self.professor.pk,
            'avaliacao_pk': self.avaliacao.pk,
            'comentario_pk': self.segundo_comentario.pk
        })
        response = self.client.get(url)
        # Verifica se o Django enviou o formulário simples
        self.assertIsInstance(response.context.get('form'), ComentarioForm)

    def test_form_class_for_reply_different_author(self):
        """Outro aluno a editar a sua resposta NÃO DEVE ver as Notas."""
        self.client.login(username='aluno2', password='123')
        url = reverse('edit_comentario', kwargs={
            'pk': self.professor.pk,
            'avaliacao_pk': self.avaliacao.pk,
            'comentario_pk': self.terceiro_comentario.pk
        })
        response = self.client.get(url)
        # Verifica se o Django enviou o formulário simples
        self.assertIsInstance(response.context.get('form'), ComentarioForm)

    def test_successful_edit_original_review_updates_notes(self):
        """Garante que ao salvar a edição, as notas mudam no Banco de Dados."""
        self.client.login(username='autor', password='123')
        url = reverse('edit_comentario', kwargs={
            'pk': self.professor.pk,
            'avaliacao_pk': self.avaliacao.pk,
            'comentario_pk': self.primeiro_comentario.pk
        })
        
        # Simulamos o envio de uma nota máxima e título novo
        data = {
            'titulo': 'Review Original Editada',
            'texto': 'Texto editado',
            'nota_geral': 5, # Subiu de 3 para 5
            'nota_didatica': 5,
            'nota_empenho': 5,
            'nota_relacao': 5,
            'nota_dificuldade': 5
        }
        self.client.post(url, data)
        
        # Atualizamos a nossa visão do banco de dados (refresh)
        self.avaliacao.refresh_from_db()
        self.primeiro_comentario.refresh_from_db()
        
        # Verifica se as notas e o texto foram de facto guardados
        self.assertEqual(self.avaliacao.nota_geral, 5)
        self.assertEqual(self.avaliacao.titulo, 'Review Original Editada')
        self.assertEqual(self.primeiro_comentario.texto, 'Texto editado')