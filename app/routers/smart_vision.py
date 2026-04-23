"""Router Smart Vision — foto/croqui → projeto completo.

Endpoints:
  POST /api/v1/smart/photo-to-project   → analisa foto real de vão
  POST /api/v1/smart/sketch-to-project  → analisa croqui/desenho a mão

Pipeline:
  Claude Vision (VisionService) → VisionResult
    → RenderRequest (auto-gerado) → render_orchestrator.executar() → RenderResponse
    → SceneBuilder.build() → Scene JSON 3D
    → view_token.encode() → viewer URL compartilhável
    → SmartProjectResponse (JSON único)
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import settings
from app.core import view_token as vt
from app.core.auth import validate_api_key
from app.core.limiter import limiter
from app.models.render import PecaInput, RenderRequest
from app.models.vision import (
    PhotoToProjectRequest,
    SketchToProjectRequest,
    SmartProjectResponse,
    VisionAnalysis,
)
from app.renderers.scene_builder import SceneBuilder
from app.services.render_orchestrator import executar
from app.services.vision_service import VisionResult, VisionService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/smart", tags=["Smart Vision"])

_vision = VisionService()
_sb = SceneBuilder()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_vision() -> None:
    if not _vision.disponivel:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Smart Vision indisponível — ANTHROPIC_API_KEY não configurada no servidor",
        )


def _auto_pecas(vr: VisionResult) -> List[PecaInput]:
    """Gera peças baseado em num_folhas e dimensões totais."""
    n = max(1, int(vr.num_folhas or 1))
    w_total = float(vr.largura_mm or 900)
    h_total = float(vr.altura_mm or 2100)
    w_cada = w_total / n
    if n == 1:
        return [PecaInput(nome="Porta", largura_mm=w_cada, altura_mm=h_total)]
    return [
        PecaInput(nome=f"Folha {i+1}", largura_mm=w_cada, altura_mm=h_total)
        for i in range(n)
    ]


def _build_viewer_url(
    request: Request,
    tipologia: str,
    largura: float,
    altura: float,
    cor_vidro: str,
    espessura: float,
) -> tuple[Optional[str], Optional[str], Optional[int]]:
    """Emite view_token e monta URL compartilhável. None em caso de erro (graceful)."""
    try:
        ttl = settings.view_token_ttl_seconds
        claims = vt.new_claims(
            tip=tipologia,
            w=largura,
            h=altura,
            cv=cor_vidro,
            fab=None,
            esp=espessura,
            ttl_seconds=ttl,
        )
        token = vt.encode(claims, settings.view_token_secret)
        base = str(request.base_url).rstrip("/")
        url = f"{base}/api/v1/3d/viewer?t={token}"
        return url, token, ttl
    except Exception as e:
        log.warning("SmartVision: falha ao emitir view_token: %s", e)
        return None, None, None


async def _run_pipeline(
    request: Request,
    vr: VisionResult,
    override_cor: Optional[str],
    override_espessura: Optional[float],
) -> SmartProjectResponse:
    """Shared pipeline — VisionResult → SmartProjectResponse."""
    cor = override_cor or vr.cor_vidro or "incolor"
    espessura = float(override_espessura or vr.espessura_vidro_mm or 8.0)

    pecas = _auto_pecas(vr)
    req = RenderRequest(
        tipologia_nome=vr.tipologia_sugerida,
        pecas=pecas,
        espessura_vidro_mm=espessura,
        tipo_vidro="temperado",
    )
    resp = await executar(req)

    scene = _sb.build(resp, espessura_vidro=espessura, cor_vidro=cor)

    largura_total = float(scene.get("dimensoes", {}).get("largura", vr.largura_mm))
    altura_total = float(scene.get("dimensoes", {}).get("altura", vr.altura_mm))
    tipologia_chave = resp.metadata.get("tipologia_chave", vr.tipologia_sugerida) if resp.metadata else vr.tipologia_sugerida

    viewer_url, viewer_token, viewer_ttl = _build_viewer_url(
        request, tipologia_chave, largura_total, altura_total, cor, espessura,
    )

    # Serializar peças e ferragens de forma genérica
    pecas_out = [p.model_dump() if hasattr(p, "model_dump") else dict(p) for p in resp.pecas]
    ferragens_flat: List[dict] = []
    for p in resp.pecas:
        for f in getattr(p, "ferragens", []) or []:
            d = f.model_dump() if hasattr(f, "model_dump") else dict(f)
            d["peca"] = p.nome
            ferragens_flat.append(d)
    kit_out = resp.kit.model_dump() if getattr(resp, "kit", None) else None

    analise = VisionAnalysis(
        tipologia_sugerida=vr.tipologia_sugerida,
        largura_mm=vr.largura_mm,
        altura_mm=vr.altura_mm,
        tipo_abertura=vr.tipo_abertura,
        num_folhas=vr.num_folhas,
        espessura_vidro_mm=vr.espessura_vidro_mm,
        cor_vidro=vr.cor_vidro,
        observacoes=vr.observacoes,
        confianca=vr.confianca,
    )

    log.info(
        "SmartVision pipeline OK tip=%s %dx%d folhas=%d confianca=%.2f",
        vr.tipologia_sugerida, vr.largura_mm, vr.altura_mm, vr.num_folhas, vr.confianca,
    )

    return SmartProjectResponse(
        analise=analise,
        tipologia_chave=tipologia_chave,
        svg=resp.svg,
        scene=scene,
        pecas=pecas_out,
        ferragens=ferragens_flat,
        kit=kit_out,
        viewer_url=viewer_url,
        viewer_token=viewer_token,
        viewer_expires_in=viewer_ttl,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/photo-to-project", response_model=SmartProjectResponse)
@limiter.limit("10/minute")
async def photo_to_project(
    request: Request,
    body: PhotoToProjectRequest,
    _auth: None = Depends(validate_api_key),
) -> SmartProjectResponse:
    """Foto real de vão → projeto completo (3D + ferragens + viewer URL)."""
    _require_vision()
    log.info("POST /api/v1/smart/photo-to-project contexto_len=%d", len(body.contexto or ""))
    try:
        vr = _vision.analisar_foto_vao(body.image_base64, contexto=body.contexto or "")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Falha ao interpretar resposta Vision: {e}")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log.exception("photo-to-project: erro ao chamar Claude Vision")
        raise HTTPException(status_code=502, detail=f"Erro Claude Vision: {e}")

    return await _run_pipeline(request, vr, body.cor_vidro, body.espessura_vidro_mm)


@router.post("/sketch-to-project", response_model=SmartProjectResponse)
@limiter.limit("10/minute")
async def sketch_to_project(
    request: Request,
    body: SketchToProjectRequest,
    _auth: None = Depends(validate_api_key),
) -> SmartProjectResponse:
    """Croqui/desenho a mão → projeto completo."""
    _require_vision()
    log.info("POST /api/v1/smart/sketch-to-project notas_len=%d", len(body.notas or ""))
    try:
        vr = _vision.analisar_croqui(body.image_base64, notas=body.notas or "")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Falha ao interpretar resposta Vision: {e}")
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log.exception("sketch-to-project: erro ao chamar Claude Vision")
        raise HTTPException(status_code=502, detail=f"Erro Claude Vision: {e}")

    return await _run_pipeline(request, vr, body.cor_vidro, body.espessura_vidro_mm)
