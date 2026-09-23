import io
import json
import os
import shutil
import tempfile
from datetime import date, timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from ..management.commands.baixar_catalogo_disciplinas import resumir_catalogo
from ..models import ArquivoProva, Disciplina, Instituto, Professor, ProvaAntiga, Universidade
from ..provas import detectar_tipo, preparar_arquivo, salvar_arquivos, semestre_atual, semestres_ate_hoje

GPS_IFD = 0x8825
ORIENTACAO = 0x0112


def foto_jpeg(nome='foto.jpg', tamanho=(800, 1100), orientacao=None, com_gps=True):
    """Foto de celular: JPEG com EXIF (marca, GPS e, se pedido, orientação)."""
    imagem = Image.new('RGB', tamanho, 'white')
    exif = Image.Exif()
    exif[0x010F] = 'Celular de Teste'
    if orientacao:
        exif[ORIENTACAO] = orientacao
    if com_gps:
        gps = exif.get_ifd(GPS_IFD)
        gps[1] = 'S'
        gps[2] = (23.0, 33.0, 0.0)
    saida = io.BytesIO()
    imagem.save(saida, 'JPEG', exif=exif)
    return SimpleUploadedFile(nome, saida.getvalue(), content_type='image/jpeg')


def png_transparente(nome='pagina.png'):
    imagem = Image.new('RGBA', (400, 560), (0, 0, 0, 0))
    saida = io.BytesIO()
    imagem.save(saida, 'PNG')
    return SimpleUploadedFile(nome, saida.getvalue(), content_type='image/png')


def pdf(nome='prova.pdf'):
    return SimpleUploadedFile(nome, b'%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n', content_type='application/pdf')


class MediaTemporariaMixin:
    """Cada teste grava os arquivos numa pasta temporária, apagada no fim."""
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        configuracao = override_settings(MEDIA_ROOT=self.media)
        configuracao.enable()
        self.addCleanup(configuracao.disable)
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

    def arquivos_no_disco(self):
        return [os.path.join(raiz, nome) for raiz, _, nomes in os.walk(self.media) for nome in nomes]


class ProvasTestCase(MediaTemporariaMixin, TestCase):
    def setUp(self):
        super().setUp()
        usp = Universidade.objects.create(nome='Universidade de São Paulo', sigla='USP')
        self.ime = Instituto.objects.create(nome='Instituto de Matemática e Estatística', sigla='IME', universidade=usp)
        self.professor = Professor.objects.create(nome='Ana Souza', descricao='IME', instituto=self.ime)
        self.calculo = Disciplina.objects.create(
            codigo='MAT0111', nome='Cálculo Diferencial e Integral I', unidade='Instituto de Matemática e Estatística'
        )
        self.algebra = Disciplina.objects.create(
            codigo='MAT0112', nome='Vetores e Geometria', unidade='Instituto de Matemática e Estatística'
        )
        self.fisica = Disciplina.objects.create(codigo='4302111', nome='Física I', unidade='Instituto de Física')
        self.user = User.objects.create_user(username='john', password='123')

        self.provas_url = reverse('professor_provas', kwargs={'pk': self.professor.pk})
        self.enviar_url = reverse('enviar_prova', kwargs={'pk': self.professor.pk})

    def criar_prova(self, disciplina=None, semestre='2025/1', tipo='P1', enviado_por=None, arquivos=None):
        prova = ProvaAntiga.objects.create(
            professor=self.professor, disciplina=disciplina or self.calculo,
            semestre=semestre, tipo=tipo, enviado_por=enviado_por or self.user,
        )
        salvar_arquivos(prova, [preparar_arquivo(a) for a in (arquivos or [foto_jpeg()])])
        return prova

    def dados_envio(self, **extra):
        dados = {
            'disciplina': 'MAT0111 - Cálculo Diferencial e Integral I',
            'semestre': '2024/2',
            'tipo': 'P1',
            'observacao': '',
            'arquivos': [foto_jpeg('p1.jpg'), foto_jpeg('p2.jpg')],
        }
        dados.update(extra)
        return dados


