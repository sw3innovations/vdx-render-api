"""
Claude como professor — resolve tipologias desconhecidas e registra na Constitution.
Modo 2 do pipeline: quando a Constitution não sabe, Claude resolve e aprende.
"""
import json
import logging
from app.core import constitution

log = logging.getLogger(__name__)

# Termos que identificam tipologias claramente fora do domínio de vidraçaria.
# Qualquer chave que contenha um desses termos é rejeitada antes de ser salva na Constitution.
_BLACKLIST_TIPOLOGIA = frozenset({
    "escada", "elevador", "piscina", "churrasqueira", "telhado", "carro",
    "moto", "bicicleta", "teste", "test", "xyz", "foo", "bar", "asdf",
    "hello", "world", "lorem", "ipsum", "dummy", "fake", "example",
})


def _tipologia_valida(chave: str) -> bool:
    """Retorna False para tipologias claramente fora do domínio de vidraçaria."""
    chave_lower = chave.lower()
    return not any(termo in chave_lower for termo in _BLACKLIST_TIPOLOGIA)


def _get_client():
    from app.config import settings
    if not settings.anthropic_api_key:
        return None
    try:
        from anthropic import Anthropic
        return Anthropic(api_key=settings.anthropic_api_key)
    except ImportError:
        log.warning("anthropic package não instalado")
        return None


async def resolver_tipologia_desconhecida(
    tipologia_nome: str,
    pecas: list[dict],
    puxador: dict = None,
) -> dict:
    """
    Claude resolve uma tipologia que a Constitution não conhece.
    Retorna dados no formato da Constitution E registra para próxima vez.
    """
    client = _get_client()
    if not client:
        log.warning("ANTHROPIC_API_KEY não configurada — não pode resolver tipologia desconhecida")
        return None

    todas = constitution.listar_entries(tipo="tipologia")
    exemplos = []
    for e in todas[:5]:
        entry = constitution.buscar(e["chave"], tipo="tipologia")
        if entry:
            exemplos.append({"chave": e["chave"], "dados": entry["dados"]})

    pecas_str = json.dumps(
        [{"nome": p["nome"], "largura_mm": p["largura_mm"], "altura_mm": p["altura_mm"]}
         for p in pecas],
        ensure_ascii=False,
    )

    prompt = f"""Você é um especialista em aplicação de vidros temperados no mercado brasileiro.
Conheça as normas ABNT (NBR 7199, 14207, 14718, 16259).

A tipologia "{tipologia_nome}" não está cadastrada no sistema.
Peças: {pecas_str}

Com base no seu conhecimento, retorne SOMENTE um JSON válido (sem markdown) com a estrutura:
{{
  "nome_display": "Nome da tipologia",
  "classificacao_pecas": {{"nome_peca": "fixa|movel|correr", ...}},
  "ferragens_por_peca": {{
    "movel": [
      {{"codigo": "XXXX", "nome": "Nome", "tipo": "dobradica|fechadura|trinco|roldana|suporte|bate_fecha",
        "y_formula": "expressão com altura e largura", "x_formula": "expressão",
        "lado": "esquerdo|direito|centro", "visual": "retangulo|circulo|linha_h",
        "recorte": "padrao_sm|furo_passante|nenhum"}}
    ],
    "correr": [],
    "puxador_config": {{
      "y_formula": "altura * 0.50", "x_formula": "largura - 35",
      "lado": "direito", "aceita_eixo": true
    }}
  }},
  "kit": {{
    "codigo": "KIT_XX", "nome": "Kit ...",
    "itens": [{{"codigo": "XXXX", "nome": "...", "qtd": 1}}],
    "puxador_separado": true
  }},
  "normas": [{{"nbr": "NBR XXXX:YYYY", "espessura_min_mm": 8}}]
}}

REGRAS DE POSICIONAMENTO:
- Dobradiça: y=altura-50 (sup) ou y=50 (inf), x=15 (borda esquerda)
- Fechadura: y=altura*0.50, x=largura-15 (borda direita)
- Puxador: y=altura*0.50, x=largura-35
- Roldana: y=20 (base), x=50 de cada borda
- Peça FIXA nunca recebe ferragem
- Fórmulas usam variáveis 'altura' e 'largura' em mm

Exemplos de tipologias conhecidas:
{json.dumps(exemplos[:3], ensure_ascii=False, indent=2)[:2000]}
"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[:-1])

        dados = json.loads(raw)

        chave = (tipologia_nome.lower().strip()
                 .replace(" ", "_").replace("-", "_"))

        if not _tipologia_valida(chave):
            log.warning(
                f"Claude Teacher: tipologia '{chave}' rejeitada pela blacklist "
                f"— não é uma tipologia de vidraçaria válida"
            )
            return None

        constitution.registrar(chave, dados, tipo="tipologia",
                               origem="claude_inferido", confianca=0.7)
        constitution.registrar_alias(chave, chave, "tipologia",
                                     origem="claude_inferido")

        log.info(f"Claude resolveu tipologia '{tipologia_nome}' → '{chave}' (confiança 0.7)")

        # Disparar geração de preview SVG + imagem em background
        try:
            import asyncio
            from app.services import preview_generator, image_generator

            preview_generator.invalidar_cache(chave)
            asyncio.get_event_loop().run_in_executor(
                None, preview_generator.gerar_preview, chave, dados
            )
            log.info(f"Preview SVG disparado em background para '{chave}'")

            asyncio.create_task(image_generator.gerar_imagem(chave, dados))
            log.info(f"Geração de imagem disparada em background para '{chave}'")
        except Exception as e:
            log.warning(f"Falha ao disparar geração de assets para '{chave}': {e}")

        return dados

    except Exception as e:
        log.warning(f"Claude falhou para tipologia '{tipologia_nome}': {e}")
        return None
