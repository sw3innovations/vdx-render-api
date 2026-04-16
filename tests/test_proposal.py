"""
Testes Sprint 5 — Proposta Comercial PDF.

Cobre:
  - Funções utilitárias do serviço (_fmt_brl, _hex_rgb, _lighter, _gerar_numero)
  - Geração de PDF (validade %PDF-, multi-item, sem desenho, sem ferragens,
    white-label, logo base64, auto-number, condições, valor total, graceful)
  - Endpoints POST /api/v1/proposal e /api/v1/proposal/preview
  - Autenticação (sem key → 401, body vazio → 422)

Rode com: python -m pytest tests/test_proposal.py -v
"""
from __future__ import annotations

import asyncio
import base64
import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.constitution import init_db
from app.core.constitution_seed import seed as _seed
from app.models.proposal import (
    ClienteInfo,
    CondicoesPagamento,
    EmpresaInfo,
    ItemProposta,
    ProposalRequest,
)
from app.services.proposal_service import (
    _fmt_brl,
    _gerar_numero,
    _hex_rgb,
    _lighter,
    gerar_proposta,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def db_pronto():
    """Garante DB e seed antes dos testes."""
    init_db()
    _seed()


def _empresa(**kwargs) -> EmpresaInfo:
    defaults = {
        "nome": "Vidraçaria Teste",
        "telefone": "(85) 99999-0001",
        "email": "teste@vdx.tec.br",
        "cnpj": "12.345.678/0001-99",
        "cor_primaria": "#1a5276",
    }
    defaults.update(kwargs)
    return EmpresaInfo(**defaults)


def _cliente(**kwargs) -> ClienteInfo:
    defaults = {
        "nome": "João da Silva",
        "telefone": "(85) 98888-0001",
        "endereco": "Rua das Flores, 123",
    }
    defaults.update(kwargs)
    return ClienteInfo(**defaults)


def _item_porta(**kwargs) -> ItemProposta:
    defaults = {
        "descricao": "Porta Pivotante Simples",
        "tipologia": "porta_pivotante_simples",
        "largura": 900,
        "altura": 2100,
        "quantidade": 1,
        "espessura": 8,
        "valor_unitario": 1250.0,
        "valor_total": 1250.0,
    }
    defaults.update(kwargs)
    return ItemProposta(**defaults)


def _item_box(**kwargs) -> ItemProposta:
    defaults = {
        "descricao": "Box de Banheiro",
        "tipologia": "box_banheiro",
        "largura": 800,
        "altura": 1900,
        "quantidade": 2,
        "valor_unitario": 980.0,
        "valor_total": 1960.0,
    }
    defaults.update(kwargs)
    return ItemProposta(**defaults)


def _proposal(itens=None, **kwargs) -> ProposalRequest:
    return ProposalRequest(
        empresa=_empresa(),
        cliente=_cliente(),
        itens=itens or [_item_porta()],
        **kwargs,
    )


def _run(coro):
    return asyncio.run(coro)


# ── 1. Utilitários ────────────────────────────────────────────────────────────

class TestFmtBrl:
    def test_formato_basico(self):
        assert _fmt_brl(1250.0) == "R$ 1.250,00"

    def test_formato_sem_milhar(self):
        assert _fmt_brl(99.9) == "R$ 99,90"

    def test_formato_zero(self):
        assert _fmt_brl(0.0) == "R$ 0,00"

    def test_formato_none(self):
        assert _fmt_brl(None) == "-"

    def test_formato_milhar_duplo(self):
        s = _fmt_brl(1_234_567.89)
        assert "R$" in s
        assert "1.234.567,89" in s


class TestHexRgb:
    def test_azul_vdx(self):
        assert _hex_rgb("#1a5276") == (26, 82, 118)

    def test_vermelho(self):
        assert _hex_rgb("#ff0000") == (255, 0, 0)

    def test_fallback_invalido(self):
        r, g, b = _hex_rgb("INVALIDO")
        assert (r, g, b) == (26, 82, 118)

    def test_sem_hash(self):
        assert _hex_rgb("1a5276") == (26, 82, 118)


class TestLighter:
    def test_clareia_cor(self):
        r, g, b = _lighter((26, 82, 118), factor=0.85)
        assert r > 26 and g > 82 and b > 118

    def test_nao_passa_de_255(self):
        r, g, b = _lighter((255, 255, 255), factor=0.9)
        assert r <= 255 and g <= 255 and b <= 255


class TestGerarNumero:
    def test_usa_numero_fornecido(self):
        assert _gerar_numero("PROP-001") == "PROP-001"

    def test_gera_formato_vdx(self):
        n = _gerar_numero()
        assert n.startswith("VDX-")
        parts = n.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD

    def test_incremento_sequencial(self):
        n1 = _gerar_numero()
        n2 = _gerar_numero()
        seq1 = int(n1.split("-")[-1])
        seq2 = int(n2.split("-")[-1])
        assert seq2 > seq1


# ── 2. Geração de PDF ─────────────────────────────────────────────────────────

class TestGerarProposta:
    def test_retorna_bytes_pdf(self):
        """PDF deve começar com %PDF-."""
        pdf = _run(gerar_proposta(_proposal()))
        assert isinstance(pdf, bytes)
        assert pdf[:4] == b"%PDF"

    def test_multi_item(self):
        """Proposta com vários itens gera PDF válido."""
        req = _proposal(itens=[_item_porta(), _item_box(), _item_porta()])
        pdf = _run(gerar_proposta(req))
        assert pdf[:4] == b"%PDF"

    def test_sem_desenho(self):
        """incluir_desenho=False não quebra a geração."""
        req = _proposal(incluir_desenho=False)
        pdf = _run(gerar_proposta(req))
        assert pdf[:4] == b"%PDF"

    def test_sem_ferragens(self):
        """incluir_ferragens=False não quebra a geração."""
        req = _proposal(incluir_ferragens=False)
        pdf = _run(gerar_proposta(req))
        assert pdf[:4] == b"%PDF"

    def test_sem_desenho_e_sem_ferragens(self):
        """Ambos False ainda gera PDF válido."""
        req = _proposal(incluir_desenho=False, incluir_ferragens=False)
        pdf = _run(gerar_proposta(req))
        assert pdf[:4] == b"%PDF"

    def test_white_label_cor_personalizada(self):
        """Cor primária personalizada não quebra geração."""
        empresa = _empresa(cor_primaria="#e74c3c")
        req = ProposalRequest(
            empresa=empresa,
            cliente=_cliente(),
            itens=[_item_porta()],
            incluir_desenho=False,
        )
        pdf = _run(gerar_proposta(req))
        assert pdf[:4] == b"%PDF"

    def test_logo_base64(self):
        """Logo em base64 é inserida sem exceção (PNG 1×1 pixel)."""
        # PNG 1×1 pixel transparente em base64
        png_1x1 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQ"
            "VR42mP8/5+hHgAHggJ/PchI6QAAAABJRU5ErkJggg=="
        )
        empresa = _empresa(logo_base64=png_1x1)
        req = ProposalRequest(
            empresa=empresa,
            cliente=_cliente(),
            itens=[_item_porta()],
            incluir_desenho=False,
        )
        pdf = _run(gerar_proposta(req))
        assert pdf[:4] == b"%PDF"

    def test_validade_personalizada(self):
        """validade_dias=30 gera PDF sem erros."""
        req = _proposal(validade_dias=30, incluir_desenho=False)
        pdf = _run(gerar_proposta(req))
        assert pdf[:4] == b"%PDF"

    def test_numero_proposta_automatico(self):
        """numero_proposta=None → número gerado automaticamente."""
        req = _proposal(numero_proposta=None, incluir_desenho=False)
        pdf = _run(gerar_proposta(req))
        assert pdf[:4] == b"%PDF"

    def test_numero_proposta_customizado(self):
        """numero_proposta fornecido é preservado."""
        req = _proposal(numero_proposta="PROP-2024-001", incluir_desenho=False)
        pdf = _run(gerar_proposta(req))
        assert pdf[:4] == b"%PDF"

    def test_condicoes_pagamento(self):
        """Condições de pagamento com desconto e parcelas."""
        cond = CondicoesPagamento(forma="Cartão", desconto_percentual=5.0, parcelas=3)
        req = _proposal(condicoes=cond, incluir_desenho=False)
        pdf = _run(gerar_proposta(req))
        assert pdf[:4] == b"%PDF"

    def test_valor_total_calculado(self):
        """PDF tem tamanho razoável quando há valores preenchidos."""
        itens = [_item_porta(), _item_box()]
        req = _proposal(itens=itens, incluir_desenho=False)
        pdf = _run(gerar_proposta(req))
        assert len(pdf) > 1_000  # PDF não pode ser ínfimo

    def test_fabricante_informado(self):
        """Fabricante no item não quebra geração."""
        item = _item_porta(fabricante="HE")
        req = _proposal(itens=[item], incluir_desenho=False)
        pdf = _run(gerar_proposta(req))
        assert pdf[:4] == b"%PDF"

    def test_tipologia_invalida_graceful(self):
        """Tipologia inexistente não lança exceção — graceful degradation."""
        item = ItemProposta(
            descricao="Produto Inexistente",
            tipologia="tipologia_que_nao_existe_xyzabc",
            largura=900,
            altura=2000,
            quantidade=1,
        )
        req = ProposalRequest(
            empresa=_empresa(),
            cliente=_cliente(),
            itens=[item],
            incluir_desenho=True,
        )
        pdf = _run(gerar_proposta(req))
        assert pdf[:4] == b"%PDF"

    def test_observacoes_gerais(self):
        """Observações gerais são incluídas sem erro."""
        req = _proposal(
            observacoes_gerais="Entrega em 15 dias úteis. Instalação inclusa.",
            incluir_desenho=False,
        )
        pdf = _run(gerar_proposta(req))
        assert pdf[:4] == b"%PDF"


