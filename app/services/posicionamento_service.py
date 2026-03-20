"""
Motor de posicionamento determinístico de ferragens — ZERO IA.
Regras de mercado brasileiro para vidraçaria temperada.

Todas as posições posicao_y_mm são medidas DA BASE da peça para cima.
distancia_borda_mm = distância da borda lateral ativa (esquerda).

REGRA FUNDAMENTAL — dobradiças e puxador/fechadura ficam em lados OPOSTOS:
  Porta pivotante: dobradiças à ESQUERDA (dist=15), puxador+fechadura à DIREITA
  Box banheiro:    dobradiças à ESQUERDA (dist=25), puxador botão ao CENTRO
  Janela correr:   roldanas na base, bate-fecha/trinco na borda ativa
"""


def _eh_porta(tipologia_nome: str, peca_nome: str) -> bool:
    tip = tipologia_nome.lower()
    pec = peca_nome.lower()
    return any(k in tip or k in pec for k in ("porta", "pivotante", "abrir"))


def _eh_box(tipologia_nome: str, peca_nome: str) -> bool:
    tip = tipologia_nome.lower()
    pec = peca_nome.lower()
    return any(k in tip or k in pec for k in ("box", "banheiro"))


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

    REGRA FUNDAMENTAL: dobradiças num lado, puxador+fechadura no lado OPOSTO.

    Porta pivotante:
      - Dobradiça sup: y = altura_mm - 200, dist = 15 (ESQUERDA)
      - Dobradiça inf: y = 200,             dist = 15 (ESQUERDA)
      - Puxador:       y = altura_mm * 0.50, dist = largura_mm - 35 (DIREITA)
      - Fechadura:     y = altura_mm * 0.50, dist = largura_mm - 15 (DIREITA)

    Box banheiro:
      - Dobradiça sup: y = altura_mm - 150, dist = 25 (ESQUERDA)
      - Dobradiça inf: y = 150,             dist = 25 (ESQUERDA)
      - Puxador botão: y = altura_mm * 0.50, dist = largura_mm / 2 (CENTRO)
      - Trinco:        y = altura_mm * 0.85, dist = 0

    Janela correr:
      - Roldana:       y = 20,              dist = 50
      - Bate-fecha:    y = altura_mm * 0.50, dist = 0
      - Trinco:        y = altura_mm * 0.85, dist = 0

    Janela pivotante/basculante:
      - Dobradiças:    y = topo/base,       dist = 15 (borda esquerda/direita)
      - Trinco:        y = altura_mm * 0.50, dist = 0
    """
    resultado: list[dict] = []

    eh_porta = _eh_porta(tipologia_nome, peca_nome)
    eh_box = _eh_box(tipologia_nome, peca_nome)

    # Puxador explícito do frontend sobrepõe puxadores já na lista (evita duplicatas)
    if puxador:
        ferragens = [f for f in ferragens if (f.get("tipo") or "").lower() != "puxador"]

    # ── PUXADOR ─────────────────────────────────────────────────────────────────
    if puxador:
        tipo = puxador.get("tipo_furacao", "")
        eixo = puxador.get("eixo_mm") or 0
        center_y = altura_mm * 0.50  # padrão mercado: 50% da altura

        # Porta: puxador no lado DIREITO (oposto às dobradiças à esquerda)
        # Box: puxador botão no CENTRO da folha
        if eh_box:
            dist_puxador = round(largura_mm / 2, 1)
        else:
            dist_puxador = round(largura_mm - 35, 1)

        if "EIXO" in tipo.upper() and eixo > 0:
            resultado.append({
                "tipo": "puxador",
                "nome": "Furo sup.",
                "posicao_y_mm": round(center_y + eixo / 2, 1),
                "distancia_borda_mm": dist_puxador,
                "tipo_visual": "circulo",
                "eixo_mm": eixo,
                "inferida_por_ia": False,
            })
            resultado.append({
                "tipo": "puxador",
                "nome": "Furo inf.",
                "posicao_y_mm": round(center_y - eixo / 2, 1),
                "distancia_borda_mm": dist_puxador,
                "tipo_visual": "circulo",
                "eixo_mm": eixo,
                "inferida_por_ia": False,
            })
        else:
            resultado.append({
                "tipo": "puxador",
                "nome": "Furo puxador",
                "posicao_y_mm": round(center_y, 1),
                "distancia_borda_mm": dist_puxador,
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

        # ── Dobradiças ────────────────────────────────────────────────────────
        if "dobradica" in tipo or "dobradiça" in nome_lower or "dobradica" in nome_lower:
            if any(k in nome_lower for k in ("sup", "superior", "topo")):
                pos_y = altura_mm - 200  # 200mm do topo, medido da base
            elif any(k in nome_lower for k in ("inf", "inferior", "base")):
                pos_y = 200              # 200mm da base
            else:
                pos_y = altura_mm - 200  # default: superior
            # Dobradiças sempre à ESQUERDA (borda do eixo de giro)
            if dist_borda is None:
                dist_borda = 25 if eh_box else 15
            tipo_visual = tipo_visual or "retangulo"

        # ── Fechadura ─────────────────────────────────────────────────────────
        elif "fechadura" in tipo or "fechadura" in nome_lower:
            pos_y = altura_mm * 0.50
            # Fechadura de porta: lado DIREITO (oposto às dobradiças)
            if dist_borda is None:
                dist_borda = round(largura_mm - 15, 1) if eh_porta else 15
            tipo_visual = tipo_visual or "retangulo"

        # ── Trinco ────────────────────────────────────────────────────────────
        elif "trinco" in tipo or "trinco" in nome_lower:
            if any(k in nome_lower for k in ("basculante", "central")):
                pos_y = altura_mm * 0.50
            else:
                pos_y = altura_mm * 0.85
            dist_borda = dist_borda if dist_borda is not None else 0
            tipo_visual = tipo_visual or "linha_h"

        # ── Bate-fecha ────────────────────────────────────────────────────────
        elif ("bate" in tipo and "fecha" in tipo) or ("bate" in nome_lower and "fecha" in nome_lower):
            pos_y = altura_mm * 0.50
            dist_borda = dist_borda if dist_borda is not None else 0
            tipo_visual = tipo_visual or "linha_h"

        # ── Roldana ───────────────────────────────────────────────────────────
        elif "roldana" in tipo or "roldana" in nome_lower:
            pos_y = 20
            dist_borda = dist_borda if dist_borda is not None else 50
            tipo_visual = tipo_visual or "circulo"

        # ── Genérico ──────────────────────────────────────────────────────────
        else:
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
