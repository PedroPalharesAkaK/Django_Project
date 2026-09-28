"""Monta um lote de provas a partir de uma pasta organizada como o Drive do IFUSP.

Rode no SEU computador (não no servidor), com a pasta extraída do ZIP do Drive:

    python manage.py preparar_lote_provas "<pasta extraída>" "<pasta do lote>" --mapa boards/data/lote_ifusp.json

Estrutura esperada da origem:  <Disciplina>/<Semestre - Professor>/[subpastas/]arquivo
O lote gerado tem:
    manifesto.csv   uma linha por prova (coluna "incluir" = sim/nao), lido pelo importar_lote_provas
    arquivos/       cópia dos arquivos das provas
    miniaturas/     primeira página dos PDFs (precisa do PyMuPDF instalado aqui, não no servidor)
    excluidos.csv   o que ficou de fora e por quê
    revisao.html    página para conferir tudo, com miniaturas
"""
import csv
import hashlib
import html
import io
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from PIL import Image

from boards.lote_provas import (
    EXTENSOES_IMAGEM, EXTENSOES_PDF, SEMESTRE_SEM_DATA, chave_de_pagina, extrair_semestre,
    identificar_tipo, interpretar_pasta_professor, normalizar, parece_avaliacao,
)
from boards.models import ProvaAntiga

from .baixar_catalogo_disciplinas import ARQUIVO_PADRAO as CATALOGO

CAMPOS_MANIFESTO = ['id', 'incluir', 'alerta', 'disciplina', 'professor', 'semestre', 'tipo',
                    'observacao', 'arquivos', 'miniaturas', 'origem']
TIPOS = dict(ProvaAntiga.TIPOS)
ARQUIVOS_DE_SISTEMA = {'.ds_store', 'thumbs.db', 'desktop.ini'}


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, 'rb') as f:
        for bloco in iter(lambda: f.read(1 << 20), b''):
            h.update(bloco)
    return h.hexdigest()


def miniatura_pdf(caminho, destino, largura=480):
    """Primeira página do PDF como JPEG. Devolve False se não der (sem PyMuPDF, PDF protegido...)."""
    try:
        import pymupdf
        with pymupdf.open(caminho) as doc:
            pagina = doc[0]
            zoom = largura / pagina.rect.width
            pix = pagina.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            Image.frombytes('RGB', (pix.width, pix.height), pix.samples).save(destino, 'JPEG', quality=75)
        return True
    except Exception:
        return False


