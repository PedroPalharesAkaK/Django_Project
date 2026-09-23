import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from boards.models import Disciplina
from boards.utils import normalizar

from .baixar_catalogo_disciplinas import ARQUIVO_PADRAO

CAMPOS = ('nome', 'unidade', 'departamento')


class Command(BaseCommand):
    help = (
        'Importa o catálogo de disciplinas (boards/data/disciplinas_usp.json) para o banco. '
        'Pode rodar de novo quando o catálogo for atualizado: cria as novas e atualiza nomes que mudaram.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--arquivo', default=str(ARQUIVO_PADRAO))

    @transaction.atomic
    def handle(self, *args, **options):
        catalogo = json.loads(Path(options['arquivo']).read_text(encoding='utf-8'))

        existentes = {d.codigo: d for d in Disciplina.objects.all()}
        novas, alteradas = [], []
        for item in catalogo:
            disciplina = existentes.get(item['codigo'])
            if disciplina is None:
                disciplina = Disciplina(codigo=item['codigo'])
                novas.append(disciplina)
            elif all(getattr(disciplina, campo) == item.get(campo, '') for campo in CAMPOS):
                continue
            else:
                alteradas.append(disciplina)
            for campo in CAMPOS:
                setattr(disciplina, campo, item.get(campo, ''))
            # bulk_create/bulk_update não chamam save(): preenche a busca aqui
            disciplina.busca = normalizar(f'{disciplina.codigo} {disciplina.nome}')

        Disciplina.objects.bulk_create(novas, batch_size=1000)
        Disciplina.objects.bulk_update(alteradas, CAMPOS + ('busca',), batch_size=1000)

        self.stdout.write(self.style.SUCCESS(f'Disciplinas: {len(novas)} novas, {len(alteradas)} atualizadas.'))
