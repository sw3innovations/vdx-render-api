"""View token — JWT HS256 mínimo (stdlib pura, zero dependências externas).

Emitido por POST /api/v1/3d/viewer/token (requer X-VDX-Key).
Aceito por GET /api/v1/3d/viewer?t=<token> (sem header — funciona em browser,
WhatsApp, iframe e e-mail).

Claims no payload:
    typ  — "view" (identifica o propósito do token)
    tip  — tipologia_nome
    w    — largura_mm
    h    — altura_mm
    cv   — cor_vidro
    fab  — fabricante (pode ser None)
    esp  — espessura_mm
    iat  — issued-at (epoch)
    exp  — expires-at (epoch)
    jti  — UUID único (permite auditoria futura)

Segurança:
    - Assinatura HMAC-SHA256 — qualquer alteração de payload invalida o token
    - Timing-safe via hmac.compare_digest
    - Dimensões e tipologia ficam na assinatura — receptor não pode forjar parâmetros
"""
import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from typing import Optional


# ─── Exceções ─────────────────────────────────────────────────────────────────

class ViewTokenError(Exception):
    """Base para erros de view token."""

class ViewTokenExpiredError(ViewTokenError):
    """Token expirado."""

class ViewTokenInvalidError(ViewTokenError):
    """Token malformado, assinatura inválida ou tipo errado."""


# ─── Claims ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ViewTokenClaims:
    tip: str
    w: float
    h: float
    cv: str
    fab: Optional[str]
    esp: float
    iat: int
    exp: int
    jti: str


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _sign(header_b64: str, payload_b64: str, secret: str) -> str:
    msg = f"{header_b64}.{payload_b64}".encode()
    return _b64url_encode(hmac.new(secret.encode(), msg, hashlib.sha256).digest())


# ─── API pública ──────────────────────────────────────────────────────────────

def encode(claims: ViewTokenClaims, secret: str) -> str:
    """Serializa e assina as claims, retornando o token JWT HS256."""
    header = _b64url_encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    payload = _b64url_encode(
        json.dumps(
            {
                "typ": "view",
                "tip": claims.tip,
                "w":   claims.w,
                "h":   claims.h,
                "cv":  claims.cv,
                "fab": claims.fab,
                "esp": claims.esp,
                "iat": claims.iat,
                "exp": claims.exp,
                "jti": claims.jti,
            },
            separators=(",", ":"),
        ).encode()
    )
    sig = _sign(header, payload, secret)
    return f"{header}.{payload}.{sig}"


def decode(token: str, secret: str) -> ViewTokenClaims:
    """Valida assinatura, expiração e tipo. Retorna ViewTokenClaims ou levanta ViewTokenError."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ViewTokenInvalidError("Formato inválido — esperado header.payload.sig")

    header_b64, payload_b64, sig_b64 = parts

    # Verificação timing-safe da assinatura
    expected = _sign(header_b64, payload_b64, secret)
    if not hmac.compare_digest(sig_b64, expected):
        raise ViewTokenInvalidError("Assinatura inválida")

    # Decodificar payload
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as exc:
        raise ViewTokenInvalidError(f"Payload inválido: {exc}") from exc

    # Verificar propósito
    if payload.get("typ") != "view":
        raise ViewTokenInvalidError(f"Tipo de token inválido: {payload.get('typ')!r}")

    # Verificar expiração
    if int(payload.get("exp", 0)) < int(time.time()):
        raise ViewTokenExpiredError("Token expirado")

    # Montar dataclass (falha se campo obrigatório ausente ou tipo errado)
    try:
        return ViewTokenClaims(
            tip=str(payload["tip"]),
            w=float(payload["w"]),
            h=float(payload["h"]),
            cv=str(payload.get("cv", "default")),
            fab=payload.get("fab"),
            esp=float(payload.get("esp", 8.0)),
            iat=int(payload["iat"]),
            exp=int(payload["exp"]),
            jti=str(payload["jti"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ViewTokenInvalidError(f"Claims inválidas: {exc}") from exc


def new_claims(
    tip: str,
    w: float,
    h: float,
    cv: str,
    fab: Optional[str],
    esp: float,
    ttl_seconds: int,
) -> ViewTokenClaims:
    """Cria ViewTokenClaims com iat/exp/jti preenchidos automaticamente."""
    now = int(time.time())
    return ViewTokenClaims(
        tip=tip,
        w=w,
        h=h,
        cv=cv,
        fab=fab,
        esp=esp,
        iat=now,
        exp=now + ttl_seconds,
        jti=str(uuid.uuid4()),
    )
