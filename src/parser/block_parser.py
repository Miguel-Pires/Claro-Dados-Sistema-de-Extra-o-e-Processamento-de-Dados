"""
Parser de blocos multi-coluna das faturas Claro Empresas.

Cada bloco tem a estrutura:
  VALOR DE COBRANÇAS POR CELULAR - USO POR TIPO DE LIGAÇÃO E SERVIÇOS EXCEDENTES
  (11) XXXXX XXXX  (11) XXXXX XXXX  ...  (até 6 telefones por bloco)
  Fidelidade até dd/mm/yyyy  Fidelidade até dd/mm/yyyy  ...
  Cobranças e Descontos
  Oferta Claro Total Mix Plugin Smartphone  R$ 21,37  R$ 21,37  ...
  Oferta Claro Total Mix Tablet e Modem    R$ 16,03  R$ 16,03  ...
  TOTAL PARA CADA CELULAR  R$ 21,37  R$ 16,03  ...

Cada coluna de telefone tem um âncora X fixo (~219, 275, 330, 385, 441, 496).
O mapeamento telefone→plano→valor é feito por proximidade de coordenada X.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .fidelity_parser import extract_date
from .phone_parser import build_masked, normalize_phone
from .value_parser import parse_valor
from ..models.line import PhoneLine

logger = logging.getLogger(__name__)

# Tolerância em pontos (pt) para associar valores à coluna do telefone.
# Espaçamento entre colunas é ~55pt; 30pt cobre metade sem ambiguidade.
X_TOLERANCE = 30

# Mapeamento de palavras-chave do plano → nome curto padronizado
PLAN_NAME_MAP: List[Tuple[re.Pattern, str, bool]] = [
    # (regex, nome_curto, é_individual)
    (re.compile(r"Plugin|Smartphone", re.I),          "Plugin Smartphone", False),
    (re.compile(r"Tablet.*Modem|Modem.*Tablet", re.I), "Tablet e Modem",   False),
    (re.compile(r"Oferta\s+Conjunta|Claro\s+MIX", re.I), "Claro MIX",     True),
    (re.compile(r"Claro\s+P[oó]s",         re.I),     "Claro Pós",         True),
    (re.compile(r"Claro\s+Life",           re.I),     "Claro Life",        True),
    (re.compile(r"Claro\s+Controle",       re.I),     "Claro Controle",    True),
    (re.compile(r"Claro\s+Flex",           re.I),     "Claro Flex",        True),
]

# Capacidade individual em planos do Cenário 2  ex.: "Claro Pós 25GB", "1TB"
_INDIVIDUAL_GB_RE = re.compile(r"(\d+)\s*(GB|TB|MB)", re.I)

# Detecta linhas de bônus de dados  ex.: "Bônus de 5GB", "Bônus de 500MB"
_BONUS_RE = re.compile(r"[Bb][oôõ]n[uú]s", re.I)


def _add_gb_strings(base: str, bonus: str) -> str:
    """Soma dois valores GB/MB/TB e retorna na unidade mais adequada."""
    def to_mb(s: str) -> float:
        m = re.match(r"(\d+(?:[.,]\d+)?)\s*(GB|TB|MB)", s.strip(), re.I)
        if not m:
            return 0.0
        val = float(m.group(1).replace(",", "."))
        unit = m.group(2).upper()
        if unit == "TB":
            return val * 1024 * 1024
        if unit == "GB":
            return val * 1024
        return val
    total_mb = to_mb(base) + to_mb(bonus)
    if total_mb >= 1024 * 1024:
        return f"{int(total_mb / (1024 * 1024))}TB"
    if total_mb >= 1024:
        val = total_mb / 1024
        return f"{int(val)}GB" if val == int(val) else f"{val:.1f}GB"
    return f"{int(total_mb)}MB"


# ---------------------------------------------------------------------------
# Estruturas internas
# ---------------------------------------------------------------------------

Word = dict  # dicionário de word com text/x0/x1/top/bottom


@dataclass
class _Block:
    """Estado acumulado de um bloco enquanto é processado."""
    phones: List[Tuple[str, float]] = field(default_factory=list)
    # [(masked_phone, x_anchor)]

    fidelidades: List[Tuple[str, float]] = field(default_factory=list)
    # [(date_str, x_anchor)]

    plan_values: Dict[str, List[Tuple[float, float]]] = field(default_factory=dict)
    # {plan_short_name: [(amount, x_anchor), ...]}

    individual_gb: Dict[str, str] = field(default_factory=dict)
    # {plan_short_name: "25GB"|"1TB"|"15MB"}  — usado apenas no Cenário 2

    def resolve(self, shared_gb: str) -> List[PhoneLine]:
        """Combina telefones com seus planos/valores via âncora X."""
        lines: List[PhoneLine] = []

        for phone_masked, phone_x in self.phones:
            value, plan_name = self._find_plan_and_value(phone_x)
            if value is None or plan_name is None:
                logger.warning("Telefone %s sem plano/valor mapeado", phone_masked)
                continue

            fidelidade = self._find_fidelidade(phone_x)
            is_individual = plan_name in self.individual_gb

            gb: str
            if is_individual:
                gb = self.individual_gb.get(plan_name, "")
            else:
                gb = shared_gb

            lines.append(PhoneLine(
                telefone=normalize_phone(phone_masked),
                telefone_mask=phone_masked,
                plano=plan_name,
                gb=gb,
                fidelidade=fidelidade,
                valor=value,
                is_individual_plan=is_individual,
            ))

        return lines

    def _find_plan_and_value(
        self, phone_x: float
    ) -> Tuple[Optional[float], Optional[str]]:
        for plan_name, value_list in self.plan_values.items():
            for amount, val_x in value_list:
                if abs(val_x - phone_x) <= X_TOLERANCE:
                    return amount, plan_name
        return None, None

    def _find_fidelidade(self, phone_x: float) -> Optional[str]:
        best_date: Optional[str] = None
        best_dist = X_TOLERANCE + 1
        for date, fid_x in self.fidelidades:
            dist = abs(fid_x - phone_x)
            if dist < best_dist:
                best_dist = dist
                best_date = date
        return best_date if best_dist <= X_TOLERANCE else None


# ---------------------------------------------------------------------------
# Detecção de tipo de linha
# ---------------------------------------------------------------------------

def _row_text(row: List[Word]) -> str:
    return " ".join(w["text"] for w in row)


def _is_block_header(row: List[Word]) -> bool:
    """'VALOR DE COBRANÇAS POR CELULAR - USO POR TIPO ...'"""
    t = _row_text(row).upper()
    return "COBRAN" in t and "CELULAR" in t and "VALOR" in t and "USO" in t


def _is_phone_row(row: List[Word]) -> bool:
    """Linha com padrão (DD) em x > 150 (fora da margem esquerda)."""
    return any(
        re.match(r"^\(\d{2}\)$", w["text"]) and w["x0"] > 150
        for w in row
    )


def _is_fidelidade_row(row: List[Word]) -> bool:
    t = _row_text(row)
    return "idelidade" in t  # cobre encoding variante


def _is_plan_row(row: List[Word]) -> bool:
    """Linha de plano com valor R$."""
    t = _row_text(row)
    has_rs = "R$" in t
    has_plan = any(pat.search(t) for pat, _, _ in PLAN_NAME_MAP)
    return has_rs and has_plan


def _is_total_row(row: List[Word]) -> bool:
    """'TOTAL PARA CADA CELULAR R$ ...'"""
    t = _row_text(row).upper()
    return "TOTAL" in t and "CADA" in t and "CELULAR" in t


# ---------------------------------------------------------------------------
# Extratores de linha
# ---------------------------------------------------------------------------

def _extract_phones(row: List[Word]) -> List[Tuple[str, float]]:
    """
    Extrai [(masked_phone, x_anchor), ...] de uma linha de telefones.
    Padrão: (DD) → XXXXX → XXXX  (3 tokens consecutivos)
    """
    phones: List[Tuple[str, float]] = []
    i = 0
    while i < len(row):
        w = row[i]
        if re.match(r"^\(\d{2}\)$", w["text"]) and w["x0"] > 150:
            x_anchor = w["x0"]
            ddd = w["text"][1:3]
            parts: List[str] = []
            j = i + 1
            while j < len(row) and len(parts) < 2:
                nw = row[j]
                if re.match(r"^\d{4,5}$", nw["text"]):
                    parts.append(nw["text"])
                    j += 1
                else:
                    break
            if len(parts) == 2:
                phones.append((build_masked(ddd, parts[0], parts[1]), x_anchor))
                i = j
            else:
                i += 1
        else:
            i += 1
    return phones


def _extract_fidelidades(row: List[Word]) -> List[Tuple[str, float]]:
    """
    Extrai [(date, x_anchor), ...] de uma linha de fidelidade.
    'Fidelidade@x=219 até@x=240 03/11/2026@x=248' → ('03/11/2026', 219.0)
    """
    results: List[Tuple[str, float]] = []
    for i, w in enumerate(row):
        if "idelidade" in w["text"]:
            x_anchor = w["x0"]
            # Procura a data nas próximas 3 palavras
            for j in range(i + 1, min(i + 4, len(row))):
                date = extract_date(row[j]["text"])
                if date:
                    results.append((date, x_anchor))
                    break
    return results


def _extract_plan_name(row: List[Word]) -> Tuple[str, bool, Optional[str]]:
    """
    Retorna (plan_short_name, is_individual, gb_label_or_none).
    gb_label ex.: "25GB", "1TB", "15MB" — apenas para Cenário 2.
    """
    t = _row_text(row)
    for pattern, short_name, is_individual in PLAN_NAME_MAP:
        if pattern.search(t):
            gb_label: Optional[str] = None
            if is_individual:
                m = _INDIVIDUAL_GB_RE.search(t)
                if m:
                    gb_label = f"{m.group(1)}{m.group(2).upper()}"
            return short_name, is_individual, gb_label
    return "Desconhecido", False, None


def _extract_values_with_x(row: List[Word]) -> List[Tuple[float, float]]:
    """
    Extrai [(amount, x_anchor), ...] onde x_anchor é o x do token 'R$'.
    'R$@x=219 16,03@x=252' → (16.03, 219.0)
    """
    results: List[Tuple[float, float]] = []
    for i, w in enumerate(row):
        if w["text"] == "R$" and i + 1 < len(row):
            amount = parse_valor(row[i + 1]["text"])
            if amount is not None:
                results.append((amount, w["x0"]))
    return results


# ---------------------------------------------------------------------------
# Agrupamento por linha (eixo Y)
# ---------------------------------------------------------------------------

def _group_by_y(words: List[Word], tolerance: int = 5) -> List[List[Word]]:
    """
    Agrupa palavras em linhas por proximidade no eixo Y.
    Retorna lista de linhas, cada uma ordenada da esquerda para direita.
    """
    if not words:
        return []

    sorted_words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    rows: List[List[Word]] = [[sorted_words[0]]]

    for w in sorted_words[1:]:
        if abs(w["top"] - rows[-1][0]["top"]) <= tolerance:
            rows[-1].append(w)
        else:
            rows.append([w])

    return [sorted(r, key=lambda w: w["x0"]) for r in rows]


# ---------------------------------------------------------------------------
# Parser principal de página
# ---------------------------------------------------------------------------

def parse_page_words(
    words: List[Word],
    shared_gb: str,
    open_block: Optional[_Block] = None,
) -> Tuple[List[PhoneLine], Optional[_Block]]:
    """Processa words pré-extraídos de uma página (sem chamar extract_words)."""
    rows = _group_by_y(words, tolerance=5)

    lines: List[PhoneLine] = []
    block: Optional[_Block] = open_block  # Continua bloco da página anterior
    last_plan_name: Optional[str] = None  # Último plano com valores reais (para capturar GB sub-row)

    for row in rows:
        if not row:
            continue

        if _is_block_header(row):
            # Se há bloco sem TOTAL vindo da página anterior, descarta
            # (situação anômala — o bloco correto já foi resolvido ou perdido).
            if block is not None and block.phones and open_block is not block:
                logger.debug("Bloco intermediário descartado: %d telefones", len(block.phones))
            block = _Block()
            last_plan_name = None
            continue

        if block is None:
            continue  # Fora de bloco

        if _is_phone_row(row):
            if block.phones:
                # Duplicata do cabeçalho de continuação de página — ignora.
                logger.debug("Linha de telefones duplicada ignorada (continuação de página)")
            else:
                block.phones = _extract_phones(row)

        elif _is_fidelidade_row(row):
            if not block.fidelidades:  # Só coleta uma vez
                block.fidelidades = _extract_fidelidades(row)

        elif _is_plan_row(row):
            plan_name, is_individual, gb = _extract_plan_name(row)
            values = _extract_values_with_x(row)
            if values:
                block.plan_values.setdefault(plan_name, []).extend(values)
                last_plan_name = plan_name
                if is_individual and gb is not None:
                    block.individual_gb[plan_name] = gb

        elif _is_total_row(row):
            resolved = block.resolve(shared_gb)
            lines.extend(resolved)
            logger.debug("Bloco finalizado: %d linhas", len(resolved))
            block = None
            last_plan_name = None

        else:
            # Sub-info rows: linhas sem R$ dentro de um bloco ativo.
            if last_plan_name is not None:
                t = _row_text(row)
                if "R$" not in t:
                    m_gb = _INDIVIDUAL_GB_RE.search(t)
                    if m_gb:
                        gb_label = f"{m_gb.group(1)}{m_gb.group(2).upper()}"
                        if _BONUS_RE.search(t):
                            # Bônus de dados: soma ao GB base do plano pai
                            base = block.individual_gb.get(last_plan_name, "")
                            new_gb = _add_gb_strings(base, gb_label) if base else gb_label
                            block.individual_gb[last_plan_name] = new_gb
                            logger.debug("GB bônus: %s + %s → %s", last_plan_name, gb_label, new_gb)
                        elif any(pat.search(t) for pat, _, _ in PLAN_NAME_MAP):
                            # Sub-row de plano (ex.: "Claro Pós 25GB"): define o GB base
                            block.individual_gb[last_plan_name] = gb_label
                            logger.debug("GB sub-info: %s → %s", last_plan_name, gb_label)

    # Retorna bloco aberto para ser continuado na próxima página
    return lines, block
