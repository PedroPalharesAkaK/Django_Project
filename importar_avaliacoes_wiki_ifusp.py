import os
import sys
import re
import json
import unicodedata
import django

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ProjetoDjanto.settings')
django.setup()

from django.contrib.auth.models import User
from boards.models import Professor, Avaliacao, Comentario

CAMINHO_DADOS = os.path.join('data_wiki_ifusp', 'avaliacoes_wiki_final.json')

FONTE_URL = 'https://ifusp.fandom.com/wiki/Professores'

# Nomes de arquivo que precisam de correção/normalização para bater com o
# nome oficial já cadastrado no site (abreviações, apelidos, typos da wiki).
CORRECOES_NOME = {
    'Manoel Robillota': 'Manoel Roberto Robilotta',
    'Ernesto G. Birgin': 'Ernesto Birgin',
    'Guilherme Menegon Arante (IQ)': 'Guilherme Menegon Arantes',
    'Enrico Bertuzzo (RIP)': 'Enrico Bertuzzo',
}


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = s.lower().strip()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'[^a-z ]', '', s)
    return s


def nome_arquivo_limpo(nome):
    return re.sub(r'\s*\([^)]*\)\s*$', '', nome).strip()


def encontrar_professor(nome_arquivo, todos_professores):
    nome_busca = CORRECOES_NOME.get(nome_arquivo, nome_arquivo_limpo(nome_arquivo))
    alvo = set(norm(nome_busca).split())
    for p in todos_professores:
        if alvo.issubset(set(norm(p.nome).split())):
            return p
    return None


def popular_banco_dados():
    autor, criado = User.objects.get_or_create(
        username='WikiIFUSP',
        defaults={
            'email': 'wiki-ifusp@avaliaprofessor.app',
            'first_name': 'Comunidade',
            'last_name': 'Wiki do IFUSP',
            'is_active': True,
        }
    )
    if criado:
        autor.set_unusable_password()
        autor.save()
        print(f"✅ Conta de sistema '{autor.username}' criada.")
    else:
        print(f"ℹ️  Conta de sistema '{autor.username}' já existia.")

    with open(CAMINHO_DADOS, 'r', encoding='utf-8') as f:
        registros = json.load(f)

    todos_professores = list(Professor.objects.all())

    criados = 0
    ignorados = 0
    sem_professor = 0
    professores_nao_encontrados = set()

    print(f"\nProcessando {len(registros)} avaliações da Wiki do IFUSP...\n")

    for reg in registros:
        professor = encontrar_professor(reg['arquivo'], todos_professores)
        if professor is None:
            sem_professor += 1
            professores_nao_encontrados.add(reg['arquivo'])
            continue

        avaliacao, foi_criada = Avaliacao.objects.get_or_create(
            professor=professor,
            starter=autor,
            titulo=reg['titulo'],
            defaults={
                'nota_geral': reg['nota_geral'],
                'nota_didatica': reg['nota_didatica'],
                'nota_empenho': reg['nota_empenho'],
                'nota_relacao': reg['nota_relacao'],
                'nota_dificuldade': reg['nota_dificuldade'],
                'excluir_da_media': reg['excluir_da_media'],
                'views': 0,
            }
        )

        if not foi_criada:
            ignorados += 1
            continue

        texto = reg['texto'] + f"\n\n*Comentário importado da [Wiki do IFUSP]({FONTE_URL}).*"
        Comentario.objects.create(
            texto=texto,
            avaliacao=avaliacao,
            created_by=autor,
        )
        criados += 1

    print("\n" + "=" * 40)
    print("RELATÓRIO DE IMPORTAÇÃO")
    print("=" * 40)
    print(f"Avaliações criadas: {criados}")
    print(f"Já existentes (ignoradas): {ignorados}")
    print(f"Sem professor correspondente: {sem_professor}")
    if professores_nao_encontrados:
        print("\nProfessores da wiki que não foram encontrados no banco:")
        for nome in sorted(professores_nao_encontrados):
            print(f"  - {nome}")


if __name__ == '__main__':
    popular_banco_dados()
