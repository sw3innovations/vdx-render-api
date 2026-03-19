import os
import json
import logging
from typing import Optional
from anthropic import Anthropic, APIError
from app.core.catalogo import FERRAGEM_DEFAULTS, aplicar_defaults_ferragem

log = logging.getLogger(__name__)

_client: Optional[Anthropic] = None


def _get_client() -> Optional[Anthropic]:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if api_key:
            _client = Anthropic(api_key=api_key)
    return _client


async def inferir_ferragens(
    tipologia_nome: str,
    peca_nome: str,
    largura_mm: float,
    altura_mm: float,
    ferragens_sem_posicao: list[dict],
) -> tuple[list[dict], bool]:
    """
    Tenta usar Claude para inferir posicionamento técnico das ferragens.
    Retorna (ferragens_enriquecidas, claude_usado).
    Fallback para FERRAGEM_DEFAULTS se Claude indisponível ou falhar.
    """
    client = _get_client()
    if not client or not ferragens_sem_posicao:
        return _aplicar_defaults(ferragens_sem_posicao, altura_mm), False

    lista_str = json.dumps(
        [{"tipo": f["tipo"], "nome": f.get("nome", f["tipo"])} for f in ferragens_sem_posicao],
        ensure_ascii=False,
    )

    prompt = (
        f"Você é especialista em vidraçaria brasileira com 20 anos de experiência.\n"
        f"Contexto: tipologia '{tipologia_nome}', peça '{peca_nome}' de {largura_mm:.0f}mm × {altura_mm:.0f}mm.\n\n"
        f"Para cada ferragem abaixo, infira a posição técnica correta conforme "
        f"normas ABNT e prática do mercado brasileiro.\n\n"
        f"Ferragens: {lista_str}\n\n"
        f"Retorne SOMENTE JSON válido (sem markdown):\n"
        f"[\n"
        f"  {{\n"
        f'    "tipo": "bate_fecha",\n'
        f'    "posicao_y_mm": 1100,\n'
        f'    "distancia_borda_mm": 0,\n'
        f'    "tipo_visual": "linha_h"\n'
        f"  }}\n"
        f"]\n\n"
        f"tipo_visual deve ser: linha_h (bate-fecha/trinco), circulo (puxador), retangulo (dobradiça/fechadura)"
    )

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Remove markdown se presente
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.split("\n")[:-1])
        inferidas = json.loads(raw)
        resultado = _mesclar_com_originais(ferragens_sem_posicao, inferidas, altura_mm)
        return resultado, True
    except (APIError, json.JSONDecodeError, Exception) as e:
        log.warning("Claude falhou para ferragens (%s), usando defaults: %s", peca_nome, e)
        return _aplicar_defaults(ferragens_sem_posicao, altura_mm), False


def _aplicar_defaults(ferragens: list[dict], altura_mm: float) -> list[dict]:
    resultado = []
    for f in ferragens:
        d = aplicar_defaults_ferragem(f["tipo"], altura_mm)
        resultado.append({
            "tipo": f["tipo"],
            "nome": f.get("nome"),
            "posicao_y_mm": f.get("posicao_y_mm") or d["posicao_y_mm"],
            "distancia_borda_mm": f.get("distancia_borda_mm") if f.get("distancia_borda_mm") is not None else d["distancia_borda_mm"],
            "tipo_visual": f.get("tipo_visual") or d["tipo_visual"],
            "inferida_por_ia": False,
        })
    return resultado


def _mesclar_com_originais(originais: list[dict], inferidas: list[dict], altura_mm: float) -> list[dict]:
    """Mescla resultados do Claude com os dados originais, usando defaults para campos ausentes."""
    resultado = []
    for i, orig in enumerate(originais):
        inf = inferidas[i] if i < len(inferidas) else {}
        d = aplicar_defaults_ferragem(orig["tipo"], altura_mm)
        resultado.append({
            "tipo": orig["tipo"],
            "nome": orig.get("nome"),
            "posicao_y_mm": inf.get("posicao_y_mm") or orig.get("posicao_y_mm") or d["posicao_y_mm"],
            "distancia_borda_mm": inf.get("distancia_borda_mm") if inf.get("distancia_borda_mm") is not None else d["distancia_borda_mm"],
            "tipo_visual": inf.get("tipo_visual") or orig.get("tipo_visual") or d["tipo_visual"],
            "inferida_por_ia": True,
        })
    return resultado
