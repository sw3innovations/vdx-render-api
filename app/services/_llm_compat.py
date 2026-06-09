"""
Camada de compatibilidade Anthropic → OpenAI.
Mantém a API .messages.create() esperada pelos serviços existentes.

NOTA: settings.anthropic_api_key armazena uma key OpenAI (sk-proj-...).
O nome do campo foi mantido para não quebrar os consumidores.
"""
from openai import OpenAI
from openai import APIError  # re-exportar para consumidores que capturam APIError

MODEL_MAP = {
    "claude-sonnet-4-6": "gpt-4o",
    "claude-3-5-sonnet-20241022": "gpt-4o",
    "claude-3-5-sonnet": "gpt-4o",
    "claude-haiku-4-5-20251001": "gpt-4o-mini",
    "claude-3-haiku-20240307": "gpt-4o-mini",
    "claude-3-haiku": "gpt-4o-mini",
}
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class _CompatTextBlock:
    def __init__(self, text: str):
        self.text = text
        self.type = "text"


class _CompatUsage:
    def __init__(self, prompt_tokens: int, completion_tokens: int):
        self.input_tokens = prompt_tokens
        self.output_tokens = completion_tokens


class _CompatMessage:
    def __init__(self, openai_resp):
        choice = openai_resp.choices[0]
        text = choice.message.content or ""
        self.content = [_CompatTextBlock(text)]
        self.stop_reason = choice.finish_reason
        self.role = "assistant"
        self.id = openai_resp.id
        self.model = openai_resp.model
        self.type = "message"
        if openai_resp.usage:
            self.usage = _CompatUsage(
                openai_resp.usage.prompt_tokens,
                openai_resp.usage.completion_tokens,
            )
        else:
            self.usage = _CompatUsage(0, 0)


class _MessagesEndpoint:
    def __init__(self, client: OpenAI):
        self._client = client

    def create(self, *, model: str, max_tokens: int = 1024,
               messages: list, system: str | None = None,
               temperature: float | None = None, **kwargs):
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        openai_messages.extend(messages)
        openai_model = MODEL_MAP.get(model, DEFAULT_OPENAI_MODEL)
        params: dict = {
            "model": openai_model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            params["temperature"] = temperature
        resp = self._client.chat.completions.create(**params)
        return _CompatMessage(resp)


class _CompatClient:
    """Drop-in replacement do Anthropic() client."""
    def __init__(self, api_key: str | None = None):
        from app.config import settings
        key = api_key or settings.anthropic_api_key
        _openai = OpenAI(api_key=key)
        self.messages = _MessagesEndpoint(_openai)


def get_compat_client(api_key: str | None = None) -> _CompatClient:
    """Constrói o client compatível. Use no lugar de Anthropic()."""
    return _CompatClient(api_key=api_key)
