"""Importa um lote gerado pelo preparar_lote_provas.

No servidor, com a pasta do lote dentro de ~/Django_Project (visível no container em /app):

    docker compose exec web python manage.py importar_lote_provas importacao/lote_ifusp --simular
    docker compose exec web python manage.py importar_lote_provas importacao/lote_ifusp

Só entram as linhas com incluir = sim. Pode rodar de novo: prova que já existe (mesmo professor,
disciplina, semestre, tipo e observação) é pulada. Se alguma linha tiver problema (professor ou
disciplina que não existe no banco, arquivo faltando...), nada é importado.
"""
import csv
import re
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from boards.models import Disciplina, Professor, ProvaAntiga
from boards.provas import preparar_arquivo, salvar_arquivos

TIPOS = {codigo for codigo, _ in ProvaAntiga.TIPOS}


class Command(BaseCommand):
    help = 'Importa as provas de um lote (manifesto.csv + arquivos/ + miniaturas/).'

    def add_arguments(self, parser):
        parser.add_argument('pasta', help='Pasta do lote')
        parser.add_argument('--simular', action='store_true', help='Só confere e mostra o que seria importado')

    def handle(self, *args, **options):
        pasta = Path(options['pasta'])
        manifesto = pasta / 'manifesto.csv'
        if not manifesto.is_file():
            raise CommandError(f'Não achei {manifesto}')
        with open(manifesto, newline='', encoding='utf-8-sig') as f:
            linhas = [l for l in csv.DictReader(f, delimiter=';') if l['incluir'].strip().lower() == 'sim']

        professores = {p.nome: p for p in Professor.objects.filter(nome__in={l['professor'] for l in linhas})}
        disciplinas = {d.codigo: d for d in Disciplina.objects.filter(codigo__in={l['disciplina'] for l in linhas})}

        problemas = []
        for l in linhas:
            if l['professor'] not in professores:
                problemas.append(f'#{l["id"]}: professor "{l["professor"]}" não existe no banco')
            if l['disciplina'] not in disciplinas:
                problemas.append(f'#{l["id"]}: disciplina {l["disciplina"]} não existe (rodou o importar_disciplinas?)')
            if not re.fullmatch(r'\d{4}/[12]', l['semestre']):
                problemas.append(f'#{l["id"]}: semestre inválido "{l["semestre"]}"')
            if l['tipo'] not in TIPOS:
                problemas.append(f'#{l["id"]}: tipo inválido "{l["tipo"]}"')
            if len(l['observacao']) > 200:
                problemas.append(f'#{l["id"]}: observação com mais de 200 caracteres')
            for caminho in l['arquivos'].split('|'):
                if not (pasta / caminho).is_file():
                    problemas.append(f'#{l["id"]}: arquivo {caminho} não está na pasta do lote')
        if problemas:
            for problema in problemas:
                self.stderr.write(problema)
            raise CommandError(f'{len(problemas)} problema(s) no manifesto; nada foi importado.')

        novas, existentes = [], 0
        for l in linhas:
            ja_existe = ProvaAntiga.objects.filter(
                professor=professores[l['professor']], disciplina=disciplinas[l['disciplina']],
                semestre=l['semestre'], tipo=l['tipo'], observacao=l['observacao'],
            ).exists()
            if ja_existe:
                existentes += 1
            else:
                novas.append(l)

        if options['simular']:
            self.stdout.write(f'Simulação: {len(novas)} provas seriam criadas, {existentes} já existem. Nada foi gravado.')
            return

        criadas = 0
        for l in novas:
            try:
                self.importar(pasta, l, professores[l['professor']], disciplinas[l['disciplina']])
            except ValidationError as erro:
                raise CommandError(f'#{l["id"]}: {" ".join(erro.messages)} ({criadas} provas já tinham sido criadas)')
            criadas += 1
            if criadas % 25 == 0:
                self.stdout.write(f'  {criadas} de {len(novas)}...')
        self.stdout.write(self.style.SUCCESS(f'{criadas} provas criadas, {existentes} já existiam.'))

    def importar(self, pasta, linha, professor, disciplina):
        caminhos = linha['arquivos'].split('|')
        miniaturas = (linha.get('miniaturas') or '').split('|')
        abertos = [open(pasta / c, 'rb') for c in caminhos]
        try:
            preparados = []
            for ordem, (caminho, aberto) in enumerate(zip(caminhos, abertos)):
                preparado = preparar_arquivo(File(aberto, name=Path(caminho).name))
                miniatura = miniaturas[ordem] if ordem < len(miniaturas) else ''
                if preparado.miniatura is None and miniatura and (pasta / miniatura).is_file():
                    preparado.miniatura = (pasta / miniatura).read_bytes()  # primeira página do PDF
                preparados.append(preparado)
            with transaction.atomic():
                prova = ProvaAntiga.objects.create(
                    professor=professor, disciplina=disciplina, semestre=linha['semestre'],
                    tipo=linha['tipo'], observacao=linha['observacao'], enviado_por=None,
                )
                salvar_arquivos(prova, preparados)
        finally:
            for aberto in abertos:
                aberto.close()
