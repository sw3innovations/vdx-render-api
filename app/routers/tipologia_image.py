from fastapi import APIRouter, Header, HTTPException, Query
from app.core.normalizer import normalizar_tipologia
from app.core.constitution import listar_entries, buscar
from app.services import image_generator

router = APIRouter(prefix="/api/v1", tags=["tipologia-image"])


@router.get("/tipologia/{chave}/image")
async def tipologia_image(
    chave: str,
    regenerar: bool = Query(False),
    x_vdx_key: str = Header(None, alias="X-VDX-Key"),
):
    if not x_vdx_key:
        raise HTTPException(status_code=401, detail="X-VDX-Key obrigatório")

    chave_norm, dados = normalizar_tipologia(chave)
    if not dados:
        raise HTTPException(status_code=404, detail=f"Tipologia '{chave}' não encontrada")

    if regenerar:
        image_generator.invalidar_cache_imagem(chave_norm)

    image_url = await image_generator.gerar_imagem(chave_norm, dados)

    if not image_url:
        raise HTTPException(status_code=503, detail="Erro gerando imagem")

    return {"chave": chave_norm, "image_url": image_url}


@router.post("/tipologias/images/gerar-todas")
async def gerar_todas(
    x_vdx_key: str = Header(None, alias="X-VDX-Key"),
):
    if not x_vdx_key:
        raise HTTPException(status_code=401, detail="X-VDX-Key obrigatório")

    entries = listar_entries(tipo="tipologia")
    resultados = []
    for e in entries:
        entry = buscar(e["chave"], tipo="tipologia")
        if not entry:
            continue
        cached = image_generator.get_cached_image(e["chave"])
        if cached:
            resultados.append({"chave": e["chave"], "image_url": cached, "status": "cached"})
        else:
            url = await image_generator.gerar_imagem(e["chave"], entry["dados"])
            resultados.append({
                "chave": e["chave"],
                "image_url": url or "erro",
                "status": "gerado" if url else "erro",
            })

    return {"total": len(resultados), "images": resultados}
