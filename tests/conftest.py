"""Fixtures compartilhadas para os testes do VDX Glass Engine."""
import asyncio
import pytest

from app.core.constitution import init_db
from app.core.constitution_seed import seed
from app.models.render import PecaInput, RenderRequest
from app.services.render_orchestrator import executar


# ── Ambiente de teste ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _force_test_env(monkeypatch):
    """Força modo dev em runtime: master_key vazia aceita qualquer X-VDX-Key.

    Evita que o .env de produção (VDX_API_MASTER_KEY=vdx-render-prod-2026)
    invalide os headers hardcoded test-key nos testes de proposal e view_token.
    Também garante view_token_secret estável para testes de encode/decode.
    """
    from app.config import settings
    monkeypatch.setattr(settings, "vdx_api_master_key", "", raising=False)
    monkeypatch.setattr(
        settings,
        "view_token_secret",
        "test-secret-32chars-xxxxxxxxxx",
        raising=False,
    )


# ── DB ────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def db_ready():
    """Inicializa o banco e popula com o seed antes de qualquer teste."""
    init_db()
    seed()


# ── Request helpers ───────────────────────────────────────────────────────────

@pytest.fixture
def porta_simples_request() -> RenderRequest:
    """RenderRequest mínimo para porta_pivotante_simples 900×2100."""
    return RenderRequest(
        tipologia_nome="porta_pivotante_simples",
        pecas=[PecaInput(nome="Porta", largura_mm=900, altura_mm=2100)],
    )


@pytest.fixture
def box_banheiro_request() -> RenderRequest:
    """RenderRequest para box_banheiro com fixo + porta."""
    return RenderRequest(
        tipologia_nome="box_banheiro",
        pecas=[
            PecaInput(nome="Fixo", largura_mm=300, altura_mm=1900),
            PecaInput(nome="Porta", largura_mm=700, altura_mm=1900),
        ],
    )


# ── Render helpers ────────────────────────────────────────────────────────────

@pytest.fixture
def render_porta_simples(porta_simples_request):
    """RenderResponse pronto para porta_pivotante_simples."""
    return asyncio.run(executar(porta_simples_request))
