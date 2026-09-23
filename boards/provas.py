"""Validação e preparo dos arquivos enviados em "Provas antigas".

Fotos são reprocessadas antes de salvar: giradas conforme o EXIF, reduzidas e
regravadas como JPEG *sem* EXIF (fotos de celular trazem a localização GPS de
quem tirou). PDFs são guardados como vieram, depois de conferir a assinatura.
"""
import io
import uuid
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile, File
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

LADO_MAXIMO = 2200          # px do lado maior da página salva: legível e leve
LARGURA_MINIATURA = 480
PIXELS_MAXIMO = 60_000_000  # recusa antes de decodificar, para não estourar a RAM da VM

ASSINATURAS = [
    (b'%PDF-', 'pdf'),
    (b'\x89PNG\r\n\x1a\n', 'imagem'),
    (b'\xff\xd8\xff', 'imagem'),
]


@dataclass
class ArquivoPreparado:
    conteudo: File
    tipo_conteudo: str
    extensao: str
    tamanho: int
    miniatura: bytes | None = None


def semestre_atual(hoje=None):
    hoje = hoje or timezone.localdate()
    return f'{hoje.year}/{1 if hoje.month <= 6 else 2}'


def semestres_ate_hoje(primeiro_ano=2000, hoje=None):
    """['2026/2', '2026/1', '2025/2', ...] do semestre atual até o primeiro ano."""
    ano, periodo = map(int, semestre_atual(hoje).split('/'))
    semestres = []
    while ano >= primeiro_ano:
        semestres.append(f'{ano}/{periodo}')
        ano, periodo = (ano, 1) if periodo == 2 else (ano - 1, 2)
    return semestres


def detectar_tipo(arquivo):
    arquivo.seek(0)
    inicio = arquivo.read(8)
    arquivo.seek(0)
    for assinatura, tipo in ASSINATURAS:
        if inicio.startswith(assinatura):
            return tipo
    return None


def _para_jpeg(imagem, qualidade):
    saida = io.BytesIO()
    # Sem o parâmetro exif=..., o Pillow não grava metadados
    imagem.save(saida, 'JPEG', quality=qualidade, optimize=True)
    return saida.getvalue()


def _sem_transparencia(imagem):
    if imagem.mode in ('RGBA', 'LA') or (imagem.mode == 'P' and 'transparency' in imagem.info):
        imagem = imagem.convert('RGBA')
        fundo = Image.new('RGB', imagem.size, 'white')
        fundo.paste(imagem, mask=imagem.getchannel('A'))
        return fundo
    return imagem.convert('RGB')


def preparar_imagem(arquivo):
    try:
        imagem = Image.open(arquivo)
        if imagem.width * imagem.height > PIXELS_MAXIMO:
            raise ValidationError(f'"{arquivo.name}" tem resolução alta demais. Envie uma foto menor.')
        imagem.draft('RGB', (LADO_MAXIMO, LADO_MAXIMO))  # JPEG já decodifica reduzido
        imagem = ImageOps.exif_transpose(imagem)
        imagem = _sem_transparencia(imagem)
        imagem.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
        pagina = _para_jpeg(imagem, qualidade=85)
        imagem.thumbnail((LARGURA_MINIATURA, LARGURA_MINIATURA * 3))
        miniatura = _para_jpeg(imagem, qualidade=75)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError):
        raise ValidationError(f'"{arquivo.name}" não pôde ser aberta como imagem. O arquivo pode estar corrompido.')
    return ArquivoPreparado(
        conteudo=ContentFile(pagina), tipo_conteudo='image/jpeg', extensao='jpg',
        tamanho=len(pagina), miniatura=miniatura,
    )


def preparar_arquivo(arquivo):
    tipo = detectar_tipo(arquivo)
    if tipo == 'pdf':
        return ArquivoPreparado(conteudo=arquivo, tipo_conteudo='application/pdf', extensao='pdf', tamanho=arquivo.size)
    if tipo == 'imagem':
        return preparar_imagem(arquivo)
    raise ValidationError(f'"{arquivo.name}" não é PDF, JPG nem PNG.')


def salvar_arquivos(prova, preparados):
    """Grava os arquivos da prova. Se algo falhar, apaga o que já foi para o disco."""
    from .models import ArquivoProva

    gravados = []
    try:
        for ordem, preparado in enumerate(preparados):
            nome = uuid.uuid4().hex
            arquivo = ArquivoProva(
                prova=prova, tipo_conteudo=preparado.tipo_conteudo,
                tamanho=preparado.tamanho, ordem=ordem,
            )
            gravados.append(arquivo)
            arquivo.arquivo.save(f'{nome}.{preparado.extensao}', preparado.conteudo, save=False)
            if preparado.miniatura:
                arquivo.miniatura.save(f'{nome}.jpg', ContentFile(preparado.miniatura), save=False)
            arquivo.save()
    except Exception:
        for arquivo in gravados:
            for campo in (arquivo.arquivo, arquivo.miniatura):
                if campo:
                    campo.delete(save=False)
        raise
