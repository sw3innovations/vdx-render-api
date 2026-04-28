"""Helpers para desenho dinâmico de ferragens com base em dimensões reais do catálogo."""
from __future__ import annotations


def _r(v: float) -> str:
    return f"{v:.1f}"


def desenhar_puxador_dinamico(
    dimensoes: dict,
    px: float,
    py: float,
    sc: float,
    acab: str,
    orientacao: str = "vertical",
) -> str:
    """
    Desenha puxador com forma derivada de dimensoes_json do catálogo.

    Formas:
    - CÍRCULO  : diametro > 0 e (comprimento == 0 ou comprimento <= diametro)
    - CÁPSULA  : diametro > 0 e 0 < comprimento < 100
    - BARRA    : comprimento >= 100
    - FALLBACK : estático quando nenhuma dimensão útil disponível
    """
    diametro = dimensoes.get("diametro") or 0
    comprimento = dimensoes.get("comprimento") or 0
    largura_dim = dimensoes.get("largura") or 0

    # CÍRCULO
    if diametro > 0 and (comprimento == 0 or comprimento <= diametro):
        r = max(4.0, min(40.0, diametro / 2 * sc))
        return "\n".join([
            f'<circle cx="{_r(px)}" cy="{_r(py)}" r="{_r(r)}"'
            f' fill="{acab}" fill-opacity="0.35" stroke="{acab}" stroke-width="1.5"/>',
            f'<circle cx="{_r(px)}" cy="{_r(py)}" r="{_r(r * 0.35)}"'
            f' fill="white" stroke="{acab}" stroke-width="0.8"/>',
        ])

    # CÁPSULA
    if diametro > 0 and 0 < comprimento < 100:
        w = max(10.0, min(80.0, comprimento * sc))
        h = max(5.0, min(30.0, diametro * sc))
        rx = h / 2
        if orientacao == "vertical":
            x0, y0 = px - h / 2, py - w / 2
            return (
                f'<rect x="{_r(x0)}" y="{_r(y0)}" width="{_r(h)}" height="{_r(w)}"'
                f' rx="{_r(rx)}" fill="{acab}" fill-opacity="0.35"'
                f' stroke="{acab}" stroke-width="1.5"/>'
            )
        else:
            x0, y0 = px - w / 2, py - h / 2
            return (
                f'<rect x="{_r(x0)}" y="{_r(y0)}" width="{_r(w)}" height="{_r(h)}"'
                f' rx="{_r(rx)}" fill="{acab}" fill-opacity="0.35"'
                f' stroke="{acab}" stroke-width="1.5"/>'
            )

    # BARRA
    if comprimento >= 100:
        bar_len = max(40.0, min(300.0, comprimento * sc))
        bar_w = max(6.0, min(20.0, (largura_dim or 25) * sc))
        rx = bar_w / 2
        if orientacao == "vertical":
            x0, y0 = px - bar_w / 2, py - bar_len / 2
        else:
            x0, y0 = px - bar_len / 2, py - bar_w / 2
            bar_len, bar_w = bar_w, bar_len
        return "\n".join([
            f'<rect x="{_r(x0)}" y="{_r(y0)}" width="{_r(bar_w)}" height="{_r(bar_len)}"'
            f' rx="{_r(rx)}" fill="{acab}" fill-opacity="0.35"'
            f' stroke="{acab}" stroke-width="1.5"/>',
            f'<circle cx="{_r(px)}" cy="{_r(y0 + bar_w / 2)}" r="{_r(bar_w * 0.3)}"'
            f' fill="white" stroke="{acab}" stroke-width="0.8"/>',
            f'<circle cx="{_r(px)}" cy="{_r(y0 + bar_len - bar_w / 2)}" r="{_r(bar_w * 0.3)}"'
            f' fill="white" stroke="{acab}" stroke-width="0.8"/>',
        ])

    # FALLBACK
    return "\n".join([
        "<!-- puxador padrão (sem dimensões) -->",
        f'<line x1="{_r(px - 12)}" y1="{_r(py)}" x2="{_r(px + 12)}" y2="{_r(py)}"'
        f' stroke="{acab}" stroke-width="3.5"/>',
        f'<circle cx="{_r(px - 12)}" cy="{_r(py)}" r="3.0" fill="{acab}"/>',
        f'<circle cx="{_r(px + 12)}" cy="{_r(py)}" r="3.0" fill="{acab}"/>',
    ])
