"""Pre-gera imagens fotorrealistas das 29 tipologias (padrão: incolor + cromado).

Executa diretamente no servidor com acesso ao app VDX.
"""
import asyncio
import sys
import time

sys.path.insert(0, "/home/sw3innovation/vdx-render-api")

from app.config import settings
from app.models.render import PecaInput, RenderRequest
from app.services.render_orchestrator import executar
from app.services.photorealistic_pipeline import gerar_fotorrealista, _cache_path

TIPOLOGIAS = [
    ("porta_pivotante_simples", "Porta", 900, 2100),
    ("porta_pivotante_dupla_bandeira", "Porta", 1200, 2100),
    ("porta_abrir", "Porta", 900, 2100),
    ("porta_correr_2_folhas", "Porta", 1200, 2100),
    ("porta_correr_3_folhas", "Porta", 1800, 2100),
    ("porta_quatro_folhas", "Porta", 2400, 2100),
    ("janela_correr_2_folhas", "Janela", 1200, 1000),
    ("janela_correr_2_folhas_oriun_plus", "Janela", 1200, 1000),
    ("janela_quatro_folhas", "Janela", 2400, 1000),
    ("janela_quatro_folhas_orion_plus", "Janela", 2400, 1000),
    ("janela_3_folhas", "Janela", 1800, 1000),
    ("janela_pivotante", "Janela", 900, 1000),
    ("janela_basculante", "Janela", 1200, 600),
    ("janela_maxim_ar", "Janela", 1200, 800),
    ("box_frontal_2_folhas", "Box", 700, 1900),
    ("box_canto_90", "Box", 900, 1900),
    ("box_articulado", "Box", 700, 1900),
    ("box_de_giro", "Box", 700, 1900),
    ("box_flex", "Box", 900, 1900),
    ("divisoria_porta_pivotante", "Fixo", 1200, 2400),
    ("guarda_corpo_linear", "Fixo", 1500, 1100),
    ("cobertura", "Fixo", 2000, 1000),
    ("fechamento_de_sacada_6_folhas", "Fixo", 3600, 2100),
    ("fachada_fixa", "Fixo", 1200, 2400),
    ("vitrine", "Fixo", 1200, 2100),
    ("balcão_de_pia_duas_folhas", "Fixo", 900, 800),
    ("balcão_de_pia_quatro_folhas", "Fixo", 1800, 800),
    ("diâmetro", "Fixo", 800, 800),
    ("diâmetro_com_furo_no_meio", "Fixo", 800, 800),
]

COR = "incolor"
ACABAMENTO = "cromado"
RATE_LIMIT_S = 5  # segundos entre requests à Pollinations


async def pregen():
    total = len(TIPOLOGIAS)
    ok = 0
    skip = 0
    err = 0

    for i, (chave, nome_peca, larg, alt) in enumerate(TIPOLOGIAS, 1):
        cache = _cache_path(settings.app_upload_dir, chave, float(larg), float(alt), COR, ACABAMENTO)
        if cache.exists():
            print(f"[{i:2d}/{total}] SKIP  {chave} ({larg}x{alt}) — cache hit")
            skip += 1
            continue

        print(f"[{i:2d}/{total}] GEN   {chave} ({larg}x{alt})…", end=" ", flush=True)
        try:
            req = RenderRequest(
                tipologia_nome=chave,
                pecas=[PecaInput(nome=nome_peca, largura_mm=float(larg), altura_mm=float(alt))],
            )
            resp = await executar(req)
            svg = resp.svg

            img_bytes, mime = await gerar_fotorrealista(
                svg=svg,
                chave=chave,
                largura_mm=float(larg),
                altura_mm=float(alt),
                upload_dir=settings.app_upload_dir,
                cor=COR,
                acabamento=ACABAMENTO,
            )
            print(f"OK {len(img_bytes)//1024}KB ({mime})")
            ok += 1
        except Exception as e:
            print(f"ERR {type(e).__name__}: {e}")
            err += 1

        if i < total:
            time.sleep(RATE_LIMIT_S)

    print(f"\nDone: {ok} geradas, {skip} em cache, {err} erros")


if __name__ == "__main__":
    asyncio.run(pregen())
