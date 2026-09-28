"""Leitura de bancos de provas em pastas (ex.: Drive do IFUSP) para importação em lote.

Tudo aqui é puro (sem banco de dados), para poder ser testado e usado tanto pelo
comando `preparar_lote_provas` (no computador de quem organiza o lote) quanto pelo
`importar_lote_provas` (no servidor).

Regras combinadas com o dono do site:
- semestre ausente -> 1º semestre do ano; sem data nenhuma -> 2021/1 (pandemia);
- provinhas, gabaritos e listas não ganham tipo próprio: viram "Outra", exceto quando
  o nome indica P1/P2/P3/Sub/Rec;
- a origem vai na observação.
"""
import re
import unicodedata
from pathlib import PurePosixPath

SEMESTRE_SEM_DATA = '2021/1'

EXTENSOES_PDF = {'.pdf'}
EXTENSOES_IMAGEM = {'.jpg', '.jpeg', '.png'}


def normalizar(texto):
    texto = unicodedata.normalize('NFKD', texto or '')
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', texto).strip().lower()


# ---------------------------------------------------------------------------
# Pasta do professor: "2024/2 - Germano Penello" (no ZIP do Drive vira "2024-2 - ...")
# ---------------------------------------------------------------------------

_SEMESTRE_PADROES = [
    # 2024-2, 2018_2, 2020-01, 2017-_ (semestre desconhecido: "2017/?")
    (re.compile(r'(?<!\d)((?:19|20)\d{2})\s*[-_/.]\s*0?([12_?])(?!\d)'), lambda m: (m.group(1), m.group(2))),
    # 2-2020, 02-2020 (semestre antes do ano)
    (re.compile(r'(?<!\d)0?([12])\s*[-_/.]\s*((?:19|20)\d{2})(?!\d)'), lambda m: (m.group(2), m.group(1))),
    # só o ano: 2018, (2022)
    (re.compile(r'(?<!\d)((?:19|20)\d{2})(?!\d)'), lambda m: (m.group(1), '')),
]


def extrair_semestre(texto):
    """Devolve (semestre 'AAAA/S' ou None, texto sem a data)."""
    for padrao, partes in _SEMESTRE_PADROES:
        m = padrao.search(texto)
        if m:
            ano, periodo = partes(m)
            periodo = periodo if periodo in ('1', '2') else '1'  # sem semestre: assume o 1º
            restante = (texto[:m.start()] + ' ' + texto[m.end():])
            return f'{ano}/{periodo}', restante
    return None, texto


def interpretar_pasta_professor(nome_pasta):
    """'2024-2 - Germano Penello' -> ('2024/2', 'Germano Penello'); sem data -> (None, nome)."""
    semestre, resto = extrair_semestre(nome_pasta)
    resto = re.sub(r'[()]', ' ', resto)
    partes = [p.strip() for p in re.split(r'\s+-\s*|\s*-\s+', resto) if p.strip(' -_')]
    # Descarta rótulos de turma ("Noturno", "IME", "IAG") que não são nomes de pessoa
    turmas = {'noturno', 'diurno', 'ime', 'iag', 'if', 'lic', 'bach'}
    partes = [p.strip(' -_') for p in partes if normalizar(p.strip(' -_')) not in turmas]
    return semestre, (partes[0] if partes else '')


# ---------------------------------------------------------------------------
# Tipo da avaliação a partir do caminho do arquivo
# ---------------------------------------------------------------------------

_ROMANOS = {'i': '1', 'ii': '2', 'iii': '3'}


def identificar_tipo(caminho_relativo):
    """Tipo (P1, P2, P3, SUB, REC ou OUTRA) pelas pastas e pelo nome do arquivo.

    `caminho_relativo` começa DEPOIS da pasta do professor (ex.: 'Provinhas/p1.pdf').
    """
    partes = [normalizar(p) for p in PurePosixPath(caminho_relativo).parts]
    pastas, nome = partes[:-1], re.sub(r'\.[a-z0-9]+$', '', partes[-1])
    contexto = ' '.join(pastas)

    # Provinhas, listas, exercícios e EPs: "Outra", mesmo que o nome tenha "p1"
    if re.search(r'provinha|lista|exercic|(?<![a-z])eps?(?![a-z])', contexto):
        return 'OUTRA'
    texto = f'{contexto} {nome}'
    if re.search(r'provinha|lista|exercic|(?<![a-z])l\d+[a-z]?_|teste\s*\d|(?<![a-z])aa\d|(?<![a-z])ep\s*\d', nome):
        return 'OUTRA'
    if re.search(r'(?<![a-z])p?sub', texto):
        return 'SUB'
    if re.search(r'(?<![a-z])rec(?![a-z])|recupera', texto):
        return 'REC'
    padroes = [
        r'prova\s*[-_ ]?\s*p?0?([123])(?![0-9])',          # prova1, Prova-1, prova01, ProvaP1
        r'gab(?:arito)?\s*[-_ ]?\s*p\s*([123])(?![0-9])',   # GabaritoP1, gab-P2
        r'(?<![a-z])p\s*[-_ ]?0?([123])(?![0-9])',          # P1, p 1, P1A, P1MAT0216, gab-P2-D
    ]
    for padrao in padroes:
        m = re.search(padrao, texto)
        if m:
            return f'P{m.group(1)}'
    m = re.search(r'(?<![a-z])p\s*(i{1,3})(?![a-z])', nome)  # "PI - 2020.1"
    if m:
        return f'P{_ROMANOS[m.group(1)]}'
    return 'OUTRA'


# ---------------------------------------------------------------------------
# O que é conteúdo de prova/lista (entra) e o que não é (fica de fora)
# ---------------------------------------------------------------------------

_PALAVRAS_DE_AVALIACAO = re.compile(
    r'prova|provinha|(?<![a-z])p\s*[-_ ]?\d|(?<![a-z])p(?![a-z0-9])|p?sub|(?<![a-z])rec(?![a-z])|recupera|gabarito|(?<![a-z])gab|'
    r'lista|(?<![a-z])l\d+|exerc|teste|(?<![a-z])eps?\s*\d|resolu|solu|(?<![a-z])sol(?![a-z])|resolvida|'
    r'(?<![a-z])aa\d|atividade|exame|correc|(?<![a-z])pi(?![a-z])'
)


def parece_avaliacao(caminho_relativo):
    return bool(_PALAVRAS_DE_AVALIACAO.search(normalizar(caminho_relativo)))


def chave_de_pagina(nome_arquivo):
    """'Prova1_12.jpeg' -> ('prova1', 12); 'pagina 3.jpg' -> ('pagina', 3); sem número -> (nome, None)."""
    base = normalizar(re.sub(r'\.[A-Za-z0-9]+$', '', nome_arquivo))
    m = re.match(r'^(.*?)[\s_-]*(\d+)$', base)
    if m and m.group(1):
        return m.group(1).strip(), int(m.group(2))
    return base, None
