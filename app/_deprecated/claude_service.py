import os
import json
import logging
from typing import Optional
from anthropic import Anthropic, APIError
from app._deprecated.catalogo import FERRAGEM_DEFAULTS, aplicar_defaults_ferragem  # TODO Sprint 2: remover dependência legada

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
) -> tuple[list[dict], bool, list[dict]]:
    """
    Tenta usar Claude para inferir posicionamento técnico das ferragens.
    Retorna (ferragens_enriquecidas, claude_usado, alertas_norma).
    Fallback para FERRAGEM_DEFAULTS se Claude indisponível ou falhar.
    """
    client = _get_client()
    if not client or not ferragens_sem_posicao:
        return _aplicar_defaults(ferragens_sem_posicao, altura_mm), False, []

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
        f"REGRAS DE POSICIONAMENTO:\n"
        f"- posicao_y_mm é medida da BASE da peça para cima (não do topo)\n"
        f"- posicao_y_mm deve estar entre 20 e {altura_mm - 20:.0f} (dentro da peça)\n"
        f"- tipo_visual: linha_h (bate-fecha/trinco), circulo (puxador), retangulo (dobradiça/fechadura)\n\n"
        f"VERIFICAÇÃO DE NORMAS ABNT (inclua alerta_norma somente se houver violação):\n"
        f"- Box banheiro: vidro mínimo 8mm (NBR 14207:2009)\n"
        f"- Porta pivotante: vidro mínimo 10mm (NBR 7199:2016)\n"
        f"- Janela: vidro mínimo 6mm (NBR 7199:2016)\n"
        f"- Guarda-corpo: altura mínima 1100mm, laminado obrigatório (NBR 14718:2019)\n"
        f"- Cobertura: temperado simples PROIBIDO, usar laminado (NBR 7199:2016)\n\n"
        f"Retorne SOMENTE JSON válido (sem markdown), array com as ferragens posicionadas.\n"
        f"Se houver violação de norma, adicione ao final do array:\n"
        f'{{"alerta_norma": {{"nivel": "CRITICO", "norma": "NBR X", "mensagem": "..."}}}}\n\n'
        f"Exemplo de retorno:\n"
        f"[\n"
        f"  {{\n"
        f'    "tipo": "bate_fecha",\n'
        f'    "posicao_y_mm": {altura_mm * 0.85:.0f},\n'
        f'    "distancia_borda_mm": 0,\n'
        f'    "tipo_visual": "linha_h"\n'
        f"  }}\n"
        f"]"
    )

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Remove markdown se presente
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.split("\n")[:-1])
        todos = json.loads(raw)
        alertas = [item["alerta_norma"] for item in todos
                   if isinstance(item, dict) and "alerta_norma" in item]
        ferragens_inferidas = [item for item in todos
                               if isinstance(item, dict) and "alerta_norma" not in item]
        resultado = _mesclar_com_originais(ferragens_sem_posicao, ferragens_inferidas, altura_mm)
        return resultado, True, alertas
    except (APIError, json.JSONDecodeError, Exception) as e:
        log.warning("Claude falhou para ferragens (%s), usando defaults: %s", peca_nome, e)
        return _aplicar_defaults(ferragens_sem_posicao, altura_mm), False, []


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
