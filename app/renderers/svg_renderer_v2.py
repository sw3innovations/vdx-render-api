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
ML, MT, MR, MB = 65, 52, 112, 40

_COR_COTA  = "#4A7098"
_COR_COTAL = "#7A9AAA"
_COR_LABEL = "#503880"

BANDEIRA_H_MM = 300   # altura fixa da bandeira em arrangement "v"
GAP_V_MM      = 20    # gap vertical entre bandeira e porta (mm)

# ─── Schemas explícitos das 29 tipologias ────────────────────────────────────
# (arrangement, [panel_types])
# arrangement: "h" = side-by-side  |  "L" = canto 90°  |
#              "v" = bandeira+porta |  "landscape" = painel horizontal plano

_SCHEMAS: dict[str, tuple[str, list[str]]] = {
    "balcão_de_pia_duas_folhas":          ("h", ["movel", "movel"]),
    "balcão_de_pia_quatro_folhas":        ("h", ["movel", "movel", "movel", "movel"]),
    "box_articulado":                     ("h", ["movel"]),
    "box_canto_90":                       ("L", ["movel", "fixa"]),
    "box_de_giro":                        ("h", ["movel"]),
    "box_flex":                           ("h", ["movel"]),
    "box_frontal_2_folhas":               ("h", ["fixa", "movel"]),
    "cobertura":                          ("landscape", ["fixo"]),
    "divisoria_porta_pivotante":          ("h", ["fixa", "movel"]),
    "diâmetro":                           ("h", ["fixo"]),
    "diâmetro_com_furo_no_meio":          ("h", ["fixo"]),
    "fachada_fixa":                       ("h", ["fixo"]),
    "fechamento_de_sacada_6_folhas":      ("h", ["correr", "correr", "correr",
                                                  "correr", "correr", "correr"]),
    "guarda_corpo_linear":                ("landscape", ["fixo"]),
    "janela_3_folhas":                    ("h", ["fixa", "movel", "movel"]),
    "janela_basculante":                  ("h", ["movel"]),
    "janela_correr_2_folhas":             ("h", ["fixa", "correr"]),
    "janela_correr_2_folhas_oriun_plus":  ("h", ["fixa", "correr"]),
    "janela_maxim_ar":                    ("h", ["movel"]),
    "janela_pivotante":                   ("h", ["movel"]),
    "janela_quatro_folhas":               ("h", ["fixa", "correr", "correr", "fixa"]),
    "janela_quatro_folhas_orion_plus":    ("h", ["movel"]),
    "porta_abrir":                        ("h", ["movel"]),
    "porta_correr_2_folhas":              ("h", ["fixa", "correr"]),
    "porta_correr_3_folhas":              ("h", ["correr", "correr", "correr"]),
    "porta_pivotante_dupla_bandeira":     ("v", ["fixa", "movel"]),
    "porta_pivotante_simples":            ("h", ["movel"]),
    "porta_quatro_folhas":                ("h", ["fixa", "correr", "correr", "fixa"]),
    "vitrine":                            ("h", ["movel"]),
}


def _gap_px(n: int) -> float:
    if n <= 1: return 0.0
    if n == 2: return 10.0
    if n <= 4: return 7.0
    return 4.0


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
    if "dobradica" in t or "dobradiça" in t: return _sim_dobradica(px, py, acab)
    if "pivo" in t or "pivô" in t:           return _sim_pivo(px, py, acab)
    if "fechadura" in t:                      return _sim_fechadura(px, py, acab)
    if "puxador" in t:                        return _sim_puxador(px, py, acab)
    if "roldana" in t:                        return _sim_roldana(px, py, acab)
    if "suporte" in t:                        return _sim_suporte(px, py, acab)
    if "trinco" in t:                         return _sim_trinco(px, py, acab)
    if "bate" in t:                           return _sim_bate_fecha(px, py, acab)
    return _sim_suporte(px, py, acab)


