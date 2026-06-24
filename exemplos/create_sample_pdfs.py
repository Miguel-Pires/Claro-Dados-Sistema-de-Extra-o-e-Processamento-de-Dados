"""
Gera faturas Claro Empresas fictícias para testes do parser.

Cobre todos os tipos de plano suportados:
  fatura_compartilhado_900gb.pdf  — Plugin Smartphone + Tablet e Modem, 900 GB compartilhado
  fatura_claro_mix_25gb.pdf       — Oferta Conjunta Claro MIX, Claro Pos 25 GB individual
  fatura_planos_individuais.pdf   — Claro Controle 15GB + Claro Flex + Claro Life

Execução:
    python exemplos/create_sample_pdfs.py
"""
from __future__ import annotations

from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

PAGE_W, PAGE_H = A4   # 595.28 x 841.89

# Âncoras X exatas das colunas (copiadas do PDF real via PyMuPDF)
COL_X = [219.2, 274.5, 329.9, 385.3, 440.6, 496.0]

FONT_B = "Helvetica-Bold"
FONT_R = "Helvetica"
FS = 7.0  # tamanho de fonte que reproduz a densidade do PDF real


def _rl(pymupdf_y_top: float) -> float:
    """Converte y_top do PyMuPDF (origem superior) para baseline do reportlab (origem inferior)."""
    return PAGE_H - pymupdf_y_top - FS * 0.85


# Posições Y de cada linha dentro de um bloco (mesmos offsets do PDF real)
_Y = {
    "header":  _rl(17.3),
    "phones":  _rl(32.9),
    "fidel":   _rl(42.3),
    "subhdr":  _rl(50.4),
    "plan1":   _rl(60.1),
    "sub1a":   _rl(69.8),
    "sub1b":   _rl(79.5),
    "plan2":   _rl(89.2),
    "sub2a":   _rl(99.0),
    "sub2b":   _rl(108.7),
    "total":   _rl(125.7),
}
BLOCK_H = _Y["header"] - _rl(144.0)  # altura de um bloco em pontos


# ---------------------------------------------------------------------------
# Primitivas de desenho
# ---------------------------------------------------------------------------

def _font(c: canvas.Canvas, bold: bool = False, size: float = FS):
    c.setFont(FONT_B if bold else FONT_R, size)


def draw_block_header(c: canvas.Canvas, base: float):
    """Linha 'VALOR DE COBRANCAS POR CELULAR - USO POR TIPO ...'"""
    _font(c, bold=True)
    c.drawString(
        43.9, base,
        "VALOR DE COBRANCAS POR CELULAR - USO POR TIPO DE LIGACAO E SERVICOS EXCEDENTES",
    )


def draw_phones(c: canvas.Canvas, y: float, phones: list[tuple]):
    """Desenha até 6 telefones.

    IMPORTANTE: drawString com espaços faz o PyMuPDF separar os tokens
    '(11)', 'XXXXX', 'XXXX' como palavras distintas — o que o block_parser
    precisa para detectar _is_phone_row e extrair o x_anchor correto.
    """
    _font(c, bold=False)
    for i, (ddd, p5, p4) in enumerate(phones[:6]):
        c.drawString(COL_X[i], y, f"({ddd}) {p5} {p4}")


def draw_fidelidade(c: canvas.Canvas, y: float, phones: list, date: str):
    """'Fidelidade ate DD/MM/YYYY' em cada coluna de telefone."""
    _font(c, bold=False)
    for i in range(len(phones)):
        c.drawString(COL_X[i], y, f"Fidelidade ate {date}")


def draw_plan_row(c: canvas.Canvas, y: float, plan_label: str, valor: str, cols: list[int]):
    """Linha de plano com R$ nos índices de coluna indicados.

    'R$ XX,XX' como string única garante que o PyMuPDF separe 'R$' e 'XX,XX'
    em dois tokens — exatamente o que _extract_values_with_x espera.
    """
    _font(c, bold=False)
    c.drawString(43.9, y, plan_label)
    for idx in cols:
        c.drawString(COL_X[idx], y, f"R$ {valor}")


