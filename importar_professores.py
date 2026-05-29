import os
import django

# 1. Conecta este script às configurações do seu projeto Django
# Substitua 'ProjetoDjanto.settings' pelo nome exato da sua pasta principal, se for diferente
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ProjetoDjanto.settings')

# Inicia o motor do Django
django.setup()

# 2. Só podemos importar os models DEPOIS de rodar o django.setup()
from boards.models import Professor

def popular_banco_dados():
    caminho_arquivo = 'Nome professores ifusp.txt'
    
    # Abre o arquivo garantindo a leitura correta de acentos (utf-8)
    with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()

    cadastrados = 0
    ignorados = 0

    print("Iniciando a importação de docentes...\n")

    for linha in linhas:
        # Remove quebras de linha (\n) e espaços nas pontas
        nome = linha.strip()

        # Verifica se a linha não está vazia e ignora marcações de sistema (se houver)
        if len(nome) > 2 and not nome.startswith('['):
            
            # O get_or_create é mágico: ele verifica se o nome já existe. 
            # Se existir, ele ignora. Se não existir, ele cria. 
            # Isso impede professores duplicados se você rodar o script duas vezes!
            professor, foi_criado = Professor.objects.get_or_create(
                nome=nome,
                defaults={
                    'descricao': 'Instituto de Física da USP (IFUSP)',
                    'visualizacoes': 0
                }
            )

            if foi_criado:
                cadastrados += 1
                print(f"✅ Cadastrado: {nome}")
            else:
                ignorados += 1

    print("\n" + "="*40)
    print("RELATÓRIO DE IMPORTAÇÃO")
    print("="*40)
    print(f"Novos professores inseridos: {cadastrados}")
    print(f"Nomes já existentes ignorados: {ignorados}")

if __name__ == '__main__':
    popular_banco_dados()