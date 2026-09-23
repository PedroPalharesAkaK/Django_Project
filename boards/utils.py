import re
import unicodedata


def normalizar(texto):
    """Minúsculas, sem acentos e com espaços simples: 'Cálculo  I' -> 'calculo i'."""
    texto = unicodedata.normalize('NFKD', texto or '')
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', texto).strip().lower()
