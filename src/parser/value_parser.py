import re
from typing import Optional


def parse_valor(text: str) -> Optional[float]:
    """
    Converte string monetária brasileira para float.
    Aceita: "16,03", "R$ 16,03", "R$16,03", "1.234,56"
    Retorna None se não for valor válido.
    """
    text = text.strip()
    # Remove prefixo R$
    text = re.sub(r"^R\$\s*", "", text)
    # Remove separador de milhar (ponto antes de vírgula decimal)
    # "1.234,56" → "1234,56"
    text = re.sub(r"\.(?=\d{3},)", "", text)
    match = re.fullmatch(r"(\d+),(\d{2})", text)
    if match:
        return float(f"{match.group(1)}.{match.group(2)}")
    return None
