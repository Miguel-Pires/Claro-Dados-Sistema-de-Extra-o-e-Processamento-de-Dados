import re
from typing import Optional


DATE_PATTERN = re.compile(r"\d{2}/\d{2}/\d{4}")


def extract_date(text: str) -> Optional[str]:
    """Extrai 'dd/mm/yyyy' de qualquer string."""
    m = DATE_PATTERN.search(text)
    return m.group(0) if m else None
