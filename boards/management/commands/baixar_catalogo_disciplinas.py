import json
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand

URL_PADRAO = 'https://uspavalia.com/api/matrusp/disciplines'
ARQUIVO_PADRAO = Path(__file__).resolve().parents[2] / 'data' / 'disciplinas_usp.json'


def resumir_catalogo(disciplinas):
    """Fica só com o que o site usa: código, nome, unidade e departamento."""
    resumo = {}
    for item in disciplinas:
        codigo = (item.get('codigo') or '').strip()
        if codigo:
            resumo[codigo] = {
                'codigo': codigo,
                'nome': (item.get('nome') or '').strip(),
                'unidade': (item.get('unidade') or '').strip(),
                'departamento': (item.get('departamento') or '').strip(),
            }
    return [resumo[codigo] for codigo in sorted(resumo)]


class Command(BaseCommand):
    help = (
        'Baixa o catálogo de disciplinas da USP (dados da JupiterWeb publicados pela API do USPAvalia) '
        'e grava um resumo em boards/data/disciplinas_usp.json. Rode no seu computador, não no servidor: '
        'a resposta da API é grande. Depois faça commit do JSON e rode importar_disciplinas.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--url', default=URL_PADRAO)
        parser.add_argument('--saida', default=str(ARQUIVO_PADRAO))

    def handle(self, *args, **options):
        pedido = urllib.request.Request(options['url'], headers={'User-Agent': 'avaliaprofessor.app'})
        with urllib.request.urlopen(pedido, timeout=120) as resposta:
            dados = json.load(resposta)
        disciplinas = dados if isinstance(dados, list) else list(dados.values())

        resumo = resumir_catalogo(disciplinas)
        saida = Path(options['saida'])
        saida.parent.mkdir(parents=True, exist_ok=True)
        saida.write_text(json.dumps(resumo, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'{len(resumo)} disciplinas gravadas em {saida}.'))
