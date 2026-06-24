"""
Extrator de faturas Claro Empresas — ponto de entrada.

Uso:
    python main.py <caminho_do_pdf> [caminho_de_saida.xlsx]

Exemplos:
    python main.py fatura.pdf
    python main.py fatura.pdf resultado.xlsx
    python main.py fatura.pdf --debug
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.parser import read_pdf
from src.export import export_excel


def _configure_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Silencia warnings do pdfplumber sobre cores inválidas
    logging.getLogger("pdfminer").setLevel(logging.ERROR)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extrai dados de fatura Claro Empresas (PDF) → Excel"
    )
    parser.add_argument("pdf", help="Caminho para o PDF da fatura")
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="Arquivo de saída .xlsx (padrão: resultado.xlsx no mesmo diretório do PDF)",
    )
    parser.add_argument("--debug", action="store_true", help="Logs detalhados")
    args = parser.parse_args()

    _configure_logging(args.debug)
    logger = logging.getLogger(__name__)

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        logger.error("PDF não encontrado: %s", pdf_path)
        return 1

    output_path = Path(args.output) if args.output else pdf_path.parent / "resultado.xlsx"

    # --- Extração ---
    logger.info("Iniciando extração: %s", pdf_path.name)
    try:
        lines = read_pdf(pdf_path)
    except Exception:
        logger.exception("Falha na extração do PDF")
        return 2

    if not lines:
        logger.error("Nenhuma linha extraída — verifique o PDF")
        return 3

    # --- Resumo no terminal ---
    plans = {}
    for line in lines:
        plans[line.plano] = plans.get(line.plano, 0) + 1

    logger.info("=" * 50)
    logger.info("RESUMO DA EXTRAÇÃO")
    logger.info("Total de linhas: %d", len(lines))
    for plan, count in sorted(plans.items()):
        logger.info("  %-25s %d linhas", plan, count)
    if lines:
        gb_set = {l.gb for l in lines}
        logger.info("GB compartilhado: %s", ", ".join(str(g) for g in gb_set))
        fids = {l.fidelidade for l in lines if l.fidelidade}
        if fids:
            logger.info("Fidelidade: %s", ", ".join(sorted(fids)))
    logger.info("=" * 50)

    # --- Exportação ---
    try:
        export_excel(lines, output_path)
    except Exception:
        logger.exception("Falha na geração do Excel")
        return 4

    logger.info("Concluído! Arquivo: %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
