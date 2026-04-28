"""Router de importação de tipologia livre — POST /api/v1/import/tipologia."""
import uuid
from pathlib import Path

import cairosvg
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.limiter import limiter
from app.renderers.svg_renderer_livre import render_geometria_livre
from app.schemas.import_tipologia import TipologiaImportadaSchema
from app.services.import_validator import validar_geometria

router = APIRouter(prefix="/api/v1/import", tags=["import"])

_UPLOADS = Path("uploads/import")


@router.post("/tipologia")
@limiter.limit("10/minute")
async def importar_tipologia(
    request: Request,
    body: TipologiaImportadaSchema,
) -> JSONResponse:
    """Importa tipologia de geometria livre e gera SVG + PNG opcional."""
    erros = validar_geometria(body)
    if erros:
        raise HTTPException(status_code=400, detail=erros[0].mensagem)

    svg = render_geometria_livre(body)

    uid = str(uuid.uuid4())
    png_url: str | None = None
    avisos: list[str] = []

    if body.opcoes.incluir_png:
        out_dir = _UPLOADS / uid
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            png_bytes = cairosvg.svg2png(bytestring=svg.encode())
            (out_dir / "render.png").write_bytes(png_bytes)
            png_url = f"/uploads/import/{uid}/render.png"
        except Exception as exc:
            avisos.append(f"PNG não gerado: {exc}")

    return JSONResponse({
        "tipologia_chave": uid,
        "svg": svg,
        "png_url": png_url,
        "avisos": avisos,
    })
