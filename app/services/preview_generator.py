import json
import os
import logging
from anthropic import Anthropic, APIError
from app.core import constitution

log = logging.getLogger(__name__)


def _get_client():
    key = os.getenv("ANTHROPIC_API_KEY")
    return Anthropic(api_key=key) if key else None


def get_cached_preview(chave: str) -> str:
    entry = constitution.buscar(chave, tipo="preview")
    if entry:
        return entry["dados"].get("svg", None)
    return None


def gerar_preview(chave: str, tipologia_dados: dict) -> str:
    cached = get_cached_preview(chave)
    if cached:
        return cached

    client = _get_client()
    if not client:
        return _fallback_svg(tipologia_dados.get("nome_display", chave))

    nome = tipologia_dados.get("nome_display", chave)
    classificacao = tipologia_dados.get("classificacao_pecas", {})
    ferragens = tipologia_dados.get("ferragens_por_peca", {})
    kit = tipologia_dados.get("kit", {})

    prompt = f"""Você é um designer especialista em vidraçaria brasileira criando SVGs interativos para um catálogo digital premium.

TAREFA: Gerar um SVG animado de ALTA QUALIDADE para a tipologia "{nome}".

DADOS TÉCNICOS DA TIPOLOGIA:
- Nome: {nome}
- Peças: {json.dumps(classificacao, ensure_ascii=False)}
- Ferragens: {json.dumps(ferragens, ensure_ascii=False)[:1500]}
- Kit: {json.dumps(kit, ensure_ascii=False)[:500]}

ESPECIFICAÇÕES OBRIGATÓRIAS DO SVG:
1. viewBox="0 0 300 200" — proporção fixa
2. Fundo TRANSPARENTE (sem rect de background)
3. Retorne SOMENTE o código SVG (começando com <svg e terminando com </svg>). Nada antes, nada depois. Sem markdown.

DESIGN SYSTEM:
- Vidro: fill="#DCE8F5" fill-opacity="0.55" stroke="#185FA5" stroke-width="1.2"
- Perfil alumínio: fill="#94A3B8" (barras finas 3-4px nos marcos/batentes, rx="1")
- Ferragens: fill="#D85A30" (dobradiças=circle r=3, puxador=line stroke-width=2.5 stroke-linecap=round, roldana=circle r=3.5 com cruz +, fechadura=rect pequeno, trinco=rect fino)
- Labels de peça: font-family="'Courier New',monospace" font-size="8" fill="#64748B" text-anchor="middle"
- Nome da tipologia no rodapé: font-size="9" fill="#475569" font-weight="bold" text-anchor="middle" y="195"
- Sombra sutil: filter com feDropShadow stdDeviation="1" dx="0" dy="1" flood-opacity="0.08"
- X do temperado: 2 diagonais canto a canto, opacity="0.15" stroke-width="0.4" stroke="#185FA5"
- Reflexo no vidro: rect branco diagonal opacity="0.08"

REGRAS DE ANIMAÇÃO:
- TODA peça móvel deve ter animação de abertura/funcionamento no hover
- Animação ativa com svg:hover .classe (CSS transitions 0.5-0.8s ease-in-out)
- Estado padrão: FECHADO. Estado hover: ABERTO
- Arco/seta de abertura: aparece com opacity transition no hover, stroke="#185FA5" stroke-dasharray="4 2"
- Tipos de movimento:
  * Pivotante: rotate no eixo das dobradiças (transform-origin no lado do pivô)
  * Correr/deslizante: translateX na direção do trilho
  * Basculante: simular tombamento (translateY + scaleY)
  * Maxim-ar: abrir de baixo pra cima (transform-origin topo)
  * Box: porta gira com dobradiça automática (~25deg)
  * Fixo/guarda-corpo: shimmer sutil (fill-opacity oscilando via @keyframes)
  * Cobertura: sem movimento, efeito de reflexo

DETALHES DE QUALIDADE:
- Proporções realistas: porta mais alta que larga, janela mais larga que alta, basculante compacta, guarda-corpo largo e baixo
- Se tem FIXO + MÓVEL: divisor vertical (perfil entre peças)
- Perfis formam o marco/batente completo (retângulos finos nos 3-4 lados)
- Ferragens nos pontos tecnicamente corretos conforme os dados
- Dobradiças no lado do pivô, puxador no lado oposto
- Roldanas no TOPO (trilho superior) pra tipologias de correr
- Cada peça deve ter label pequeno (FIXO, PORTA, etc.)

REFERÊNCIA DE LAYOUT POR TIPO:
- Porta Pivotante: FIXO esq ~35% + PORTA dir ~65%, porta gira no pivô esquerdo
- Porta Pivotante Dupla com Bandeira: Bandeira em cima, 2 portas embaixo
- Janela Correr 2 Folhas: 2 folhas sobrepostas, móvel desliza no hover, trilhos sup/inf
- Box Frontal: FIXO + PORTA, sem perfil inferior (chão banheiro)
- Box Canto 90: vista de cima (planta baixa) em L, lateral fixa + frontal com porta
- Basculante: retângulo único, tomba pra fora, braço articulado
- Maxim-Ar: retângulo único, abre de baixo pra cima, 2 braços
- Guarda-Corpo: painéis lado a lado, colunas entre eles, sem movimento
- Cobertura/Claraboia: vista lateral, perfis inclinados, vidros entre eles
- Divisória com Porta: painéis fixos + porta central pivotante
- Janela Pivotante: como porta pivotante mas menor, com perfil em volta

PRODUZA O MELHOR SVG QUE CONSEGUIR. Qualidade de produto premium."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        svg = message.content[0].text.strip()

        if svg.startswith("```"):
            svg = "\n".join(svg.split("\n")[1:])
        if svg.endswith("```"):
            svg = "\n".join(svg.split("\n")[:-1])

        start = svg.find("<svg")
        close_idx = svg.rfind("</svg>")
        if start >= 0 and close_idx >= 0:
            svg = svg[start:close_idx + 6]
        else:
            log.warning(f"SVG inválido para '{chave}' — fallback")
            return _fallback_svg(nome)

        constitution.registrar(
            chave, {"svg": svg, "nome": nome}, tipo="preview",
            origem="claude_generated", confianca=1.0)
        log.info(f"Preview gerado e cacheado: '{chave}' ({len(svg)} bytes)")
        return svg

    except (APIError, Exception) as e:
        log.error(f"Erro gerando preview para '{chave}': {e}")
        return _fallback_svg(nome)


def invalidar_cache(chave: str):
    conn = constitution._get_conn()
    conn.execute("DELETE FROM constitution_entries WHERE tipo='preview' AND chave=?", (chave,))
    conn.commit()
    conn.close()


def _fallback_svg(nome: str) -> str:
    return f'''<svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
  <rect x="60" y="20" width="180" height="155" rx="4" fill="#DCE8F5" fill-opacity="0.4" stroke="#185FA5" stroke-width="1" stroke-dasharray="4 2"/>
  <line x1="62" y1="22" x2="238" y2="173" stroke="#185FA5" stroke-width="0.3" opacity="0.15"/>
  <line x1="238" y1="22" x2="62" y2="173" stroke="#185FA5" stroke-width="0.3" opacity="0.15"/>
  <text x="150" y="105" text-anchor="middle" font-size="10" fill="#64748B" font-family="Courier New">{nome}</text>
  <text x="150" y="193" text-anchor="middle" font-size="9" fill="#475569" font-family="Courier New" font-weight="bold">{nome}</text>
</svg>'''