# ---------------------------------------------------------------------------
# Processamento dos arquivos
# ---------------------------------------------------------------------------

class SemestresTests(TestCase):
    def test_semestre_atual(self):
        self.assertEqual(semestre_atual(date(2026, 3, 1)), '2026/1')
        self.assertEqual(semestre_atual(date(2026, 6, 30)), '2026/1')
        self.assertEqual(semestre_atual(date(2026, 7, 1)), '2026/2')

    def test_semestres_ate_hoje_do_mais_recente_ao_primeiro_ano(self):
        semestres = semestres_ate_hoje(primeiro_ano=2024, hoje=date(2026, 9, 23))
        self.assertEqual(semestres, ['2026/2', '2026/1', '2025/2', '2025/1', '2024/2', '2024/1'])


class PrepararArquivoTests(TestCase):
    def test_detecta_tipo_pela_assinatura_e_nao_pelo_nome(self):
        self.assertEqual(detectar_tipo(pdf('foto.jpg')), 'pdf')
        self.assertEqual(detectar_tipo(foto_jpeg('prova.pdf')), 'imagem')
        self.assertEqual(detectar_tipo(png_transparente()), 'imagem')
        self.assertIsNone(detectar_tipo(SimpleUploadedFile('prova.pdf', b'<html>oi</html>')))

    def test_foto_perde_exif_e_gps(self):
        original = foto_jpeg()
        self.assertTrue(Image.open(io.BytesIO(original.read())).getexif().get_ifd(GPS_IFD))
        original.seek(0)

        preparado = preparar_arquivo(original)
        salvo = Image.open(io.BytesIO(preparado.conteudo.read()))
        self.assertEqual(preparado.tipo_conteudo, 'image/jpeg')
        self.assertEqual(len(salvo.getexif()), 0)
        self.assertNotIn('exif', salvo.info)

    def test_foto_e_girada_conforme_o_exif(self):
        # Orientação 6: a câmera gravou deitada; a página em pé tem largura e altura trocadas
        preparado = preparar_arquivo(foto_jpeg(tamanho=(1100, 800), orientacao=6))
        salvo = Image.open(io.BytesIO(preparado.conteudo.read()))
        self.assertEqual(salvo.size, (800, 1100))

    def test_foto_grande_e_reduzida_e_ganha_miniatura(self):
        preparado = preparar_arquivo(foto_jpeg(tamanho=(3000, 4000)))
        salvo = Image.open(io.BytesIO(preparado.conteudo.read()))
        miniatura = Image.open(io.BytesIO(preparado.miniatura))
        self.assertEqual(max(salvo.size), 2200)
        self.assertEqual(miniatura.width, 480)

    def test_png_transparente_vira_jpeg_com_fundo_branco(self):
        preparado = preparar_arquivo(png_transparente())
        salvo = Image.open(io.BytesIO(preparado.conteudo.read())).convert('RGB')
        self.assertEqual(preparado.tipo_conteudo, 'image/jpeg')
        self.assertEqual(salvo.getpixel((10, 10)), (255, 255, 255))

    def test_pdf_e_guardado_como_veio(self):
        preparado = preparar_arquivo(pdf())
        self.assertEqual(preparado.tipo_conteudo, 'application/pdf')
        self.assertIsNone(preparado.miniatura)

    def test_recusa_arquivo_que_nao_e_pdf_nem_imagem(self):
        with self.assertRaisesMessage(ValidationError, 'não é PDF, JPG nem PNG'):
            preparar_arquivo(SimpleUploadedFile('prova.pdf', b'MZ\x90\x00 executavel'))

    def test_recusa_imagem_corrompida(self):
        corrompida = SimpleUploadedFile('foto.jpg', b'\xff\xd8\xff\xe0' + b'lixo' * 50)
        with self.assertRaisesMessage(ValidationError, 'não pôde ser aberta como imagem'):
            preparar_arquivo(corrompida)


