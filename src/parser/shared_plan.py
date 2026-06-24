import re
from typing import Optional


_SHARED_RE = re.compile(
    r"Compartilhado\s+(\d+)\s*(GB|TB|MB)",
    re.IGNORECASE,
)


def extract_shared_gb(text: str) -> Optional[str]:
    """
    Extrai a capacidade do plano compartilhado como string com unidade.
    Exemplos: 'Compartilhado 900GB' → '900GB'
              'Compartilhado 1TB'   → '1TB'
              'Compartilhado 15MB'  → '15MB'
    Retorna None se não encontrado.
    """
    m = _SHARED_RE.search(text)
    if m:
        return f"{m.group(1)}{m.group(2).upper()}"
    return None
