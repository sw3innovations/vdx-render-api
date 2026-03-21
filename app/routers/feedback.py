import os
import logging
from fastapi import APIRouter, Header, HTTPException
from typing import Optional
from app.models.feedback import FeedbackRequest, FeedbackResponse
from app.services import feedback_service

logger = logging.getLogger(__name__)

_VDX_API_KEY = os.getenv("VDX_API_MASTER_KEY", "")

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def receber_feedback(
    body: FeedbackRequest,
    x_vdx_key: Optional[str] = Header(None),
):
    if not x_vdx_key:
        raise HTTPException(status_code=401, detail="X-VDX-Key header obrigatório")
    if _VDX_API_KEY and x_vdx_key != _VDX_API_KEY:
        raise HTTPException(status_code=403, detail="X-VDX-Key inválida")

    return feedback_service.processar(body)
