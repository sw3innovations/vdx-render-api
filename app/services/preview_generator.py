"""Gerador e cache de previews SVG animados — renderizados por Claude Sonnet."""
import asyncio
import json
import os
import re
import logging
from anthropic import Anthropic, APIError
from app.core import constitution

log = logging.getLogger(__name__)


def _get_client():
    from app.config import settings
    return Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None


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

    prompt = f"""Você é um engenheiro de vidraçaria brasileira criando um diagrama técnico SVG animado.

TAREFA: Criar SVG para "{nome}" — diagrama FECHADO que ABRE SUAVEMENTE no hover.

DADOS DA TIPOLOGIA:
- Peças: {json.dumps(classificacao, ensure_ascii=False)}
- Ferragens: {json.dumps(ferragens, ensure_ascii=False)[:1200]}

═══ ESPECIFICAÇÕES SVG OBRIGATÓRIAS ═══

viewBox="0 0 300 200"
Fundo: TRANSPARENTE (sem retângulo de fundo)
Retorne SOMENTE <svg>...</svg>. Sem markdown. Sem texto antes ou depois.

═══ DESIGN SYSTEM (use exatamente estas cores) ═══

Vidro: fill="#DCE8F5" fill-opacity="0.5" stroke="#185FA5" stroke-width="1.5"
Perfil/marco alumínio: fill="#8B9DB5" rx="1" (barras de 3-4px)
Ferragem dobradiça: fill="#C85A30" circle r="2.5"
Ferragem puxador: stroke="#C85A30" stroke-width="2" line vertical 12px
Ferragem roldana: fill="#C85A30" circle r="3" com stroke-width="0.5"
Ferragem fechadura: fill="#C85A30" rect 5×4px rx="1"
X temperado: 2 diagonais dentro do vidro, stroke="#185FA5" stroke-width="0.3" opacity="0.12"
Label peça: font-family="'Courier New',monospace" font-size="7" fill="#8B9DB5"
Título rodapé: font-size="8" fill="#64748B" font-weight="bold" y="195" text-anchor="middle" x="150"

═══ REGRAS CRÍTICAS DE ANIMAÇÃO ═══

ESTADO PADRÃO: Tudo FECHADO, dentro do marco.
HOVER (svg:hover): Peça móvel abre SUAVEMENTE com CSS transition.

A animação DEVE seguir estas regras exatas por tipo:

### PIVOTANTE (porta ou janela):
- A porta gira NO EIXO DAS DOBRADIÇAS (lado esquerdo)
- transform-origin: BORDA ESQUERDA DA PORTA (ex: "135px 100px" se porta começa em x=135)
- Ângulo de abertura: rotate(-15deg) no hover (MÁXIMO 20deg)
- Arco tracejado: quarter-circle pequeno na borda oposta às dobradiças
- NUNCA girar no centro. NUNCA girar mais de 20deg.
- A porta NÃO pode sair do viewBox.
- Dobradiças: 2 pontos no lado esquerdo da porta (topo e base)
- Puxador: barra vertical no lado DIREITO da porta

### PIVOTANTE DUPLA COM BANDEIRA:
- Bandeira: retângulo fixo no TOPO (sem movimento)
- Porta 1: gira à esquerda, transform-origin na borda esquerda, rotate(-12deg)
- Porta 2: gira à direita, transform-origin na borda direita, rotate(12deg)
- As duas portas JUNTAS, com divisor no centro
- Ângulo MÁXIMO 15deg cada lado

### CORRER (janela ou porta):
- Folha fixa: NÃO se move
- Folha móvel: translateX(25px) no hover (desliza pra direita)
- SEM rotação. Apenas translação horizontal.
- Trilho superior e inferior: linhas horizontais finas
- Roldanas: 2 pontos no TOPO da folha móvel
- As folhas se sobrepõem levemente (a móvel fica na frente)
- Setas de direção: triangulozinho indicando pra onde desliza

### CORRER 3 FOLHAS:
- 3 retângulos: FIXO à esquerda, MÓVEL no centro (na frente), FIXO à direita
- Folha central desliza translateX(30px) no hover
- Roldanas no topo da folha central
- Trilhos sup/inf

### CORRER 4 FOLHAS:
- 4 retângulos lado a lado dentro do marco
- Folhas externas (1 e 4): FIXAS
- Folhas internas (2 e 3): deslizam pra FORA no hover
- Folha 2: translateX(-15px), Folha 3: translateX(15px)
- Roldanas no topo das folhas internas

### BOX BANHEIRO (frontal):
- FIXO à esquerda, PORTA à direita
- Porta gira na borda ESQUERDA (onde tem dobradiça automática)
- transform-origin: borda esquerda da porta
- Ângulo: rotate(-15deg) no hover
- SEM perfil inferior (é chão de banheiro)
- Puxador: círculo no CENTRO da porta (botão)

### BOX CANTO 90:
- Vista FRONTAL (não planta baixa)
- Lateral fixa à esquerda + frontal com porta à direita
- A porta da parte frontal gira rotate(-12deg) no hover

### BASCULANTE:
- Retângulo único dentro do marco
- Abre pra FORA pelo TOPO: translateY(-8px) + scale(0.95)
- Braço articulado: linha do centro lateral até o marco
- Trinco: ponto no centro

### MAXIM-AR:
- Retângulo único dentro do marco
- transform-origin: borda SUPERIOR
- No hover: rotateX(10deg) com perspective(300px)
- 2 braços articulados nos lados
- Trinco no centro

### GUARDA-CORPO:
- 2-3 painéis lado a lado, colunas/postes entre eles
- NENHUM movimento
- Shimmer sutil: @keyframes oscilando fill-opacity de 0.4 a 0.55

### COBERTURA/CLARABOIA:
- Vista LATERAL: perfis inclinados (~15°) com vidro entre eles
- NENHUM movimento
- Shimmer + efeito de gotas

### DIVISÓRIA COM PORTA:
- 2 painéis fixos nas laterais + porta central pivotante
- Porta gira no eixo esquerdo, rotate(-12deg) no hover

═══ REGRAS DE LAYOUT ═══

- Margem: 20px de todos os lados (conteúdo entre x=20..280, y=15..185)
- Marco/moldura: retângulo de perfil alumínio envolvendo TODAS as peças
- Vidro DENTRO do marco (não pode ultrapassar)
- No hover, a peça pode sair LEVEMENTE do marco (máximo 15px) pra simular abertura
- Labels de peça: FIXO, PORTA, etc. em 7px, centralizados na peça, cor clara
- NÃO colocar códigos de ferragem (1101, 1520). Só os símbolos visuais (pontos, barras)
- NÃO colocar legenda separada. NÃO colocar cotas/medidas.
- NÃO colocar "hover para abrir" ou instruções de uso

═══ CSS — DEVE FUNCIONAR EM DESKTOP (hover) E MOBILE (auto-loop) ═══

Para CADA peça móvel, usar DUAS estratégias no mesmo bloco <style>:

1. DESKTOP (hover): svg:hover .classe {{ transform: ... }}
2. MOBILE (auto-loop): @media (hover: none) com @keyframes loop infinito

Regra: dispositivos touch NÃO suportam hover — o @media (hover: none) ativa
automaticamente em mobile/tablet. Desktop usa hover normalmente.

Ciclo do @keyframes: 4s total — 0% fechado, 40% aberto, 60% aberto, 100% fechado.

Exemplo para PIVOTANTE:
.porta {{ transition: transform 0.6s ease-in-out; transform-origin: 125px 100px; }}
svg:hover .porta {{ transform: rotate(-15deg); }}
@media (hover: none) {{
  .porta {{ animation: abrePorta 4s ease-in-out infinite; }}
}}
@keyframes abrePorta {{
  0%, 100% {{ transform: rotate(0deg); }}
  40%, 60% {{ transform: rotate(-15deg); }}
}}

Exemplo para CORRER (translateX):
.folha {{ transition: transform 0.6s ease-in-out; }}
svg:hover .folha {{ transform: translateX(25px); }}
@media (hover: none) {{
  .folha {{ animation: abreCorrer 4s ease-in-out infinite; }}
}}
@keyframes abreCorrer {{
  0%, 100% {{ transform: translateX(0); }}
  40%, 60% {{ transform: translateX(25px); }}
}}

Para o ARCO de abertura:
.arco {{ opacity: 0; transition: opacity 0.4s; }}
svg:hover .arco {{ opacity: 1; }}
@media (hover: none) {{
  .arco {{ animation: mostraArco 4s ease-in-out infinite; }}
}}
@keyframes mostraArco {{
  0%, 100% {{ opacity: 0; }}
  40%, 60% {{ opacity: 1; }}
}}

@keyframes shimmer (só pra guarda-corpo e cobertura, SEM @media condicional)

REGRA ABSOLUTA: toda classe de peça móvel DEVE ter hover + @media (hover: none).

═══ EXEMPLO DE REFERÊNCIA (porta pivotante simples com fixo) ═══

<svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
<style>
  .porta {{ transition: transform 0.6s ease-in-out; transform-origin: 125px 100px; }}
  svg:hover .porta {{ transform: rotate(-15deg); }}
  .arco {{ opacity: 0; transition: opacity 0.4s; }}
  svg:hover .arco {{ opacity: 1; }}
  @media (hover: none) {{
    .porta {{ animation: abrePorta 4s ease-in-out infinite; }}
    .arco {{ animation: mostraArco 4s ease-in-out infinite; }}
  }}
  @keyframes abrePorta {{
    0%, 100% {{ transform: rotate(0deg); }}
    40%, 60% {{ transform: rotate(-15deg); }}
  }}
  @keyframes mostraArco {{
    0%, 100% {{ opacity: 0; }}
    40%, 60% {{ opacity: 1; }}
  }}
</style>
<!-- Marco -->
<rect x="30" y="15" width="240" height="170" rx="2" fill="none" stroke="#8B9DB5" stroke-width="3"/>
<!-- Fixo -->
<rect x="33" y="18" width="90" height="164" fill="#DCE8F5" fill-opacity="0.5" stroke="#185FA5" stroke-width="1.2"/>
<line x1="35" y1="20" x2="121" y2="180" stroke="#185FA5" stroke-width="0.3" opacity="0.12"/>
<line x1="121" y1="20" x2="35" y2="180" stroke="#185FA5" stroke-width="0.3" opacity="0.12"/>
<text x="78" y="105" text-anchor="middle" font-size="7" fill="#8B9DB5" font-family="'Courier New',monospace">FIXO</text>
<!-- Divisor -->
<rect x="123" y="15" width="4" height="170" fill="#8B9DB5" rx="1"/>
<!-- Porta (animada) -->
<g class="porta">
  <rect x="127" y="18" width="140" height="164" fill="#DCE8F5" fill-opacity="0.5" stroke="#185FA5" stroke-width="1.5"/>
  <line x1="129" y1="20" x2="265" y2="180" stroke="#185FA5" stroke-width="0.3" opacity="0.12"/>
  <line x1="265" y1="20" x2="129" y2="180" stroke="#185FA5" stroke-width="0.3" opacity="0.12"/>
  <text x="197" y="105" text-anchor="middle" font-size="7" fill="#8B9DB5" font-family="'Courier New',monospace">PORTA</text>
  <!-- Dobradiças -->
  <circle cx="130" cy="35" r="2.5" fill="#C85A30"/>
  <circle cx="130" cy="165" r="2.5" fill="#C85A30"/>
  <!-- Puxador -->
  <line x1="258" y1="94" x2="258" y2="106" stroke="#C85A30" stroke-width="2" stroke-linecap="round"/>
  <!-- Fechadura -->
  <rect x="254" y="98" width="5" height="4" rx="1" fill="#C85A30" opacity="0.7"/>
</g>
<!-- Arco de abertura -->
<path class="arco" d="M 267 100 A 70 70 0 0 0 240 30" fill="none" stroke="#185FA5" stroke-width="0.7" stroke-dasharray="3 2"/>
<!-- Título -->
<text x="150" y="195" text-anchor="middle" font-size="8" fill="#64748B" font-family="'Courier New',monospace" font-weight="bold">{nome}</text>
</svg>

USE ESSE NÍVEL DE QUALIDADE E PRECISÃO. A porta fica DENTRO do marco e gira SUAVEMENTE no hover."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=6000,
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


async def gerar_preview_async(chave: str, tipologia_dados: dict) -> str:
    """Versão async: roda gerar_preview em thread pool para não bloquear o event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, gerar_preview, chave, tipologia_dados)


