"""
Orquestrador principal: abre o PDF e coordena a extração.

Fluxo:
  1. PyMuPDF extrai texto e words de todas as páginas (rápido, C++)
  2. shared_plan e mb_parser usam o texto já pronto
  3. block_parser usa as words com bounding boxes
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

import fitz

from .block_parser import parse_page_words
from .mb_parser import extract_mb_usage
from .shared_plan import extract_shared_gb
from ..models.line import PhoneLine

logger = logging.getLogger(__name__)

Word = dict


def _extract_all_pages(path: Path) -> Tuple[List[List[Word]], List[str]]:
    """
    Usa PyMuPDF para extrair words + texto de todas as páginas.
    Retorna (all_words, page_texts), onde all_words[i] é a lista de word-dicts
    da página i.
    """
    doc = fitz.open(path)
    all_words: List[List[Word]] = []
    page_texts: List[str] = []

    try:
        for page in doc:
            page_texts.append(page.get_text("text"))

            words: List[Word] = []
            for x0, y0, x1, y1, text, *_ in page.get_text("words"):
                if text.strip():
                    words.append({
                        "text": text,
                        "x0": x0,
                        "x1": x1,
                        "top": y0,
                        "bottom": y1,
                    })
            all_words.append(words)
    finally:
        doc.close()

    return all_words, page_texts


def read_pdf(path: str | Path) -> List[PhoneLine]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF não encontrado: {path}")

    logger.info("Abrindo PDF: %s", path.name)

    all_words, page_texts = _extract_all_pages(path)
    total_pages = len(all_words)
    logger.info("Total de páginas: %d", total_pages)

    shared_gb = extract_shared_gb(page_texts[0]) if page_texts else None
    if shared_gb is not None:
        logger.info("Plano compartilhado detectado: %s", shared_gb)
    else:
        logger.info("Sem plano compartilhado na página 1 - assumindo planos individuais")
        shared_gb = ""

    mb_usage = extract_mb_usage(page_texts)
    logger.info("Consumo MB: %d telefones encontrados", len(mb_usage))

    all_lines: List[PhoneLine] = []
    seen_phones: set[str] = set()
    open_block = None

    for page_num, words in enumerate(all_words, start=1):
        try:
            page_lines, open_block = parse_page_words(words, shared_gb, open_block)
        except Exception:
            logger.exception("Erro na página %d - pulando", page_num)
            open_block = None
            continue

        for line in page_lines:
            if line.telefone not in seen_phones:
                seen_phones.add(line.telefone)
                line.mb_usage = mb_usage.get(line.telefone, 0.0)
                line.consumo = "Não" if line.mb_usage == 0.0 else "Sim"
                all_lines.append(line)

        if page_lines:
            logger.debug("Página %d: %d linhas extraídas", page_num, len(page_lines))

    if open_block and open_block.phones:
        logger.warning("PDF terminou com bloco aberto (%d telefones não resolvidos)", len(open_block.phones))

    logger.info("Total de linhas únicas extraídas: %d", len(all_lines))

    all_lines.sort(key=lambda l: l.telefone)
    return all_lines
