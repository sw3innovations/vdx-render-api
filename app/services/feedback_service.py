"""
Serviço de feedback do vidraceiro.
Aplica correções manuais à Constitution com confiança máxima (1.0).
"""
import logging
from app.core import constitution
from app.models.feedback import FeedbackRequest, FeedbackResponse

log = logging.getLogger(__name__)


def processar(req: FeedbackRequest) -> FeedbackResponse:
    """
    Aplica a correção do vidraceiro na Constitution.
    Localiza a ferragem pelo nome dentro da classificação da peça e atualiza a fórmula.
    """
    entry = constitution.buscar(req.tipologia_chave, tipo="tipologia")
    if not entry:
        return FeedbackResponse(
            aceito=False,
            mensagem=f"Tipologia '{req.tipologia_chave}' não encontrada na Constitution.",
            tipologia_chave=req.tipologia_chave,
            ferragem_nome=req.ferragem_nome,
            campo_corrigido=req.campo_corrigido,
            valor_novo=req.valor_correto,
        )

    dados = entry["dados"]
    ferragens_por_peca = dados.get("ferragens_por_peca", {})
    lista_ferragens = ferragens_por_peca.get(req.peca_classificacao)

    if not isinstance(lista_ferragens, list):
        return FeedbackResponse(
            aceito=False,
            mensagem=(
                f"Classificação '{req.peca_classificacao}' não encontrada "
                f"em ferragens_por_peca para '{req.tipologia_chave}'."
            ),
            tipologia_chave=req.tipologia_chave,
            ferragem_nome=req.ferragem_nome,
            campo_corrigido=req.campo_corrigido,
            valor_novo=req.valor_correto,
        )

    valor_anterior = None
    atualizado = False

    for ferragem in lista_ferragens:
        if ferragem.get("nome", "").lower() == req.ferragem_nome.lower():
            valor_anterior = ferragem.get(req.campo_corrigido)
            ferragem[req.campo_corrigido] = req.valor_correto
            atualizado = True
            # Atualiza todos com o mesmo nome (ex: Roldana aparece 2×)
            # não fazemos break para corrigir todas as ocorrências

    if not atualizado:
        return FeedbackResponse(
            aceito=False,
            mensagem=(
                f"Ferragem '{req.ferragem_nome}' não encontrada em "
                f"'{req.peca_classificacao}' de '{req.tipologia_chave}'."
            ),
            tipologia_chave=req.tipologia_chave,
            ferragem_nome=req.ferragem_nome,
            campo_corrigido=req.campo_corrigido,
            valor_novo=req.valor_correto,
        )

    # Persiste com confiança 1.0 (feedback humano = verdade)
    constitution.registrar(
        req.tipologia_chave, dados, tipo="tipologia",
        origem="feedback_vidraceiro", confianca=1.0,
    )
    constitution.registrar_validacao(
        req.tipologia_chave, "feedback_vidraceiro", "corrigido",
        correcoes=f"{req.campo_corrigido}: '{valor_anterior}' → '{req.valor_correto}' "
                  f"(ferragem: {req.ferragem_nome}, peca: {req.peca_classificacao})",
        validado_por="vidraceiro",
    )

    log.info(
        f"Feedback aplicado: '{req.tipologia_chave}' / '{req.ferragem_nome}' / "
        f"{req.campo_corrigido}: '{valor_anterior}' → '{req.valor_correto}'"
    )

    return FeedbackResponse(
        aceito=True,
        mensagem="Correção aplicada com sucesso. Constitution atualizada.",
        tipologia_chave=req.tipologia_chave,
        ferragem_nome=req.ferragem_nome,
        campo_corrigido=req.campo_corrigido,
        valor_anterior=str(valor_anterior) if valor_anterior is not None else None,
        valor_novo=req.valor_correto,
    )
