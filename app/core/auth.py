"""Dependência FastAPI de autenticação via X-VDX-Key header."""
import hmac
import logging
from typing import Optional
from fastapi import Header, HTTPException, status
from app.config import settings

log = logging.getLogger(__name__)

# RFC 7235 — informa ao cliente qual esquema de auth esperar
_WWW_AUTH = 'ApiKey realm="VDX Glass Engine"'


def validate_api_key(
    x_vdx_key: Optional[str] = Header(None, alias="X-VDX-Key"),
) -> None:
    """FastAPI dependency — valida X-VDX-Key com comparação timing-safe.

    Retorna 401 para qualquer falha de autenticação (ausente ou inválida).
    VDX não tem permissões granulares — auth é binária (chave válida ou não),
    portanto 403 Forbidden nunca é o código correto aqui.
    """
    if not x_vdx_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-VDX-Key header obrigatório",
            headers={"WWW-Authenticate": _WWW_AUTH},
        )
    master = settings.vdx_api_master_key
    if master and not hmac.compare_digest(x_vdx_key, master):
        log.warning("API key inválida recebida (primeiros 4 chars: %s...)", x_vdx_key[:4])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-VDX-Key inválida",
            headers={"WWW-Authenticate": _WWW_AUTH},
        )
