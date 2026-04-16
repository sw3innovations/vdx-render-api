"""VDX Glass Engine — Entrypoint FastAPI.

Configura a aplicação, middlewares, rate limiting e registra todos os routers.
Lifespan: init_db() → seed() garante que o banco está pronto antes do primeiro request.
"""
import logging
import os
import time
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from slowapi.errors import RateLimitExceeded

from app import __version__
from app.config import settings
from app.core.limiter import limiter
from app.models.error import ErrorResponse, status_to_code
from app.routers import render, chat, feedback, preview, tipologia_image, tipologia_sync, export, viewer_3d, proposal
from app.core.constitution import init_db
from app.core.constitution_seed import seed as _constitution_seed

load_dotenv()


# ─── Logging setup ────────────────────────────────────────────────────────────

def _setup_logging() -> None:
    """Configura logging com stdout + RotatingFileHandler (10 MB, 5 backups)."""
    os.makedirs(settings.log_dir, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Evitar handlers duplicados se init_db() recarregar o módulo
    if not root.handlers:
        stdout_h = logging.StreamHandler()
        stdout_h.setFormatter(fmt)
        root.addHandler(stdout_h)

    file_h = RotatingFileHandler(
        os.path.join(settings.log_dir, "vdx.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_h.setFormatter(fmt)
    root.addHandler(file_h)

    access_h = RotatingFileHandler(
        os.path.join(settings.log_dir, "access.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    access_h.setFormatter(fmt)
    logging.getLogger("vdx.access").addHandler(access_h)
    logging.getLogger("vdx.access").propagate = False


log = logging.getLogger(__name__)
_access_log = logging.getLogger("vdx.access")


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia startup e shutdown da aplicação."""
    _setup_logging()
    log.info("VDX Glass Engine v%s starting...", __version__)
    init_db()
    _constitution_seed()
    app.state.start_time = time.time()
    log.info("VDX Glass Engine ready")
    yield
    log.info("VDX Glass Engine shutting down...")


# ─── OpenAPI metadata ─────────────────────────────────────────────────────────

_TAGS_METADATA = [
    {"name": "render",          "description": "Geração de desenhos técnicos SVG de peças de vidraçaria"},
    {"name": "export",          "description": "Conversão de SVG para PNG, PDF e thumbnail"},
    {"name": "3d",              "description": "Viewer 3D interativo (Three.js) e Scene JSON"},
    {"name": "preview",         "description": "Previews SVG animados de tipologias cadastradas"},
    {"name": "tipologia-image", "description": "Imagens fotorrealistas de tipologias via Stable Diffusion"},
    {"name": "tipologia-sync",  "description": "Sincronização e descoberta de tipologias via Claude"},
    {"name": "feedback",        "description": "Correções de fórmulas de posicionamento pelo vidraceiro"},
    {"name": "chat",            "description": "Consultor técnico via Claude + Constitution"},
    {"name": "proposal",        "description": "Geração de proposta comercial em PDF white-label"},
    {"name": "infra",           "description": "Health check e métricas operacionais"},
]


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="VDX Glass Engine",
    description="Motor de inteligência visual para vidraçaria. Gera desenhos técnicos SVG, PNG, PDF e visualização 3D interativa.",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=_TAGS_METADATA,
    lifespan=lifespan,
)

app.state.limiter = limiter


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Rate limit excedido — retorna 429 no envelope padrão {error, message}."""
    response = JSONResponse(
        status_code=429,
        content=ErrorResponse(
            error="rate_limit_exceeded",
            message=f"Rate limit excedido: {exc.detail}",
        ).model_dump(),
    )
    response = request.app.state.limiter._inject_headers(
        response, request.state.view_rate_limit
    )
    return response


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods.split(","),
    allow_headers=settings.cors_allow_headers.split(","),
)

app.include_router(render.router)
app.include_router(chat.router)
app.include_router(feedback.router)
app.include_router(preview.router)
app.include_router(tipologia_image.router)
app.include_router(tipologia_sync.router)
app.include_router(export.router)
app.include_router(viewer_3d.router)
app.include_router(proposal.router)


# ─── Middlewares ──────────────────────────────────────────────────────────────

@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Injeta security headers em todas as respostas."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Loga método, path, status e latência de cada request."""
    t0 = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - t0) * 1000
    _access_log.info("%s %s → %d (%.0fms)", request.method, request.url.path, response.status_code, ms)
    return response


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    """Rejeita requests com body maior que settings.max_body_size_bytes (padrão: 100KB)."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_body_size_bytes:
        return JSONResponse(
            status_code=413,
            content=ErrorResponse(
                error="payload_too_large",
                message=f"Request body excede o limite de {settings.max_body_size_kb}KB",
            ).model_dump(),
        )
    return await call_next(request)


# ─── Exception handlers ───────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Formata HTTPException no envelope padrão {error, message}."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=status_to_code(exc.status_code),
            message=str(exc.detail),
        ).model_dump(),
        headers=exc.headers,  # preserva WWW-Authenticate e outros headers customizados
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formata erros de validação Pydantic no envelope padrão."""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="validation_error",
            message="Dados de entrada inválidos",
            detail={"errors": exc.errors()},
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Captura exceções não tratadas e retorna 500 no envelope padrão."""
    log.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_error",
            message="Erro interno do servidor",
        ).model_dump(),
    )


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["infra"])
def health() -> dict:
    """Health check básico — verifica DB e retorna versão da API."""
    from app.core.constitution import _get_conn
    try:
        conn = _get_conn()
        db_entries = conn.execute("SELECT COUNT(*) FROM constitution_entries").fetchone()[0]
        conn.close()
        db_status = "ok"
    except Exception as e:
        db_entries = 0
        db_status = f"erro: {e}"

    return {
        "status": "ok",
        "versao": __version__,
        "api": "VDX Glass Engine",
        "db": {"status": db_status, "entries": db_entries},
    }


@app.get("/health/detailed", tags=["infra"])
def health_detailed() -> dict:
    """Health check detalhado com métricas de DB, dependências e sistema."""
    from app.core.constitution import _get_conn
    from app.core.auth import validate_api_key  # noqa: imported but checked below

    # DB metrics
    try:
        conn = _get_conn()
        db_entries  = conn.execute("SELECT COUNT(*) FROM constitution_entries").fetchone()[0]
        db_ferragens = conn.execute("SELECT COUNT(*) FROM ferragens").fetchone()[0]
        db_kits     = conn.execute("SELECT COUNT(*) FROM kits").fetchone()[0]
        db_aliases  = conn.execute("SELECT COUNT(*) FROM constitution_aliases").fetchone()[0]
        conn.close()
        db_size = os.path.getsize(settings.db_path) if os.path.exists(settings.db_path) else 0
        db_status = "ok"
    except Exception as e:
        db_entries = db_ferragens = db_kits = db_aliases = db_size = 0
        db_status = f"erro: {e}"

    # Dependency checks
    def _dep(mod: str) -> str:
        try:
            __import__(mod)
            return "ok"
        except ImportError:
            return "missing"

    # System metrics (opcional — requer psutil)
    system: dict = {}
    try:
        import psutil
        vm = psutil.virtual_memory()
        system = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": round(vm.percent, 1),
            "disk_free_gb": round(psutil.disk_usage("/").free / (1024 ** 3), 1),
        }
    except ImportError:
        system = {"note": "psutil não instalado — adicionar ao requirements.txt para métricas de sistema"}

    uptime = round(time.time() - getattr(app.state, "start_time", time.time()), 1)

    return {
        "status": "healthy",
        "versao": __version__,
        "uptime_seconds": uptime,
        "db": {
            "status": db_status,
            "entries": db_entries,
            "ferragens": db_ferragens,
            "kits": db_kits,
            "aliases": db_aliases,
            "size_bytes": db_size,
        },
        "dependencies": {
            "cairosvg": _dep("cairosvg"),
            "pillow":   _dep("PIL"),
            "fpdf2":    _dep("fpdf"),
            "anthropic": _dep("anthropic"),
        },
        "system": system,
    }
