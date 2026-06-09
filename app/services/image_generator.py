"""Gerador de imagens realistas — Claude escreve o prompt, SD 1.5 renderiza."""
import json
import uuid
import logging
import subprocess
from pathlib import Path
from typing import Optional
from app.services._llm_compat import get_compat_client as Anthropic, APIError
from app.core import constitution
from app.config import settings

log = logging.getLogger(__name__)

IMAGEGEN_SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "generate_image.py"


def _get_claude():
    return Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None


def get_cached_image(chave: str) -> Optional[str]:
    """Retorna URL da imagem cacheada ou None."""
    entry = constitution.buscar(chave, tipo="tipologia_imagem")
    if entry:
        return entry["dados"].get("image_url")
    return None


def gerar_prompt_imagem(chave: str, tipologia_dados: dict) -> str:
    """Claude escreve o prompt perfeito pra SD baseado na Constitution."""
    client = _get_claude()
    if not client:
        return _prompt_fallback(tipologia_dados)

    nome = tipologia_dados.get("nome_display", chave)
    classificacao = tipologia_dados.get("classificacao_pecas", {})
    ferragens = tipologia_dados.get("ferragens_por_peca", {})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": f"""Escreva um prompt de Stable Diffusion pra gerar uma foto realista de produto da tipologia de vidraçaria "{nome}".

Dados técnicos:
- Peças: {json.dumps(classificacao, ensure_ascii=False)}
- Ferragens visíveis: {json.dumps(list(ferragens.keys()), ensure_ascii=False)}

Regras do prompt:
- Em inglês
- Foto de estúdio, fundo branco/cinza claro
- Vidro temperado transparente com leve reflexo
- Ferragens de aço inox visíveis nos pontos corretos
- Perfis de alumínio se aplicável
- Iluminação profissional de produto
- Ângulo 3/4 (mostra profundidade)
- Resolução alta, nítido
- SEM pessoas, SEM ambientes completos
- Máximo 80 palavras

Retorne APENAS o prompt, sem explicação."""}]
    )
    return response.content[0].text.strip()


def _prompt_fallback(dados: dict) -> str:
    nome = dados.get("nome_display", "glass door")
    return (
        f"professional product photography of a {nome}, "
        "frameless tempered glass, stainless steel hardware, "
        "white studio background, soft lighting, 4K, sharp focus"
    )


async def gerar_imagem(chave: str, tipologia_dados: dict) -> Optional[str]:
    """Gera imagem via SD 1.5 e retorna URL pública."""
    cached = get_cached_image(chave)
    if cached:
        return cached

    log.info(f"Gerando imagem para '{chave}'...")
    prompt = gerar_prompt_imagem(chave, tipologia_dados)
    log.info(f"Prompt: {prompt[:100]}...")

    upload_dir = settings.app_upload_dir
    filename = f"tipologia_{chave}_{uuid.uuid4().hex[:8]}.png"
    import os
    filepath = os.path.join(upload_dir, filename)
    os.makedirs(upload_dir, exist_ok=True)

    try:
        import asyncio
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                [settings.imagegen_venv_path, str(IMAGEGEN_SCRIPT), prompt, filepath],
                capture_output=True, text=True, timeout=300
            )
        )

        if result.returncode != 0:
            log.error(f"SD falhou: {result.stderr[:200]}")
            return None

        if not os.path.exists(filepath):
            log.error(f"Imagem não gerada: {filepath}")
            return None

        image_url = f"/uploads/{filename}"

        constitution.registrar(
            chave, {"image_url": image_url, "prompt": prompt},
            tipo="tipologia_imagem", origem="sd15_local", confianca=1.0
        )
        log.info(f"Imagem gerada e cacheada: {image_url}")
        return image_url

    except subprocess.TimeoutExpired:
        log.error(f"Timeout gerando imagem para '{chave}'")
        return None
    except Exception as e:
        log.error(f"Erro gerando imagem: {e}")
        return None


def invalidar_cache_imagem(chave: str) -> None:
    conn = constitution._get_conn()
    conn.execute(
        "DELETE FROM constitution_entries WHERE tipo='tipologia_imagem' AND chave=?",
        (chave,)
    )
    conn.commit()
    conn.close()
