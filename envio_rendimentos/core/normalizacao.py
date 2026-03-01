import unicodedata
import re


def normalizar_nome(valor: str) -> str:
    if not valor:
        return ""

    valor = unicodedata.normalize("NFKD", valor)
    valor = valor.encode("ascii", "ignore").decode("ascii")
    valor = re.sub(r"\s+", " ", valor)
    return valor.strip().upper()


def slugify_name(valor: str) -> str:
    """Return a filesystem-safe slug for folder/file names.

    - removes accents and special characters
    - replaces sequences of non-alphanumeric with underscore
    - trims and returns uppercased string
    """
    if not valor:
        return ""
    v = unicodedata.normalize("NFKD", valor)
    v = v.encode("ascii", "ignore").decode("ascii")
    # replace non-word characters with underscore
    v = re.sub(r"[^A-Za-z0-9]+", "_", v)
    v = re.sub(r"_+", "_", v)
    return v.strip("_").upper()


def normalize_filename(valor: str) -> str:
    """Normalize a filename/pasta: remove accents, collapse non-alnum to underscore, keep readable uppercase.

    Use this function for folder and file names to ensure consistent ASCII-only names.
    """
    return slugify_name(valor)


def normalizar_nome_completo(nome: str) -> str:
    """Normalize a creditor name for display and folder naming.

    Steps:
    - remove numeric prefixes like "9 - "
    - remove parenthetical suffixes like " (CAPTADOR)"
    - remove accents
    - collapse duplicate spaces
    - strip and uppercase
    """
    if not nome:
        return ""
    import re, unicodedata
    v = str(nome)
    v = re.sub(r'^\d+\s*-\s*', '', v)
    v = re.sub(r'\s*\([^)]*\)', '', v)
    v = unicodedata.normalize('NFKD', v)
    v = ''.join(c for c in v if not unicodedata.combining(c))
    v = re.sub(r'\s+', ' ', v)
    return v.strip().upper()

