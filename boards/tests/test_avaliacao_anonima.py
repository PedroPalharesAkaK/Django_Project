from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ..forms import NewAvaliacaoForm
from ..models import Professor, Avaliacao, Comentario

MARCA_NAO_VERIFICADA = 'Conta não verificada'
NOTA_ANONIMA = 'Avaliação anônima, enviada sem login por uma conta não verificada.'

DADOS_VALIDOS = {
    'titulo': 'Aulas muito boas',
    'texto': 'Explica bem e responde as dúvidas.',
    'nota_geral': 4,
    'nota_didatica': 5,
    'nota_empenho': 4,
    'nota_relacao': 3,
    'nota_dificuldade': 2,
}


class AvaliacaoAnonimaTestCase(TestCase):
    """
    Cenário base: um professor, sem nenhum usuário logado.
    """
    def setUp(self):
        self.professor = Professor.objects.create(nome='Professor de Teste', descricao='Instituto de Física')
        self.url = reverse('new_avaliacao', kwargs={'pk': self.professor.pk})
        self.professor_url = reverse('professor_avaliacoes', kwargs={'pk': self.professor.pk})

    def criar_avaliacao_anonima(self):
        avaliacao = Avaliacao.objects.create(
            titulo='Avaliação sem login', professor=self.professor, starter=None, nota_geral=3
        )
        comentario = Comentario.objects.create(
            texto='Comentário de quem não tem conta.', avaliacao=avaliacao, created_by=None
        )
        return avaliacao, comentario

    def comentarios_url(self, avaliacao):
        return reverse('avaliacao_comentarios', kwargs={'pk': self.professor.pk, 'avaliacao_pk': avaliacao.pk})


