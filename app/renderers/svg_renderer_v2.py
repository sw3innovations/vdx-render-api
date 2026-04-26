"""
SVG Renderer v2 — renderizador autônomo de tipologias de vidraçaria.

Consulta constitution.db diretamente; sem dependências do pipeline antigo.
Única API pública: render(tipologia, largura, altura, cor, acabamento) → str SVG
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "constitution.db"

# ─── Paletas ──────────────────────────────────────────────────────────────────

_VIDRO: dict[str, tuple[str, str]] = {
    "incolor": ("#D4EAF7", "#5E8CB0"),
    "verde":   ("#BDDAB0", "#5A8A50"),
    "fume":    ("#8E9EA8", "#4A5E6A"),
    "bronze":  ("#C9A870", "#8B6830"),
    "azul":    ("#9DBFE0", "#3D70A8"),
    "espelho": ("#D4DCE4", "#7090A8"),
}

_ACABAMENTO: dict[str, str] = {
    "cromado": "#90B0C8",
    "inox":    "#8898A8",
    "preto":   "#303840",
    "dourado": "#C0A030",
}

# ─── Constantes de layout ─────────────────────────────────────────────────────

VW, VH = 600, 800
ML, MT, MR, MB = 65, 52, 112, 40   # margem left/top/right/bottom em px
GAP_PX = 12                          # gap entre peças side-by-side

_COR_COTA  = "#4A7098"
_COR_COTAL = "#7A9AAA"
_COR_LABEL = "#503880"

# ─── Primitivas SVG ───────────────────────────────────────────────────────────

def _r(v: float) -> str:
    return f"{v:.1f}"


def _rect(x, y, w, h, fill, stroke="none", sw=1.5, rx=0) -> str:
    return (f'<rect x="{_r(x)}" y="{_r(y)}" width="{_r(w)}" height="{_r(h)}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"/>')


def _line(x1, y1, x2, y2, stroke, sw=1.0, dash="") -> str:
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{_r(x1)}" y1="{_r(y1)}" x2="{_r(x2)}" y2="{_r(y2)}" '
            f'stroke="{stroke}" stroke-width="{sw}"{da}/>')


def _circle(cx, cy, r, fill, stroke, sw=1.5) -> str:
    return (f'<circle cx="{_r(cx)}" cy="{_r(cy)}" r="{_r(r)}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def _text(x, y, txt, fill, size=9, anchor="middle", weight="normal", rotate=0) -> str:
    rot = f' transform="rotate({rotate},{_r(x)},{_r(y)})"' if rotate else ""
    return (f'<text x="{_r(x)}" y="{_r(y)}" fill="{fill}" font-size="{size}" '
            f'font-family="\'Courier New\',monospace" text-anchor="{anchor}" '
            f'dominant-baseline="middle" font-weight="{weight}"{rot}>{txt}</text>')


def _arrow_h(x1, y, x2, stroke, sz=4.0) -> str:
    d = 1.0 if x2 > x1 else -1.0
    return (f'<line x1="{_r(x1)}" y1="{_r(y)}" x2="{_r(x2)}" y2="{_r(y)}" '
            f'stroke="{stroke}" stroke-width="1"/>'
            f'<polygon points="{_r(x2)},{_r(y)} {_r(x2-d*sz)},{_r(y-sz/2)} '
            f'{_r(x2-d*sz)},{_r(y+sz/2)}" fill="{stroke}"/>')


def _arrow_v(x, y1, y2, stroke, sz=4.0) -> str:
    d = 1.0 if y2 > y1 else -1.0
    return (f'<line x1="{_r(x)}" y1="{_r(y1)}" x2="{_r(x)}" y2="{_r(y2)}" '
            f'stroke="{stroke}" stroke-width="1"/>'
            f'<polygon points="{_r(x)},{_r(y2)} {_r(x-sz/2)},{_r(y2-d*sz)} '
            f'{_r(x+sz/2)},{_r(y2-d*sz)}" fill="{stroke}"/>')


# ─── Avaliação de fórmulas ────────────────────────────────────────────────────

def _eval_formula(formula: str, largura: float, altura: float) -> float:
    try:
        return float(eval(formula, {"__builtins__": {}},
                          {"largura": largura, "altura": altura}))
    except Exception:
        return 0.0


# ─── Símbolos de ferragem ─────────────────────────────────────────────────────

def _sim_dobradica(px, py, acab) -> str:
    rw, rh = 14, 24
    x0, y0 = px - rw / 2, py - rh / 2
    return "\n".join([
        f'<rect x="{_r(x0)}" y="{_r(y0)}" width="{rw}" height="{rh}" '
        f'fill="{acab}" fill-opacity="0.35" stroke="{acab}" stroke-width="1.5"/>',
        _circle(px, y0 + 5, 2.0, acab, acab, 0),
        _circle(px, y0 + rh - 5, 2.0, acab, acab, 0),
    ])


def _sim_pivo(px, py, acab) -> str:
    return "\n".join([
        _circle(px, py, 7.0, acab, acab, 1.5),
        _circle(px, py, 2.5, "white", "white", 0),
    ])


def _sim_fechadura(px, py, acab) -> str:
    rw, rh = 12, 18
    x0, y0 = px - rw / 2, py - rh / 2
    return "\n".join([
        f'<rect x="{_r(x0)}" y="{_r(y0)}" width="{rw}" height="{rh}" '
        f'fill="{acab}" fill-opacity="0.35" stroke="{acab}" stroke-width="1.5"/>',
        _circle(px, y0 + 6.5, 2.8, "white", acab, 0.8),
        (f'<polygon points="{_r(px-2.0)},{_r(y0+9.5)} {_r(px+2.0)},{_r(y0+9.5)} '
         f'{_r(px+3.0)},{_r(y0+15)} {_r(px-3.0)},{_r(y0+15)}" '
         f'fill="white" stroke="{acab}" stroke-width="0.5"/>'),
    ])


def _sim_puxador(px, py, acab) -> str:
    return "\n".join([
        _line(px - 12, py, px + 12, py, acab, 3.5),
        _circle(px - 12, py, 3.0, acab, acab, 0),
        _circle(px + 12, py, 3.0, acab, acab, 0),
    ])


def _sim_roldana(px, py, acab) -> str:
    return "\n".join([
        _circle(px, py, 7.5, acab, acab, 1.5),
        _circle(px, py, 2.5, "white", "white", 0),
        _line(px - 13, py, px + 13, py, acab, 0.8),
    ])


def _sim_suporte(px, py, acab) -> str:
    return "\n".join([
        _circle(px, py, 6.5, acab, acab, 1.5),
        _circle(px, py, 2.0, "white", "white", 0),
    ])


def _sim_trinco(px, py, acab) -> str:
    rw, rh = 16, 10
    x0, y0 = px - rw / 2, py - rh / 2
    return "\n".join([
        f'<rect x="{_r(x0)}" y="{_r(y0)}" width="{rw}" height="{rh}" '
        f'fill="{acab}" fill-opacity="0.4" stroke="{acab}" stroke-width="1.2"/>',
        _circle(px, py, 3.0, "white", acab, 0.8),
    ])


def _sim_bate_fecha(px, py, acab) -> str:
    rw, rh = 10, 20
    x0, y0 = px - rw / 2, py - rh / 2
    return (f'<rect x="{_r(x0)}" y="{_r(y0)}" width="{rw}" height="{rh}" '
            f'fill="{acab}" fill-opacity="0.4" stroke="{acab}" stroke-width="1.2" rx="2"/>')


def _simbolo(tipo: str, px: float, py: float, acab: str) -> str:
    t = tipo.lower()
    if "dobradica" in t or "dobradiça" in t:
        return _sim_dobradica(px, py, acab)
    if "pivo" in t or "pivô" in t:
        return _sim_pivo(px, py, acab)
    if "fechadura" in t:
        return _sim_fechadura(px, py, acab)
    if "puxador" in t:
        return _sim_puxador(px, py, acab)
    if "roldana" in t:
        return _sim_roldana(px, py, acab)
    if "suporte" in t:
        return _sim_suporte(px, py, acab)
    if "trinco" in t:
        return _sim_trinco(px, py, acab)
    if "bate" in t:
        return _sim_bate_fecha(px, py, acab)
    return _sim_suporte(px, py, acab)


# ─── Cotas ────────────────────────────────────────────────────────────────────

def _cotas(gx, gy, gw, gh, largura_mm, altura_mm) -> str:
    parts = []
    cy = gy - 20
    parts += [
        _line(gx, cy, gx + gw, cy, _COR_COTAL, 1.0),
        _line(gx, gy, gx, cy, _COR_COTAL, 0.7, "2 2"),
        _line(gx + gw, gy, gx + gw, cy, _COR_COTAL, 0.7, "2 2"),
        _arrow_h(gx + 7, cy, gx, _COR_COTA),
        _arrow_h(gx + gw - 7, cy, gx + gw, _COR_COTA),
        _text(gx + gw / 2, cy - 9, f"{largura_mm:.0f} mm", _COR_COTA, 9),
    ]
    cx = gx - 20
    parts += [
        _line(cx, gy, cx, gy + gh, _COR_COTAL, 1.0),
        _line(gx, gy, cx, gy, _COR_COTAL, 0.7, "2 2"),
        _line(gx, gy + gh, cx, gy + gh, _COR_COTAL, 0.7, "2 2"),
        _arrow_v(cx, gy + 7, gy, _COR_COTA),
        _arrow_v(cx, gy + gh - 7, gy + gh, _COR_COTA),
        _text(cx - 9, gy + gh / 2, f"{altura_mm:.0f} mm", _COR_COTA, 9, rotate=-90),
    ]
    return "\n".join(parts)


# ─── Ferragens + labels ───────────────────────────────────────────────────────

def _ferragens_svg(ferragens: list[dict], gx, gy, gw, gh, sc, acab, label_x) -> str:
    parts = []
    posicoes = []
    for f in ferragens:
        fx = gx + f["x_mm"] * sc
        fy = gy + gh - f["y_mm"] * sc
        fx = max(gx + 5, min(gx + gw - 5, fx))
        fy = max(gy + 5, min(gy + gh - 5, fy))
        posicoes.append((fx, fy))

    # Anti-collision para labels (empurra para baixo se conflito)
    label_ys = [fy for _, fy in posicoes]
    order = sorted(range(len(label_ys)), key=lambda i: label_ys[i])
    for _ in range(8):
        changed = False
        for k in range(1, len(order)):
            pi, ci = order[k - 1], order[k]
            if label_ys[ci] - label_ys[pi] < 16:
                label_ys[ci] = label_ys[pi] + 16
                changed = True
        if not changed:
            break

    for i, f in enumerate(ferragens):
        fx, fy = posicoes[i]
        lfy = max(gy + 5, min(gy + gh - 5, label_ys[i]))

        parts.append(_simbolo(f["tipo"], fx, fy, acab))

        # Linha guia tracejada símbolo → label
        ex = min(fx + 10, label_x - 4)
        if abs(lfy - fy) > 6:
            parts.append(_line(ex, fy, label_x - 4, lfy, _COR_LABEL, 0.5, "2 2"))
        else:
            parts.append(_line(ex, fy, label_x - 4, lfy, _COR_LABEL, 0.5))

        cod = f.get("codigo", "")
        nome = f.get("nome", "")
        label = f"{cod}: {nome}" if cod else nome
        parts.append(_text(label_x, lfy, label, _COR_LABEL, 8, "start"))

    return "\n".join(parts)


# ─── Render principal ─────────────────────────────────────────────────────────

def render(tipologia: str, largura: float, altura: float,
           cor: str = "incolor", acabamento: str = "cromado") -> str:
    """
    Renderiza uma tipologia como SVG de catálogo.

    Args:
        tipologia: chave da tipologia (ex: 'porta', 'porta_correr_2_folhas')
        largura: largura da peça em mm
        altura: altura da peça em mm
        cor: cor do vidro — incolor | verde | fume | bronze | azul | espelho
        acabamento: acabamento da ferragem — cromado | inox | preto | dourado

    Returns:
        String SVG completa, viewBox 600×800
    """
    # ── 1. Consultar DB ───────────────────────────────────────────────────────
    tipologia_dados: dict | None = None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        row = conn.execute(
            "SELECT dados FROM constitution_entries WHERE chave=? AND tipo='tipologia'",
            (tipologia,),
        ).fetchone()
        conn.close()
        if row:
            tipologia_dados = json.loads(row[0])
    except Exception:
        pass

    # ── 2. Coletar peças com ferragens ────────────────────────────────────────
    # Cada entrada: (label_tipo, lista de ferragens avaliadas)
    pieces: list[tuple[str, list[dict]]] = []
    if tipologia_dados:
        fpb = tipologia_dados.get("ferragens_por_peca", {})
        for key in ("movel", "correr", "fixo", "fixa"):
            lst = fpb.get(key) or []
            if not lst:
                continue
            evaluated = []
            for f in lst:
                x = _eval_formula(f.get("x_formula", "0"), largura, altura)
                y = _eval_formula(f.get("y_formula", "0"), largura, altura)
                evaluated.append({**f, "x_mm": x, "y_mm": y})
            pieces.append((key, evaluated))

    if not pieces:
        pieces = [("vidro", [])]

    # ── 3. Layout ─────────────────────────────────────────────────────────────
    n = len(pieces)
    area_w = VW - ML - MR
    area_h = VH - MT - MB

    sc = min(
        (area_w - GAP_PX * (n - 1)) / (largura * n),
        area_h / altura,
    )
    gw = largura * sc
    gh = altura * sc

    total_gw = gw * n + GAP_PX * (n - 1)
    ox = ML + (area_w - total_gw) / 2
    oy = MT + (area_h - gh) / 2

    # ── 4. Cores ──────────────────────────────────────────────────────────────
    vidro_fill, vidro_borda = _VIDRO.get(cor.lower(), _VIDRO["incolor"])
    acab = _ACABAMENTO.get(acabamento.lower(), _ACABAMENTO["cromado"])

    # ── 5. Montar SVG ─────────────────────────────────────────────────────────
    hatch_stroke = vidro_borda

    defs = (
        "  <defs>\n"
        f'    <pattern id="gh" patternUnits="userSpaceOnUse" width="10" height="10">\n'
        f'      <path d="M0,10 L10,0" stroke="{hatch_stroke}" stroke-width="0.45"'
        f' stroke-opacity="0.22"/>\n'
        f'    </pattern>\n'
        f'    <linearGradient id="vhl" x1="0" y1="0" x2="1" y2="0">\n'
        f'      <stop offset="0%" stop-color="white" stop-opacity="0.32"/>\n'
        f'      <stop offset="22%" stop-color="white" stop-opacity="0.0"/>\n'
        f'    </linearGradient>\n'
        f'  </defs>'
    )

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (f'<!-- VDX v2 | tipologia={tipologia} | {largura:.0f}x{altura:.0f}mm'
         f' | {cor} | {acabamento} -->'),
        (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VW} {VH}"'
         f' width="{VW}" height="{VH}">'),
        defs,
        f'  <rect width="{VW}" height="{VH}" fill="white"/>',
        '  <g id="desenho">',
    ]

    label_x = ox + total_gw + 8  # labels à direita de todas as peças

    for idx, (ptype, ferragens) in enumerate(pieces):
        gx = ox + idx * (gw + GAP_PX)
        gy = oy

        # Vidro: fill sólido + hatch overlay + highlight
        parts.append(_rect(gx, gy, gw, gh, vidro_fill, vidro_borda, 1.5))
        parts.append(_rect(gx, gy, gw, gh, "url(#gh)", "none", 0))
        # Faixa de destaque (reflexo)
        hl_w = max(gw * 0.07 + 3, 6)
        parts.append(_rect(gx + 3, gy + 4, hl_w, gh - 8, "url(#vhl)", "none", 0))

        # Cotas somente na primeira peça
        if idx == 0:
            parts.append(_cotas(gx, gy, gw, gh, largura, altura))

        # Ferragens e labels
        if ferragens:
            parts.append(_ferragens_svg(ferragens, gx, gy, gw, gh, sc, acab, label_x))

    parts.append("  </g>")
    parts.append("</svg>")

    return "\n".join(parts)
