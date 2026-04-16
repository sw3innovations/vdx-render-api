"""
Validador ABNT para vidro temperado.
Extraído de app/routers/render.py — fonte única de verdade para checks normativos.

Normas cobertas:
  NBR 7199:2016  — vidros na construção civil (geral)
  NBR 14207:2009 — boxes de banheiro
  NBR 14718:2019 — guarda-corpos
  NBR 16259:2014 — sacadas e varandas

Consulta folgas_nbr da Constitution DB (não usa valores hardcoded).
Se uma folga não for encontrada no DB, usa fallback seguro e loga warning.
"""
import logging
from typing import Optional

log = logging.getLogger(__name__)

# Fallbacks seguros caso o DB não tenha o tipo de folga
_FOLGAS_FALLBACK: dict[str, float] = {
    "movel_fixo":      3.0,
    "movel_movel":     4.0,
    "movel_piso":      8.0,
    "fixo_fixo":       1.0,
    "movel_alvenaria": 5.0,
}


class ABNTValidator:
    """Valida conformidade de peças de vidraçaria com normas ABNT brasileiras."""

    def __init__(self):
        # Import lazy para evitar circular dependency — constitution importa aqui,
        # não no module level, para que o validator possa ser instanciado antes do DB
        from app.core.constitution import todas_folgas_nbr
        try:
            self._folgas = todas_folgas_nbr()
        except Exception as e:
            log.warning(f"ABNTValidator: falha ao carregar folgas do DB: {e} — usando fallback")
            self._folgas = {}

    def folga(self, tipo: str) -> float:
        """Retorna folga NBR em mm. Busca no DB, fallback para valor seguro."""
        val = self._folgas.get(tipo)
        if val is not None:
            return val
        val = _FOLGAS_FALLBACK.get(tipo)
        if val is not None:
            log.warning(f"ABNTValidator: folga '{tipo}' não no DB — usando fallback {val}mm")
            return val
        log.warning(f"ABNTValidator: folga '{tipo}' desconhecida — usando 3mm como mínimo seguro")
        return 3.0

    def verificar(
        self,
        tipologia_nome: str,
        skill_chave: str,
        espessura_vidro_mm: Optional[float],
        tipo_vidro: Optional[str],
        alturas_pecas: list[float] | None = None,
    ) -> list[dict]:
        """
        Verifica conformidade com normas ABNT.

        Retorna lista de alertas:
            [{"nivel": "CRITICO|ALERTA|INFO", "norma": "NBR XXXX:YYYY", "mensagem": "..."}]

        Parâmetros:
            tipologia_nome  — nome da tipologia (pode conter palavras como "porta", "box")
            skill_chave     — chave canônica (ex: "porta_pivotante_simples")
            espessura_vidro_mm — espessura em mm ou None
            tipo_vidro      — "temperado"|"laminado"|"aramado"|"comum" ou None
            alturas_pecas   — lista de alturas de peças em mm (para guarda-corpo)
        """
        alertas: list[dict] = []
        tip = (tipologia_nome or "").lower().strip()
        esp = espessura_vidro_mm
        tv = (tipo_vidro or "").strip().lower()
        alturas = alturas_pecas or []

        def _a(nivel: str, norma: str, msg: str):
            alertas.append({"nivel": nivel, "norma": norma, "mensagem": msg})

        # ── PORTA (pivotante, de abrir, de correr) ────────────────────────────
        eh_porta = any(k in tip for k in ("porta", "pivotante", "correr_porta", "abrir"))
        if eh_porta:
            if tv == "comum":
                _a("CRITICO", "NBR 7199:2016",
                   "Porta: vidro comum PROIBIDO. Use temperado ou laminado.")
            if esp is not None:
                if esp < 8:
                    _a("CRITICO", "NBR 7199:2016",
                       f"Porta: espessura {esp:.0f}mm insuficiente. Mínimo 8mm (recomendado 10mm).")
                elif esp < 10:
                    _a("ALERTA", "NBR 7199:2016",
                       f"Porta: espessura {esp:.0f}mm abaixo do recomendado de 10mm.")

        # ── BOX DE BANHEIRO ───────────────────────────────────────────────────
        eh_box = any(k in tip for k in ("box", "banheiro"))
        if eh_box:
            if tv == "comum":
                _a("CRITICO", "NBR 14207:2009",
                   "Box banheiro: vidro comum PROIBIDO. Obrigatório temperado ou laminado.")
            if esp is not None and esp < 8:
                nivel = "CRITICO" if esp < 6 else "ALERTA"
                _a(nivel, "NBR 14207:2009",
                   f"Box banheiro: espessura {esp:.0f}mm — mínimo 8mm temperado. "
                   "4mm permitido apenas encaixilhado ≤700×2000mm.")

        # ── JANELA ────────────────────────────────────────────────────────────
        eh_janela = "janela" in tip
        if eh_janela:
            if esp is not None and esp < 6:
                _a("ALERTA", "NBR 7199:2016",
                   f"Janela: espessura {esp:.0f}mm — recomendado mínimo 6mm temperado.")
            if esp is not None and esp <= 4:
                _a("ALERTA", "NBR 7199:2016",
                   "Janela 4mm: permitido apenas encaixilhado nos 4 cantos e acima de 1100mm do piso.")

        # ── GUARDA-CORPO ──────────────────────────────────────────────────────
        eh_gc = ("guarda_corpo" in skill_chave
                 or any(k in tip for k in ("guarda_corpo", "guarda corpo", "guarda-corpo")))
        if eh_gc:
            altura_min_gc = 1100.0
            for alt in alturas:
                if alt < altura_min_gc:
                    _a("CRITICO", "NBR 14718:2019",
                       f"Peça {alt:.0f}mm abaixo do mínimo de {altura_min_gc:.0f}mm "
                       "exigido para guarda-corpo.")
            if tv and tv != "laminado":
                _a("CRITICO", "NBR 14718:2019 + NBR 7199:2016",
                   f"Guarda-corpo: vidro '{tv}' PROIBIDO. Obrigatório vidro LAMINADO.")
            elif not tv:
                _a("INFO", "NBR 14718:2019",
                   "Guarda-corpo: confirme que o vidro é LAMINADO (temperado simples é proibido).")
            if esp is not None and esp < 10:
                _a("ALERTA", "NBR 14718:2019",
                   f"Guarda-corpo: espessura {esp:.0f}mm — recomendado mínimo 10mm laminado.")

        # ── COBERTURA / CLARABOIA ─────────────────────────────────────────────
        eh_cob = any(k in tip for k in ("cobertura", "claraboia", "telhado", "marquise"))
        if eh_cob:
            if tv not in ("laminado", "aramado"):
                nivel = "CRITICO" if tv in ("temperado", "comum") else "INFO"
                _a(nivel, "NBR 7199:2016",
                   "Cobertura/claraboia: vidro temperado simples PROIBIDO. "
                   "Obrigatório laminado ou aramado.")
            if esp is not None and esp < 8:
                _a("ALERTA", "NBR 7199:2016",
                   f"Cobertura: espessura {esp:.0f}mm — recomendado mínimo 8mm laminado.")

        # ── SACADA / VARANDA ──────────────────────────────────────────────────
        eh_sacada = any(k in tip for k in ("sacada", "varanda", "fechamento_varanda"))
        if eh_sacada:
            if tv == "comum":
                _a("CRITICO", "NBR 16259:2014",
                   "Sacada/varanda: vidro de segurança OBRIGATÓRIO. Vidro comum PROIBIDO.")
            if esp is not None and esp < 8:
                _a("ALERTA", "NBR 16259:2014",
                   f"Sacada/varanda: espessura {esp:.0f}mm — recomendado mínimo 8mm.")

        # ── DIVISÓRIA / BIOMBO ────────────────────────────────────────────────
        eh_div = any(k in tip for k in ("divisoria", "divisória", "biombo"))
        if eh_div:
            if tv == "comum":
                _a("ALERTA", "NBR 7199:2016",
                   "Divisória abaixo de 1100mm: vidro de segurança obrigatório.")
            if esp is not None and esp < 8:
                _a("ALERTA", "NBR 7199:2016",
                   f"Divisória: espessura {esp:.0f}mm — recomendado mínimo 8mm temperado.")

        # ── Espessura 4mm em aplicações críticas ──────────────────────────────
        if esp is not None and esp <= 4:
            apps_criticas = ("porta", "guarda_corpo", "cobertura", "sacada", "varanda", "marquise")
            if any(k in tip or k in skill_chave for k in apps_criticas):
                _a("CRITICO", "NBR 7199:2016",
                   f"Vidro 4mm PROIBIDO para '{tipologia_nome or 'esta aplicação'}'. "
                   "Permitido apenas em janelas encaixilhadas ou box encaixilhado ≤700×2000mm.")

        return alertas
