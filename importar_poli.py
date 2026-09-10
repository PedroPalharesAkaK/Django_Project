import os
import sys
import django

# Evita erro de encoding ao imprimir emojis/acentos no console do Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 1. Conecta este script às configurações do seu projeto Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ProjetoDjanto.settings')
django.setup()

from boards.models import Professor, Instituto, Universidade


def popular_banco_dados():
    caminho_arquivo = os.path.join('zNome professores', 'Nome professores poli.txt')

    usp, _ = Universidade.objects.get_or_create(
        sigla="USP",
        defaults={"nome": "Universidade de São Paulo"}
    )

    poli, _ = Instituto.objects.get_or_create(
        sigla="EP",
        defaults={"nome": "Escola Politécnica", "universidade": usp}
    )

    with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()

    cadastrados = 0
    ignorados = 0

    print("Iniciando a importação de docentes da Escola Politécnica...\n")

    for linha in linhas:
        nome = linha.strip()

        if len(nome) > 2 and not nome.startswith('['):
            professor, foi_criado = Professor.objects.get_or_create(
                nome=nome,
                defaults={
                    'descricao': 'Escola Politécnica (Poli)',
                    'visualizacoes': 0,
                    'universidade': usp,
                    'instituto': poli,
                }
            )

            if foi_criado:
                cadastrados += 1
                print(f"✅ Cadastrado: {nome}")
            else:
                ignorados += 1

    print("\n" + "=" * 40)
    print("RELATÓRIO DE IMPORTAÇÃO")
    print("=" * 40)
    print(f"Novos professores inseridos: {cadastrados}")
    print(f"Nomes já existentes ignorados: {ignorados}")


if __name__ == '__main__':
    popular_banco_dados()
