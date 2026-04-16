"""
Validador pós-render — Claude verifica se o posicionamento de ferragens faz sentido técnico.
Roda apenas para entries com confiança < 0.95.
Se encontrar erro, corrige a Constitution. Próxima vez sai certo sem IA.
"""
import json
import logging

from app.core import constitution
from app.models.render import FerragemPosicionada, PecaRenderizada

log = logging.getLogger(__name__)

REGRAS_VALIDACAO = """
REGRAS DE POSICIONAMENTO NO MERCADO BRASILEIRO DE VIDROS:

ROLDANAS (janela/porta de correr):
- SEMPRE no TOPO da peça (trilho superior), y = altura - 20mm
- NUNCA na base (y = 20mm é ERRADO para roldana)
- 2 roldanas: uma a 50mm de cada borda lateral

DOBRADIÇAS (pivotante/abrir):
- Lado do pivô (geralmente ESQUERDO)
- Superior: 50mm do topo (y = altura - 50)
- Inferior: 50mm da base (y = 50)

PUXADOR:
- Lado OPOSTO às dobradiças
- Centro vertical (50% da altura)
- Furos conforme eixo selecionado

FECHADURA:
- Mesma altura do puxador (50% da altura)
- Mesmo lado do puxador (oposto às dobradiças)

BATE-FECHA:
- Centro vertical (50% da altura)
- Borda do encontro das folhas

TRINCO (basculante/maxim-ar):
- Centro da peça (50% altura, 50% largura)

PEÇA FIXA: ZERO ferragens, ZERO furos, ZERO recortes

REGRAS DE SEGURANÇA:
- Distância mínima furo-borda: 50mm (norma de têmpera)
- Ferragem nunca pode estar a menos de 20mm de qualquer borda
- Dobradiça e puxador NUNCA no mesmo lado
"""


async def validar_posicionamento(
    tipologia_chave: str,
    tipologia_nome: str,
    pecas: list[PecaRenderizada],
    tipologia_dados: dict,
) -> dict:
    """
    Claude valida o posicionamento das ferragens após o render.
    Retorna: {"valido": True/False, "erros": [...], "ferragens_por_peca_corrigido": {...}}
    """
    if constitution.foi_validada(tipologia_chave):
        return {"valido": True, "erros": [], "ja_validada": True}

    client = _get_client()
    if not client:
        log.warning("ANTHROPIC_API_KEY não configurada — skip validação pós-render")
        return {"valido": True, "erros": [], "skip": True}

    resultado_atual = []
    for p in pecas:
        ferr_desc = []
        for f in p.ferragens:
            ferr_desc.append(f"    {f.nome}: x={f.x_mm}mm y={f.y_mm}mm lado={f.lado}")
        resultado_atual.append(
            f"  {p.nome} ({p.classificacao}, {p.largura_mm}×{p.altura_mm}mm):\n"
            + ("\n".join(ferr_desc) if ferr_desc else "    NENHUMA ferragem")
        )

    prompt = f"""Você é um validador técnico de posicionamento de ferragens para vidros.

{REGRAS_VALIDACAO}

TIPOLOGIA: "{tipologia_nome}"
RESULTADO DO POSICIONAMENTO ATUAL:
{chr(10).join(resultado_atual)}

FÓRMULAS ATUAIS NA BASE DE DADOS:
{json.dumps(tipologia_dados.get('ferragens_por_peca', {}), ensure_ascii=False, indent=2)[:2000]}

TAREFA: Analise se o posicionamento está CORRETO conforme as regras acima.

Responda SOMENTE com JSON válido (sem markdown):
{{
  "valido": true/false,
  "erros": [
    {{
      "ferragem": "nome da ferragem",
      "problema": "descrição do erro",
      "y_formula_atual": "formula errada",
      "y_formula_correta": "formula correta",
      "x_formula_atual": "formula errada (se aplicável)",
      "x_formula_correta": "formula correta (se aplicável)"
    }}
  ],
  "ferragens_por_peca_corrigido": {{ ... formato completo corrigido se houver erros ... }}
}}

Se tudo estiver correto, retorne {{"valido": true, "erros": []}}
"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences (handles ```json, ```, etc.)
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if "```" in raw:
            raw = raw[:raw.rfind("```")]
        raw = raw.strip()
        # Extract first JSON object even if Claude added trailing text
        import re as _re
        m = _re.search(r'\{.*\}', raw, _re.DOTALL)
        if m:
            raw = m.group(0)

        resultado = json.loads(raw)

        if resultado.get("valido"):
            constitution.marcar_validada(tipologia_chave, confianca=0.95)
            constitution.registrar_validacao(
                tipologia_chave, "auto_validator", "ok",
                validado_por="claude_validator")
            log.info(f"Validação OK: '{tipologia_chave}' → confiança 0.95")
        else:
            erros = resultado.get("erros", [])
            corrigido = resultado.get("ferragens_por_peca_corrigido")
            if corrigido:
                tipologia_dados["ferragens_por_peca"] = corrigido
                constitution.registrar(
                    tipologia_chave, tipologia_dados, tipo="tipologia",
                    origem="claude_validator_corrigido", confianca=0.9)
                constitution.registrar_validacao(
                    tipologia_chave, "auto_validator", "corrigido",
                    correcoes=json.dumps(erros, ensure_ascii=False),
                    validado_por="claude_validator")
                log.warning(
                    f"Validação CORRIGIU: '{tipologia_chave}' → "
                    f"{len(erros)} erro(s) → Constitution atualizada"
                )

        return resultado

    except Exception as e:
        log.warning(f"Validação falhou para '{tipologia_chave}': {e}")
        return {"valido": True, "erros": [], "erro": str(e)}


def _get_client():
    from app.config import settings
    if not settings.anthropic_api_key:
        return None
    key = settings.anthropic_api_key
    try:
        from anthropic import Anthropic
        return Anthropic(api_key=key)
    except ImportError:
        return None