# ── 3. Endpoints HTTP ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


_HEADERS = {"X-VDX-Key": "test-key"}

_PAYLOAD = {
    "empresa": {
        "nome": "Vidraçaria Teste",
        "telefone": "(85) 99999-0001",
        "cor_primaria": "#1a5276",
    },
    "cliente": {"nome": "João da Silva"},
    "itens": [
        {
            "descricao": "Porta Pivotante Simples",
            "tipologia": "porta_pivotante_simples",
            "largura": 900,
            "altura": 2100,
            "quantidade": 1,
            "valor_unitario": 1250.0,
            "valor_total": 1250.0,
        }
    ],
    "incluir_desenho": False,
    "incluir_ferragens": False,
}


class TestProposalEndpoints:
    def test_gerar_proposta_200(self, client):
        """POST /api/v1/proposal deve retornar 200 e PDF válido."""
        resp = client.post("/api/v1/proposal", json=_PAYLOAD, headers=_HEADERS)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"

    def test_gerar_proposta_sem_auth_401(self, client):
        """Sem X-VDX-Key deve retornar 401."""
        resp = client.post("/api/v1/proposal", json=_PAYLOAD)
        assert resp.status_code == 401

    def test_gerar_proposta_body_vazio_422(self, client):
        """Body vazio deve retornar 422 (ValidationError)."""
        resp = client.post("/api/v1/proposal", json={}, headers=_HEADERS)
        assert resp.status_code == 422

    def test_preview_proposta_200(self, client):
        """POST /api/v1/proposal/preview deve retornar 200 e JSON de metadados."""
        resp = client.post("/api/v1/proposal/preview", json=_PAYLOAD, headers=_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "numero_proposta" in data
        assert "total_itens" in data
        assert data["total_itens"] == 1
        assert data["pdf_bytes"] == 0
        assert "validade_ate" in data

    def test_preview_sem_auth_401(self, client):
        """Preview sem X-VDX-Key deve retornar 401."""
        resp = client.post("/api/v1/proposal/preview", json=_PAYLOAD)
        assert resp.status_code == 401

    def test_preview_valor_total(self, client):
        """Preview deve somar valor_total dos itens."""
        payload = dict(_PAYLOAD)
        payload["itens"] = [
            {**_PAYLOAD["itens"][0], "valor_total": 1000.0},
            {
                "descricao": "Box de Banheiro",
                "tipologia": "box_banheiro",
                "largura": 800,
                "altura": 1900,
                "quantidade": 1,
                "valor_total": 500.0,
            },
        ]
        resp = client.post("/api/v1/proposal/preview", json=payload, headers=_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_itens"] == 2
        assert abs((data["valor_total"] or 0) - 1500.0) < 0.01