class ModelTests(ProvasTestCase):
    def test_busca_da_disciplina_fica_sem_acentos(self):
        self.assertEqual(self.calculo.busca, 'mat0111 calculo diferencial e integral i')

    def test_ordenacao_mais_recente_primeiro_e_p1_antes_de_p2(self):
        provas = [
            ProvaAntiga(semestre='2024/2', tipo='P1'),
            ProvaAntiga(semestre='2025/1', tipo='REC'),
            ProvaAntiga(semestre='2025/1', tipo='P2'),
            ProvaAntiga(semestre='2025/1', tipo='P1'),
        ]
        ordenadas = sorted(provas, key=ProvaAntiga.chave_ordenacao)
        self.assertEqual([(p.semestre, p.tipo) for p in ordenadas],
                         [('2025/1', 'P1'), ('2025/1', 'P2'), ('2025/1', 'REC'), ('2024/2', 'P1')])

    def test_resumo_dos_arquivos(self):
        self.assertEqual(self.criar_prova().get_resumo_arquivos(), '')
        self.assertEqual(self.criar_prova(arquivos=[foto_jpeg(), foto_jpeg(), foto_jpeg()]).get_resumo_arquivos(), '3 páginas')
        self.assertEqual(self.criar_prova(arquivos=[foto_jpeg(), pdf()]).get_resumo_arquivos(), '2 arquivos')

    def test_apagar_prova_apaga_os_arquivos_do_disco(self):
        prova = self.criar_prova(arquivos=[foto_jpeg(), pdf()])
        self.assertEqual(len(self.arquivos_no_disco()), 3)  # foto + miniatura + pdf
        prova.delete()
        self.assertEqual(self.arquivos_no_disco(), [])

    def test_apagar_professor_apaga_os_arquivos_das_provas(self):
        self.criar_prova()
        self.professor.delete()
        self.assertEqual(self.arquivos_no_disco(), [])

    def test_prova_continua_se_a_conta_de_quem_enviou_for_apagada(self):
        prova = self.criar_prova()
        self.user.delete()
        prova.refresh_from_db()
        self.assertIsNone(prova.enviado_por)


# ---------------------------------------------------------------------------
# Aba "Provas antigas"
# ---------------------------------------------------------------------------

