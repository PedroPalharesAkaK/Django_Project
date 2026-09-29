from django.urls import reverse

from ..models import Avaliacao, Disciplina, Instituto, Professor, ProvaAntiga, Universidade
from .test_provas_antigas import ProvasTestCase, foto_jpeg, pdf


class DisciplinaTestCase(ProvasTestCase):
    """Base dos testes da página por disciplina: um segundo professor e atalhos de URL."""
    def setUp(self):
        super().setUp()
        self.outro = Professor.objects.create(nome='Bruno Lima', descricao='IME', instituto=self.ime)
        self.calculo_url = reverse('disciplina_provas', kwargs={'codigo': 'MAT0111'})
        self.indice_url = reverse('disciplinas')

    def prova_de(self, professor, disciplina=None, semestre='2025/1', tipo='P1', enviado_por=None):
        """Prova sem arquivos: basta para as listagens (aparece como folha de PDF)."""
        return ProvaAntiga.objects.create(
            professor=professor, disciplina=disciplina or self.calculo, semestre=semestre, tipo=tipo,
            enviado_por=enviado_por,
        )


# ---------------------------------------------------------------------------
# Índice /disciplinas/
# ---------------------------------------------------------------------------

class IndiceDisciplinasTests(DisciplinaTestCase):
    def test_lista_so_disciplinas_com_provas_separadas_por_unidade(self):
        self.prova_de(self.professor)
        self.prova_de(self.professor, tipo='P2')
        self.prova_de(self.outro, disciplina=self.fisica)

        response = self.client.get(self.indice_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('disciplina_provas', kwargs={'codigo': 'MAT0111'}))
        self.assertContains(response, reverse('disciplina_provas', kwargs={'codigo': '4302111'}))
        self.assertNotContains(response, 'MAT0112')
        self.assertContains(response, 'Instituto de Física')
        self.assertContains(response, 'Instituto de Matemática e Estatística')
        self.assertContains(response, '3 provas de 2 disciplinas')

    def test_contagem_de_provas_professores_e_semestre_mais_recente(self):
        self.prova_de(self.professor, semestre='2023/2')
        self.prova_de(self.outro, semestre='2025/1')
        self.prova_de(self.outro, semestre='2024/1')

        response = self.client.get(self.indice_url)
        calculo = response.context['com_provas'].get(codigo='MAT0111')
        self.assertEqual((calculo.total_provas, calculo.total_professores, calculo.ultimo_semestre), (3, 2, '2025/1'))
        self.assertContains(response, '3 provas')
        self.assertContains(response, '2 professores')
        self.assertContains(response, 'até 2025/1')

    def test_sem_provas_no_site(self):
        response = self.client.get(self.indice_url)
        self.assertContains(response, 'Ainda não há provas no site')

    def test_busca_sem_acento_separa_disciplinas_com_e_sem_provas(self):
        self.prova_de(self.professor)
        Disciplina.objects.create(codigo='MAT2453', nome='Cálculo Diferencial e Integral para Engenharia I')

        response = self.client.get(self.indice_url, {'q': 'calculo integral'})
        self.assertEqual([d.codigo for d in response.context['com_provas']], ['MAT0111'])
        self.assertEqual([d.codigo for d in response.context['sem_provas']], ['MAT2453'])
        self.assertContains(response, 'Ainda sem provas')
        self.assertNotContains(response, 'Vetores')

    def test_busca_por_codigo_exato_vai_direto_para_a_disciplina(self):
        response = self.client.get(self.indice_url, {'q': ' mat0112 '})
        self.assertRedirects(response, reverse('disciplina_provas', kwargs={'codigo': 'MAT0112'}))

    def test_busca_sem_resultado(self):
        response = self.client.get(self.indice_url, {'q': 'astrologia'})
        self.assertContains(response, 'Nenhuma disciplina encontrada')

    def test_busca_curta_pede_mais_letras(self):
        response = self.client.get(self.indice_url, {'q': 'a'})
        self.assertContains(response, 'pelo menos duas letras')

    def test_busca_limita_disciplinas_sem_provas(self):
        Disciplina.objects.bulk_create([
            Disciplina(codigo=f'FAP{numero:04d}', nome='Laboratório', busca=f'fap{numero:04d} laboratorio')
            for numero in range(25)
        ])
        response = self.client.get(self.indice_url, {'q': 'laboratorio'})
        self.assertEqual(len(response.context['sem_provas']), 20)
        self.assertContains(response, 'Mostrando 20 de 25')

    def test_link_no_menu(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, f'href="{self.indice_url}"')