class Command(BaseCommand):
    help = 'Monta um lote de provas (manifesto + arquivos + página de revisão) a partir de uma pasta do Drive.'

    def add_arguments(self, parser):
        parser.add_argument('origem', help='Pasta extraída do ZIP (a que contém as pastas das disciplinas)')
        parser.add_argument('destino', help='Pasta do lote a criar (não pode existir)')
        parser.add_argument('--mapa', required=True, help='JSON com disciplinas, professores e exclusões')

    def handle(self, *args, **options):
        origem, destino = Path(options['origem']), Path(options['destino'])
        if not origem.is_dir():
            raise CommandError(f'Pasta de origem não encontrada: {origem}')
        if destino.exists():
            raise CommandError(f'A pasta do lote já existe, apague ou escolha outra: {destino}')
        self.mapa = json.loads(Path(options['mapa']).read_text(encoding='utf-8'))
        self.fonte = self.mapa['fonte']
        self.catalogo = {d['codigo'] for d in json.loads(CATALOGO.read_text(encoding='utf-8'))}

        codigos_invalidos = sorted(c for c in self.mapa['disciplinas'].values() if c not in self.catalogo)
        codigos_invalidos += sorted(a['disciplina'] for a in self.mapa.get('avulsos', {}).values() if a['disciplina'] not in self.catalogo)
        if codigos_invalidos:
            raise CommandError(f'Códigos de disciplina fora do catálogo no mapa: {", ".join(codigos_invalidos)}')

        self.excluidos = []  # (origem, motivo)
        self.a_confirmar = Counter()  # (nome na pasta, nome no site) -> arquivos
        candidatos = self.classificar(origem)
        provas = self.agrupar(candidatos)

        (destino / 'arquivos').mkdir(parents=True)
        (destino / 'miniaturas').mkdir()
        linhas = self.copiar(provas, destino)
        self.escrever(destino, linhas)

        incluidas = [l for l in linhas if l['incluir'] == 'sim']
        tamanho = sum((destino / a).stat().st_size for l in incluidas for a in l['arquivos'].split('|'))
        self.stdout.write(self.style.SUCCESS(
            f'Lote criado em {destino}: {len(incluidas)} provas incluídas ({tamanho / 1e6:.1f} MB), '
            f'{len(linhas) - len(incluidas)} para conferir, {len(self.excluidos)} arquivos fora.'
        ))

    # -------------------------------------------------------------------
    # 1. Classificar cada arquivo
    # -------------------------------------------------------------------
    def classificar(self, origem):
        por_hash = {}
        candidatos = []
        arquivos = sorted(p for p in origem.rglob('*') if p.is_file())
        # Na dúvida entre duplicatas, fica a que está mais "no lugar certo": fora de "passadas",
        # dentro da pasta de um professor, com caminho mais curto.
        arquivos.sort(key=lambda p: ('passadas' in normalizar(str(p)), len(p.relative_to(origem).parts) < 3, len(str(p))))

        for caminho in arquivos:
            rel = caminho.relative_to(origem).as_posix()
            partes = rel.split('/')
            ext = caminho.suffix.lower()

            if caminho.name.lower() in ARQUIVOS_DE_SISTEMA or ext == '.gdoc':
                self.excluidos.append((rel, 'arquivo de sistema ou atalho do Google Docs'))
                continue
            if ext not in EXTENSOES_PDF | EXTENSOES_IMAGEM:
                self.excluidos.append((rel, f'formato {ext or "sem extensão"} não é aceito (só PDF, JPG e PNG)'))
                continue
            motivo = self.motivo_para_excluir(rel)
            if motivo:
                self.excluidos.append((rel, motivo))
                continue
            digest = sha256(caminho)
            if digest in por_hash:
                self.excluidos.append((rel, f'duplicata de {por_hash[digest]}'))
                continue
            por_hash[digest] = rel

            item = self.interpretar(caminho, rel, partes)
            if item:
                candidatos.append(item)
        return candidatos

    def motivo_para_excluir(self, rel):
        partes_norm = [normalizar(p) for p in rel.split('/')[:-1]]
        for pasta, motivo in self.mapa.get('ignorar_pastas', {}).items():
            if normalizar(pasta) in partes_norm:
                return motivo
        for regra in self.mapa.get('excluir', []):
            if normalizar(regra['padrao']) in normalizar(rel):
                return regra['motivo']
        return None

    def interpretar(self, caminho, rel, partes):
        avulso = self.mapa.get('avulsos', {}).get(rel)
        if avulso:
            return {
                'caminho': caminho, 'rel': rel, 'grupo': (rel,), 'disciplina': avulso['disciplina'],
                'professor': avulso['professor'], 'semestre': avulso['semestre'], 'tipo': avulso['tipo'],
                'incluir': True, 'alertas': [f'arquivo avulso, confira: {avulso["confirmar"]}'], 'rotulo': rel,
            }
        if len(partes) < 3:
            self.excluidos.append((rel, 'arquivo solto, fora da pasta de um professor: não dá para saber de quem é'))
            return None

        pasta_disciplina, pasta_professor, resto = partes[0], partes[1], '/'.join(partes[2:])
        codigo = self.mapa['disciplinas'].get(pasta_disciplina)
        if not codigo:
            self.excluidos.append((rel, f'disciplina "{pasta_disciplina}" sem código no mapa'))
            return None

        semestre, nome_professor = interpretar_pasta_professor(pasta_professor)
        alertas = []
        if semestre is None:
            semestre, _ = extrair_semestre(caminho.stem)
            if semestre:
                alertas.append('semestre tirado do nome do arquivo')
            else:
                semestre = SEMESTRE_SEM_DATA
                alertas.append(f'sem data: usei {SEMESTRE_SEM_DATA}')

        if nome_professor not in self.mapa['professores']:
            self.excluidos.append((rel, f'professor "{nome_professor}" não está no mapa'))
            return None
        professor = self.mapa['professores'][nome_professor]
        incluir = True
        if professor is None:
            incluir = False
            alertas.append(f'"{nome_professor}" não está no site')
        elif nome_professor in self.mapa.get('professores_a_confirmar', []):
            # Confirmação vale para o professor, não para cada prova: vai para o topo da revisão
            self.a_confirmar[(nome_professor, professor)] += 1

        if not parece_avaliacao(resto):
            incluir = False
            alertas.append('não parece prova nem lista, confira')
        for regra in self.mapa.get('conferir', []):
            if normalizar(regra['padrao']) in normalizar(rel):
                incluir = False
                alertas.append(regra['motivo'])

        # Fotos de uma mesma prova (Prova1_0.jpeg, Prova1_1.jpeg...) viram uma prova só
        pasta_arquivo = '/'.join(partes[:-1])
        if caminho.suffix.lower() in EXTENSOES_IMAGEM:
            prefixo, _ = chave_de_pagina(caminho.name)
            grupo = (pasta_arquivo, 'imagens', prefixo)
        else:
            grupo = (rel,)
        return {
            'caminho': caminho, 'rel': rel, 'grupo': grupo, 'disciplina': codigo, 'professor': professor or '',
            'semestre': semestre, 'tipo': identificar_tipo(resto), 'incluir': incluir, 'alertas': alertas,
            'rotulo': resto,
        }

    # -------------------------------------------------------------------
    # 2. Juntar páginas de fotos numa prova
    # -------------------------------------------------------------------
    def agrupar(self, candidatos):
        grupos = defaultdict(list)
        for item in candidatos:
            grupos[item['grupo']].append(item)
        provas = []
        for itens in grupos.values():
            itens.sort(key=lambda i: (chave_de_pagina(i['caminho'].name)[1] or 0, i['caminho'].name))
            primeiro = itens[0]
            alertas = list(dict.fromkeys(a for i in itens for a in i['alertas']))
            if len(itens) > 1:
                rotulo = f'{itens[0]["rotulo"]} a {itens[-1]["caminho"].name} ({len(itens)} páginas)'
            else:
                rotulo = primeiro['rotulo']
            provas.append({**primeiro, 'itens': itens, 'alertas': alertas, 'rotulo': rotulo,
                           'incluir': all(i['incluir'] for i in itens)})
        provas.sort(key=lambda p: (p['disciplina'], p['professor'] or '~', p['semestre'],
                                   list(TIPOS).index(p['tipo']), normalizar(p['rotulo'])))
        return provas

    # -------------------------------------------------------------------
    # 3. Copiar arquivos, gerar miniaturas e linhas do manifesto
    # -------------------------------------------------------------------
    def copiar(self, provas, destino):
        linhas = []
        for numero, prova in enumerate(provas, start=1):
            arquivos, miniaturas = [], []
            for ordem, item in enumerate(prova['itens'], start=1):
                nome = f'{numero:04d}-{ordem:02d}{item["caminho"].suffix.lower()}'
                shutil.copy2(item['caminho'], destino / 'arquivos' / nome)
                arquivos.append(f'arquivos/{nome}')
                miniatura = ''
                if item['caminho'].suffix.lower() in EXTENSOES_PDF:
                    mini = f'miniaturas/{numero:04d}-{ordem:02d}.jpg'
                    if miniatura_pdf(item['caminho'], destino / mini):
                        miniatura = mini
                    else:
                        prova['alertas'].append('não consegui gerar a miniatura do PDF')
                miniaturas.append(miniatura)
            observacao = f'{self.fonte} (arquivo: {prova["rotulo"]})'
            if len(observacao) > 200:
                observacao = observacao[:197] + '...'
            linhas.append({
                'id': numero,
                'incluir': 'sim' if prova['incluir'] else 'nao',
                'alerta': '; '.join(prova['alertas']),
                'disciplina': prova['disciplina'],
                'professor': prova['professor'],
                'semestre': prova['semestre'],
                'tipo': prova['tipo'],
                'observacao': observacao,
                'arquivos': '|'.join(arquivos),
                'miniaturas': '|'.join(miniaturas),
                'origem': '|'.join(i['rel'] for i in prova['itens']),
            })
        return linhas

    # -------------------------------------------------------------------
    # 4. Manifesto, excluídos e página de revisão
    # -------------------------------------------------------------------
    def escrever(self, destino, linhas):
        # ";" e BOM: abre direto no Excel em português
        with open(destino / 'manifesto.csv', 'w', newline='', encoding='utf-8-sig') as f:
            escritor = csv.DictWriter(f, fieldnames=CAMPOS_MANIFESTO, delimiter=';')
            escritor.writeheader()
            escritor.writerows(linhas)
        with open(destino / 'excluidos.csv', 'w', newline='', encoding='utf-8-sig') as f:
            escritor = csv.writer(f, delimiter=';')
            escritor.writerow(['origem', 'motivo'])
            escritor.writerows(sorted(self.excluidos))
        (destino / 'revisao.html').write_text(self.pagina_de_revisao(linhas), encoding='utf-8')

    def pagina_de_revisao(self, linhas):
        e = html.escape
        grupos = defaultdict(list)
        for linha in linhas:
            grupos[(linha['disciplina'], linha['professor'] or '(não está no site)')].append(linha)

        blocos = []
        for (disciplina, professor), itens in grupos.items():
            cartoes = []
            for l in itens:
                primeiro = l['arquivos'].split('|')[0]
                capa = l['miniaturas'].split('|')[0] or (primeiro if not primeiro.endswith('.pdf') else '')
                imagem = f'<img src="{e(capa)}" alt="" loading="lazy">' if capa else '<span class="sem-capa">PDF</span>'
                classe = 'fora' if l['incluir'] == 'nao' else ('alerta' if l['alerta'] else '')
                status = 'fica de fora' if l['incluir'] == 'nao' else 'entra'
                cartoes.append(
                    f'<a class="cartao {classe}" href="{e(primeiro)}" target="_blank">'
                    f'<div class="folha">{imagem}</div>'
                    f'<div class="info"><strong>#{l["id"]} {e(TIPOS[l["tipo"]])} {e(l["semestre"])}</strong>'
                    f'<span class="status">{status}</span>'
                    f'<span class="arquivo">{e(l["observacao"].split("(arquivo: ", 1)[-1].rstrip(")"))}</span>'
                    + (f'<span class="aviso">{e(l["alerta"])}</span>' if l['alerta'] else '') +
                    '</div></a>'
                )
            blocos.append(f'<section><h2><span>{e(disciplina)}</span> {e(professor)}</h2><div class="grade">{"".join(cartoes)}</div></section>')

        confirmar = ''.join(
            f'<li>"{e(pasta)}" é <strong>{e(site)}</strong> ({n} arquivos)</li>'
            for (pasta, site), n in sorted(self.a_confirmar.items())
        )
        bloco_confirmar = (f'<div class="confirmar"><h2>Professores ligados por aproximação: confirme</h2>'
                           f'<ul>{confirmar}</ul></div>') if confirmar else ''
        motivos = Counter(m.split(' de ')[0] if m.startswith('duplicata') else m for _, m in self.excluidos)
        lista_excluidos = ''.join(f'<li><code>{e(o)}</code>: {e(m)}</li>' for o, m in sorted(self.excluidos))
        resumo_motivos = ''.join(f'<li>{n} × {e(m)}</li>' for m, n in motivos.most_common())
        incluidas = sum(1 for l in linhas if l['incluir'] == 'sim')
        com_alerta = sum(1 for l in linhas if l['incluir'] == 'sim' and l['alerta'])

        return f'''<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="utf-8"><title>Revisão do lote: {e(self.fonte)}</title>
<style>
  :root {{ --bg:#f7f5f0; --surface:#fff; --border:#e2ddd0; --accent:#1f3a5f; --text:#262420; --muted:#6f6a5c; --warn:#a97c1f; --danger:#a13c3c; }}
  body {{ margin:0; padding:2rem; background:var(--bg); color:var(--text); font:15px/1.5 Inter, system-ui, sans-serif; }}
  h1, h2 {{ font-family: Lora, Georgia, serif; }}
  h1 {{ margin:0 0 .25rem; }} .resumo {{ color:var(--muted); max-width:75ch; }}
  label.filtro {{ display:inline-block; margin:1rem 0; font-weight:600; }}
  section {{ margin:2.25rem 0; }} h2 {{ font-size:1.1rem; margin:0 0 .75rem; }} h2 span {{ color:var(--accent); margin-right:.4rem; }}
  .grade {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(170px, 1fr)); gap:1rem; }}
  .cartao {{ display:block; color:inherit; text-decoration:none; background:var(--surface); border:1px solid var(--border); border-radius:4px; overflow:hidden; }}
  .cartao.alerta {{ border-color:var(--warn); box-shadow:inset 0 3px 0 var(--warn); }}
  .cartao.fora {{ opacity:.55; border-style:dashed; }}
  .folha {{ aspect-ratio:210/297; background:#fff; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:center; overflow:hidden; }}
  .folha img {{ width:100%; height:100%; object-fit:cover; object-position:top; }}
  .sem-capa {{ color:var(--muted); font-family:Lora, serif; }}
  .info {{ padding:.55rem .65rem; display:flex; flex-direction:column; gap:.15rem; font-size:.82rem; }}
  .info strong {{ font-size:.95rem; }} .status {{ color:var(--muted); }} .arquivo {{ overflow-wrap:anywhere; }}
  .aviso {{ color:var(--warn); font-weight:600; }} .fora .aviso {{ color:var(--danger); }}
  body.so-alertas .cartao:not(.alerta):not(.fora) {{ display:none; }}
  details {{ margin-top:3rem; }} code {{ font-size:.8rem; }}
  .confirmar {{ background:var(--surface); border:1px solid var(--border); border-left:4px solid var(--warn); border-radius:4px; padding:.75rem 1.25rem; max-width:75ch; margin-top:1.25rem; }}
  .confirmar h2 {{ margin:.25rem 0 .5rem; }} .confirmar ul {{ margin:0; padding-left:1.1rem; }}
</style></head>
<body>
  <h1>Revisão do lote: {e(self.fonte)}</h1>
  <p class="resumo">{incluidas} provas entram ({com_alerta} com algo para conferir, em amarelo); {len(linhas) - incluidas} ficam de fora até você decidir (tracejadas);
  {len(self.excluidos)} arquivos foram descartados (lista no fim). Clique num cartão para abrir o arquivo. Para mudar algo, me diga o número (#) da prova.</p>
  {bloco_confirmar}
  <label class="filtro"><input type="checkbox" onchange="document.body.classList.toggle('so-alertas', this.checked)"> Mostrar só o que precisa de atenção</label>
  {"".join(blocos)}
  <details><summary>Arquivos descartados ({len(self.excluidos)})</summary><ul>{resumo_motivos}</ul><ul>{lista_excluidos}</ul></details>
</body></html>'''
