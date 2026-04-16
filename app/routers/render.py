"""
Router de render — apenas concerns HTTP.
Toda lógica de negócio está em services/render_orchestrator.py.
"""
import logging
from fastapi import APIRouter, Depends, Request
from app.models.render import RenderRequest, RenderResponse
from app.services.render_orchestrator import executar
from app.core.limiter import limiter
from app.core.auth import validate_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["render"])


@router.post("/render", response_model=RenderResponse)
@limiter.limit("10/second")
async def render_endpoint(
    request: Request,
    body: RenderRequest,
    _auth: None = Depends(validate_api_key),
):
    """Gera desenho técnico SVG de peça de vidraçaria."""
    return await executar(body)
