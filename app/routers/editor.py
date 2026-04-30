"""Router do editor visual — POST /api/v1/editor/salvar, GET /api/v1/editor/{uuid}."""
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.limiter import limiter
from app.schemas.import_tipologia import TipologiaImportadaSchema

router = APIRouter(prefix="/api/v1/editor", tags=["editor"])

_UPLOADS = Path("uploads/editor")


@router.post("/salvar")
@limiter.limit("60/minute")
async def salvar_editor(
    request: Request,
    body: TipologiaImportadaSchema,
) -> JSONResponse:
    """Persiste o estado do editor e retorna a chave para recarregar."""
    editor_uuid = str(uuid.uuid4())
    out_dir = _UPLOADS / editor_uuid

    manifest = {
        "editor_chave": editor_uuid,
        "tipologia_json": body.model_dump(mode="json"),
        "url": f"/editor?carregar={editor_uuid}",
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    return JSONResponse(manifest)


@router.get("/{editor_uuid}")
def recuperar_editor(editor_uuid: str) -> JSONResponse:
    """Recupera um estado de editor salvo anteriormente."""
    manifest_path = _UPLOADS / editor_uuid / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Estado do editor não encontrado")
    return JSONResponse(json.loads(manifest_path.read_text(encoding="utf-8")))
