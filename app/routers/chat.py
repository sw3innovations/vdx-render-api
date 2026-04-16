"""
POST /api/v1/chat — Consultor técnico via Claude + Constitution.
Modo público: sem autenticação de usuário, requer X-VDX-Key.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from app.core.limiter import limiter
from app.core import constitution
from app.core.normalizer import normalizar_tipologia
from app.core.auth import validate_api_key
from app.config import settings

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])

SYSTEM_PROMPT = """Você é um consultor técnico especializado em vidraçaria brasileira temperada.
Conhece profundamente:
- Aplicações: box, portas, janelas, guarda-corpo, sacadas, coberturas, divisórias.
- Ferragens: dobradiças, trincos, fechaduras, puxadores, roldanas, perfis.
- Fabricantes: HE (Glasspeças/Santa Marina), AL (AL Indústria), Dorma, Blindex.
- Normas ABNT: NBR 7199:2016, NBR 14207:2009, NBR 14718:2019, NBR 16259:2014.
Responda de forma objetiva e prática, como um vidraceiro experiente.
Máximo 250 palavras. Inclua códigos de ferragens quando souber."""


class MensagemHistorico(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    mensagem: str
    historico: list[MensagemHistorico] = []
    contexto: Optional[dict] = None


class ChatResponse(BaseModel):
    resposta: str
    tipologia_detectada: Optional[str] = None
    sugestoes: list[str] = []
    fonte: str = "claude"


def _get_anthropic_client():
    if not settings.anthropic_api_key:
        return None
    try:
        from anthropic import Anthropic
        return Anthropic(api_key=settings.anthropic_api_key)
    except ImportError:
        return None


def _constitution_context(contexto: Optional[dict], mensagem: str) -> str:
    """Monta contexto adicional a partir da Constitution e do contexto da tela."""
    partes = []

    if contexto:
        tip = contexto.get("tipologia_nome")
        esp = contexto.get("espessura_mm")
        if tip:
            partes.append(f"Tipologia atual: {tip}")
            _, dados = normalizar_tipologia(tip)
            if dados:
                normas = dados.get("normas", [])
                for n in normas[:2]:
                    partes.append(f"Norma aplicável: {n.get('nbr')} — esp. mín. {n.get('espessura_min_mm', '?')}mm")
        if esp:
            partes.append(f"Espessura informada: {esp}mm")

    return ("\n\nContexto da tela:\n" + "\n".join(partes)) if partes else ""


def _sugestoes_followup(resposta: str) -> list[str]:
    """Gera sugestões de perguntas de follow-up baseadas na resposta."""
    r = resposta.lower()
    sugestoes = []
    if "dobradiça" in r or "dobradica" in r:
        sugestoes.append("Quantas dobradiças para uma porta de 2400mm?")
    if "espessura" in r or "mm" in r:
        sugestoes.append("Qual a norma ABNT para esta espessura?")
    if "temperado" in r:
        sugestoes.append("Posso usar vidro laminado no lugar?")
    if "box" in r:
        sugestoes.append("Ferragens recomendadas para box de canto 90°?")
    if "guarda" in r or "corpo" in r:
        sugestoes.append("Qual altura mínima para guarda-corpo?")
    if not sugestoes:
        sugestoes = [
            "Me explique as normas ABNT para esta aplicação.",
            "Quais ferragens preciso para instalar?",
        ]
    return sugestoes[:4]


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat_endpoint(
    request: Request,
    body: ChatRequest,
    _auth: None = Depends(validate_api_key),
):
    """Consulta o assistente técnico especializado em vidraçaria brasileira."""
    client = _get_anthropic_client()
    if not client:
        return ChatResponse(
            resposta="Serviço de IA não configurado. Configure ANTHROPIC_API_KEY.",
            fonte="fallback",
        )

    ctx = _constitution_context(body.contexto, body.mensagem)
    system = SYSTEM_PROMPT + ctx

    # Construir histórico para Claude
    messages = [{"role": m.role, "content": m.content} for m in body.historico]
    messages.append({"role": "user", "content": body.mensagem})

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=system,
            messages=messages,
        )
        resposta = resp.content[0].text.strip()
    except Exception as e:
        log.warning(f"Claude chat falhou: {e}")
        return ChatResponse(
            resposta="Serviço temporariamente indisponível. Tente novamente.",
            fonte="erro",
        )

    # Detectar tipologia mencionada
    r_lower = resposta.lower()
    tipologia = None
    for nome, token in [
        ("Porta Pivotante", "porta pivotante"),
        ("Box de Banheiro", "box"),
        ("Janela de Correr", "janela de correr"),
        ("Guarda-Corpo", "guarda-corpo"),
        ("Cobertura", "cobertura"),
        ("Divisória", "divisória"),
    ]:
        if token in r_lower:
            tipologia = nome
            break

    return ChatResponse(
        resposta=resposta,
        tipologia_detectada=tipologia,
        sugestoes=_sugestoes_followup(resposta),
        fonte="claude",
    )