# ─── Cotas ────────────────────────────────────────────────────────────────────

def _cota_h(gx: float, gy: float, total_gw: float, largura_mm: float) -> str:
    cy = gy - 20
    parts = [
        _line(gx, cy, gx + total_gw, cy, _COR_COTAL, 1.0),
        _line(gx, gy, gx, cy, _COR_COTAL, 0.7, "2 2"),
        _line(gx + total_gw, gy, gx + total_gw, cy, _COR_COTAL, 0.7, "2 2"),
        _arrow_h(gx + 7, cy, gx, _COR_COTA),
        _arrow_h(gx + total_gw - 7, cy, gx + total_gw, _COR_COTA),
        _text(gx + total_gw / 2, cy - 9, f"{largura_mm:.0f} mm", _COR_COTA, 9),
    ]
    return "\n".join(parts)


def _cota_v(gx: float, gy: float, gh: float, altura_mm: float) -> str:
    cx = gx - 20
    parts = [
        _line(cx, gy, cx, gy + gh, _COR_COTAL, 1.0),
        _line(gx, gy, cx, gy, _COR_COTAL, 0.7, "2 2"),
        _line(gx, gy + gh, cx, gy + gh, _COR_COTAL, 0.7, "2 2"),
        _arrow_v(cx, gy + 7, gy, _COR_COTA),
        _arrow_v(cx, gy + gh - 7, gy + gh, _COR_COTA),
        _text(cx - 9, gy + gh / 2, f"{altura_mm:.0f} mm", _COR_COTA, 9, rotate=-90),
    ]
    return "\n".join(parts)


# ─── Ferragens + labels ───────────────────────────────────────────────────────

def _ferragens_svg(ferragens: list[dict], gx, gy, gw, gh, sc,
                   acab, label_x: float | None) -> str:
    """
    Renderiza ferragens num painel.
    label_x=None → só símbolos (sem labels/guias).
    label_x=float → símbolos + linhas-guia + labels à direita.
    """
    parts: list[str] = []
    posicoes: list[tuple[float, float]] = []

    for f in ferragens:
        fx = gx + f["x_mm"] * sc
        fy = gy + gh - f["y_mm"] * sc
        fx = max(gx + 5, min(gx + gw - 5, fx))
        fy = max(gy + 5, min(gy + gh - 5, fy))
        posicoes.append((fx, fy))

    label_ys: list[float] = []
    if label_x is not None:
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
        parts.append(_simbolo(f["tipo"], fx, fy, acab))

        if label_x is not None:
            lfy = max(gy + 5, min(gy + gh - 5, label_ys[i]))
            ex = min(fx + 10, label_x - 4)
            dash = "2 2" if abs(lfy - fy) > 6 else ""
            parts.append(_line(ex, fy, label_x - 4, lfy, _COR_LABEL, 0.5, dash))
            cod = f.get("codigo", "")
            nome = f.get("nome", "")
            label = f"{cod}: {nome}" if cod else nome
            parts.append(_text(label_x, lfy, label, _COR_LABEL, 8, "start"))

    return "\n".join(parts)


# ─── Indicadores de movimento ─────────────────────────────────────────────────

def _ind_correr(gx, gy, gw, gh, borda) -> str:
    cy = gy + gh * 0.5
    cx = gx + gw / 2
    hw = min(gw * 0.35, 30)
    return "\n".join([
        _arrow_h(cx + hw * 0.1, cy, cx - hw, borda, 5.0),
        _arrow_h(cx - hw * 0.1, cy + 1, cx + hw, borda, 5.0),
    ])


def _ind_basculante(gx, gy, gw, gh, borda) -> str:
    return _line(gx, gy + gh, gx + gw, gy, borda, 1.0, "6 3")


