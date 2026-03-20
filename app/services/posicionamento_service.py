"""
Motor de posicionamento determinístico de ferragens — ZERO IA.
Regras de mercado brasileiro para vidraçaria temperada.

Todas as posições posicao_y_mm são medidas DA BASE da peça para cima.
distancia_borda_mm = distância da borda lateral ativa (esquerda).
"""


def posicionar_ferragens(
    peca_nome: str,
    largura_mm: float,
    altura_mm: float,
    ferragens: list[dict],
    puxador: dict | None,
    tipologia_nome: str = "",
) -> list[dict]:
    """
    Posiciona ferragens com precisão milimétrica para produção.
    Retorna lista de ferragens com posicao_y_mm e distancia_borda_mm EXATOS.
    """
    resultado: list[dict] = []

    # Puxador explícito do frontend sobrepõe puxadores já na lista (evita duplicatas)
    if puxador:
        ferragens = [f for f in ferragens if (f.get("tipo") or "").lower() != "puxador"]

    # ── PUXADOR ─────────────────────────────────────────────────────────────────
    if puxador:
        tipo = puxador.get("tipo_furacao", "")
        eixo = puxador.get("eixo_mm") or 0
        center_y = altura_mm * 0.55  # padrão mercado: 55% da altura

        if "EIXO" in tipo.upper() and eixo > 0:
            # Dois furos: center ± eixo/2
            resultado.append({
                "tipo": "puxador",
                "nome": "Furo sup.",
                "posicao_y_mm": round(center_y + eixo / 2, 1),
                "distancia_borda_mm": 35,
                "tipo_visual": "circulo",
                "eixo_mm": eixo,
                "inferida_por_ia": False,
            })
            resultado.append({
                "tipo": "puxador",
                "nome": "Furo inf.",
                "posicao_y_mm": round(center_y - eixo / 2, 1),
                "distancia_borda_mm": 35,
                "tipo_visual": "circulo",
                "eixo_mm": eixo,
                "inferida_por_ia": False,
            })
        else:
            # Puxador de um furo
            resultado.append({
                "tipo": "puxador",
                "nome": "Furo puxador",
                "posicao_y_mm": round(center_y, 1),
                "distancia_borda_mm": 35,
                "tipo_visual": "circulo",
                "inferida_por_ia": False,
            })

    # ── FERRAGENS (dobradiças, fechaduras, trincos, bate-fecha, etc.) ──────────
    for f in ferragens:
        tipo = (f.get("tipo") or "").lower()
        nome = f.get("nome") or ""
        nome_lower = nome.lower()
        pos_y = f.get("posicao_y_mm")
        dist_borda = f.get("distancia_borda_mm")
        tipo_visual = f.get("tipo_visual")

        # Se já tem posição calculada (veio da skill com fórmula), usa direto
        if pos_y is not None and pos_y > 0:
            resultado.append({
                "tipo": tipo or "generico",
                "nome": nome,
                "posicao_y_mm": pos_y,
                "distancia_borda_mm": dist_borda if dist_borda is not None else 15,
                "tipo_visual": tipo_visual or _inferir_tipo_visual(tipo),
                "inferida_por_ia": False,
            })
            continue

        # Posicionamento determinístico por tipo
        if "dobradica" in tipo or "dobradiça" in nome_lower or "dobradica" in nome_lower:
            if any(k in nome_lower for k in ("sup", "superior", "topo")):
                pos_y = altura_mm - 200  # 200mm do topo (medido da base)
            elif any(k in nome_lower for k in ("inf", "inferior", "base")):
                pos_y = 200              # 200mm da base
            else:
                pos_y = altura_mm - 200  # default: superior
            dist_borda = dist_borda if dist_borda is not None else 15
            tipo_visual = tipo_visual or "retangulo"

        elif "fechadura" in tipo or "fechadura" in nome_lower:
            pos_y = altura_mm * 0.55  # mesma altura do center do puxador
            dist_borda = dist_borda if dist_borda is not None else 15
            tipo_visual = tipo_visual or "retangulo"

        elif "trinco" in tipo or "trinco" in nome_lower:
            pos_y = altura_mm * 0.85
            dist_borda = dist_borda if dist_borda is not None else 0
            tipo_visual = tipo_visual or "linha_h"

        elif ("bate" in tipo and "fecha" in tipo) or ("bate" in nome_lower and "fecha" in nome_lower):
            pos_y = altura_mm * 0.50
            dist_borda = dist_borda if dist_borda is not None else 0
            tipo_visual = tipo_visual or "linha_h"

        elif "roldana" in tipo or "roldana" in nome_lower:
            pos_y = 20  # base da peça
            dist_borda = dist_borda if dist_borda is not None else 50
            tipo_visual = tipo_visual or "circulo"

        else:
            # Genérico: 50% da altura
            pos_y = altura_mm * 0.50
            dist_borda = dist_borda if dist_borda is not None else 0
            tipo_visual = tipo_visual or _inferir_tipo_visual(tipo)

        # Clamp: nunca fora da peça
        pos_y = max(20.0, min(pos_y, altura_mm - 20.0))

        resultado.append({
            "tipo": tipo or "generico",
            "nome": nome,
            "posicao_y_mm": round(pos_y, 1),
            "distancia_borda_mm": dist_borda,
            "tipo_visual": tipo_visual,
            "inferida_por_ia": False,
        })

    return resultado


def _inferir_tipo_visual(tipo: str) -> str:
    if any(k in tipo for k in ("dobradica", "fechadura")):
        return "retangulo"
    if any(k in tipo for k in ("puxador", "roldana")):
        return "circulo"
    return "linha_h"
