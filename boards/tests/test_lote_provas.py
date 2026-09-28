import csv
import io
import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from ..lote_provas import chave_de_pagina, identificar_tipo, interpretar_pasta_professor, parece_avaliacao
from ..models import Disciplina, Professor, ProvaAntiga
from .test_provas_antigas import MediaTemporariaMixin

PDF = b'%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n'


def jpeg_bytes(cor='white'):
    saida = io.BytesIO()
    Image.new('RGB', (300, 420), cor).save(saida, 'JPEG')
    return saida.getvalue()


class InterpretarPastaProfessorTests(TestCase):
    def test_formatos_de_semestre(self):
        casos = {
            '2024-2 - Germano Penello': ('2024/2', 'Germano Penello'),       # "/" vira "-" no ZIP do Drive
            '2018_2 - Ivan Shestakov - IME': ('2018/2', 'Ivan Shestakov'),   # rótulo de turma descartado
            '2-2020 Sylvain Bonnot': ('2020/2', 'Sylvain Bonnot'),           # semestre antes do ano
            '02-2020 Tiago Fiorini': ('2020/2', 'Tiago Fiorini'),
            '2020-01 - Luís Moreira': ('2020/1', 'Luís Moreira'),
            'Paulo Costa - 2017-1': ('2017/1', 'Paulo Costa'),               # data no fim
            'Navarra(2022)': ('2022/1', 'Navarra'),                          # só o ano: 1º semestre
            '2018 - Ricardo dos Santos Freire Jr': ('2018/1', 'Ricardo dos Santos Freire Jr'),
            '2017-_ - Albert Meads Fisher': ('2017/1', 'Albert Meads Fisher'),  # "2017/?" no Drive
            '2024-2 - Noturno - Corneta': ('2024/2', 'Corneta'),
            '2019_1 -Marchetti': ('2019/1', 'Marchetti'),
            'Antonio Carlos Brolezzi': (None, 'Antonio Carlos Brolezzi'),    # sem data
        }
        for pasta, esperado in casos.items():
            with self.subTest(pasta=pasta):
                self.assertEqual(interpretar_pasta_professor(pasta), esperado)


class IdentificarTipoTests(TestCase):
    def test_tipos(self):
        casos = {
            'P1_2024-2.pdf': 'P1',
            'Provas/Prova 2.pdf': 'P2',
            'MecUsp_2Sem2015_prova01_sol.pdf': 'P1',
            'Mat2352IFw2020ProvaP1 (5).pdf': 'P1',
            'P1MAT0216-2019-Gabarito.pdf': 'P1',
            'GabaritoP2.pdf': 'P2',
            'gab-P2-D.pdf': 'P2',
            'PI - 2020.1.pdf': 'P1',
            'P1 e gabarito/Prova1_3.jpeg': 'P1',
            'PSUB_2024-2.pdf': 'SUB',
            'Provas/Prova 3 (SUB) - 2018.pdf': 'SUB',
            'MecUsp_2Sem2015_prova02_Sub_sol.pdf': 'SUB',
            'Provas/Prova Recuperação.pdf': 'REC',
            # Provinhas, listas e exercícios são "Outra", mesmo com número no nome
            'Provinhas/p1.pdf': 'OUTRA',
            'Provinha 3 Gabarito.pdf': 'OUTRA',
            'Listas_Relatividade_Gabarito - P1.pdf': 'OUTRA',
            'l5_19-sol.pdf': 'OUTRA',
            'MecUsp_2Sem2015_teste03.pdf': 'OUTRA',
            'EPs/EP 1.pdf': 'OUTRA',
            'p4.pdf': 'OUTRA',
        }
        for caminho, esperado in casos.items():
            with self.subTest(caminho=caminho):
                self.assertEqual(identificar_tipo(caminho), esperado)

    def test_o_que_parece_avaliacao(self):
        for caminho in ['P.pdf', 'Lista 1.pdf', 'resolucao-p1.pdf', 'AA1 (2).pdf', 'SUB1.pdf', 'Atividades_Exercicios.pdf']:
            with self.subTest(caminho=caminho):
                self.assertTrue(parece_avaliacao(caminho))
        for caminho in ['spin1.pdf', 'aula0205_notas.pdf', 'boyer_ajp_56_688_88.pdf', 'Sumula.pdf', 'Laplace.pdf']:
            with self.subTest(caminho=caminho):
                self.assertFalse(parece_avaliacao(caminho))

    def test_chave_de_pagina(self):
        self.assertEqual(chave_de_pagina('Prova1_12.jpeg'), ('prova1', 12))
        self.assertEqual(chave_de_pagina('pagina 3.jpg'), ('pagina', 3))
        self.assertEqual(chave_de_pagina('P3 001.jpg'), ('p3', 1))
        self.assertEqual(chave_de_pagina('P1 Shestakov.jpg'), ('p1 shestakov', None))


