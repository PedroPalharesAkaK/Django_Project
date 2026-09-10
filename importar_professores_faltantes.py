import os
import sys
import django

# Evita erro de encoding ao imprimir emojis/acentos no console do Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 1. Conecta este script às configurações do seu projeto Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ProjetoDjanto.settings')
django.setup()

from boards.models import Professor, Instituto, Universidade

# Cada item: (sigla_instituto, nome_oficial_instituto, descricao_exibida, arquivo_txt)
# A "descricao" segue o mesmo texto que já aparece nos professores existentes
# de cada instituto, para manter a listagem consistente.
INSTITUTOS = [
    ("IME",   "Instituto de Matemática e Estatística",                         "Instituto de Matemática e Estatística (IME)",  "ime.txt"),
    ("IF",    "Instituto de Física",                                           "Instituto de Física (IF)",                     "ifusp.txt"),
    ("IAG",   "Instituto de Astronomia, Geofísica e Ciências Atmosféricas",    "Instituto de Astronomia, Geofísica e Ciências Atmosféricas (IAG)", "iag.txt"),
    ("IB",    "Instituto de Biociências",                                      "Instituto de Biociências",                     "ib.txt"),
    ("ICB",   "Instituto de Ciências Biomédicas",                              "Instituto de Ciências Biomédicas",             "icb.txt"),
    ("IGC",   "Instituto de Geociências",                                      "Instituto de Geociências",                     "igc.txt"),
    ("IO",    "Instituto Oceanográfico",                                       "Instituto de Oceanografia",                    "io.txt"),
    ("IP",    "Instituto de Psicologia",                                       "Instituto de Psicologia",                      "ip.txt"),
    ("IQ",    "Instituto de Química",                                          "Instituto de Química",                         "iq.txt"),
    ("IRI",   "Instituto de Relações Internacionais",                          "Instituto de Relações Internacionais",         "iri.txt"),
    ("FO",    "Faculdade de Odontologia",                                      "Faculdade de Odontologia",                     "fo.txt"),
    ("FMVZ",  "Faculdade de Medicina Veterinária e Zootecnia",                 "Faculdade de Medicina Veterinária e Zootecnia","fmvz.txt"),
    ("FCF",   "Faculdade de Ciências Farmacêuticas",                           "Faculdade de Ciências Farmacêuticas",          "fcf.txt"),
    ("FEA",   "Faculdade de Economia, Administração e Contabilidade",          "Faculdade de Economia e Administração",        "fea.txt"),
    ("FAU",   "Faculdade de Arquitetura e Urbanismo",                          "Faculdade de Arquitetura e Urbanismo",         "fau.txt"),
    ("ECA",   "Escola de Comunicações e Artes",                                "Escola de Comunicação e Artes",                "eca.txt"),
    ("EE",    "Escola de Enfermagem",                                          "Escola de Enfermagem",                         "ee.txt"),
    ("EEFE",  "Escola de Educação Física e Esporte",                           "Escola de Educação Física e Esporte",          "eefe.txt"),
    ("fflch", "Faculdade de Filosofia, Letras e Ciências Humanas",             "Faculdade de Filosofia, Letras e Ciências Humanas (Antropologia)", "fflchANT.txt"),
    ("fflch", "Faculdade de Filosofia, Letras e Ciências Humanas",             "Faculdade de Filosofia, Letras e Ciências Humanas (Ciência Política)", "fflchCPOL.txt"),
    ("fflch", "Faculdade de Filosofia, Letras e Ciências Humanas",             "Faculdade de Filosofia, Letras e Ciências Humanas (Filosofia)", "fflchFIL.txt"),
    ("fflch", "Faculdade de Filosofia, Letras e Ciências Humanas",             "Faculdade de Filosofia, Letras e Ciências Humanas (Geografia)", "fflchGEO.txt"),
    ("fflch", "Faculdade de Filosofia, Letras e Ciências Humanas",             "Faculdade de Filosofia, Letras e Ciências Humanas (Historia)", "fflchHIS.txt"),
    ("fflch", "Faculdade de Filosofia, Letras e Ciências Humanas",             "Faculdade de Filosofia, Letras e Ciências Humanas (Letras Clássicas Vernáculas)", "fflchLCV.txt"),
    ("fflch", "Faculdade de Filosofia, Letras e Ciências Humanas",             "Faculdade de Filosofia, Letras e Ciências Humanas (Linguística)", "fflchLIN.txt"),
    ("fflch", "Faculdade de Filosofia, Letras e Ciências Humanas",             "Faculdade de Filosofia, Letras e Ciências Humanas (Letras Modernas)", "fflchLM.txt"),
    ("fflch", "Faculdade de Filosofia, Letras e Ciências Humanas",             "Faculdade de Filosofia, Letras e Ciências Humanas (Letras Orientais)", "fflchLO.txt"),
    ("fflch", "Faculdade de Filosofia, Letras e Ciências Humanas",             "Faculdade de Filosofia, Letras e Ciências Humanas (Sociologia)", "fflchSOC.txt"),
    ("fflch", "Faculdade de Filosofia, Letras e Ciências Humanas",             "Faculdade de Filosofia, Letras e Ciências Humanas (Teoria Literária e Literatura Comparada)", "fflchTLTC.txt"),
]

PASTA_ARQUIVOS = "zNome professores"


def popular_banco_dados():
    usp, _ = Universidade.objects.get_or_create(
        sigla="USP",
        defaults={"nome": "Universidade de São Paulo"}
    )

    total_cadastrados = 0
    total_ignorados = 0

    for sigla, nome_instituto, descricao, nome_arquivo in INSTITUTOS:
        instituto, _ = Instituto.objects.get_or_create(
            sigla=sigla,
            defaults={"nome": nome_instituto, "universidade": usp}
        )

        caminho_arquivo = os.path.join(PASTA_ARQUIVOS, f"Nome professores {nome_arquivo}")
        if not os.path.exists(caminho_arquivo):
            print(f"⚠️  Arquivo não encontrado, pulando: {caminho_arquivo}")
            continue

        with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
            linhas = arquivo.readlines()

        cadastrados = 0
        ignorados = 0

        for linha in linhas:
            nome = linha.strip()

            if len(nome) > 2 and not nome.startswith('['):
                professor, foi_criado = Professor.objects.get_or_create(
                    nome=nome,
                    defaults={
                        'descricao': descricao,
                        'visualizacoes': 0,
                        'universidade': usp,
                        'instituto': instituto,
                    }
                )

                if foi_criado:
                    cadastrados += 1
                    print(f"✅ Cadastrado [{descricao}]: {nome}")
                else:
                    ignorados += 1

        print(f"--- {nome_arquivo}: {cadastrados} novos, {ignorados} já existiam ---\n")
        total_cadastrados += cadastrados
        total_ignorados += ignorados

    print("\n" + "=" * 40)
    print("RELATÓRIO FINAL DE IMPORTAÇÃO")
    print("=" * 40)
    print(f"Novos professores inseridos: {total_cadastrados}")
    print(f"Nomes já existentes ignorados: {total_ignorados}")


if __name__ == '__main__':
    popular_banco_dados()
