"""Router de feedback — recebe correções do vidraceiro e aplica à Constitution."""
import logging
from fastapi import APIRouter, Depends, Request
from app.models.feedback import FeedbackRequest, FeedbackResponse
from app.services import feedback_service
from app.core.auth import validate_api_key
from app.core.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
@limiter.limit("10/minute")
async def receber_feedback(
    request: Request,
    body: FeedbackRequest,
    _auth: None = Depends(validate_api_key),
):
    """Recebe correção de fórmula de posicionamento e aplica à Constitution."""
    return feedback_service.processar(body)
