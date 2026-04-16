"""Modelo de resposta de erro padronizado para todos os endpoints da API."""
from typing import Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Envelope de erro retornado em todas as respostas de erro da API."""

    error: str          # código máquina: "not_found", "unauthorized", "internal_error"
    message: str        # mensagem legível para humanos
    detail: Optional[dict] = None  # contexto adicional opcional


def status_to_code(status: int) -> str:
    """Converte HTTP status code para código máquina de erro."""
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_error",
        503: "service_unavailable",
    }.get(status, f"error_{status}")
