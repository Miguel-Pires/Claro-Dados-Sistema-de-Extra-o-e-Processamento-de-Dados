"""
Extrai consumo de Internet (MB) por telefone nas páginas de detalhamento.

Estrutura no PDF:
  DETALHAMENTO DE LIGAÇÕES E SERVIÇOS DO CELULAR (11) 91248 7198
  ...
  Internet (MB)
  Serviço  Mbytes Utilizados  ...
  Internet  550,570  ...
  Internet - meses anteriores  165,953  ...   (opcional)
  Subtotal  266,636  ...

Retorna: dict {telefone_normalizado: mb_float}
  ex.: {"11912487198": 266.636}
"""
from __future__ import annotations

import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)

# "DETALHAMENTO" + qualquer coisa + phone "(DD) NNNNN NNNN" ou "(DD) NNNN NNNN"
_RE_DETALHE = re.compile(
    r"DETALHAMENTO.{0,80}CELULAR\s*\((\d{2})\)\s*([\d][\d\s]{7,11})",
    re.IGNORECASE,
)

# Bloco "Internet (MB)" seguido de "Subtotal  NNN,NNN"
_RE_MB_BLOCK = re.compile(
    r"Internet\s*\(MB\).{0,2000}?Subtotal\s+([\d.,]+)",
    re.IGNORECASE | re.DOTALL,
)

# Converte "1.601,686" → 1601.686
def _parse_mb(raw: str) -> float:
    raw = raw.strip().replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _normalize(ddd: str, rest: str) -> str:
    digits = re.sub(r"\D", "", ddd + rest)
    return digits[:11]  # máximo 11 dígitos (DDD + 9 dígitos)


def extract_mb_usage(texts: list) -> Dict[str, float]:
    """
    Extrai consumo MB a partir de textos pré-extraídos (uma string por página).
    Retorna {telefone_normalizado: total_mb}.
    """
    usage: Dict[str, float] = {}

    full_text = "\n".join(texts)

    # Divide em seções por telefone usando o marcador DETALHAMENTO
    segments = re.split(
        r"(?=DETALHAMENTO.{0,80}CELULAR\s*\(\d{2}\))",
        full_text,
        flags=re.IGNORECASE,
    )

    for seg in segments:
        m_tel = _RE_DETALHE.search(seg)
        if not m_tel:
            continue

        phone = _normalize(m_tel.group(1), m_tel.group(2))

        m_mb = _RE_MB_BLOCK.search(seg)
        if not m_mb:
            continue

        mb = _parse_mb(m_mb.group(1))
        if phone in usage:
            usage[phone] += mb  # soma se aparecer em mais de um segmento
        else:
            usage[phone] = mb

        logger.debug("MB: %s → %.3f MB", phone, mb)

    logger.info("Consumo MB extraído: %d telefones", len(usage))
    return usage
