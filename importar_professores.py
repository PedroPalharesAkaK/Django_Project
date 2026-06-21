import os #[cite: 2]
import django #[cite: 2]
# super harcoded btw
# 1. Conecta este script às configurações do seu projeto Django[cite: 2]
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ProjetoDjanto.settings') #[cite: 2]
django.setup() #[cite: 2]

# IMPORTANTE: Agora também importamos Instituto e Universidade[cite: 2]
from boards.models import Professor, Instituto, Universidade

def popular_banco_dados(): #[cite: 2]
    # Atualizado para o novo arquivo
    caminho_arquivo = 'Nome professores fflchTLTC.txt' 
    
    # 2. Preparamos as chaves estrangeiras ANTES do loop começar
    usp, _ = Universidade.objects.get_or_create(
        sigla="USP",
        defaults={"nome": "Universidade de São Paulo"}
    )
    
    fflch, _ = Instituto.objects.get_or_create(
        sigla="fflch",
        defaults={"nome": "Faculdade de Filosofia, Letras e Ciências Humanas", "universidade": usp}
    )

    # Abre o arquivo garantindo a leitura correta de acentos (utf-8)[cite: 2]
    with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo: #[cite: 2]
        linhas = arquivo.readlines() #[cite: 2]

    cadastrados = 0 #[cite: 2]
    ignorados = 0 #[cite: 2]

    print("Iniciando a importação de docentes do fflch...\n") 

    for linha in linhas: #[cite: 2]
        # Remove quebras de linha (\n) e espaços nas pontas[cite: 2]
        nome = linha.strip() #[cite: 2]

        # Verifica se a linha não está vazia e ignora marcações de sistema (se houver)[cite: 2]
        if len(nome) > 2 and not nome.startswith('['): #[cite: 2]
            
            # O get_or_create é mágico: ele verifica se o nome já existe.[cite: 2]
            # Injetamos a universidade e o instituto no bloco de defaults!
            professor, foi_criado = Professor.objects.get_or_create( #[cite: 2]
                nome=nome, #[cite: 2]
                defaults={ #[cite: 2]
                    'descricao': 'Faculdade de Filosofia, Letras e Ciências Humanas (Teoria Literária e Literatura Comparada)', 
                    'visualizacoes': 0, #[cite: 2]
                    'universidade': usp,
                    'instituto': fflch
                }
            )

            if foi_criado: #[cite: 2]
                cadastrados += 1 #[cite: 2]
                print(f"✅ Cadastrado: {nome}") #[cite: 2]
            else: #[cite: 2]
                ignorados += 1 #[cite: 2]

    print("\n" + "="*40) #[cite: 2]
    print("RELATÓRIO DE IMPORTAÇÃO") #[cite: 2]
    print("="*40) #[cite: 2]
    print(f"Novos professores inseridos: {cadastrados}") #[cite: 2]
    print(f"Nomes já existentes ignorados: {ignorados}") #[cite: 2]

if __name__ == '__main__': #[cite: 2]
    popular_banco_dados() #[cite: 2]