class ProvasProfessorViewTests(ProvasTestCase):
    def test_aba_abre_sem_login_e_mostra_as_duas_abas(self):
        response = self.client.get(self.provas_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Provas antigas')
        self.assertContains(response, f'href="{reverse("professor_avaliacoes", kwargs={"pk": self.professor.pk})}"')
        self.assertContains(response, 'aria-current="page"', count=1)

    def test_aba_de_avaliacoes_tambem_mostra_as_abas(self):
        response = self.client.get(reverse('professor_avaliacoes', kwargs={'pk': self.professor.pk}))
        self.assertContains(response, f'href="{self.provas_url}"')

    def test_sem_provas_mostra_convite_para_enviar(self):
        response = self.client.get(self.provas_url)
        self.assertContains(response, 'Ainda não há provas de Ana Souza')
        self.assertContains(response, f'href="{self.enviar_url}"')

    def test_provas_agrupadas_por_disciplina_e_ordenadas(self):
        self.criar_prova(semestre='2024/2', tipo='P1')
        self.criar_prova(semestre='2025/1', tipo='P2')
        self.criar_prova(semestre='2025/1', tipo='P1')
        self.criar_prova(disciplina=self.algebra, semestre='2023/1', tipo='SUB')

        response = self.client.get(self.provas_url)
        grupos = response.context['grupos']
        self.assertEqual([g['disciplina'].codigo for g in grupos], ['MAT0111', 'MAT0112'])
        self.assertEqual([(p.semestre, p.tipo) for p in grupos[0]['provas']],
                         [('2025/1', 'P1'), ('2025/1', 'P2'), ('2024/2', 'P1')])
        self.assertContains(response, 'Cálculo Diferencial e Integral I')
        self.assertContains(response, 'Substitutiva')
        self.assertContains(response, f'{self.enviar_url}?disciplina=MAT0111')

    def test_nao_mostra_provas_de_outro_professor(self):
        outro = Professor.objects.create(nome='Outro Professor', descricao='IF')
        ProvaAntiga.objects.create(professor=outro, disciplina=self.fisica, semestre='2025/1', tipo='P1')
        response = self.client.get(self.provas_url)
        self.assertEqual(response.context['grupos'], [])
        self.assertNotContains(response, 'Física I')

    def test_foto_aparece_como_miniatura_e_pdf_como_folha(self):
        foto = self.criar_prova(tipo='P1')
        documento = self.criar_prova(tipo='P2', arquivos=[pdf()])
        response = self.client.get(self.provas_url)
        self.assertContains(response, reverse('miniatura_prova', kwargs={'pk': foto.arquivos.get().pk}))
        self.assertContains(response, 'class="folha-pdf"', count=1)
        self.assertContains(response, reverse('prova_detalhe', kwargs={'pk': documento.pk}))

    def test_provas_da_mesma_disciplina_ficam_na_mesma_secao(self):
        # Duas pessoas enviam provas de Vetores, uma pelo código e outra pelo nome sugerido
        self.client.login(username='john', password='123')
        self.client.post(self.enviar_url, self.dados_envio(disciplina='MAT0112', semestre='2024/1', arquivos=[pdf()]))
        User.objects.create_user(username='maria', password='123')
        self.client.login(username='maria', password='123')
        self.client.post(self.enviar_url, self.dados_envio(
            disciplina='MAT0112 - Vetores e Geometria', semestre='2025/2', tipo='P2', arquivos=[pdf()]))

        grupos = self.client.get(self.provas_url).context['grupos']
        self.assertEqual(len(grupos), 1)
        self.assertEqual(grupos[0]['disciplina'].codigo, 'MAT0112')
        self.assertEqual([(p.semestre, p.tipo) for p in grupos[0]['provas']], [('2025/2', 'P2'), ('2024/1', 'P1')])

    def test_contagem_na_aba(self):
        self.criar_prova()
        self.criar_prova(tipo='P2')
        self.assertEqual(self.professor.get_provas_count(), 2)


# ---------------------------------------------------------------------------
# Envio
# ---------------------------------------------------------------------------

class EnviarProvaTests(ProvasTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='john', password='123')

    def test_envio_exige_login(self):
        self.client.logout()
        response = self.client.get(self.enviar_url)
        self.assertRedirects(response, f'{reverse("login")}?next={self.enviar_url}')

    def test_formulario_abre_com_a_disciplina_do_link(self):
        response = self.client.get(self.enviar_url, {'disciplina': 'mat0111'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].initial['disciplina'], 'MAT0111 - Cálculo Diferencial e Integral I')
        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_formulario_sugere_disciplinas_que_ja_tem_provas_do_professor(self):
        self.criar_prova(disciplina=self.algebra)
        response = self.client.get(self.enviar_url)
        self.assertEqual(list(response.context['sugestoes']), [self.algebra])
        self.assertContains(response, 'data-disciplina="MAT0112 - Vetores e Geometria"')

    def test_envio_valido_publica_na_hora(self):
        response = self.client.post(self.enviar_url, self.dados_envio(observacao='Turma do noturno'), follow=True)

        prova = ProvaAntiga.objects.get()
        self.assertEqual(prova.professor, self.professor)
        self.assertEqual(prova.disciplina, self.calculo)
        self.assertEqual((prova.semestre, prova.tipo, prova.observacao), ('2024/2', 'P1', 'Turma do noturno'))
        self.assertEqual(prova.enviado_por, self.user)
        self.assertEqual([a.ordem for a in prova.arquivos.all()], [0, 1])
        self.assertEqual(len(self.arquivos_no_disco()), 4)  # 2 páginas + 2 miniaturas

        self.assertRedirects(response, reverse('prova_detalhe', kwargs={'pk': prova.pk}))
        self.assertContains(response, 'Prova enviada.')
        # Sem moderação: já aparece na aba do professor
        self.assertContains(self.client.get(self.provas_url), reverse('prova_detalhe', kwargs={'pk': prova.pk}))

    def test_aceita_so_o_codigo_da_disciplina(self):
        self.client.post(self.enviar_url, self.dados_envio(disciplina='mat0111'))
        self.assertEqual(ProvaAntiga.objects.get().disciplina, self.calculo)

    def test_envio_de_pdf(self):
        self.client.post(self.enviar_url, self.dados_envio(arquivos=[pdf()]))
        arquivo = ArquivoProva.objects.get()
        self.assertEqual(arquivo.tipo_conteudo, 'application/pdf')
        self.assertFalse(arquivo.miniatura)

    def assertEnvioRecusado(self, response, mensagem):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, mensagem)
        self.assertFalse(ProvaAntiga.objects.exists())
        self.assertEqual(self.arquivos_no_disco(), [])

    def test_disciplina_fora_do_catalogo(self):
        response = self.client.post(self.enviar_url, self.dados_envio(disciplina='XYZ9999 - Inventada'))
        self.assertEnvioRecusado(response, 'Escolha uma disciplina da lista')

    def test_semestre_no_futuro(self):
        response = self.client.post(self.enviar_url, self.dados_envio(semestre='2099/1'))
        self.assertEnvioRecusado(response, 'Faça uma escolha válida')

    def test_sem_arquivos(self):
        response = self.client.post(self.enviar_url, self.dados_envio(arquivos=[]))
        self.assertEnvioRecusado(response, 'Este campo é obrigatório')

    def test_arquivo_que_nao_e_prova(self):
        falso = SimpleUploadedFile('prova.pdf', b'<script>alert(1)</script>', content_type='application/pdf')
        response = self.client.post(self.enviar_url, self.dados_envio(arquivos=[foto_jpeg(), falso]))
        self.assertEnvioRecusado(response, '&quot;prova.pdf&quot; não é PDF, JPG nem PNG.')

    @override_settings(PROVAS_TAMANHO_MAXIMO=1024)
    def test_passa_do_tamanho_maximo(self):
        response = self.client.post(self.enviar_url, self.dados_envio())
        self.assertEnvioRecusado(response, 'o limite é 1,0\xa0KB')

    @override_settings(PROVAS_MAX_ARQUIVOS=1)
    def test_passa_do_numero_de_arquivos(self):
        response = self.client.post(self.enviar_url, self.dados_envio())
        self.assertEnvioRecusado(response, 'Envie no máximo 1 arquivos por prova.')

    @override_settings(PROVAS_LIMITE_DIARIO=2)
    def test_limite_diario_por_usuario(self):
        self.client.post(self.enviar_url, self.dados_envio(arquivos=[pdf()]))
        self.client.post(self.enviar_url, self.dados_envio(arquivos=[pdf()]))
        response = self.client.post(self.enviar_url, self.dados_envio(arquivos=[pdf()]))
        self.assertContains(response, 'o limite diário')
        self.assertEqual(ProvaAntiga.objects.count(), 2)

    @override_settings(PROVAS_LIMITE_DIARIO=1)
    def test_limite_diario_libera_depois_de_24_horas(self):
        self.client.post(self.enviar_url, self.dados_envio(arquivos=[pdf()]))
        ProvaAntiga.objects.update(criado_em=timezone.now() - timedelta(hours=25))
        self.client.post(self.enviar_url, self.dados_envio(arquivos=[pdf()]))
        self.assertEqual(ProvaAntiga.objects.count(), 2)

    def test_falha_ao_gravar_nao_deixa_arquivo_orfao(self):
        with mock.patch.object(ArquivoProva, 'save', side_effect=RuntimeError('banco fora do ar')):
            with self.assertRaises(RuntimeError):
                self.client.post(self.enviar_url, self.dados_envio())
        self.assertFalse(ProvaAntiga.objects.exists())
        self.assertEqual(self.arquivos_no_disco(), [])


