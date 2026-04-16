"""Configurações centralizadas do VDX Glass Engine.

Todas as variáveis de ambiente lidas em um único lugar.
Importar via: from app.config import settings
"""
from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

_log = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.parent

# Carrega variáveis do arquivo .env sem sobrescrever o que já está no ambiente
# (systemd Environment= tem prioridade; .env é fallback para vars não definidas)
_env_file = _ROOT / ".env"
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                if _k not in os.environ:
                    os.environ[_k] = _v


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in ("true", "1", "yes")


@dataclass
class Settings:
    """Configurações da aplicação lidas do ambiente (.env ou variáveis de sistema)."""

    # Auth
    vdx_api_master_key: str = field(
        default_factory=lambda: _env("VDX_API_MASTER_KEY", "")
    )

    # AI
    anthropic_api_key: str = field(
        default_factory=lambda: _env("ANTHROPIC_API_KEY", "")
    )

    # DB
    db_path: str = field(
        default_factory=lambda: _env("DB_PATH", str(_ROOT / "data" / "constitution.db"))
    )

    # Server
    host: str = field(default_factory=lambda: _env("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: _env_int("PORT", 8000))
    debug: bool = field(default_factory=lambda: _env_bool("VDX_DEBUG", False))

    # Upload / image generation
    app_upload_dir: str = field(
        default_factory=lambda: _env("APP_UPLOAD_DIR", str(_ROOT / "uploads"))
    )
    imagegen_venv_path: str = field(
        default_factory=lambda: _env(
            "IMAGEGEN_VENV_PATH",
            "/home/sw3innovation/vdx-imagegen/bin/python3",
        )
    )

    # CORS
    cors_origins: str = field(
        default_factory=lambda: _env(
            "CORS_ORIGINS",
            "https://vdx.sw3.tec.br,http://localhost:5173,http://localhost:3000",
        )
    )
    cors_allow_credentials: bool = field(
        default_factory=lambda: _env_bool("CORS_ALLOW_CREDENTIALS", True)
    )
    cors_allow_methods: str = field(
        default_factory=lambda: _env("CORS_ALLOW_METHODS", "GET,POST,OPTIONS")
    )
    cors_allow_headers: str = field(
        default_factory=lambda: _env(
            "CORS_ALLOW_HEADERS", "Content-Type,X-VDX-Key,Authorization"
        )
    )

    # Logging
    log_dir: str = field(
        default_factory=lambda: _env("LOG_DIR", str(_ROOT / "logs"))
    )

    # Request limits
    max_body_size_kb: int = field(
        default_factory=lambda: _env_int("MAX_BODY_SIZE_KB", 100)
    )

    # View token (JWT HS256 para viewer 3D em browser)
    view_token_secret: str = field(
        default_factory=lambda: _env("VDX_VIEW_TOKEN_SECRET", "")
    )
    view_token_ttl_seconds: int = field(
        default_factory=lambda: _env_int("VDX_VIEW_TOKEN_TTL_SECONDS", 3600)
    )
    view_token_max_ttl_seconds: int = field(
        default_factory=lambda: _env_int("VDX_VIEW_TOKEN_MAX_TTL_SECONDS", 86400)
    )

    def __post_init__(self) -> None:
        """Valida e completa configurações pós-inicialização."""
        if not self.view_token_secret:
            if self.vdx_api_master_key:
                # Produção sem segredo configurado — falha na inicialização
                raise ValueError(
                    "VDX_VIEW_TOKEN_SECRET deve ser definido em produção "
                    "(quando VDX_API_MASTER_KEY está configurado). "
                    "Gere com: python3 -c \"import secrets; print(secrets.token_hex(32))\""
                )
            # Dev: gera segredo efêmero com aviso
            ephemeral = secrets.token_hex(32)
            object.__setattr__(self, "view_token_secret", ephemeral)
            _log.warning(
                "VDX_VIEW_TOKEN_SECRET não configurado — usando segredo efêmero. "
                "View tokens não sobreviverão a reinicializações. "
                "Configure VDX_VIEW_TOKEN_SECRET para uso em produção."
            )

    @property
    def max_body_size_bytes(self) -> int:
        """Tamanho máximo do body de request em bytes."""
        return self.max_body_size_kb * 1024

    @property
    def anthropic_available(self) -> bool:
        """True se a chave Anthropic está configurada."""
        return bool(self.anthropic_api_key)

    @property
    def auth_required(self) -> bool:
        """True se auth está habilitada (VDX_API_MASTER_KEY configurada)."""
        return bool(self.vdx_api_master_key)


# Instância singleton — importar em todos os módulos que precisam de config
settings = Settings()