def draw_subplan_row(c: canvas.Canvas, y: float, label: str, ncols: int):
    """Sub-linha de plano sem R$ (ex: 'Claro Pos 25GB', 'Aplicativos Digitais')."""
    _font(c, bold=False)
    c.drawString(52.4, y, label)
    for i in range(ncols):
        c.drawString(COL_X[i] + 8.0, y, "-")


def draw_total(c: canvas.Canvas, y: float, phone_values: list[tuple[int, str]]):
    """'TOTAL PARA CADA CELULAR' + R$ XX,XX por coluna."""
    _font(c, bold=True)
    c.drawString(43.9, y, "TOTAL PARA CADA CELULAR")
    _font(c, bold=False)
    for idx, val in phone_values:
        c.drawString(COL_X[idx], y, f"R$ {val}")


def draw_detalhamento(
    c: canvas.Canvas,
    start_y: float,
    masked_phone: str,   # ex: "(11) 97001 0001"
    plan_label: str,
    valor: str,
    mb_total: str,       # ex: "1234,567"
) -> float:
    """Bloco DETALHAMENTO para um telefone. Retorna Y após o bloco."""
    _font(c, bold=True)
    c.drawString(43.9, start_y,
        f"DETALHAMENTO DE LIGACOES E SERVICOS DO CELULAR {masked_phone}")

    y = start_y - 12
    _font(c, bold=True)
    c.drawString(43.9, y, "Mensalidades e Pacotes Promocionais")

    y -= 10
    _font(c, bold=False)
    c.drawString(43.9, y, "Descricao")
    c.drawString(400,  y, "Total (R$)")

    y -= 10
    c.drawString(43.9, y, plan_label)
    c.drawString(400,  y, valor)

    y -= 10
    _font(c, bold=True)
    c.drawString(43.9, y, "TOTAL")
    _font(c, bold=False)
    c.drawString(400,  y, f"R$ {valor}")

    y -= 16
    _font(c, bold=True)
    c.drawString(43.9, y, "Internet (MB)")

    y -= 10
    _font(c, bold=False)
    c.drawString(43.9, y, "Servico")
    c.drawString(200,  y, "Mbytes Utilizados")
    c.drawString(360,  y, "Tarifa (R$)")
    c.drawString(450,  y, "Valor (R$)")

    y -= 10
    c.drawString(43.9, y, "Internet")
    c.drawString(200,  y, mb_total)
    c.drawString(360,  y, "0,00")
    c.drawString(450,  y, "0,00")

    y -= 10
    _font(c, bold=True)
    c.drawString(43.9, y, "Subtotal")
    _font(c, bold=False)
    c.drawString(200,  y, mb_total)
    c.drawString(360,  y, "0,00")

    return y - 20


def _detalhamento_pages(c: canvas.Canvas, phones: list, plan_labels: list, valores: list, mb_vals: list):
    """Gera páginas de detalhamento para todos os telefones (3 por página)."""
    y_cursor = _rl(17.3)
    for i, ph in enumerate(phones):
        if i % 3 == 0 and i > 0:
            c.showPage()
            y_cursor = _rl(17.3)
        masked = f"({ph[0]}) {ph[1]} {ph[2]}"
        y_cursor = draw_detalhamento(c, y_cursor, masked, plan_labels[i], valores[i], mb_vals[i])
    c.showPage()


# ---------------------------------------------------------------------------
# Fatura 1 — Compartilhado 900 GB
# ---------------------------------------------------------------------------