class NewAvaliacaoAnonimaViewTests(AvaliacaoAnonimaTestCase):
    """
    Envio de avaliações por visitantes sem login.
    """
    def test_get_sem_login_mostra_formulario(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context.get('form'), NewAvaliacaoForm)
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_get_sem_login_avisa_que_sera_anonima(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Você não está logado')
        self.assertContains(response, 'conta não verificada')
        # Oferece login voltando para o formulário
        self.assertContains(response, f'href="{reverse("login")}?next={self.url}"')

    def test_get_logado_nao_mostra_aviso(self):
        User.objects.create_user(username='john', password='123')
        self.client.login(username='john', password='123')
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Você não está logado')

    def test_post_valido_cria_avaliacao_sem_autor(self):
        response = self.client.post(self.url, DADOS_VALIDOS)

        avaliacao = Avaliacao.objects.get()
        comentario = Comentario.objects.get()
        self.assertIsNone(avaliacao.starter)
        self.assertIsNone(comentario.created_by)
        self.assertTrue(avaliacao.is_anonima())
        self.assertTrue(comentario.is_anonimo())
        self.assertEqual(avaliacao.professor, self.professor)
        self.assertEqual(avaliacao.titulo, DADOS_VALIDOS['titulo'])
        self.assertEqual(avaliacao.nota_geral, 4)
        self.assertEqual(avaliacao.nota_dificuldade, 2)
        self.assertEqual(comentario.avaliacao, avaliacao)
        self.assertEqual(comentario.texto, DADOS_VALIDOS['texto'])
        self.assertRedirects(response, self.comentarios_url(avaliacao))

    def test_post_valido_mostra_mensagem_de_sucesso_anonima(self):
        response = self.client.post(self.url, DADOS_VALIDOS, follow=True)
        self.assertContains(response, 'Sua avaliação anônima foi publicada')

    def test_post_invalido_nao_cria_nada(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertFalse(Avaliacao.objects.exists())
        self.assertFalse(Comentario.objects.exists())

    def test_segunda_avaliacao_na_mesma_sessao_e_bloqueada(self):
        self.client.post(self.url, DADOS_VALIDOS)
        response = self.client.post(self.url, DADOS_VALIDOS)
        self.assertRedirects(response, self.professor_url)
        self.assertEqual(Avaliacao.objects.count(), 1)
        self.assertEqual(Comentario.objects.count(), 1)

    def test_get_depois_de_avaliar_redireciona(self):
        self.client.post(self.url, DADOS_VALIDOS)
        response = self.client.get(self.url)
        self.assertRedirects(response, self.professor_url)

    def test_pagina_do_professor_desativa_botao_depois_de_avaliar(self):
        response = self.client.get(self.professor_url)
        self.assertContains(response, f'href="{self.url}"')

        self.client.post(self.url, DADOS_VALIDOS)
        response = self.client.get(self.professor_url)
        self.assertNotContains(response, f'href="{self.url}"')
        self.assertContains(response, 'Você já avaliou este professor')

    def test_bloqueio_da_sessao_e_por_professor(self):
        outro = Professor.objects.create(nome='Outro Professor', descricao='Instituto de Química')
        self.client.post(self.url, DADOS_VALIDOS)
        self.client.post(reverse('new_avaliacao', kwargs={'pk': outro.pk}), DADOS_VALIDOS)
        self.assertEqual(Avaliacao.objects.filter(professor=self.professor).count(), 1)
        self.assertEqual(Avaliacao.objects.filter(professor=outro).count(), 1)

    def test_usuario_logado_continua_publicando_com_a_conta(self):
        user = User.objects.create_user(username='john', password='123')
        self.client.login(username='john', password='123')
        response = self.client.post(self.url, DADOS_VALIDOS, follow=True)

        avaliacao = Avaliacao.objects.get()
        self.assertEqual(avaliacao.starter, user)
        self.assertEqual(avaliacao.comentarios.get().created_by, user)
        self.assertFalse(avaliacao.is_anonima())
        self.assertContains(response, 'Sua avaliação foi publicada com sucesso!')
        self.assertNotContains(response, MARCA_NAO_VERIFICADA)

    def test_avaliacao_anonima_conta_na_media_do_professor(self):
        self.client.post(self.url, DADOS_VALIDOS)
        self.assertEqual(self.professor.get_media_geral(), 4)
        self.assertEqual(self.professor.get_avaliacoes_count(), 1)


class AvaliacaoAnonimaExibicaoTests(AvaliacaoAnonimaTestCase):
    """
    A avaliação anônima precisa aparecer marcada como de conta não verificada.
    """
    def setUp(self):
        super().setUp()
        self.avaliacao, self.comentario = self.criar_avaliacao_anonima()

    def test_pagina_da_avaliacao_marca_conta_nao_verificada(self):
        response = self.client.get(self.comentarios_url(self.avaliacao))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Anônimo')
        self.assertContains(response, MARCA_NAO_VERIFICADA)
        self.assertContains(response, NOTA_ANONIMA)

    def test_resposta_de_usuario_verificado_nao_e_marcada(self):
        maria = User.objects.create_user(username='maria', password='123')
        Comentario.objects.create(texto='Concordo.', avaliacao=self.avaliacao, created_by=maria)

        response = self.client.get(self.comentarios_url(self.avaliacao))
        self.assertContains(response, 'maria')
        # Só o comentário anônimo recebe a marca
        self.assertContains(response, MARCA_NAO_VERIFICADA, count=1)
        self.assertContains(response, NOTA_ANONIMA, count=1)

    def test_avaliacao_de_conta_verificada_nao_e_marcada(self):
        john = User.objects.create_user(username='john', password='123')
        verificada = Avaliacao.objects.create(titulo='Com conta', professor=self.professor, starter=john)
        Comentario.objects.create(texto='Texto com conta.', avaliacao=verificada, created_by=john)

        response = self.client.get(self.comentarios_url(verificada))
        self.assertContains(response, 'john')
        self.assertNotContains(response, MARCA_NAO_VERIFICADA)
        self.assertNotContains(response, NOTA_ANONIMA)

    def test_lista_de_avaliacoes_do_professor_marca_autor_anonimo(self):
        response = self.client.get(self.professor_url)
        self.assertContains(response, 'Anônimo')
        self.assertContains(response, MARCA_NAO_VERIFICADA)

    def test_home_mostra_ultimo_comentario_como_anonimo(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Por Anônimo')

    def test_pagina_de_resposta_marca_comentario_anonimo(self):
        User.objects.create_user(username='john', password='123')
        self.client.login(username='john', password='123')
        url = reverse('reply_avaliacao', kwargs={'pk': self.professor.pk, 'avaliacao_pk': self.avaliacao.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Anônimo')
        self.assertContains(response, MARCA_NAO_VERIFICADA)


class AvaliacaoAnonimaPermissoesTests(AvaliacaoAnonimaTestCase):
    """
    Ninguém (logado ou não) pode editar uma avaliação anônima, e responder continua exigindo login.
    """
    def setUp(self):
        super().setUp()
        self.avaliacao, self.comentario = self.criar_avaliacao_anonima()
        self.edit_url = reverse('edit_comentario', kwargs={
            'pk': self.professor.pk,
            'avaliacao_pk': self.avaliacao.pk,
            'comentario_pk': self.comentario.pk,
        })

    def test_visitante_nao_ve_botao_editar(self):
        response = self.client.get(self.comentarios_url(self.avaliacao))
        self.assertNotContains(response, self.edit_url)

    def test_usuario_logado_nao_ve_botao_editar(self):
        User.objects.create_user(username='john', password='123')
        self.client.login(username='john', password='123')
        response = self.client.get(self.comentarios_url(self.avaliacao))
        self.assertNotContains(response, self.edit_url)

    def test_visitante_nao_consegue_editar(self):
        response = self.client.post(self.edit_url, {'texto': 'Texto alterado'})
        self.assertRedirects(response, f'{reverse("login")}?next={self.edit_url}')
        self.comentario.refresh_from_db()
        self.assertEqual(self.comentario.texto, 'Comentário de quem não tem conta.')

    def test_usuario_logado_nao_consegue_editar(self):
        User.objects.create_user(username='john', password='123')
        self.client.login(username='john', password='123')
        self.assertEqual(self.client.get(self.edit_url).status_code, 404)

        response = self.client.post(self.edit_url, {'texto': 'Texto alterado'})
        self.assertEqual(response.status_code, 404)
        self.comentario.refresh_from_db()
        self.assertEqual(self.comentario.texto, 'Comentário de quem não tem conta.')

    def test_visitante_nao_pode_responder(self):
        url = reverse('reply_avaliacao', kwargs={'pk': self.professor.pk, 'avaliacao_pk': self.avaliacao.pk})
        response = self.client.post(url, {'texto': 'Resposta sem login'})
        self.assertRedirects(response, f'{reverse("login")}?next={url}')
        self.assertEqual(Comentario.objects.count(), 1)


class AvaliacaoAnonimaModelTests(AvaliacaoAnonimaTestCase):
    def test_autor_display_anonimo(self):
        avaliacao, comentario = self.criar_avaliacao_anonima()
        self.assertEqual(avaliacao.get_autor_display(), 'Anônimo')
        self.assertEqual(comentario.get_autor_display(), 'Anônimo')

    def test_autor_display_com_conta(self):
        john = User.objects.create_user(username='john', password='123')
        avaliacao = Avaliacao.objects.create(titulo='Com conta', professor=self.professor, starter=john)
        comentario = Comentario.objects.create(texto='Oi', avaliacao=avaliacao, created_by=john)
        self.assertFalse(avaliacao.is_anonima())
        self.assertFalse(comentario.is_anonimo())
        self.assertEqual(avaliacao.get_autor_display(), 'john')
        self.assertEqual(comentario.get_autor_display(), 'john')


class ComentarioMarkdownSeguroTests(AvaliacaoAnonimaTestCase):
    """
    Qualquer visitante pode escrever agora, então o HTML do comentário não pode executar script.
    """
    def render(self, texto):
        return Comentario(texto=texto).get_texto_as_markdown()

    def test_remove_tag_script(self):
        html = self.render('<script>alert(1)</script>Oi')
        self.assertNotIn('<script', html)
        self.assertNotIn('alert(1)', html)
        self.assertIn('Oi', html)

    def test_remove_atributos_de_evento(self):
        html = self.render('Foto <img src="x" onerror="alert(1)">')
        self.assertNotIn('onerror', html)

    def test_remove_links_javascript(self):
        for texto in ['[clique](javascript:alert(1))', '[clique](javascript&#58;alert(1))']:
            with self.subTest(texto=texto):
                html = self.render(texto)
                self.assertNotIn('javascript', html)
                self.assertIn('clique', html)

    def test_mantem_markdown_normal(self):
        html = self.render('*itálico*, **negrito** e [USPAvalia](https://uspavalia.com/)\n\n> citação')
        self.assertIn('<em>itálico</em>', html)
        self.assertIn('<strong>negrito</strong>', html)
        self.assertIn('href="https://uspavalia.com/"', html)
        self.assertIn('<blockquote>', html)

    def test_script_enviado_anonimamente_nao_chega_na_pagina(self):
        dados = dict(DADOS_VALIDOS, texto='Bom professor <script>alert("xss")</script>')
        response = self.client.post(self.url, dados, follow=True)
        self.assertContains(response, 'Bom professor')
        self.assertNotContains(response, '<script>alert')
        self.assertNotContains(response, 'alert("xss")')
