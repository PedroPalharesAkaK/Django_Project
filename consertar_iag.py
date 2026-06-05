import os
import django

# 1. Conecta este script ao Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ProjetoDjanto.settings')
django.setup()

from boards.models import Professor, Instituto, Universidade

def consertar_dados():
    # Coloque o nome exato do arquivo de texto que você usou para o IAG
    caminho_arquivo = 'Nome professores iag.txt' 
    
    # 2. Garante que a USP e o IAG existem corretamente no banco
    usp = Universidade.objects.get(sigla="USP")
    iag, _ = Instituto.objects.get_or_create(
        sigla="IAG",
        defaults={"nome": "Instituto de Astronomia, Geofísica e Ciências Atmosféricas", "universidade": usp}
    )

    with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
        linhas = arquivo.readlines()

    atualizados = 0

    print("Iniciando a correção dos docentes do IAG...\n") 

    for linha in linhas:
        nome = linha.strip()

        if len(nome) > 2 and not nome.startswith('['):
            # 3. A Mágica do Overwrite:
            # Usamos o filter() para encontrar o professor pelo nome exato da lista,
            # e o .update() para reescrever APENAS os campos que estavam errados.
            linhas_afetadas = Professor.objects.filter(nome=nome).update(
                descricao='Instituto de Astronomia, Geofísica e Ciências Atmosféricas (IAG)',
                instituto=iag
            )
            
            if linhas_afetadas > 0:
                atualizados += 1
                print(f"🔄 Corrigido: {nome}")

    print("\n" + "="*40)
    print("RELATÓRIO DE CORREÇÃO")
    print("="*40)
    print(f"Professores do IAG atualizados com sucesso: {atualizados}")

if __name__ == '__main__':
    consertar_dados()