def make_fatura_compartilhado_900gb(out_dir: Path):
    """
    12 telefones: 9 Plugin Smartphone (R$21,37) + 3 Tablet e Modem (R$16,03)
    Plano compartilhado 900 GB — sem fidelidade individual no cabeçalho do bloco,
    apenas a data de fidelidade por linha.
    """
    path = out_dir / "fatura_compartilhado_900gb.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)

    FIDELIDADE = "01/08/2027"
    PLUGIN_VAL = "21,37"
    TABLET_VAL = "16,03"

    phones = [
        ("11", "97001", "0001"), ("11", "97001", "0002"), ("11", "97001", "0003"),
        ("11", "97001", "0004"), ("11", "97001", "0005"), ("11", "97001", "0006"),
        ("11", "97001", "0007"), ("11", "97001", "0008"), ("11", "97001", "0009"),
        ("11", "97002", "0001"), ("11", "97002", "0002"), ("11", "97002", "0003"),
    ]
    plan_type = ["plugin"] * 9 + ["tablet"] * 3
    mb_vals = [
        "550,570", "1601,686", "4835,303", "14679,320",
        "57426,258", "4680,111", "117,289", "441,306",
        "360,719", "730,276", "7732,860", "3017,046",
    ]

    # Página 1 — cabeçalho com declaração do plano compartilhado
    _font(c, bold=True, size=11)
    c.drawString(43.9, 800, "CLARO EMPRESAS")
    _font(c, bold=False, size=9)
    c.drawString(43.9, 785, "Fatura de Servicos de Telecomunicacoes")
    c.drawString(43.9, 773, "Empresa Ficticia Ltda   CNPJ: 00.000.000/0001-00")
    c.drawString(43.9, 761, "Referencia: Jan/2026")
    _font(c, bold=False, size=7)
    # shared_plan.py detecta: "Compartilhado 900GB"
    c.drawString(43.9, 740, "Plano Compartilhado 900GB")
    c.drawString(43.9, 728, "Compartilhado 900GB")
    c.showPage()

    # Páginas de cobrança — 2 blocos de 6 linhas
    for batch_start in (0, 6):
        batch = phones[batch_start:batch_start + 6]
        btypes = plan_type[batch_start:batch_start + 6]
        plugin_cols = [i for i, t in enumerate(btypes) if t == "plugin"]
        tablet_cols = [i for i, t in enumerate(btypes) if t == "tablet"]

        draw_block_header(c, _Y["header"])
        draw_phones(c, _Y["phones"], batch)
        draw_fidelidade(c, _Y["fidel"], batch, FIDELIDADE)

        _font(c, bold=False)
        c.drawString(43.9, _Y["subhdr"], "Cobrancas e Descontos")

        if plugin_cols:
            draw_plan_row(c, _Y["plan1"],
                "Oferta Claro Total Mix Plugin Smartphone", PLUGIN_VAL, plugin_cols)
            draw_subplan_row(c, _Y["sub1a"], "Assinatura Smartphone [192]", len(plugin_cols))
            draw_subplan_row(c, _Y["sub1b"], "Aplicativos Digitais", len(plugin_cols))

        if tablet_cols:
            draw_plan_row(c, _Y["plan2"],
                "Oferta Claro Total Mix Tablet e Modem", TABLET_VAL, tablet_cols)
            draw_subplan_row(c, _Y["sub2a"], "Assinatura Tablet/Modem [192]", len(tablet_cols))
            draw_subplan_row(c, _Y["sub2b"], "Aplicativos Digitais", len(tablet_cols))

        total_vals = [
            (i, PLUGIN_VAL if btypes[i] == "plugin" else TABLET_VAL)
            for i in range(len(batch))
        ]
        draw_total(c, _Y["total"], total_vals)
        c.showPage()

    # Páginas de detalhamento
    plan_labels = [
        "Oferta Claro Total Mix Plugin Smartphone" if t == "plugin"
        else "Oferta Claro Total Mix Tablet e Modem"
        for t in plan_type
    ]
    valores = [PLUGIN_VAL if t == "plugin" else TABLET_VAL for t in plan_type]
    _detalhamento_pages(c, phones, plan_labels, valores, mb_vals)

    c.save()
    print(f"  OK  {path.name}  ({len(phones)} linhas)")