# ---------------------------------------------------------------------------
# Página da prova, arquivos e exclusão
# ---------------------------------------------------------------------------

class ProvaDetalheTests(ProvasTestCase):
    def setUp(self):
        super().setUp()
        self.prova = self.criar_prova(arquivos=[foto_jpeg(), pdf()])
        self.foto, self.documento = self.prova.arquivos.all()
        self.url = reverse('prova_detalhe', kwargs={'pk': self.prova.pk})
        self.excluir_url = reverse('excluir_prova', kwargs={'pk': self.prova.pk})

    def test_mostra_paginas_e_pdf(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'P1 de 2025/1, com Ana Souza')
        self.assertContains(response, f'src="{reverse("arquivo_prova", kwargs={"pk": self.foto.pk})}"')
        self.assertContains(response, 'Abrir PDF')
        self.assertContains(response, 'Enviada por john')

    def test_link_de_pedir_remocao_preenche_o_contato(self):
        response = self.client.get(self.url)
        contato_url = f'{reverse("contato")}?remover_prova={self.prova.pk}'
        self.assertContains(response, contato_url)
        form = self.client.get(contato_url).context['form']
        self.assertIn('Peço a remoção da prova MAT0111 2025/1 P1', form.initial['mensagem'])

    def test_arquivo_e_servido_com_o_tipo_certo(self):
        response = self.client.get(reverse('arquivo_prova', kwargs={'pk': self.foto.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertTrue(response['Content-Disposition'].startswith('inline'))
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

        response = self.client.get(reverse('arquivo_prova', kwargs={'pk': self.documento.pk}))
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('MAT0111-2025-1-P1-2.pdf', response['Content-Disposition'])

    def test_miniatura(self):
        self.assertEqual(self.client.get(reverse('miniatura_prova', kwargs={'pk': self.foto.pk})).status_code, 200)
        self.assertEqual(self.client.get(reverse('miniatura_prova', kwargs={'pk': self.documento.pk})).status_code, 404)

    def test_arquivo_sumido_do_disco_da_404(self):
        os.remove(self.foto.arquivo.path)
        self.assertEqual(self.client.get(reverse('arquivo_prova', kwargs={'pk': self.foto.pk})).status_code, 404)

    def test_botao_excluir_so_para_quem_enviou(self):
        self.assertNotContains(self.client.get(self.url), self.excluir_url)
        self.client.login(username='john', password='123')
        self.assertContains(self.client.get(self.url), self.excluir_url)

    def test_quem_enviou_pode_excluir(self):
        self.client.login(username='john', password='123')
        self.assertContains(self.client.get(self.excluir_url), 'Excluir esta prova?')
        response = self.client.post(self.excluir_url)
        self.assertRedirects(response, self.provas_url)
        self.assertFalse(ProvaAntiga.objects.exists())
        self.assertEqual(self.arquivos_no_disco(), [])

    def test_outro_usuario_nao_pode_excluir(self):
        User.objects.create_user(username='maria', password='123')
        self.client.login(username='maria', password='123')
        self.assertEqual(self.client.post(self.excluir_url).status_code, 403)
        self.assertTrue(ProvaAntiga.objects.exists())

    def test_visitante_e_mandado_para_o_login(self):
        response = self.client.post(self.excluir_url)
        self.assertRedirects(response, f'{reverse("login")}?next={self.excluir_url}')
        self.assertTrue(ProvaAntiga.objects.exists())

    def test_admin_pode_excluir(self):
        User.objects.create_user(username='admin', password='123', is_staff=True)
        self.client.login(username='admin', password='123')
        self.client.post(self.excluir_url)
        self.assertFalse(ProvaAntiga.objects.exists())


# ---------------------------------------------------------------------------
# Busca de disciplinas e catálogo
# ---------------------------------------------------------------------------

class BuscarDisciplinasTests(ProvasTestCase):
    def buscar(self, q, **extra):
        response = self.client.get(reverse('buscar_disciplinas'), {'q': q, **extra})
        return [d['codigo'] for d in response.json()['resultados']]

    def test_busca_sem_acento_e_por_varias_palavras(self):
        self.assertEqual(self.buscar('calculo'), ['MAT0111'])
        self.assertEqual(self.buscar('integral diferencial'), ['MAT0111'])
        self.assertEqual(self.buscar('mat01'), ['MAT0111', 'MAT0112'])

    def test_busca_curta_nao_retorna_nada(self):
        self.assertEqual(self.buscar('m'), [])

    def test_prioriza_disciplinas_que_ja_tem_provas_do_professor(self):
        Disciplina.objects.create(codigo='4300111', nome='Física Geral', unidade='Instituto de Física')
        self.criar_prova(disciplina=self.fisica)
        # 4302111 já tem prova dela: vem primeiro, para a próxima prova cair na mesma disciplina
        self.assertEqual(self.buscar('fisica', professor=self.professor.pk), ['4302111', '4300111'])
        self.assertEqual(self.buscar('fisica'), ['4300111', '4302111'])


class CatalogoTests(TestCase):
    def test_resumo_do_catalogo_guarda_so_os_dados_da_disciplina(self):
        catalogo = [
            {'codigo': 'MAT0112', 'nome': ' Vetores ', 'unidade': 'IME', 'departamento': '', 'turmas': [{'codigo': '2026203'}]},
            {'codigo': 'MAT0111', 'nome': 'Cálculo I', 'unidade': 'IME', 'departamento': 'MAT', 'creditos_aula': 6},
            {'codigo': '', 'nome': 'Sem código'},
        ]
        self.assertEqual(resumir_catalogo(catalogo), [
            {'codigo': 'MAT0111', 'nome': 'Cálculo I', 'unidade': 'IME', 'departamento': 'MAT'},
            {'codigo': 'MAT0112', 'nome': 'Vetores', 'unidade': 'IME', 'departamento': ''},
        ])

    def test_importar_disciplinas(self):
        catalogo = [
            {'codigo': 'MAT0111', 'nome': 'Cálculo I', 'unidade': 'IME', 'departamento': 'MAT'},
            {'codigo': 'MAT0112', 'nome': 'Vetores', 'unidade': 'IME', 'departamento': ''},
        ]
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as arquivo:
            json.dump(catalogo, arquivo)
        self.addCleanup(os.remove, arquivo.name)

        call_command('importar_disciplinas', arquivo=arquivo.name, stdout=io.StringIO())
        self.assertEqual(Disciplina.objects.count(), 2)
        self.assertEqual(Disciplina.objects.get(codigo='MAT0111').busca, 'mat0111 calculo i')

        # Rodar de novo não duplica e atualiza nomes que mudaram
        catalogo[1]['nome'] = 'Vetores e Geometria'
        with open(arquivo.name, 'w', encoding='utf-8') as f:
            json.dump(catalogo, f)
        call_command('importar_disciplinas', arquivo=arquivo.name, stdout=io.StringIO())
        self.assertEqual(Disciplina.objects.count(), 2)
        self.assertEqual(Disciplina.objects.get(codigo='MAT0112').busca, 'mat0112 vetores e geometria')