def _ind_maxim(gx, gy, gw, gh, borda) -> str:
    mx = gx + gw / 2
    return "\n".join([
        _line(gx + gw * 0.1, gy + gh * 0.5, mx, gy + gh * 0.15, borda, 1.2),
        _line(gx + gw * 0.9, gy + gh * 0.5, mx, gy + gh * 0.15, borda, 1.2),
    ])


def _marcador_90(cx, cy, acab) -> str:
    sz = 10
    return "\n".join([
        _line(cx, cy - sz, cx, cy, acab, 1.5),
        _line(cx, cy, cx + sz, cy, acab, 1.5),
        _circle(cx, cy, 2.5, acab, acab, 0),
    ])


# ─── Painel de vidro ──────────────────────────────────────────────────────────

def _painel(gx, gy, gw, gh, fill, borda) -> list[str]:
    hl_w = max(gw * 0.07 + 3, 6)
    return [
        _rect(gx, gy, gw, gh, fill, borda, 1.5),
        _rect(gx, gy, gw, gh, "url(#gh)", "none", 0),
        _rect(gx + 3, gy + 4, hl_w, gh - 8, "url(#vhl)", "none", 0),
    ]


# ─── Render principal ─────────────────────────────────────────────────────────

def render(tipologia: str, largura: float, altura: float,
           cor: str = "incolor", acabamento: str = "cromado",
           puxador_codigo: str | None = None) -> str:
    """
    Renderiza uma tipologia como SVG de catálogo.

    Args:
        tipologia: chave da tipologia (ex: 'porta_correr_3_folhas')
        largura:   largura total do sistema em mm
        altura:    altura da peça em mm
        cor:       incolor | verde | fume | bronze | azul | espelho
        acabamento: cromado | inox | preto | dourado
        puxador_codigo: código do puxador selecionado (Fase 1: override de label apenas)
    """
    # ── 1. DB ─────────────────────────────────────────────────────────────────
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

    # ── 2. Schema ─────────────────────────────────────────────────────────────
    arrangement, panel_types = _SCHEMAS.get(tipologia, ("h", ["movel"]))
    n = len(panel_types)
    fpb: dict = tipologia_dados.get("ferragens_por_peca", {}) if tipologia_dados else {}

    # ── 2b. Override de puxador (Fase 1: label only, sem novo desenho) ────────
    if puxador_codigo:
        import copy
        fpb = copy.deepcopy(fpb)
        for ptype in list(fpb.keys()):
            for entry in fpb[ptype]:
                if isinstance(entry, dict) and entry.get("tipo") == "puxador":
                    entry["codigo"] = puxador_codigo

    # ── 3. Cores ──────────────────────────────────────────────────────────────
    vidro_fill, vidro_borda = _VIDRO.get(cor.lower(), _VIDRO["incolor"])
    acab = _ACABAMENTO.get(acabamento.lower(), _ACABAMENTO["cromado"])

    # ── 4. Geometria ──────────────────────────────────────────────────────────
    area_w = VW - ML - MR   # 423
    area_h = VH - MT - MB   # 708

    # panel_boxes: list of (gx, gy, gw, gh) in SVG px
    panel_boxes: list[tuple[float, float, float, float]] = []
    sc_f: float = 1.0        # escala usada para converter mm → px nas ferragens

    if arrangement == "landscape":
        sc = min(area_w / largura, area_h / altura)
        pw, ph = largura * sc, altura * sc
        ox = ML + (area_w - pw) / 2
        oy = MT + (area_h - ph) / 2
        panel_boxes = [(ox, oy, pw, ph)]
        sc_f = sc

    elif arrangement == "v":
        band_mm = BANDEIRA_H_MM
        total_mm = band_mm + GAP_V_MM + altura
        sc = min(area_w / largura, area_h / total_mm)
        pw       = largura * sc
        ph_band  = band_mm * sc
        ph_door  = altura  * sc
        gap_sc   = GAP_V_MM * sc
        ox = ML + (area_w - pw) / 2
        total_px = ph_band + gap_sc + ph_door
        oy = MT + (area_h - total_px) / 2
        panel_boxes = [
            (ox, oy, pw, ph_band),
            (ox, oy + ph_band + gap_sc, pw, ph_door),
        ]
        sc_f = sc

    else:  # "h" or "L"
        gap = _gap_px(n)
        pl_mm = largura / n          # largura por painel em mm (CRÍTICO)
        sc = min((area_w - gap * (n - 1)) / largura, area_h / altura)
        pw_panel = pl_mm * sc
        gh = altura * sc
        total_gw = pw_panel * n + gap * (n - 1)
        ox = ML + (area_w - total_gw) / 2
        oy = MT + (area_h - gh) / 2
        panel_boxes = [(ox + i * (pw_panel + gap), oy, pw_panel, gh) for i in range(n)]
        sc_f = sc

    # métricas do conjunto para cotas/labels
    gx0      = panel_boxes[0][0]
    last_box = panel_boxes[-1]
    total_gw_px = last_box[0] + last_box[2] - gx0
    label_x     = last_box[0] + last_box[2] + 8

    # ── 5. SVG header ─────────────────────────────────────────────────────────
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

    # ── 6. Cotas ──────────────────────────────────────────────────────────────
    # Horizontal: sempre no topo do primeiro painel
    parts.append(_cota_h(gx0, panel_boxes[0][1], total_gw_px, largura))
    # Vertical: no painel de porta (índice 1 em "v", índice 0 nos demais)
    v_box = panel_boxes[1] if arrangement == "v" else panel_boxes[0]
    parts.append(_cota_v(v_box[0], v_box[1], v_box[3], altura))

    # ── 7. Último painel com ferragens (recebe labels) ────────────────────────
    label_panel_idx = -1
    if arrangement != "landscape":
        for i, pt in enumerate(panel_types):
            if fpb.get(pt):
                label_panel_idx = i

    # ── 8. Painéis ────────────────────────────────────────────────────────────
    tip_lower = tipologia.lower()
    for idx, (gx, gy, gw, gh) in enumerate(panel_boxes):
        ptype = panel_types[idx] if idx < len(panel_types) else "fixo"

        parts.extend(_painel(gx, gy, gw, gh, vidro_fill, vidro_borda))

        # Indicadores de movimento
        if ptype == "correr":
            parts.append(_ind_correr(gx, gy, gw, gh, vidro_borda))
        elif ptype == "movel":
            if "basculante" in tip_lower:
                parts.append(_ind_basculante(gx, gy, gw, gh, vidro_borda))
            elif "maxim" in tip_lower:
                parts.append(_ind_maxim(gx, gy, gw, gh, vidro_borda))

        lst = fpb.get(ptype) or []
        if not lst:
            continue
        # pl_mm e ph_mm derivados da caixa do painel (evita re-calcular)
        pl_mm_panel = gw / sc_f
        ph_mm_panel = gh / sc_f
        evaluated = [
            {**f,
             "x_mm": _eval_formula(f.get("x_formula", "0"), pl_mm_panel, ph_mm_panel),
             "y_mm": _eval_formula(f.get("y_formula", "0"), pl_mm_panel, ph_mm_panel)}
            for f in lst
        ]
        lx = label_x if idx == label_panel_idx else None
        parts.append(_ferragens_svg(evaluated, gx, gy, gw, gh, sc_f, acab, lx))

    # ── 9. Marcador de canto 90° ──────────────────────────────────────────────
    if arrangement == "L" and len(panel_boxes) >= 2:
        # Ponto de junção: centro do gap, meia altura
        jx = panel_boxes[0][0] + panel_boxes[0][2] + _gap_px(2) / 2
        jy = panel_boxes[0][1] + panel_boxes[0][3] / 2
        parts.append(_marcador_90(jx, jy, acab))

    parts.append("  </g>")
    parts.append("</svg>")
    return "\n".join(parts)
