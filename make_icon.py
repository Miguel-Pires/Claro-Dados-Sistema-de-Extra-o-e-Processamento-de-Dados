"""
Gera o icone do Analisador de Faturas.
Design: documento com dados em grade + checkmark verde no canto.
"""
from PIL import Image, ImageDraw
from pathlib import Path


def _rr(draw: ImageDraw.ImageDraw, box, r: int, **kw) -> None:
    """Rounded rectangle helper."""
    draw.rounded_rectangle(box, radius=r, **kw)


def make_frame(size: int) -> Image.Image:
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ── Fundo arredondado ─────────────────────────────────────────────────
    bg_r = max(4, s // 6)
    _rr(d, [0, 0, s - 1, s - 1], bg_r, fill=(18, 24, 38))   # azul noite

    # Faixa superior (accent)
    _rr(d, [0, 0, s - 1, s // 3], bg_r, fill=(30, 58, 95))
    d.rectangle([0, s // 6, s - 1, s // 3], fill=(30, 58, 95))  # nao arredondar embaixo

    # ── Documento (papel branco) ───────────────────────────────────────────
    ml = int(s * 0.18)   # margem esquerda
    mr = int(s * 0.78)   # margem direita
    mt = int(s * 0.14)   # margem topo
    mb = int(s * 0.84)   # margem base
    fold = int(s * 0.14) # orelha dobrada

    # Corpo do papel
    body = [(ml, mt), (mr - fold, mt), (mr, mt + fold), (mr, mb), (ml, mb)]
    d.polygon(body, fill=(240, 248, 255))

    # Orelha dobrada (canto superior direito)
    d.polygon([(mr - fold, mt), (mr, mt + fold), (mr - fold, mt + fold)],
              fill=(178, 204, 230))

    # ── Linhas de dados ────────────────────────────────────────────────────
    lx1 = int(s * 0.26)
    lh  = max(2, s // 32)
    gap = int(s * 0.095)
    y0  = int(s * 0.40)
    rows = [
        ((59, 130, 246), 0.46),   # azul - linha longa
        ((100, 160, 240), 0.36),  # azul medio - linha media
        ((59, 130, 246), 0.46),   # azul - linha longa
        ((147, 197, 253), 0.26),  # azul claro - linha curta
    ]
    for i, (color, ratio) in enumerate(rows):
        y = y0 + i * gap
        lx2 = lx1 + int((mr - fold - lx1) * ratio + (mr - fold - lx1) * 0.54)
        lx2 = min(lx2, mr - fold - int(s * 0.04))
        _rr(d, [lx1, y, lx2, y + lh], max(1, lh // 2), fill=color)

    # ── Checkmark verde (circulo no canto inferior direito) ───────────────
    cr  = int(s * 0.155)          # raio do circulo
    cx  = mr - int(s * 0.01)     # centro x
    cy  = mb - int(s * 0.01)     # centro y

    # Sombra/halo sutil
    halo = int(cr * 0.18)
    d.ellipse([cx - cr - halo, cy - cr - halo,
               cx + cr + halo, cy + cr + halo], fill=(10, 40, 20, 120))

    # Circulo verde
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(22, 163, 74))
    d.ellipse([cx - cr + 1, cy - cr + 1, cx + cr - 1, cy + cr - 1],
              fill=(34, 197, 94))

    # Checkmark (dois segmentos)
    ck = max(2, s // 38)
    p1 = (cx - int(cr * 0.50), cy + int(cr * 0.02))
    p2 = (cx - int(cr * 0.10), cy + int(cr * 0.45))
    p3 = (cx + int(cr * 0.52), cy - int(cr * 0.38))
    d.line([p1, p2], fill="white", width=ck)
    d.line([p2, p3], fill="white", width=ck)

    return img


def build_ico(out: Path) -> None:
    sizes = [256, 128, 64, 48, 32, 16]
    frames = [make_frame(s).convert("RGBA") for s in sizes]

    # PIL salva multi-resolucao quando passamos lista de imagens
    frames[0].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f"Icone salvo: {out}  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    dest = Path(__file__).parent / "icon.ico"
    build_ico(dest)

    # Preview em PNG para conferir
    preview = Path(__file__).parent / "icon_preview.png"
    make_frame(256).save(preview)
    print(f"Preview: {preview}")
