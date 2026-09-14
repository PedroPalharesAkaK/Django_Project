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

CAMINHO_DADOS = os.path.join('data_uspavalia', 'avaliacoes_uspavalia_final.json')

FONTE_URL = 'https://uspavalia.com/'


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = s.lower().strip()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'[^a-z ]', '', s)
    return s


def montar_indice_professores(todos_professores):
    por_nome_exato = {}
    for p in todos_professores:
        por_nome_exato.setdefault(norm(p.nome), []).append(p)
    return por_nome_exato


def encontrar_professor(nome_arquivo, por_nome_exato, todos_professores, ambiguos, sem_match):
    alvo_norm = norm(nome_arquivo)

    candidatos = por_nome_exato.get(alvo_norm)
    if candidatos:
        if len(candidatos) == 1:
            return candidatos[0]
        ambiguos.append((nome_arquivo, [c.nome for c in candidatos]))
        return None

    alvo_tokens = set(alvo_norm.split())
    candidatos = [p for p in todos_professores if alvo_tokens.issubset(set(norm(p.nome).split()))]
    if len(candidatos) == 1:
        return candidatos[0]
    if len(candidatos) > 1:
        ambiguos.append((nome_arquivo, [c.nome for c in candidatos]))
        return None

    sem_match.append(nome_arquivo)
    return None


def popular_banco_dados():
    autor, criado = User.objects.get_or_create(
        username='USPAvalia',
        defaults={
            'email': 'uspavalia@avaliaprofessor.app',
            'first_name': 'Comunidade',
            'last_name': 'USPAvalia',
            'is_active': True,
        }
    )
    if criado:
        autor.set_unusable_password()
        autor.save()
        print(f"Conta de sistema '{autor.username}' criada.")
    else:
        print(f"Conta de sistema '{autor.username}' ja existia.")

    with open(CAMINHO_DADOS, 'r', encoding='utf-8') as f:
        registros = json.load(f)

    todos_professores = list(Professor.objects.all())
    por_nome_exato = montar_indice_professores(todos_professores)

    avaliacoes_criadas = 0
    avaliacoes_existentes = 0
    comentarios_criados = 0
    sem_professor = 0
    ambiguos = []
    sem_match = []

    print(f"\nProcessando {len(registros)} avaliacoes do USPAvalia...\n")

    for reg in registros:
        professor = encontrar_professor(reg['arquivo'], por_nome_exato, todos_professores, ambiguos, sem_match)
        if professor is None:
            sem_professor += 1
            continue

        avaliacao, foi_criada = Avaliacao.objects.get_or_create(
            professor=professor,
            starter=autor,
            titulo=reg['titulo'],
            defaults={
                'nota_geral': reg['nota_5'],
                'nota_didatica': reg['nota_5'],
                'nota_empenho': reg['nota_5'],
                'nota_relacao': reg['nota_5'],
                'nota_dificuldade': 3 if not reg['excluir_da_media'] else 0,
                'excluir_da_media': reg['excluir_da_media'],
                'views': 0,
            }
        )

        if not foi_criada:
            avaliacoes_existentes += 1
            continue

        avaliacoes_criadas += 1
        for c in reg['comentarios']:
            data_str = f" em {c['data']}" if c.get('data') else ''
            texto = c['texto'] + f"\n\n*Comentário{data_str}, importado do [USPAvalia]({FONTE_URL}) com autorização do criador do site.*"
            Comentario.objects.create(
                texto=texto[:4000],
                avaliacao=avaliacao,
                created_by=autor,
            )
            comentarios_criados += 1

    print("\n" + "=" * 40)
    print("RELATORIO DE IMPORTACAO - USPAVALIA")
    print("=" * 40)
    print(f"Avaliacoes criadas: {avaliacoes_criadas}")
    print(f"Avaliacoes ja existentes (ignoradas): {avaliacoes_existentes}")
    print(f"Comentarios criados: {comentarios_criados}")
    print(f"Sem professor correspondente: {sem_professor}")
    if ambiguos:
        print(f"\nNomes ambiguos (mais de um candidato, PULADOS - revisar manualmente): {len(ambiguos)}")
        for nome, cands in ambiguos:
            print(f"  - {nome} -> {cands}")
    if sem_match:
        print(f"\nProfessores nao encontrados no banco: {len(sem_match)}")
        for nome in sorted(sem_match):
            print(f"  - {nome}")


if __name__ == '__main__':
    popular_banco_dados()