# ---------------------------------------------------------------------------
# Fatura 2 — Claro MIX 25 GB
# ---------------------------------------------------------------------------

def make_fatura_claro_mix_25gb(out_dir: Path):
    """
    8 telefones: todos Oferta Conjunta Claro MIX + Claro Pos 25 GB individual.
    SEM plano compartilhado — shared_plan retorna None → Cenário 2.
    """
    path = out_dir / "fatura_claro_mix_25gb.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)

    FIDELIDADE = "15/03/2027"
    MIX_VAL    = "60,99"

    phones = [
        ("11", "97003", "0001"), ("11", "97003", "0002"), ("11", "97003", "0003"),
        ("11", "97003", "0004"), ("11", "97003", "0005"), ("11", "97003", "0006"),
        ("11", "97003", "0007"), ("11", "97003", "0008"),
    ]
    mb_vals = [
        "1295,797", "2327,308", "2847,610", "17477,001",
        "8380,800", "2324,934", "0,020", "3141,592",
    ]

    # Página 1 — sem Compartilhado (Cenário 2)
    _font(c, bold=True, size=11)
    c.drawString(43.9, 800, "CLARO EMPRESAS")
    _font(c, bold=False, size=9)
    c.drawString(43.9, 785, "Fatura de Servicos de Telecomunicacoes")
    c.drawString(43.9, 773, "Empresa Ficticia Dois Ltda   CNPJ: 00.000.000/0002-00")
    c.drawString(43.9, 761, "Referencia: Fev/2026")
    c.showPage()

    # Páginas de cobrança (bloco 1 com 6 + bloco 2 com 2)
    for batch_start in (0, 6):
        batch = phones[batch_start:min(batch_start + 6, len(phones))]
        n = len(batch)
        all_cols = list(range(n))

        draw_block_header(c, _Y["header"])
        draw_phones(c, _Y["phones"], batch)
        draw_fidelidade(c, _Y["fidel"], batch, FIDELIDADE)

        _font(c, bold=False)
        c.drawString(43.9, _Y["subhdr"], "Cobrancas e Descontos")

        draw_plan_row(c, _Y["plan1"],
            "Oferta Conjunta Claro MIX", MIX_VAL, all_cols)

        # Sub-row SEM R$ → parser detecta "25GB" e define individual_gb["Claro MIX"]
        _font(c, bold=False)
        c.drawString(52.4, _Y["sub1a"], "Claro Pos 25GB")
        for i in range(n):
            c.drawString(COL_X[i] + 8.0, _Y["sub1a"], "-")

        draw_subplan_row(c, _Y["sub1b"], "Aplicativos Digitais", n)

        draw_total(c, _Y["total"], [(i, MIX_VAL) for i in range(n)])
        c.showPage()

    _detalhamento_pages(
        c, phones,
        ["Oferta Conjunta Claro MIX"] * len(phones),
        [MIX_VAL] * len(phones),
        mb_vals,
    )
    c.save()
    print(f"  OK  {path.name}  ({len(phones)} linhas)")


# ---------------------------------------------------------------------------
# Fatura 3 — Planos individuais mistos
# ---------------------------------------------------------------------------