def invalidar_cache(chave: str) -> None:
    conn = constitution._get_conn()
    conn.execute("DELETE FROM constitution_entries WHERE tipo='preview' AND chave=?", (chave,))
    conn.commit()
    conn.close()


_PECA_KEYWORDS = ['FIXO', 'PORTA', 'MOVEL', 'MÓVEL', 'BANDEIRA', 'PAINEL',
                  'LATERAL', 'FOLHA', 'ESQ', 'DIR', 'FRONTAL']

_HIGHLIGHT_CSS = """
.peca-dim{opacity:0.25!important;filter:grayscale(0.7)!important;}
.peca-dim *{animation-play-state:paused!important;}
.peca-highlight rect[fill-opacity],.peca-highlight rect[fill='#DCE8F5']{stroke:#C85A30!important;stroke-width:2.5px!important;}
"""


def aplicar_destaque(svg_str: str, highlight: str) -> str:
    """Aplica destaque server-side: peça=highlight acesa, restante esmaecido."""
    if not highlight or not svg_str:
        return svg_str

    hl = highlight.upper().strip()
    hl_words = [w for w in hl.split() if len(w) > 3]

    def matches(content: str) -> bool:
        c = content.upper().strip()
        if hl in c or c in hl:
            return True
        return (any(w in c for w in hl_words) or
                any(w in hl for w in c.split() if len(w) > 3))

    # Injetar CSS de destaque
    if '<style>' in svg_str:
        svg_str = svg_str.replace('<style>', '<style>' + _HIGHLIGHT_CSS, 1)
    else:
        idx = svg_str.find('>', svg_str.find('<svg'))
        if idx >= 0:
            svg_str = svg_str[:idx+1] + '<style>' + _HIGHLIGHT_CSS + '</style>' + svg_str[idx+1:]

    # Marcar grupos de peça
    text_pat = re.compile(r'<text[^>]*>([^<]{1,25})</text>', re.IGNORECASE)
    g_open_pat = re.compile(r'<g[\s>]')

    for m in reversed(list(text_pat.finditer(svg_str))):
        content = m.group(1).strip()
        c_upper = content.upper()

        if not any(kw in c_upper for kw in _PECA_KEYWORDS):
            continue

        classe = 'peca-highlight' if matches(content) else 'peca-dim'

        # Último <g antes deste texto
        before = svg_str[:m.start()]
        g_starts = [gm.start() for gm in g_open_pat.finditer(before)]
        if not g_starts:
            continue

        g_pos = g_starts[-1]
        g_end = svg_str.find('>', g_pos)
        if g_end < 0:
            continue

        g_tag = svg_str[g_pos:g_end + 1]
        if 'class="' in g_tag:
            new_g = g_tag.replace('class="', f'class="{classe} ', 1)
        elif "class='" in g_tag:
            new_g = g_tag.replace("class='", f"class='{classe} ", 1)
        else:
            new_g = g_tag.replace('<g', f'<g class="{classe}"', 1)

        svg_str = svg_str[:g_pos] + new_g + svg_str[g_end + 1:]

    return svg_str


def _fallback_svg(nome: str) -> str:
    return f'''<svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">
  <rect x="60" y="20" width="180" height="155" rx="4" fill="#DCE8F5" fill-opacity="0.4" stroke="#185FA5" stroke-width="1" stroke-dasharray="4 2"/>
  <line x1="62" y1="22" x2="238" y2="173" stroke="#185FA5" stroke-width="0.3" opacity="0.15"/>
  <line x1="238" y1="22" x2="62" y2="173" stroke="#185FA5" stroke-width="0.3" opacity="0.15"/>
  <text x="150" y="105" text-anchor="middle" font-size="10" fill="#64748B" font-family="Courier New">{nome}</text>
  <text x="150" y="193" text-anchor="middle" font-size="9" fill="#475569" font-family="Courier New" font-weight="bold">{nome}</text>
</svg>'''