class PrepararLoteTests(TestCase):
    """Monta uma pasta no formato do Drive e confere o lote gerado."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp, ignore_errors=True))
        self.origem = self.tmp / 'BANCO DE PROVAS'
        arquivos = {
            'Física II/2016-2 - Andre Vieira/P1-1.pdf': PDF,
            'Física II/2016-2 - Andre Vieira/Provinha3.0.pdf': PDF + b'provinha',
            'Física II/2016-2 - Andre Vieira/P1.docx': b'docx',
            'Física II/2016-2 - Andre Vieira/notas_de_aula.pdf': PDF + b'notas',
            'Física II/2016-2 - Andre Vieira/copia/P1-1.pdf': PDF,                  # mesmo conteúdo do P1-1
            'Física II/2016-2 - Andre Vieira/Fulano de Tal Lista 1.pdf': PDF + b'aluno',
            'Física II/2018-2 - Corneta/P1.pdf': PDF + b'corneta',
            'Física II/solto.pdf': PDF + b'solto',
            'Mecânica I/2012-1 - Ana Regina Blak/P3/P3 002.jpg': jpeg_bytes('gray'),
            'Mecânica I/2012-1 - Ana Regina Blak/P3/P3 001.jpg': jpeg_bytes(),
            'MAT220DUSSAN2025P1.pdf': PDF + b'dussan',
        }
        for caminho, conteudo in arquivos.items():
            destino = self.origem / caminho
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(conteudo)
        self.mapa = self.tmp / 'mapa.json'
        self.mapa.write_text(json.dumps({
            'fonte': 'Banco de Provas do IFUSP',
            'disciplinas': {'Física II': '4302112', 'Mecânica I': '4302305'},
            'professores': {'Andre Vieira': 'Andre de Pinho Vieira', 'Ana Regina Blak': 'Ana Regina Blak', 'Corneta': None},
            'professores_a_confirmar': ['Andre Vieira'],
            'avulsos': {'MAT220DUSSAN2025P1.pdf': {'disciplina': 'MAT0220', 'professor': 'Martha Patrícia Dussan Angulo',
                                                   'semestre': '2025/1', 'tipo': 'P1', 'confirmar': 'MAT220 Dussan'}},
            'excluir': [{'padrao': 'Fulano de Tal', 'motivo': 'nome de aluno'}],
        }), encoding='utf-8')
        self.lote = self.tmp / 'lote'
        call_command('preparar_lote_provas', str(self.origem), str(self.lote), mapa=str(self.mapa), stdout=io.StringIO())
        with open(self.lote / 'manifesto.csv', newline='', encoding='utf-8-sig') as f:
            self.linhas = {l['origem']: l for l in csv.DictReader(f, delimiter=';')}
        with open(self.lote / 'excluidos.csv', newline='', encoding='utf-8-sig') as f:
            self.excluidos = dict(csv.reader(f, delimiter=';'))

    def test_prova_normal_entra(self):
        linha = self.linhas['Física II/2016-2 - Andre Vieira/P1-1.pdf']
        self.assertEqual(linha['incluir'], 'sim')
        self.assertEqual((linha['disciplina'], linha['professor'], linha['semestre'], linha['tipo']),
                         ('4302112', 'Andre de Pinho Vieira', '2016/2', 'P1'))
        self.assertEqual(linha['observacao'], 'Banco de Provas do IFUSP (arquivo: P1-1.pdf)')
        self.assertNotIn('Andre', linha['alerta'])  # a confirmação do professor fica no topo da revisão
        self.assertTrue((self.lote / linha['arquivos']).is_file())

    def test_fotos_da_mesma_prova_viram_uma_prova_em_ordem(self):
        linha = self.linhas['Mecânica I/2012-1 - Ana Regina Blak/P3/P3 001.jpg|Mecânica I/2012-1 - Ana Regina Blak/P3/P3 002.jpg']
        self.assertEqual(linha['tipo'], 'P3')
        self.assertEqual(len(linha['arquivos'].split('|')), 2)

    def test_provinha_entra_como_outra(self):
        self.assertEqual(self.linhas['Física II/2016-2 - Andre Vieira/Provinha3.0.pdf']['tipo'], 'OUTRA')

    def test_o_que_nao_parece_prova_fica_para_conferir(self):
        linha = self.linhas['Física II/2016-2 - Andre Vieira/notas_de_aula.pdf']
        self.assertEqual(linha['incluir'], 'nao')
        self.assertIn('não parece prova', linha['alerta'])

    def test_professor_fora_do_site_fica_de_fora(self):
        linha = self.linhas['Física II/2018-2 - Corneta/P1.pdf']
        self.assertEqual(linha['incluir'], 'nao')
        self.assertEqual(linha['professor'], '')

    def test_arquivo_avulso_do_mapa(self):
        linha = self.linhas['MAT220DUSSAN2025P1.pdf']
        self.assertEqual((linha['disciplina'], linha['semestre'], linha['tipo']), ('MAT0220', '2025/1', 'P1'))

    def test_descartes(self):
        self.assertIn('formato .docx', self.excluidos['Física II/2016-2 - Andre Vieira/P1.docx'])
        self.assertIn('duplicata', self.excluidos['Física II/2016-2 - Andre Vieira/copia/P1-1.pdf'])
        self.assertEqual(self.excluidos['Física II/2016-2 - Andre Vieira/Fulano de Tal Lista 1.pdf'], 'nome de aluno')
        self.assertIn('arquivo solto', self.excluidos['Física II/solto.pdf'])

    def test_pagina_de_revisao(self):
        pagina = (self.lote / 'revisao.html').read_text(encoding='utf-8')
        self.assertIn('Revisão do lote', pagina)
        self.assertIn('Professores ligados por aproximação', pagina)
        self.assertIn('"Andre Vieira" é <strong>Andre de Pinho Vieira</strong>', pagina)

    def test_nao_sobrescreve_lote_existente(self):
        with self.assertRaisesMessage(CommandError, 'já existe'):
            call_command('preparar_lote_provas', str(self.origem), str(self.lote), mapa=str(self.mapa), stdout=io.StringIO())


class ImportarLoteTests(MediaTemporariaMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.professor = Professor.objects.create(nome='Andre de Pinho Vieira', descricao='IF')
        self.disciplina = Disciplina.objects.create(codigo='4302112', nome='Física II', unidade='Instituto de Física')
        self.lote = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__('shutil').rmtree(self.lote, ignore_errors=True))
        (self.lote / 'arquivos').mkdir()
        (self.lote / 'miniaturas').mkdir()
        (self.lote / 'arquivos' / '0001-01.pdf').write_bytes(PDF)
        (self.lote / 'miniaturas' / '0001-01.jpg').write_bytes(jpeg_bytes())
        (self.lote / 'arquivos' / '0002-01.jpg').write_bytes(jpeg_bytes())
        (self.lote / 'arquivos' / '0002-02.jpg').write_bytes(jpeg_bytes('gray'))
        self.escrever_manifesto([
            self.linha(1, 'sim', 'P1', 'arquivos/0001-01.pdf', 'miniaturas/0001-01.jpg'),
            self.linha(2, 'sim', 'P2', 'arquivos/0002-01.jpg|arquivos/0002-02.jpg', '|'),
            self.linha(3, 'nao', 'P3', 'arquivos/nao-existe.pdf', ''),
        ])

    def linha(self, id, incluir, tipo, arquivos, miniaturas, professor='Andre de Pinho Vieira'):
        return {'id': id, 'incluir': incluir, 'alerta': '', 'disciplina': '4302112', 'professor': professor,
                'semestre': '2016/2', 'tipo': tipo, 'observacao': f'Banco de Provas do IFUSP (arquivo: {tipo}.pdf)',
                'arquivos': arquivos, 'miniaturas': miniaturas, 'origem': 'x'}

    def escrever_manifesto(self, linhas):
        with open(self.lote / 'manifesto.csv', 'w', newline='', encoding='utf-8-sig') as f:
            escritor = csv.DictWriter(f, fieldnames=list(linhas[0]), delimiter=';')
            escritor.writeheader()
            escritor.writerows(linhas)

    def importar(self, **opcoes):
        saida = io.StringIO()
        call_command('importar_lote_provas', str(self.lote), stdout=saida, stderr=io.StringIO(), **opcoes)
        return saida.getvalue()

    def test_simular_nao_grava_nada(self):
        saida = self.importar(simular=True)
        self.assertIn('2 provas seriam criadas', saida)
        self.assertFalse(ProvaAntiga.objects.exists())

    def test_importa_so_as_linhas_incluidas(self):
        self.assertIn('2 provas criadas', self.importar())
        p1 = ProvaAntiga.objects.get(tipo='P1')
        self.assertIsNone(p1.enviado_por)
        self.assertEqual(p1.observacao, 'Banco de Provas do IFUSP (arquivo: P1.pdf)')
        pdf = p1.arquivos.get()
        self.assertTrue(pdf.is_pdf())
        self.assertTrue(pdf.miniatura)  # miniatura do lote vira a capa do PDF
        self.assertEqual(ProvaAntiga.objects.get(tipo='P2').arquivos.count(), 2)
        self.assertFalse(ProvaAntiga.objects.filter(tipo='P3').exists())

    def test_rodar_de_novo_nao_duplica(self):
        self.importar()
        self.assertIn('0 provas criadas, 2 já existiam', self.importar())
        self.assertEqual(ProvaAntiga.objects.count(), 2)

    def test_professor_inexistente_cancela_tudo(self):
        self.escrever_manifesto([
            self.linha(1, 'sim', 'P1', 'arquivos/0001-01.pdf', ''),
            self.linha(2, 'sim', 'P2', 'arquivos/0002-01.jpg', '', professor='Fulano Inexistente'),
        ])
        with self.assertRaisesMessage(CommandError, 'nada foi importado'):
            self.importar()
        self.assertFalse(ProvaAntiga.objects.exists())

    def test_prova_importada_mostra_data_e_nao_conta_removida(self):
        self.importar()
        prova = ProvaAntiga.objects.get(tipo='P1')
        response = self.client.get(reverse('prova_detalhe', kwargs={'pk': prova.pk}))
        self.assertContains(response, 'Adicionada ao site em')
        self.assertNotContains(response, 'conta removida')
        self.assertContains(response, 'Banco de Provas do IFUSP')
