import asyncio
import logging
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.normalizer import normalizar_tipologia
from app.services import claude_teacher, preview_generator, image_generator

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["tipologia-sync"])


class SyncRequest(BaseModel):
    nome: str
    id: Optional[int] = None


class SyncResponse(BaseModel):
    chave: str
    status: str  # "existente", "nova_claude", "erro"
    preview_svg: bool = False
    imagem: str = "pendente"  # "cached", "gerando", "erro"


@router.post("/tipologia/sync", response_model=SyncResponse)
async def sync_tipologia(
    request: SyncRequest,
    x_vdx_key: str = Header(None, alias="X-VDX-Key"),
):
    if not x_vdx_key:
        raise HTTPException(status_code=401, detail="X-VDX-Key obrigatório")

    chave, dados = normalizar_tipologia(request.nome)

    if dados:
        # Já existe na Constitution
        has_preview = preview_generator.get_cached_preview(chave) is not None
        has_image = image_generator.get_cached_image(chave) is not None

        if not has_preview:
            try:
                asyncio.get_event_loop().run_in_executor(
                    None, preview_generator.gerar_preview, chave, dados
                )
                has_preview = True
            except Exception as e:
                log.warning(f"Falha ao gerar preview para '{chave}': {e}")

        if not has_image:
            asyncio.create_task(image_generator.gerar_imagem(chave, dados))
            img_status = "gerando"
        else:
            img_status = "cached"

        return SyncResponse(
            chave=chave, status="existente",
            preview_svg=has_preview, imagem=img_status,
        )

    else:
        # Nova tipologia — Claude resolve e já dispara assets
        pecas_dummy = [{"nome": "Peça 1", "largura_mm": 1000, "altura_mm": 2000}]
        resultado = await claude_teacher.resolver_tipologia_desconhecida(
            request.nome, pecas_dummy
        )

        if resultado:
            return SyncResponse(
                chave=chave or request.nome.lower().replace(" ", "_"),
                status="nova_claude",
                preview_svg=True,
                imagem="gerando",
            )

        return SyncResponse(
            chave=chave or request.nome.lower().replace(" ", "_"),
            status="erro",
        )