def make_fatura_planos_individuais(out_dir: Path):
    """
    9 telefones: 3 Claro Controle 15GB (R$45,99) + 3 Claro Flex (R$35,50) + 3 Claro Life (R$29,90).
    Variação de fidelidade entre os grupos.
    """
    path = out_dir / "fatura_planos_individuais.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)

    FID_A = "10/05/2027"
    FID_B = "22/09/2026"

    CONTROLE_VAL = "45,99"
    FLEX_VAL     = "35,50"
    LIFE_VAL     = "29,90"

    phones = [
        ("11", "97004", "0001"), ("11", "97004", "0002"), ("11", "97004", "0003"),
        ("11", "97004", "0004"), ("11", "97004", "0005"), ("11", "97004", "0006"),
        ("11", "97004", "0007"), ("11", "97004", "0008"), ("11", "97004", "0009"),
    ]
    plan_type  = ["controle"] * 3 + ["flex"] * 3 + ["life"] * 3
    fidelidade = [FID_A] * 6 + [FID_B] * 3
    mb_vals    = [
        "2100,500", "3750,200", "800,100",
        "5200,350", "450,780",  "12000,000",
        "620,430",  "1890,670", "340,220",
    ]

    PLAN_LABEL = {
        "controle": "Claro Controle 15GB",
        "flex":     "Claro Flex",
        "life":     "Claro Life",
    }
    PLAN_VAL = {"controle": CONTROLE_VAL, "flex": FLEX_VAL, "life": LIFE_VAL}

    # Página 1 — cabeçalho
    _font(c, bold=True, size=11)
    c.drawString(43.9, 800, "CLARO EMPRESAS")
    _font(c, bold=False, size=9)
    c.drawString(43.9, 785, "Fatura de Servicos de Telecomunicacoes")
    c.drawString(43.9, 773, "Empresa Ficticia Tres Ltda   CNPJ: 00.000.000/0003-00")
    c.drawString(43.9, 761, "Referencia: Mar/2026")
    c.showPage()

    # Bloco 1: colunas 0-2 = Controle, colunas 3-5 = Flex
    batch1 = phones[:6]
    btypes1 = plan_type[:6]
    controle_cols = [0, 1, 2]
    flex_cols     = [3, 4, 5]

    draw_block_header(c, _Y["header"])
    draw_phones(c, _Y["phones"], batch1)

    # Fidelidade com datas diferentes por coluna
    _font(c, bold=False)
    for i in range(6):
        c.drawString(COL_X[i], _Y["fidel"], f"Fidelidade ate {fidelidade[i]}")

    _font(c, bold=False)
    c.drawString(43.9, _Y["subhdr"], "Cobrancas e Descontos")

    draw_plan_row(c, _Y["plan1"], "Claro Controle 15GB", CONTROLE_VAL, controle_cols)
    draw_subplan_row(c, _Y["sub1a"], "Aplicativos Digitais", 3)

    draw_plan_row(c, _Y["plan2"], "Claro Flex",           FLEX_VAL,     flex_cols)
    draw_subplan_row(c, _Y["sub2a"], "Aplicativos Digitais", 3)

    total_b1 = [(i, CONTROLE_VAL if i < 3 else FLEX_VAL) for i in range(6)]
    draw_total(c, _Y["total"], total_b1)
    c.showPage()

    # Bloco 2: colunas 0-2 = Life
    batch2 = phones[6:]
    life_cols = [0, 1, 2]

    draw_block_header(c, _Y["header"])
    draw_phones(c, _Y["phones"], batch2)

    _font(c, bold=False)
    for i in range(3):
        c.drawString(COL_X[i], _Y["fidel"], f"Fidelidade ate {fidelidade[6 + i]}")

    _font(c, bold=False)
    c.drawString(43.9, _Y["subhdr"], "Cobrancas e Descontos")

    draw_plan_row(c, _Y["plan1"], "Claro Life", LIFE_VAL, life_cols)
    draw_subplan_row(c, _Y["sub1a"], "Aplicativos Digitais", 3)

    draw_total(c, _Y["total"], [(i, LIFE_VAL) for i in range(3)])
    c.showPage()

    _detalhamento_pages(
        c, phones,
        [PLAN_LABEL[t] for t in plan_type],
        [PLAN_VAL[t]   for t in plan_type],
        mb_vals,
    )
    c.save()
    print(f"  OK  {path.name}  ({len(phones)} linhas)")


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    out_dir = Path(__file__).parent
    out_dir.mkdir(exist_ok=True)
    print("Gerando faturas de exemplo...\n")
    make_fatura_compartilhado_900gb(out_dir)
    make_fatura_claro_mix_25gb(out_dir)
    make_fatura_planos_individuais(out_dir)
    print(f"\nTodos os PDFs em: {out_dir.resolve()}")
