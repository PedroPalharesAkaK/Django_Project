import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ProjetoDjanto.settings')
django.setup()

from boards.models import Professor, Instituto, Universidade


def popular_banco_dados():
    caminho_arquivo = os.path.join('zNome professores', 'Nome professores ifusp faltantes wiki.txt')

    usp, _ = Universidade.objects.get_or_create(
        sigla="USP",
        defaults={"nome": "Universidade de São Paulo"}
    )

    ifusp, _ = Instituto.objects.get_or_create(
        sigla="IF",
        defaults={"nome": "Instituto de Física", "universidade": usp}
    )

    with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()

    cadastrados = 0
    ignorados = 0

    print("Iniciando a importação de docentes do IFUSP (achados via Wiki do IFUSP)...\n")

    for linha in linhas:
        nome = linha.strip()

        if len(nome) > 2 and not nome.startswith('['):
            professor, foi_criado = Professor.objects.get_or_create(
                nome=nome,
                defaults={
                    'descricao': 'Instituto de Física (IF)',
                    'visualizacoes': 0,
                    'universidade': usp,
                    'instituto': ifusp,
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
