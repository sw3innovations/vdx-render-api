"""
Router de proposta comercial — gera PDF profissional white-label.

Endpoints:
  POST /api/v1/proposal          → PDF binário (application/pdf)
  POST /api/v1/proposal/preview  → ProposalResponse JSON (metadados, sem PDF)
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from app.core.auth import validate_api_key
from app.core.limiter import limiter
from app.models.proposal import ProposalRequest, ProposalResponse
from app.services import proposal_service

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["proposal"])


@router.post("/proposal", response_class=Response)
@limiter.limit("5/minute")
async def gerar_proposta(
    request: Request,
    body: ProposalRequest,
    _auth: None = Depends(validate_api_key),
):
    """Gera proposta comercial em PDF a partir do orçamento.

    Retorna o PDF binário com cabeçalho white-label (logo + cores da empresa),
    tabela de itens em BRL, desenhos técnicos SVG convertidos para PNG e
    lista de ferragens por peça.
    """
    try:
        pdf_bytes = await proposal_service.gerar_proposta(body)
    except Exception as e:
        log.exception("Erro ao gerar proposta: %s", e)
        raise HTTPException(status_code=500, detail=f"Falha ao gerar proposta: {e}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="proposta.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.post("/proposal/preview", response_model=ProposalResponse)
@limiter.limit("10/minute")
async def preview_proposta(
    request: Request,
    body: ProposalRequest,
    _auth: None = Depends(validate_api_key),
):
    """Retorna metadados da proposta sem gerar o PDF completo.

    Útil para validar o payload e exibir resumo antes de baixar o PDF.
    Não chama o render de SVG — resposta é imediata.
    """
    numero = proposal_service._gerar_numero(body.numero_proposta)
    valor_total = sum(i.valor_total or 0 for i in body.itens) or None
    validade_ate = (datetime.now() + timedelta(days=body.validade_dias)).strftime("%Y-%m-%d")

    return ProposalResponse(
        numero_proposta=numero,
        total_itens=len(body.itens),
        valor_total=valor_total if valor_total else None,
        pdf_bytes=0,
        validade_ate=validade_ate,
    )
