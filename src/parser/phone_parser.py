import re


def normalize_phone(masked: str) -> str:
    """Remove máscara: '(11) 91338 6865' → '11913386865'"""
    return re.sub(r"\D", "", masked)


def build_masked(ddd: str, part1: str, part2: str) -> str:
    """Reconstrói formato mascarado: '(11) 91338 6865'"""
    return f"({ddd}) {part1} {part2}"
