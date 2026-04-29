"""Router de importação de tipologia livre — POST /api/v1/import/tipologia."""
import json
import uuid
from pathlib import Path

import cairosvg
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.limiter import limiter
from app.renderers.svg_renderer_livre import render_geometria_livre
from app.schemas.import_tipologia import TipologiaImportadaSchema
from app.services.import_validator import resolver_ferragens, validar_geometria

router = APIRouter(prefix="/api/v1/import", tags=["import"])

_UPLOADS = Path("uploads/import")


@router.post("/tipologia")
@limiter.limit("60/minute")
async def importar_tipologia(
    request: Request,
    body: TipologiaImportadaSchema,
) -> JSONResponse:
    """Importa tipologia de geometria livre e gera SVG + PNG/PDF/3D opcionais."""
    issues = validar_geometria(body)
    erros = [e for e in issues if not e.is_warning]
    avisos = [e.mensagem for e in issues if e.is_warning]

    if erros:
        raise HTTPException(status_code=400, detail=erros[0].mensagem)

    svg = render_geometria_livre(body)
    ferragens_resolvidas = resolver_ferragens(body)

    uid = str(uuid.uuid4())
    out_dir = _UPLOADS / uid
    png_url: str | None = None
    pdf_url: str | None = None
    viewer_3d_url: str | None = None

    if body.opcoes.incluir_png:
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            png_bytes = cairosvg.svg2png(bytestring=svg.encode())
            (out_dir / "render.png").write_bytes(png_bytes)
            png_url = f"/uploads/import/{uid}/render.png"
        except Exception as exc:
            avisos.append(f"PNG não gerado: {exc}")

    if body.opcoes.incluir_pdf:
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            from app.services.conversion_service import svg_para_pdf
            pdf_bytes = svg_para_pdf(svg)
            (out_dir / "render.pdf").write_bytes(pdf_bytes)
            pdf_url = f"/uploads/import/{uid}/render.pdf"
        except Exception as exc:
            avisos.append(f"PDF não gerado: {exc}")

    if body.opcoes.incluir_3d:
        try:
            from app.core import view_token as vt
            from app.config import settings
            total_w = sum(p.largura_mm for p in body.paineis)
            total_h = max(p.altura_mm for p in body.paineis)
            claims = vt.new_claims(
                tip="importado",
                w=total_w,
                h=total_h,
                cv=body.opcoes.cor,
                fab=None,
                esp=8.0,
                ttl_seconds=settings.view_token_ttl_seconds,
            )
            token = vt.encode(claims, settings.view_token_secret)
            viewer_3d_url = f"/api/v1/3d/viewer?t={token}"
        except Exception as exc:
            avisos.append(f"Viewer 3D não gerado: {exc}")

    manifest = {
        "tipologia_chave": uid,
        "svg": svg,
        "png_url": png_url,
        "pdf_url": pdf_url,
        "viewer_3d_url": viewer_3d_url,
        "ferragens_resolvidas": ferragens_resolvidas,
        "avisos": avisos,
    }
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    except Exception:
        pass

    return JSONResponse(manifest)


@router.get("/{chave}")
def recuperar_tipologia(chave: str) -> JSONResponse:
    """Retorna manifest persistido de uma importação anterior."""
    manifest_path = _UPLOADS / chave / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Tipologia não encontrada")
    return JSONResponse(json.loads(manifest_path.read_text(encoding="utf-8")))
