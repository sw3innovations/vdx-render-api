"""
VDX SVG Service — gera desenho técnico como string SVG pura.
Sem dependências externas além da stdlib Python.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import math

# ─── Temas ────────────────────────────────────────────────────────────────────

TEMAS = {
    "tecnico": {
        "fill": "#EEF3FB",
        "stroke": "#185FA5",
        "cota": "#185FA5",
        "ferragem": "#D85A30",
        "texto": "#1a3a8f",
        "diagonal": "rgba(24,95,165,0.06)",
        "canto": "#185FA5",
        "bg": "#FFFFFF",
    },
    "clean": {
        "fill": "#F8F8F8",
        "stroke": "#333333",
        "cota": "#555555",
        "ferragem": "#000000",
        "texto": "#111111",
        "diagonal": "rgba(0,0,0,0.06)",
        "canto": "#333333",
        "bg": "#FFFFFF",
    },
}

# ─── Helpers de escala ────────────────────────────────────────────────────────

@dataclass
class Escala:
    sx: float   # mm → px horizontal
    sy: float   # mm → px vertical
    ox: float   # offset x canvas (padding)
    oy: float   # offset y canvas (padding)


def _escalar(pecas_dims: list[tuple[float, float]], largura_px: int, altura_px: int, padding: int = 40) -> Escala:
    """Calcula escala isométrica para caber o conjunto no canvas."""
    total_w = sum(w for w, _ in pecas_dims)
    max_h = max(h for _, h in pecas_dims)
    area_w = largura_px - 2 * padding
    area_h = altura_px - 2 * padding
    sx = area_w / total_w if total_w else 1.0
    sy = area_h / max_h if max_h else 1.0
    sc = min(sx, sy)
    ox = padding + (area_w - total_w * sc) / 2
    oy = padding + (area_h - max_h * sc) / 2
    return Escala(sc, sc, ox, oy)


# ─── Primitivas SVG ───────────────────────────────────────────────────────────

def _rect(x, y, w, h, fill, stroke, stroke_w=1.5, rx=0) -> str:
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}" rx="{rx}"/>')


def _line(x1, y1, x2, y2, stroke, stroke_w=1.0, dash="") -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{stroke_w}"{dash_attr}/>')


def _text(x, y, content, fill, size=10, anchor="middle", weight="normal", rotate=0) -> str:
    rot = f' transform="rotate({rotate},{x:.1f},{y:.1f})"' if rotate else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" '
            f'font-family="\'Courier New\', monospace" text-anchor="{anchor}" dominant-baseline="middle" '
            f'font-weight="{weight}"{rot}>{content}</text>')


def _arrow_h(x1, y1, x2, stroke, size=4) -> str:
    """Seta horizontal de x1 → x2 na altura y1."""
    d = 1 if x2 > x1 else -1
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y1:.1f}" '
            f'stroke="{stroke}" stroke-width="1"/>'
            f'<polygon points="{x2:.1f},{y1:.1f} {x2-d*size:.1f},{y1-size/2:.1f} {x2-d*size:.1f},{y1+size/2:.1f}" '
            f'fill="{stroke}"/>')


def _arrow_v(x1, y1, y2, stroke, size=4) -> str:
    """Seta vertical de y1 → y2 na posição x1."""
    d = 1 if y2 > y1 else -1
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x1:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="1"/>'
            f'<polygon points="{x1:.1f},{y2:.1f} {x1-size/2:.1f},{y2-d*size:.1f} {x1+size/2:.1f},{y2-d*size:.1f}" '
            f'fill="{stroke}"/>')


# ─── Ferragens SVG ────────────────────────────────────────────────────────────

def _ferragem_svg(ferragem: dict, px: float, py: float, pw: float, ph: float,
                  sc: float, tema: dict, label_fy: float = None) -> str:
    cor = tema["ferragem"]
    tipo_v = ferragem.get("tipo_visual", "linha_h")
    pos_y_mm = ferragem.get("posicao_y_mm", ph / sc * 0.5)
    dist_mm = ferragem.get("distancia_borda_mm", 0)
    nome = ferragem.get("nome") or ferragem.get("tipo", "")

    # posicao_y_mm é medido DA BASE para cima; no SVG y=0 é o topo
    fy = py + ph - (pos_y_mm * sc)
    fy = max(py + 4, min(py + ph - 4, fy))   # clamp dentro da peça

    # label_fy separado do símbolo para permitir anti-colisão
    if label_fy is None:
        label_fy = fy

    # x a partir da borda esquerda
    fx = px + dist_mm * sc

    # Label sempre fora da peça, à direita
    label_x = px + pw + 6

    parts = []
    if tipo_v == "linha_h":
        parts.append(_line(px + 2, fy, px + pw - 2, fy, cor, 1.5, "4 2"))
        if nome:
            parts.append(_text(label_x, label_fy, nome, cor, 9, "start"))

    elif tipo_v == "circulo":
        r = max(6, min(10, pw * 0.06))
        parts.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="{r:.1f}" '
                     f'fill="none" stroke="{cor}" stroke-width="1.5"/>')
        parts.append(_line(fx - r, fy, fx + r, fy, cor, 0.8))
        parts.append(_line(fx, fy - r, fx, fy + r, cor, 0.8))
        if nome:
            parts.append(_text(label_x, label_fy, nome, cor, 9, "start"))

    elif tipo_v == "retangulo":
        rw, rh = 10, 18
        ry = fy - rh / 2
        parts.append(f'<rect x="{fx:.1f}" y="{ry:.1f}" width="{rw}" height="{rh}" '
                     f'fill="{cor}" fill-opacity="0.25" stroke="{cor}" stroke-width="1.2"/>')
        if nome:
            parts.append(_text(label_x, label_fy, nome, cor, 9, "start"))

    return "\n".join(parts)


# ─── Cota eixo puxador ────────────────────────────────────────────────────────

def _cota_eixo_puxador(ferragens: list[dict], px: float, py: float, pw: float, ph: float,
                        sc: float, cor: str) -> str:
    """Cota técnica vertical entre os dois furos do puxador (estilo desenho técnico)."""
    pares = [f for f in ferragens if f.get("tipo") == "puxador" and f.get("eixo_mm")]
    if len(pares) < 2:
        return ""

    ys_mm = sorted(f["posicao_y_mm"] for f in pares)
    fy_inf = py + ph - (ys_mm[0] * sc)   # menor y_mm → mais baixo no SVG
    fy_sup = py + ph - (ys_mm[1] * sc)   # maior y_mm → mais alto no SVG
    fy_inf = max(py + 4, min(py + ph - 4, fy_inf))
    fy_sup = max(py + 4, min(py + ph - 4, fy_sup))

    eixo_mm = pares[0]["eixo_mm"]
    cor_cota = "#444444"
    # Coluna da cota: após área de labels (~125px de label_x=px+pw+6)
    cx = px + pw + 130
    mid = (fy_sup + fy_inf) / 2

    parts = [
        # Linha guia tracejada dos furos até a coluna da cota
        _line(px + pw + 4, fy_sup, cx - 4, fy_sup, cor_cota, 0.5, "3 2"),
        _line(px + pw + 4, fy_inf, cx - 4, fy_inf, cor_cota, 0.5, "3 2"),
        # Linha vertical da cota
        _line(cx, fy_sup, cx, fy_inf, cor_cota, 0.8),
        # Serifas nas extremidades
        _line(cx - 4, fy_sup, cx + 4, fy_sup, cor_cota, 0.8),
        _line(cx - 4, fy_inf, cx + 4, fy_inf, cor_cota, 0.8),
        # Setas indicando distância
        _arrow_v(cx, fy_sup + 5, fy_sup, cor_cota, size=3),
        _arrow_v(cx, fy_inf - 5, fy_inf, cor_cota, size=3),
        # Texto centralizado ao lado
        _text(cx + 7, mid, f"Eixo {eixo_mm:.0f}mm", cor_cota, 9, "start"),
    ]
    return "\n".join(parts)


# ─── Peça SVG ─────────────────────────────────────────────────────────────────

def _peca_svg(peca: dict, px: float, py: float, pw: float, ph: float,
              tema: dict, opcoes: dict, ferragens: list[dict]) -> str:
    t = tema
    parts = []

    # Retângulo principal
    parts.append(_rect(px, py, pw, ph, t["fill"], t["stroke"], 1.5))

    # Diagonais decorativas
    parts.append(_line(px, py, px + pw, py + ph, t["diagonal"], 0.8))
    parts.append(_line(px + pw, py, px, py + ph, t["diagonal"], 0.8))

    # Cantos técnicos (L nos 4 cantos)
    cs = 10
    for cx, cy, dx, dy in [(px, py, 1, 1), (px + pw, py, -1, 1),
                            (px, py + ph, 1, -1), (px + pw, py + ph, -1, -1)]:
        parts.append(_line(cx, cy, cx + dx * cs, cy, t["canto"], 1.2))
        parts.append(_line(cx, cy, cx, cy + dy * cs, t["canto"], 1.2))

    # Nome da peça
    if opcoes.get("mostrar_nome_peca", True):
        nome = peca.get("nome", "")
        parts.append(_text(px + pw / 2, py + ph / 2, nome, t["texto"], 9, "middle", "bold"))

    # Cotas
    if opcoes.get("mostrar_cotas", True):
        lmm = peca.get("largura_mm", 0)
        hmm = peca.get("altura_mm", 0)
        # Cota horizontal — acima
        cy_cota = py - 14
        parts.append(_line(px, cy_cota, px + pw, cy_cota, t["cota"], 0.8))
        parts.append(_line(px, py, px, cy_cota, t["cota"], 0.8, "2 2"))
        parts.append(_line(px + pw, py, px + pw, cy_cota, t["cota"], 0.8, "2 2"))
        parts.append(_arrow_h(px + 4, cy_cota, px, t["cota"]))
        parts.append(_arrow_h(px + pw - 4, cy_cota, px + pw, t["cota"]))
        label_l = f"{lmm:.0f}mm" if lmm >= 1 else f"{lmm:.1f}mm"
        parts.append(_text(px + pw / 2, cy_cota - 7, label_l, t["cota"], 8))
        # Cota vertical — esquerda
        cx_cota = px - 14
        parts.append(_line(cx_cota, py, cx_cota, py + ph, t["cota"], 0.8))
        parts.append(_line(px, py, cx_cota, py, t["cota"], 0.8, "2 2"))
        parts.append(_line(px, py + ph, cx_cota, py + ph, t["cota"], 0.8, "2 2"))
        parts.append(_arrow_v(cx_cota, py + 4, py, t["cota"]))
        parts.append(_arrow_v(cx_cota, py + ph - 4, py + ph, t["cota"]))
        label_h = f"{hmm:.0f}mm" if hmm >= 1 else f"{hmm:.1f}mm"
        parts.append(_text(cx_cota - 7, py + ph / 2, label_h, t["cota"], 8, "middle", rotate=-90))

    # Ferragens
    if opcoes.get("mostrar_ferragens", True):
        sc = pw / peca["largura_mm"] if peca["largura_mm"] else 1

        # Calcular fy de cada ferragem e aplicar anti-colisão nos labels
        fys = []
        for f in ferragens:
            pos_y_mm = f.get("posicao_y_mm", ph / sc * 0.5)
            fy = py + ph - (pos_y_mm * sc)
            fys.append(max(py + 4, min(py + ph - 4, fy)))

        # Anti-colisão multi-pass: ordenar por fy e empurrar até não colidir
        min_gap = 18
        order = sorted(range(len(fys)), key=lambda i: fys[i])
        label_fys = list(fys)
        for _ in range(5):
            changed = False
            for k in range(1, len(order)):
                prev_i = order[k - 1]
                curr_i = order[k]
                if label_fys[curr_i] - label_fys[prev_i] < min_gap:
                    label_fys[curr_i] = label_fys[prev_i] + min_gap
                    changed = True
            if not changed:
                break
        # Clamp para não sair da peça
        label_fys = [max(py, min(py + ph, lfy)) for lfy in label_fys]

        for i, f in enumerate(ferragens):
            parts.append(_ferragem_svg(f, px, py, pw, ph, sc, t, label_fy=label_fys[i]))

        # Cota eixo puxador (quando há par de furos com eixo_mm)
        cota = _cota_eixo_puxador(ferragens, px, py, pw, ph, sc, t["ferragem"])
        if cota:
            parts.append(cota)

    return "\n".join(parts)


# ─── Setas de deslizamento (FIXO_MOVEL_FIXO) ─────────────────────────────────

def _setas_deslizamento(px: float, py: float, pw: float, ph: float, cor: str) -> str:
    cy = py + ph / 2
    mx = px + pw / 2
    aw = min(pw * 0.3, 24)
    parts = [
        _line(mx - aw, cy, mx + aw, cy, cor, 1.5),
        f'<polygon points="{mx-aw:.1f},{cy:.1f} {mx-aw+6:.1f},{cy-4:.1f} {mx-aw+6:.1f},{cy+4:.1f}" fill="{cor}"/>',
        f'<polygon points="{mx+aw:.1f},{cy:.1f} {mx+aw-6:.1f},{cy-4:.1f} {mx+aw-6:.1f},{cy+4:.1f}" fill="{cor}"/>',
    ]
    return "\n".join(parts)


# ─── Layouts ──────────────────────────────────────────────────────────────────

def _layout_paralelas(pecas_e: list[dict], esc: Escala, tema: dict, opcoes: dict) -> str:
    parts = []
    gap = max(esc.sx * 5, 8)
    x = esc.ox
    for p in pecas_e:
        pw = p["largura_mm"] * esc.sx
        ph = p["altura_mm"] * esc.sy
        py = esc.oy
        parts.append(_peca_svg(p, x, py, pw, ph, tema, opcoes, p.get("_ferragens", [])))
        x += pw + gap
    return "\n".join(parts)


def _layout_bandeira_topo(pecas_e: list[dict], esc: Escala, tema: dict, opcoes: dict) -> str:
    """Bandeira: peça mais larga/curta no topo, demais abaixo lado a lado."""
    parts = []
    if not pecas_e:
        return ""

    # Identifica bandeira: peça com menor altura ou nome contendo "bandeira"
    bandeira = None
    resto = []
    for p in pecas_e:
        if "bandeira" in p["nome"].lower():
            bandeira = p
        else:
            resto.append(p)
    if bandeira is None:
        bandeira = min(pecas_e, key=lambda p: p["altura_mm"])
        resto = [p for p in pecas_e if p is not bandeira]

    total_w = sum(p["largura_mm"] for p in pecas_e)
    bw = total_w * esc.sx
    bh = bandeira["altura_mm"] * esc.sy
    parts.append(_peca_svg(bandeira, esc.ox, esc.oy, bw, bh, tema, opcoes, bandeira.get("_ferragens", [])))

    gap = max(esc.sy * 3, 4)
    x = esc.ox
    py_baixo = esc.oy + bh + gap
    for p in resto:
        pw = p["largura_mm"] * esc.sx
        ph = p["altura_mm"] * esc.sy
        parts.append(_peca_svg(p, x, py_baixo, pw, ph, tema, opcoes, p.get("_ferragens", [])))
        x += pw + max(esc.sx * 3, 4)
    return "\n".join(parts)


def _layout_canto_l(pecas_e: list[dict], esc: Escala, tema: dict, opcoes: dict) -> str:
    """Peça 1 frontal + peça 2 perpendicular (90°) à direita."""
    parts = []
    if not pecas_e:
        return ""
    p1 = pecas_e[0]
    pw1 = p1["largura_mm"] * esc.sx
    ph1 = p1["altura_mm"] * esc.sy
    parts.append(_peca_svg(p1, esc.ox, esc.oy, pw1, ph1, tema, opcoes, p1.get("_ferragens", [])))

    if len(pecas_e) > 1:
        p2 = pecas_e[1]
        pw2 = p2["largura_mm"] * esc.sx
        ph2 = p2["altura_mm"] * esc.sy
        ox2 = esc.ox + pw1 + 4
        parts.append(_peca_svg(p2, ox2, esc.oy, pw2, ph2, tema, opcoes, p2.get("_ferragens", [])))
        # Bracket L na junção
        jx = esc.ox + pw1
        jy = esc.oy
        brac = 12
        parts.append(_line(jx, jy, jx, jy + brac, tema["canto"], 2))
        parts.append(_line(jx, jy, jx + brac, jy, tema["canto"], 2))

    return "\n".join(parts)


def _layout_fixo_movel_fixo(pecas_e: list[dict], esc: Escala, tema: dict, opcoes: dict) -> str:
    parts = []
    gap = max(esc.sx * 3, 4)
    x = esc.ox
    for i, p in enumerate(pecas_e):
        pw = p["largura_mm"] * esc.sx
        ph = p["altura_mm"] * esc.sy
        py = esc.oy
        parts.append(_peca_svg(p, x, py, pw, ph, tema, opcoes, p.get("_ferragens", [])))
        nome_lower = p["nome"].lower()
        if any(k in nome_lower for k in ["movel", "móvel", "porta", "folha"]):
            parts.append(_setas_deslizamento(x, py, pw, ph, tema["ferragem"]))
        x += pw + gap
    return "\n".join(parts)


def _layout_basculante(pecas_e: list[dict], esc: Escala, tema: dict, opcoes: dict) -> str:
    """Peças empilhadas com linhas de abertura diagonal."""
    parts = []
    gap = max(esc.sy * 2, 3)
    y = esc.oy
    total_w = max((p["largura_mm"] for p in pecas_e), default=600)
    for p in pecas_e:
        pw = p["largura_mm"] * esc.sx
        ph = p["altura_mm"] * esc.sy
        parts.append(_peca_svg(p, esc.ox, y, pw, ph, tema, opcoes, p.get("_ferragens", [])))
        # Linha de abertura (diagonal leve)
        parts.append(_line(esc.ox, y + ph, esc.ox + pw, y, tema["cota"], 0.8, "5 3"))
        y += ph + gap
    return "\n".join(parts)


def _layout_cobertura(pecas_e: list[dict], esc: Escala, tema: dict, opcoes: dict) -> str:
    """Peças com leve perspectiva isométrica (skewY)."""
    parts = []
    gap = max(esc.sx * 4, 6)
    x = esc.ox
    skew = -8  # graus
    for p in pecas_e:
        pw = p["largura_mm"] * esc.sx
        ph = p["altura_mm"] * esc.sy
        group_open = f'<g transform="skewY({skew})" transform-origin="{x:.1f} {esc.oy:.1f}">'
        parts.append(group_open)
        parts.append(_peca_svg(p, x, esc.oy, pw, ph, tema, opcoes, p.get("_ferragens", [])))
        parts.append("</g>")
        x += pw + gap
    return "\n".join(parts)


def _layout_paineis_lineares(pecas_e: list[dict], esc: Escala, tema: dict, opcoes: dict) -> str:
    """N painéis com divisórias finas (guarda-corpo, sacada, etc.)."""
    parts = []
    div_w = 3
    x = esc.ox
    for i, p in enumerate(pecas_e):
        pw = p["largura_mm"] * esc.sx
        ph = p["altura_mm"] * esc.sy
        parts.append(_peca_svg(p, x, esc.oy, pw, ph, tema, opcoes, p.get("_ferragens", [])))
        if i < len(pecas_e) - 1:
            # Divisória
            dx = x + pw
            parts.append(_rect(dx, esc.oy, div_w, ph, tema["stroke"], tema["stroke"], 0))
        x += pw + div_w
    return "\n".join(parts)


# ─── Despacho de layout ───────────────────────────────────────────────────────

_LAYOUT_FNS = {
    "paralelas": _layout_paralelas,
    "bandeira_topo": _layout_bandeira_topo,
    "canto_l": _layout_canto_l,
    "fixo_movel_fixo": _layout_fixo_movel_fixo,
    "basculante": _layout_basculante,
    "cobertura": _layout_cobertura,
    "paineis_lineares": _layout_paineis_lineares,
}


# ─── Função principal ─────────────────────────────────────────────────────────

def gerar_svg(
    pecas_input: list[dict] = None,
    ferragens_por_peca: list[list[dict]] = None,
    layout_usado: str = "paralelas",
    opcoes_dict: dict = None,
    tipologia_nome: str = "",
    largura_px: int = 480,
    altura_px: int = 360,
    # Novo: aceita List[PecaRenderizada]
    pecas_renderizadas=None,
) -> str:
    if opcoes_dict is None:
        opcoes_dict = {}

    # Se recebeu novo formato (PecaRenderizada), converter para formato interno
    if pecas_renderizadas is not None:
        pecas_input = []
        ferragens_por_peca = []
        for peca in pecas_renderizadas:
            pecas_input.append({
                "nome": peca.nome,
                "largura_mm": peca.largura_mm,
                "altura_mm": peca.altura_mm,
            })
            # Extrair eixo_mm do nome se contiver "eixo Xmm"
            ferragens_convertidas = []
            for f in peca.ferragens:
                eixo_mm = None
                nome_lower = f.nome.lower()
                if "eixo" in nome_lower:
                    import re
                    m = re.search(r"eixo\s+(\d+)\s*mm", nome_lower)
                    if m:
                        eixo_mm = float(m.group(1))
                ferragens_convertidas.append({
                    "tipo": f.tipo,
                    "nome": f.nome,
                    "posicao_y_mm": f.y_mm,
                    "distancia_borda_mm": f.x_mm,
                    "tipo_visual": f.visual,
                    "inferida_por_ia": False,
                    "eixo_mm": eixo_mm,
                })
            ferragens_por_peca.append(ferragens_convertidas)

    if pecas_input is None:
        pecas_input = []
    if ferragens_por_peca is None:
        ferragens_por_peca = []

    tema_nome = opcoes_dict.get("tema", "tecnico")
    tema = TEMAS.get(tema_nome, TEMAS["tecnico"])

    # Enriquecer pecas com ferragens para passar juntas
    pecas_e = []
    for i, p in enumerate(pecas_input):
        pe = dict(p)
        pe["_ferragens"] = ferragens_por_peca[i] if i < len(ferragens_por_peca) else []
        pecas_e.append(pe)

    # Escala para o layout selecionado
    # Para CANTO_L: largura total = p1.L + p2.L (lado a lado)
    # Para BANDEIRA_TOPO: largura = soma das laterais, altura = bandeira + max lateral
    dims = [(p["largura_mm"], p["altura_mm"]) for p in pecas_input]
    padding = 45
    esc = _escalar(dims, largura_px, altura_px, padding)

    layout_fn = _LAYOUT_FNS.get(layout_usado, _layout_paralelas)
    conteudo = layout_fn(pecas_e, esc, tema, opcoes_dict)

    bg = tema["bg"]
    svg = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<!-- VDX Render API v1.0.0 | layout={layout_usado} | tipologia={tipologia_nome} -->\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {largura_px} {altura_px}" '
        f'width="{largura_px}" height="{altura_px}">\n'
        f'  <rect width="{largura_px}" height="{altura_px}" fill="{bg}"/>\n'
        f'  <g id="desenho">\n'
        f'{conteudo}\n'
        f'  </g>\n'
        f'</svg>'
    )
    return svg