# ---------------------------------------------------------------------------
# Página da disciplina /disciplinas/<codigo>/
# ---------------------------------------------------------------------------

class PaginaDisciplinaTests(DisciplinaTestCase):
    def test_mostra_provas_de_todos_os_professores_da_disciplina(self):
        da_ana = self.prova_de(self.professor, semestre='2024/1')
        do_bruno = self.prova_de(self.outro, semestre='2025/2')
        de_outra_disciplina = self.prova_de(self.outro, disciplina=self.algebra)

        response = self.client.get(self.calculo_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana Souza')
        self.assertContains(response, 'Bruno Lima')
        self.assertContains(response, reverse('prova_detalhe', kwargs={'pk': da_ana.pk}))
        self.assertContains(response, reverse('prova_detalhe', kwargs={'pk': do_bruno.pk}))
        self.assertNotContains(response, reverse('prova_detalhe', kwargs={'pk': de_outra_disciplina.pk}))
        self.assertContains(response, '2 provas de 2 professores')

    def test_professor_com_prova_mais_recente_vem_primeiro(self):
        self.prova_de(self.professor, semestre='2024/1')
        self.prova_de(self.outro, semestre='2025/2')
        self.prova_de(self.outro, semestre='2020/1')

        grupos = self.client.get(self.calculo_url).context['grupos']
        self.assertEqual([g['professor'].nome for g in grupos], ['Bruno Lima', 'Ana Souza'])
        self.assertEqual([p.semestre for p in grupos[0]['provas']], ['2025/2', '2020/1'])

    def test_empate_de_semestre_em_ordem_alfabetica(self):
        self.prova_de(self.outro, semestre='2025/1')
        self.prova_de(self.professor, semestre='2025/1')
        grupos = self.client.get(self.calculo_url).context['grupos']
        self.assertEqual([g['professor'].nome for g in grupos], ['Ana Souza', 'Bruno Lima'])

    def test_folha_pontilhada_envia_com_o_professor_e_a_disciplina(self):
        self.prova_de(self.outro)
        response = self.client.get(self.calculo_url)
        envio_do_bruno = reverse('enviar_prova', kwargs={'pk': self.outro.pk})
        self.assertContains(response, f'{envio_do_bruno}?disciplina=MAT0111')
        self.assertContains(response, reverse('enviar_prova_disciplina', kwargs={'codigo': 'MAT0111'}))

    def test_mostra_miniatura_das_fotos(self):
        prova = self.criar_prova(arquivos=[foto_jpeg(), foto_jpeg('p2.jpg')])
        response = self.client.get(self.calculo_url)
        self.assertContains(response, reverse('miniatura_prova', kwargs={'pk': prova.arquivos.first().pk}))
        self.assertContains(response, 'varias-paginas')

    def test_nota_do_professor_ignora_avaliacoes_fora_da_media(self):
        self.prova_de(self.professor)
        Avaliacao.objects.create(titulo='Boa', professor=self.professor, starter=self.user, nota_geral=4)
        Avaliacao.objects.create(titulo='Importada', professor=self.professor, nota_geral=0, excluir_da_media=True)

        response = self.client.get(self.calculo_url)
        self.assertContains(response, 'Nota geral 4,0/5 em 2 avaliações')

    def test_professor_sem_avaliacoes(self):
        self.prova_de(self.outro)
        self.assertContains(self.client.get(self.calculo_url), 'Ainda sem avaliações')

    def test_disciplina_sem_provas_convida_a_enviar(self):
        response = self.client.get(reverse('disciplina_provas', kwargs={'codigo': 'MAT0112'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ainda não há provas de MAT0112')
        self.assertContains(response, reverse('enviar_prova_disciplina', kwargs={'codigo': 'MAT0112'}))

    def test_codigo_fora_do_catalogo_da_404(self):
        response = self.client.get(reverse('disciplina_provas', kwargs={'codigo': 'XYZ9999'}))
        self.assertEqual(response.status_code, 404)

    def test_codigo_em_minusculas_redireciona_para_o_oficial(self):
        response = self.client.get(reverse('disciplina_provas', kwargs={'codigo': 'mat0111'}))
        self.assertRedirects(response, self.calculo_url, status_code=301)

    def test_link_da_ementa_no_jupiterweb(self):
        response = self.client.get(self.calculo_url)
        self.assertContains(response, 'https://uspdigital.usp.br/jupiterweb/obterDisciplina?sgldis=MAT0111')

    def test_codigo_antigo_com_hifen_abre_sem_link_do_jupiterweb(self):
        Disciplina.objects.create(codigo='MAC-0115', nome='Introdução à Computação')
        response = self.client.get(reverse('disciplina_provas', kwargs={'codigo': 'MAC-0115'}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'jupiterweb')

    def test_rota_de_busca_nao_e_confundida_com_codigo(self):
        response = self.client.get(reverse('buscar_disciplinas'), {'q': 'calculo'})
        self.assertEqual(response['Content-Type'], 'application/json')


class LinksParaADisciplinaTests(DisciplinaTestCase):
    def test_aba_do_professor_liga_para_a_disciplina_e_conta_provas_de_outros(self):
        self.prova_de(self.professor)
        self.prova_de(self.outro)
        self.prova_de(self.outro, tipo='P2')

        response = self.client.get(self.provas_url)
        self.assertContains(response, f'href="{self.calculo_url}"')
        self.assertContains(response, '+ 2 provas com outros professores')

    def test_aba_sem_provas_de_outros_nao_mostra_o_aviso(self):
        self.prova_de(self.professor)
        self.prova_de(self.outro, disciplina=self.fisica)
        response = self.client.get(self.provas_url)
        self.assertNotContains(response, 'com outros professores')

    def test_pagina_da_prova_liga_para_a_disciplina(self):
        prova = self.prova_de(self.professor)
        response = self.client.get(reverse('prova_detalhe', kwargs={'pk': prova.pk}))
        self.assertContains(response, f'href="{self.calculo_url}"')
        self.assertContains(response, 'Todas as provas de MAT0111')


# ---------------------------------------------------------------------------
# Envio pela página da disciplina (a pessoa escolhe o professor)
# ---------------------------------------------------------------------------

class EnviarPelaDisciplinaTests(DisciplinaTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('enviar_prova_disciplina', kwargs={'codigo': 'MAT0111'})
        self.client.login(username='john', password='123')

    def dados(self, **extra):
        dados = {'professor': 'Bruno Lima', 'semestre': '2024/2', 'tipo': 'P1', 'observacao': '', 'arquivos': [pdf()]}
        dados.update(extra)
        return dados

    def test_exige_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{reverse("login")}?next={self.url}')

    def test_formulario_pede_o_professor_e_nao_a_disciplina(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="professor"')
        self.assertNotContains(response, 'name="disciplina"')
        self.assertContains(response, 'Cálculo Diferencial e Integral I')
        self.assertContains(response, f'{reverse("buscar_professores")}?disciplina=MAT0111')

    def test_sugere_professores_que_ja_tem_provas_da_disciplina(self):
        self.prova_de(self.outro)
        self.prova_de(self.professor, disciplina=self.algebra)
        response = self.client.get(self.url)
        self.assertContains(response, 'data-sugestao="Bruno Lima"')
        self.assertNotContains(response, 'data-sugestao="Ana Souza"')

    def test_envio_valido_cria_a_prova_do_professor_escolhido(self):
        response = self.client.post(self.url, self.dados())
        prova = ProvaAntiga.objects.get()
        self.assertRedirects(response, reverse('prova_detalhe', kwargs={'pk': prova.pk}))
        self.assertEqual((prova.professor, prova.disciplina, prova.enviado_por), (self.outro, self.calculo, self.user))
        self.assertEqual(prova.arquivos.count(), 1)

    def test_aceita_o_nome_sem_acento_e_em_minusculas(self):
        joao = Professor.objects.create(nome='João Álvares', descricao='IME')
        self.client.post(self.url, self.dados(professor='  joao   alvares '))
        self.assertEqual(ProvaAntiga.objects.get().professor, joao)

    def test_professor_que_nao_esta_no_site(self):
        response = self.client.post(self.url, self.dados(professor='Fulano de Tal'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Escolha um professor da lista')
        self.assertFalse(ProvaAntiga.objects.exists())

    def test_continua_validando_os_arquivos(self):
        response = self.client.post(self.url, self.dados(arquivos=[]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ProvaAntiga.objects.exists())

    def test_limite_diario_vale_tambem_aqui(self):
        with self.settings(PROVAS_LIMITE_DIARIO=1):
            self.prova_de(self.professor, enviado_por=self.user)
            response = self.client.post(self.url, self.dados())
        self.assertContains(response, 'limite diário')
        self.assertEqual(ProvaAntiga.objects.count(), 1)

    def test_disciplina_fora_do_catalogo_da_404(self):
        response = self.client.get(reverse('enviar_prova_disciplina', kwargs={'codigo': 'XYZ9999'}))
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Sugestões do campo Professor
# ---------------------------------------------------------------------------

class BuscarProfessoresTests(DisciplinaTestCase):
    def buscar(self, q, **extra):
        response = self.client.get(reverse('buscar_professores'), {'q': q, **extra})
        return [r['nome'] for r in response.json()['resultados']]

    def test_busca_sem_acento_e_por_varias_palavras(self):
        Professor.objects.create(nome='João Álvares', descricao='IF')
        self.assertEqual(self.buscar('joao'), ['João Álvares'])
        self.assertEqual(self.buscar('alvares jo'), ['João Álvares'])
        self.assertEqual(self.buscar('joao lima'), [])

    def test_busca_curta_nao_retorna_nada(self):
        self.assertEqual(self.buscar('a'), [])

    def test_prioriza_quem_tem_provas_da_disciplina_depois_a_unidade(self):
        usp = Universidade.objects.get(sigla='USP')
        instituto_fisica = Instituto.objects.create(nome='Instituto de Física', sigla='IF', universidade=usp)
        Professor.objects.create(nome='Carla Alves', descricao='IME', instituto=self.ime)
        Professor.objects.create(nome='Carla Bento', descricao='IF', instituto=instituto_fisica)
        com_prova = Professor.objects.create(nome='Carla Costa', descricao='IME', instituto=self.ime)
        self.prova_de(com_prova, disciplina=self.fisica)

        self.assertEqual(self.buscar('carla', disciplina='4302111'), ['Carla Costa', 'Carla Bento', 'Carla Alves'])
        self.assertEqual(self.buscar('carla'), ['Carla Alves', 'Carla Bento', 'Carla Costa'])

    def test_mostra_o_instituto(self):
        response = self.client.get(reverse('buscar_professores'), {'q': 'bruno'})
        self.assertEqual(response.json()['resultados'], [{'nome': 'Bruno Lima', 'instituto': 'Instituto de Matemática e Estatística'}])
