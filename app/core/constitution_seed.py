"""
Seed da Constitution Vidros — conhecimento base de tipologias VDX.
Idempotente via ON CONFLICT — seguro rodar múltiplas vezes.
Assume que init_db() já rodou (chamado por main.py::startup_event, após init_db).
"""
import logging

from app.core.constitution import registrar, registrar_alias

log = logging.getLogger(__name__)


def seed():
    # Assume que init_db() já rodou — não chamar aqui.

    # ═══ TIPOLOGIAS ═══

    registrar("porta_pivotante_simples", tipo="tipologia", dados={
        "nome_display": "Porta Pivotante Simples",
        "classificacao_pecas": {
            "porta": "movel", "fixo": "fixa", "bandeira": "fixa",
            "painel": "fixa", "vidro fixo": "fixa"
        },
        "ferragens_por_peca": {
            "movel": [
                {"codigo": "1201", "nome": "Pivô Superior", "tipo": "pivo",
                 "y_formula": "altura - 50", "x_formula": "15",
                 "lado": "esquerdo", "visual": "circulo", "recorte": "padrao_sm"},
                {"codigo": "1013", "nome": "Pivô Inferior", "tipo": "pivo",
                 "y_formula": "50", "x_formula": "15",
                 "lado": "esquerdo", "visual": "circulo", "recorte": "padrao_sm"},
                {"codigo": "1520", "nome": "Fechadura Central", "tipo": "fechadura",
                 "y_formula": "altura * 0.50", "x_formula": "largura - 15",
                 "lado": "direito", "visual": "retangulo", "recorte": "padrao_sm"},
            ],
            "puxador_config": {
                "y_formula": "altura * 0.50",
                "x_formula": "largura - 35",
                "lado": "direito",
                "aceita_eixo": True,
                "default": {"codigo": "1502", "nome": "Puxador Barra", "visual": "barra"}
            }
        },
        "kit": {
            "codigo": "KIT_01", "nome": "Kit Porta Pivotante Simples V/A",
            "itens": [
                {"codigo": "1201", "nome": "Pivô superior", "qtd": 1},
                {"codigo": "1101", "nome": "Dobradiça superior", "qtd": 1},
                {"codigo": "1103", "nome": "Dobradiça inferior", "qtd": 1},
                {"codigo": "1013", "nome": "Pivô inferior", "qtd": 1},
                {"codigo": "1520", "nome": "Fechadura central", "qtd": 1},
            ],
            "puxador_separado": True
        },
        "normas": [
            {"nbr": "NBR 7199:2016", "regra": "Vidro segurança obrigatório abaixo 1100mm",
             "espessura_min_mm": 8, "espessura_rec_mm": 10}
        ]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("porta_pivotante_dupla_bandeira", tipo="tipologia", dados={
        "nome_display": "Porta Pivotante Dupla c/ Bandeira",
        "classificacao_pecas": {
            "porta": "movel", "porta 1": "movel", "porta 2": "movel",
            "bandeira": "fixa", "fixo": "fixa"
        },
        "ferragens_por_peca": {
            "movel": [
                {"codigo": "1201", "nome": "Pivô Superior", "tipo": "pivo",
                 "y_formula": "altura - 50", "x_formula": "15",
                 "lado": "esquerdo", "visual": "circulo", "recorte": "padrao_sm"},
                {"codigo": "1013", "nome": "Pivô Inferior", "tipo": "pivo",
                 "y_formula": "50", "x_formula": "15",
                 "lado": "esquerdo", "visual": "circulo", "recorte": "padrao_sm"},
                {"codigo": "1520", "nome": "Fechadura Central", "tipo": "fechadura",
                 "y_formula": "altura * 0.50", "x_formula": "largura - 15",
                 "lado": "direito", "visual": "retangulo", "recorte": "padrao_sm"},
            ],
            "puxador_config": {
                "y_formula": "altura * 0.50", "x_formula": "largura - 35",
                "lado": "direito", "aceita_eixo": True,
                "default": {"codigo": "1502", "nome": "Puxador Barra", "visual": "barra"}
            }
        },
        "kit": {
            "codigo": "KIT_02", "nome": "Kit Porta Pivotante Dupla c/ Bandeira",
            "itens": [
                {"codigo": "1201", "nome": "Pivô superior", "qtd": 2},
                {"codigo": "1101", "nome": "Dobradiça superior", "qtd": 2},
                {"codigo": "1103", "nome": "Dobradiça inferior", "qtd": 2},
                {"codigo": "1013", "nome": "Pivô inferior", "qtd": 2},
                {"codigo": "1520", "nome": "Fechadura central", "qtd": 1},
            ],
            "puxador_separado": True
        },
        "normas": [
            {"nbr": "NBR 7199:2016", "regra": "Vidro segurança obrigatório",
             "espessura_min_mm": 8, "espessura_rec_mm": 10}
        ]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("box_frontal_2_folhas", tipo="tipologia", dados={
        "nome_display": "Box Frontal 2 Folhas",
        "classificacao_pecas": {
            "porta": "movel", "fixo": "fixa"
        },
        "ferragens_por_peca": {
            "movel": [
                {"codigo": "1114", "nome": "Dobradiça Auto Superior", "tipo": "dobradica",
                 "y_formula": "altura - 50", "x_formula": "25",
                 "lado": "esquerdo", "visual": "retangulo", "recorte": "padrao_sm"},
                {"codigo": "1114", "nome": "Dobradiça Auto Inferior", "tipo": "dobradica",
                 "y_formula": "50", "x_formula": "25",
                 "lado": "esquerdo", "visual": "retangulo", "recorte": "padrao_sm"},
            ],
            "puxador_config": {
                "y_formula": "altura * 0.50", "x_formula": "largura - 40",
                "lado": "direito", "aceita_eixo": False,
                "default": {"codigo": "1504", "nome": "Puxador Botão", "visual": "circulo"}
            }
        },
        "kit": {
            "codigo": "KIT_05", "nome": "Kit Box Frontal 2 Folhas",
            "itens": [
                {"codigo": "1114", "nome": "Dobradiça automática", "qtd": 2},
                {"codigo": "1629B", "nome": "Bate-fecha", "qtd": 1},
            ],
            "puxador_separado": True
        },
        "normas": [
            {"nbr": "NBR 14207:2009", "regra": "Mínimo 8mm temperado",
             "espessura_min_mm": 8}
        ]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("box_canto_90", tipo="tipologia", dados={
        "nome_display": "Box Canto 90°",
        "classificacao_pecas": {
            "porta": "movel", "frontal": "movel", "lateral": "fixa",
            "fixo": "fixa", "lateral fixa": "fixa"
        },
        "ferragens_por_peca": {
            "movel": [
                {"codigo": "1114", "nome": "Dobradiça Auto Superior", "tipo": "dobradica",
                 "y_formula": "altura - 50", "x_formula": "25",
                 "lado": "esquerdo", "visual": "retangulo", "recorte": "padrao_sm"},
                {"codigo": "1114", "nome": "Dobradiça Auto Inferior", "tipo": "dobradica",
                 "y_formula": "50", "x_formula": "25",
                 "lado": "esquerdo", "visual": "retangulo", "recorte": "padrao_sm"},
            ],
            "puxador_config": {
                "y_formula": "altura * 0.50", "x_formula": "largura - 40",
                "lado": "direito", "aceita_eixo": False,
                "default": {"codigo": "1504", "nome": "Puxador Botão", "visual": "circulo"}
            }
        },
        "kit": {
            "codigo": "KIT_03", "nome": "Kit Box Canto 90°",
            "itens": [
                {"codigo": "1114", "nome": "Dobradiça automática", "qtd": 2},
                {"codigo": "1302", "nome": "Suporte de canto", "qtd": 2},
                {"codigo": "1629B", "nome": "Bate-fecha", "qtd": 1},
            ],
            "puxador_separado": True
        },
        "normas": [
            {"nbr": "NBR 14207:2009", "regra": "Mínimo 8mm temperado",
             "espessura_min_mm": 8}
        ]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("porta_correr_2_folhas", tipo="tipologia", dados={
        "nome_display": "Porta de Correr 2 Folhas",
        "classificacao_pecas": {
            "fixo": "fixa", "porta": "correr", "movel": "correr",
            "folha 1": "fixa", "folha 2": "correr"
        },
        "ferragens_por_peca": {
            "correr": [
                {"codigo": "3530", "nome": "Roldana", "tipo": "roldana",
                 "y_formula": "altura - 20", "x_formula": "50",
                 "lado": "esquerdo", "visual": "circulo", "recorte": "nenhum"},
                {"codigo": "3530", "nome": "Roldana", "tipo": "roldana",
                 "y_formula": "altura - 20", "x_formula": "largura - 50",
                 "lado": "direito", "visual": "circulo", "recorte": "nenhum"},
                {"codigo": "1629B", "nome": "Bate-fecha", "tipo": "bate_fecha",
                 "y_formula": "altura * 0.50", "x_formula": "0",
                 "lado": "esquerdo", "visual": "linha_h", "recorte": "nenhum"},
            ],
            "puxador_config": {
                "y_formula": "altura * 0.50", "x_formula": "largura / 2",
                "lado": "centro", "aceita_eixo": True
            }
        },
        "kit": {
            "codigo": "KIT_09", "nome": "Kit Porta Correr 2 Folhas",
            "itens": [
                {"codigo": "3530", "nome": "Roldana simples", "qtd": 2},
                {"codigo": "1629B", "nome": "Bate-fecha", "qtd": 1},
                {"codigo": "3534", "nome": "Trinco", "qtd": 1},
            ],
            "puxador_separado": True
        },
        "normas": [
            {"nbr": "NBR 7199:2016", "regra": "Vidro segurança obrigatório",
             "espessura_min_mm": 8, "espessura_rec_mm": 10}
        ]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("janela_correr_2_folhas", tipo="tipologia", dados={
        "nome_display": "Janela de Correr 2 Folhas",
        "classificacao_pecas": {
            "fixo": "fixa", "folha 1": "fixa", "folha fixa": "fixa",
            "porta": "correr", "movel": "correr", "folha 2": "correr", "folha movel": "correr"
        },
        "ferragens_por_peca": {
            "correr": [
                {"codigo": "1125", "nome": "Roldana Simples", "tipo": "roldana",
                 "y_formula": "altura - 20", "x_formula": "50",
                 "lado": "esquerdo", "visual": "circulo", "recorte": "nenhum"},
                {"codigo": "1125", "nome": "Roldana Simples", "tipo": "roldana",
                 "y_formula": "altura - 20", "x_formula": "largura - 50",
                 "lado": "direito", "visual": "circulo", "recorte": "nenhum"},
                {"codigo": "1629B", "nome": "Bate-fecha Janela", "tipo": "bate_fecha",
                 "y_formula": "altura * 0.50", "x_formula": "0",
                 "lado": "esquerdo", "visual": "linha_h", "recorte": "nenhum"},
            ],
            "puxador_config": None
        },
        "kit": {
            "codigo": "KIT_05V", "nome": "Kit Janela Correr 2 Folhas",
            "itens": [
                {"codigo": "1125", "nome": "Roldana simples", "qtd": 2},
                {"codigo": "1629B", "nome": "Bate-fecha janela", "qtd": 1},
                {"codigo": "1038", "nome": "Capuchinho", "qtd": 2},
            ],
            "puxador_separado": False
        },
        "normas": [
            {"nbr": "NBR 7199:2016", "espessura_min_mm": 6}
        ]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("janela_basculante", tipo="tipologia", dados={
        "nome_display": "Janela Basculante",
        "classificacao_pecas": {"folha": "movel", "basculante": "movel"},
        "ferragens_por_peca": {
            "movel": [
                {"codigo": "1335T", "nome": "Trinco Basculante", "tipo": "trinco",
                 "y_formula": "altura * 0.50", "x_formula": "largura / 2",
                 "lado": "centro", "visual": "retangulo", "recorte": "padrao_sm"},
                {"codigo": "1500", "nome": "Suporte Abertura", "tipo": "suporte",
                 "y_formula": "altura * 0.50", "x_formula": "150",
                 "lado": "esquerdo", "visual": "retangulo", "recorte": "nenhum"},
            ],
            "puxador_config": None
        },
        "kit": {
            "codigo": "KIT_06", "nome": "Kit Janela Basculante",
            "itens": [
                {"codigo": "1335T", "nome": "Trinco basculante", "qtd": 1},
                {"codigo": "1500", "nome": "Suporte de abertura", "qtd": 1},
            ],
            "puxador_separado": False
        },
        "normas": [{"nbr": "NBR 7199:2016", "espessura_min_mm": 6}]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("janela_maxim_ar", tipo="tipologia", dados={
        "nome_display": "Janela Maxim-Ar",
        "classificacao_pecas": {"folha": "movel", "maxim": "movel"},
        "ferragens_por_peca": {
            "movel": [
                {"codigo": "1500", "nome": "Braço Articulado", "tipo": "suporte",
                 "y_formula": "altura - 30", "x_formula": "largura * 0.30",
                 "lado": "esquerdo", "visual": "retangulo", "recorte": "nenhum"},
                {"codigo": "1500", "nome": "Braço Articulado", "tipo": "suporte",
                 "y_formula": "altura - 30", "x_formula": "largura * 0.70",
                 "lado": "direito", "visual": "retangulo", "recorte": "nenhum"},
                {"codigo": "1335T", "nome": "Trinco", "tipo": "trinco",
                 "y_formula": "altura * 0.50", "x_formula": "largura / 2",
                 "lado": "centro", "visual": "retangulo", "recorte": "padrao_sm"},
            ],
            "puxador_config": None
        },
        "kit": {
            "codigo": "KIT_07", "nome": "Kit Janela Maxim-Ar",
            "itens": [
                {"codigo": "1335T", "nome": "Trinco", "qtd": 1},
                {"codigo": "1500", "nome": "Braço articulado", "qtd": 2},
            ],
            "puxador_separado": False
        },
        "normas": [{"nbr": "NBR 7199:2016", "espessura_min_mm": 6}]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("janela_pivotante", tipo="tipologia", dados={
        "nome_display": "Janela Pivotante",
        "classificacao_pecas": {"folha": "movel", "pivotante": "movel"},
        "ferragens_por_peca": {
            "movel": [
                {"codigo": "1101", "nome": "Dobradiça Superior", "tipo": "dobradica",
                 "y_formula": "altura - 50", "x_formula": "15",
                 "lado": "esquerdo", "visual": "retangulo", "recorte": "padrao_sm"},
                {"codigo": "1103", "nome": "Dobradiça Inferior", "tipo": "dobradica",
                 "y_formula": "50", "x_formula": "15",
                 "lado": "esquerdo", "visual": "retangulo", "recorte": "padrao_sm"},
                {"codigo": "1520", "nome": "Fechadura", "tipo": "fechadura",
                 "y_formula": "altura * 0.50", "x_formula": "largura - 15",
                 "lado": "direito", "visual": "retangulo", "recorte": "padrao_sm"},
            ],
            "puxador_config": {
                "y_formula": "altura * 0.50", "x_formula": "largura - 35",
                "lado": "direito", "aceita_eixo": True
            }
        },
        "kit": {
            "codigo": "KIT_01J", "nome": "Kit Janela Pivotante",
            "itens": [
                {"codigo": "1101", "nome": "Dobradiça superior", "qtd": 1},
                {"codigo": "1103", "nome": "Dobradiça inferior", "qtd": 1},
                {"codigo": "1520", "nome": "Fechadura", "qtd": 1},
            ],
            "puxador_separado": True
        },
        "normas": [{"nbr": "NBR 7199:2016", "espessura_min_mm": 6}]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("guarda_corpo_linear", tipo="tipologia", dados={
        "nome_display": "Guarda-Corpo Linear",
        "classificacao_pecas": {"painel": "fixa", "fixo": "fixa", "vidro": "fixa"},
        "ferragens_por_peca": {},
        "puxador_config": None,
        "kit": {"codigo": "NENHUM", "nome": "Sem kit — fixação por coluna/base",
                "itens": [], "puxador_separado": False},
        "normas": [
            {"nbr": "NBR 14718:2019", "regra": "Altura min 1100mm, laminado obrigatório",
             "espessura_min_mm": 10, "tipo_obrigatorio": "laminado"}
        ]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("cobertura", tipo="tipologia", dados={
        "nome_display": "Cobertura / Claraboia",
        "classificacao_pecas": {"painel": "fixa", "fixo": "fixa", "vidro": "fixa"},
        "ferragens_por_peca": {},
        "puxador_config": None,
        "kit": {"codigo": "NENHUM", "nome": "Sem kit — apoio em perfis",
                "itens": [], "puxador_separado": False},
        "normas": [
            {"nbr": "NBR 7199:2016", "regra": "Temperado simples PROIBIDO, usar laminado",
             "tipo_proibido": "temperado", "espessura_min_mm": 8}
        ]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("divisoria_porta_pivotante", tipo="tipologia", dados={
        "nome_display": "Divisória com Porta Pivotante",
        "classificacao_pecas": {
            "porta": "movel", "painel": "fixa", "fixo": "fixa",
            "divisoria": "fixa", "vidro fixo": "fixa"
        },
        "ferragens_por_peca": {
            "movel": [
                {"codigo": "1201", "nome": "Pivô Superior", "tipo": "pivo",
                 "y_formula": "altura - 50", "x_formula": "15",
                 "lado": "esquerdo", "visual": "circulo", "recorte": "padrao_sm"},
                {"codigo": "1013", "nome": "Pivô Inferior", "tipo": "pivo",
                 "y_formula": "50", "x_formula": "15",
                 "lado": "esquerdo", "visual": "circulo", "recorte": "padrao_sm"},
                {"codigo": "1520", "nome": "Fechadura Central", "tipo": "fechadura",
                 "y_formula": "altura * 0.50", "x_formula": "largura - 15",
                 "lado": "direito", "visual": "retangulo", "recorte": "padrao_sm"},
            ],
            "puxador_config": {
                "y_formula": "altura * 0.50", "x_formula": "largura - 35",
                "lado": "direito", "aceita_eixo": True,
                "default": {"codigo": "1502", "nome": "Puxador Barra", "visual": "barra"}
            }
        },
        "kit": {
            "codigo": "KIT_01", "nome": "Kit Porta Pivotante (divisória)",
            "itens": [
                {"codigo": "1201", "nome": "Pivô superior", "qtd": 1},
                {"codigo": "1101", "nome": "Dobradiça superior", "qtd": 1},
                {"codigo": "1103", "nome": "Dobradiça inferior", "qtd": 1},
                {"codigo": "1013", "nome": "Pivô inferior", "qtd": 1},
                {"codigo": "1520", "nome": "Fechadura central", "qtd": 1},
            ],
            "puxador_separado": True
        },
        "normas": [{"nbr": "NBR 7199:2016", "espessura_min_mm": 8}]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("porta_correr_3_folhas", tipo="tipologia", dados={
        "nome_display": "Porta de Correr 3 Folhas",
        "classificacao_pecas": {
            "fixo": "fixa", "fixo 1": "fixa", "fixo 2": "fixa",
            "porta": "correr", "movel": "correr"
        },
        "ferragens_por_peca": {
            "correr": [
                {"codigo": "3530", "nome": "Roldana", "tipo": "roldana",
                 "y_formula": "altura - 20", "x_formula": "50",
                 "lado": "esquerdo", "visual": "circulo", "recorte": "nenhum"},
                {"codigo": "3530", "nome": "Roldana", "tipo": "roldana",
                 "y_formula": "altura - 20", "x_formula": "largura - 50",
                 "lado": "direito", "visual": "circulo", "recorte": "nenhum"},
                {"codigo": "1629B", "nome": "Bate-fecha", "tipo": "bate_fecha",
                 "y_formula": "altura * 0.50", "x_formula": "0",
                 "lado": "esquerdo", "visual": "linha_h", "recorte": "nenhum"},
            ],
            "puxador_config": {
                "y_formula": "altura * 0.50", "x_formula": "largura / 2",
                "lado": "centro", "aceita_eixo": True
            }
        },
        "kit": {
            "codigo": "KIT_10", "nome": "Kit Porta Correr 3 Folhas",
            "itens": [
                {"codigo": "3530", "nome": "Roldana simples", "qtd": 2},
                {"codigo": "1629B", "nome": "Bate-fecha", "qtd": 1},
                {"codigo": "3534", "nome": "Trinco", "qtd": 1},
            ],
            "puxador_separado": True
        },
        "normas": [
            {"nbr": "NBR 7199:2016", "espessura_min_mm": 8, "espessura_rec_mm": 10}
        ]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("box_de_giro", tipo="tipologia", dados={
        "nome_display": "Box de Giro",
        "classificacao_pecas": {
            "porta": "movel", "giro": "movel"
        },
        "ferragens_por_peca": {
            "movel": [
                {"codigo": "1201", "nome": "Pivô Superior", "tipo": "pivo",
                 "y_formula": "altura - 30", "x_formula": "largura / 2",
                 "lado": "centro", "visual": "circulo", "recorte": "nenhum"},
                {"codigo": "1013", "nome": "Pivô Inferior", "tipo": "pivo",
                 "y_formula": "30", "x_formula": "largura / 2",
                 "lado": "centro", "visual": "circulo", "recorte": "nenhum"},
            ],
            "puxador_config": {
                "y_formula": "altura * 0.50", "x_formula": "largura - 40",
                "lado": "direito", "aceita_eixo": False,
                "default": {"codigo": "1504", "nome": "Puxador Botão", "visual": "circulo"}
            }
        },
        "kit": {
            "codigo": "KIT_04", "nome": "Kit Box de Giro",
            "itens": [
                {"codigo": "1201", "nome": "Pivô superior", "qtd": 1},
                {"codigo": "1013", "nome": "Pivô inferior", "qtd": 1},
                {"codigo": "1629B", "nome": "Bate-fecha", "qtd": 1},
            ],
            "puxador_separado": True
        },
        "normas": [
            {"nbr": "NBR 14207:2009", "regra": "Mínimo 8mm temperado",
             "espessura_min_mm": 8}
        ]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("fechamento_de_sacada_6_folhas", tipo="tipologia", dados={
        "nome_display": "Fechamento de Sacada 6 Folhas",
        "classificacao_pecas": {
            "folha 1": "correr", "folha 2": "correr", "folha 3": "correr",
            "folha 4": "correr", "folha 5": "correr", "folha 6": "correr",
            "folha": "correr", "painel": "correr", "movel": "correr"
        },
        "ferragens_por_peca": {
            "correr": [
                {"codigo": "3530", "nome": "Roldana", "tipo": "roldana",
                 "y_formula": "altura - 20", "x_formula": "50",
                 "lado": "esquerdo", "visual": "circulo", "recorte": "nenhum"},
                {"codigo": "3530", "nome": "Roldana", "tipo": "roldana",
                 "y_formula": "altura - 20", "x_formula": "largura - 50",
                 "lado": "direito", "visual": "circulo", "recorte": "nenhum"},
            ],
            "puxador_config": {
                "y_formula": "altura * 0.50", "x_formula": "largura / 2",
                "lado": "centro", "aceita_eixo": True
            }
        },
        "kit": {
            "codigo": "KIT_11", "nome": "Kit Fechamento de Sacada 6 Folhas",
            "itens": [
                {"codigo": "3530", "nome": "Roldana simples", "qtd": 12},
                {"codigo": "1629B", "nome": "Bate-fecha", "qtd": 2},
                {"codigo": "3534", "nome": "Trinco", "qtd": 1},
            ],
            "puxador_separado": True
        },
        "normas": [
            {"nbr": "NBR 7199:2016", "regra": "Temperado mínimo 8mm, laminado recomendado em sacadas",
             "espessura_min_mm": 8, "espessura_rec_mm": 10}
        ]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("janela_quatro_folhas", tipo="tipologia", dados={
        "nome_display": "Janela Quatro Folhas",
        "classificacao_pecas": {
            "folha 1": "fixa", "folha fixa 1": "fixa",
            "folha 2": "fixa", "folha fixa 2": "fixa",
            "folha 3": "correr", "folha 4": "correr",
            "folha movel": "correr", "movel": "correr", "correr": "correr"
        },
        "ferragens_por_peca": {
            "correr": [
                {"codigo": "1125", "nome": "Roldana Simples", "tipo": "roldana",
                 "y_formula": "altura - 20", "x_formula": "50",
                 "lado": "esquerdo", "visual": "circulo", "recorte": "nenhum"},
                {"codigo": "1125", "nome": "Roldana Simples", "tipo": "roldana",
                 "y_formula": "altura - 20", "x_formula": "largura - 50",
                 "lado": "direito", "visual": "circulo", "recorte": "nenhum"},
                {"codigo": "1629B", "nome": "Bate-fecha Janela", "tipo": "bate_fecha",
                 "y_formula": "altura * 0.50", "x_formula": "0",
                 "lado": "esquerdo", "visual": "linha_h", "recorte": "nenhum"},
            ],
            "puxador_config": None
        },
        "kit": {
            "codigo": "KIT_05V4", "nome": "Kit Janela Quatro Folhas",
            "itens": [
                {"codigo": "1125", "nome": "Roldana simples", "qtd": 4},
                {"codigo": "1629B", "nome": "Bate-fecha janela", "qtd": 2},
                {"codigo": "1038", "nome": "Capuchinho", "qtd": 4},
            ],
            "puxador_separado": False
        },
        "normas": [
            {"nbr": "NBR 7199:2016", "espessura_min_mm": 6}
        ]
    }, origem="catalogo_glasspecas", confianca=1.0)

    registrar("janela_correr_2_folhas_oriun_plus", tipo="tipologia", dados={
        "nome_display": "Janela Duas Folhas Sistema Oriun Plus",
        "classificacao_pecas": {
            "fixo": "fixa", "folha 1": "fixa", "folha fixa": "fixa",
            "porta": "correr", "movel": "correr", "folha 2": "correr", "folha movel": "correr"
        },
        "ferragens_por_peca": {
            "correr": [
                {"codigo": "1125", "nome": "Roldana Simples", "tipo": "roldana",
                 "y_formula": "altura - 20", "x_formula": "50",
                 "lado": "esquerdo", "visual": "circulo", "recorte": "nenhum"},
                {"codigo": "1125", "nome": "Roldana Simples", "tipo": "roldana",
                 "y_formula": "altura - 20", "x_formula": "largura - 50",
                 "lado": "direito", "visual": "circulo", "recorte": "nenhum"},
                {"codigo": "1629B", "nome": "Bate-fecha Janela", "tipo": "bate_fecha",
                 "y_formula": "altura * 0.50", "x_formula": "0",
                 "lado": "esquerdo", "visual": "linha_h", "recorte": "nenhum"},
            ],
            "puxador_config": None
        },
        "kit": {
            "codigo": "KIT_05V_ORIUN", "nome": "Kit Janela Correr 2 Folhas Oriun Plus",
            "itens": [
                {"codigo": "1125", "nome": "Roldana simples", "qtd": 2},
                {"codigo": "1629B", "nome": "Bate-fecha janela", "qtd": 1},
                {"codigo": "1038", "nome": "Capuchinho", "qtd": 2},
            ],
            "puxador_separado": False
        },
        "normas": [{"nbr": "NBR 7199:2016", "espessura_min_mm": 6}]
    }, origem="catalogo_glasspecas", confianca=1.0)

    # Porta de abrir — mesmas ferragens que porta pivotante simples
    registrar("porta_abrir", tipo="tipologia", dados={
        "nome_display": "Porta de Abrir",
        "classificacao_pecas": {
            "porta": "movel", "folha": "movel", "fixo": "fixa"
        },
        "ferragens_por_peca": {
            "movel": [
                {"codigo": "1101", "nome": "Dobradiça Superior", "tipo": "dobradica",
                 "y_formula": "altura - 50", "x_formula": "15",
                 "lado": "esquerdo", "visual": "retangulo", "recorte": "padrao_sm"},
                {"codigo": "1103", "nome": "Dobradiça Inferior", "tipo": "dobradica",
                 "y_formula": "50", "x_formula": "15",
                 "lado": "esquerdo", "visual": "retangulo", "recorte": "padrao_sm"},
                {"codigo": "1520", "nome": "Fechadura Central", "tipo": "fechadura",
                 "y_formula": "altura * 0.50", "x_formula": "largura - 15",
                 "lado": "direito", "visual": "retangulo", "recorte": "padrao_sm"},
            ],
            "puxador_config": {
                "y_formula": "altura * 0.50", "x_formula": "largura - 35",
                "lado": "direito", "aceita_eixo": True
            }
        },
        "kit": {
            "codigo": "KIT_01", "nome": "Kit Porta de Abrir",
            "itens": [
                {"codigo": "1101", "nome": "Dobradiça superior", "qtd": 1},
                {"codigo": "1103", "nome": "Dobradiça inferior", "qtd": 1},
                {"codigo": "1520", "nome": "Fechadura central", "qtd": 1},
            ],
            "puxador_separado": True
        },
        "normas": [
            {"nbr": "NBR 7199:2016", "espessura_min_mm": 8, "espessura_rec_mm": 10}
        ]
    }, origem="catalogo_glasspecas", confianca=1.0)

    # Vitrine — painel fixo comercial sem ferragens ativas
    registrar("vitrine", tipo="tipologia", dados={
        "nome_display": "Vitrine",
        "classificacao_pecas": {
            "painel": "fixa", "vidro": "fixa", "fixo": "fixa", "porta": "movel"
        },
        "ferragens_por_peca": {
            "movel": [
                {"codigo": "1101", "nome": "Dobradiça Superior", "tipo": "dobradica",
                 "y_formula": "altura - 50", "x_formula": "15",
                 "lado": "esquerdo", "visual": "retangulo", "recorte": "padrao_sm"},
                {"codigo": "1103", "nome": "Dobradiça Inferior", "tipo": "dobradica",
                 "y_formula": "50", "x_formula": "15",
                 "lado": "esquerdo", "visual": "retangulo", "recorte": "padrao_sm"},
                {"codigo": "1520", "nome": "Fechadura Central", "tipo": "fechadura",
                 "y_formula": "altura * 0.50", "x_formula": "largura - 15",
                 "lado": "direito", "visual": "retangulo", "recorte": "padrao_sm"},
            ],
        },
        "kit": {
            "codigo": "NENHUM", "nome": "Sem kit padrão — configuração sob medida",
            "itens": [], "puxador_separado": True
        },
        "normas": [
            {"nbr": "NBR 7199:2016", "espessura_min_mm": 8}
        ]
    }, origem="catalogo_glasspecas", confianca=1.0)

    # ═══ ALIASES ═══
    aliases_tipologia = {
        "porta_pivotante_simples": ["porta_pivotante", "pivotante_simples", "porta_de_vidro_pivotante"],
        "porta_pivotante_dupla_bandeira": ["pivotante_dupla", "dupla_bandeira", "porta_dupla_bandeira"],
        "box_frontal_2_folhas": ["box_frontal", "box_2_folhas", "box_de_banheiro", "box_banheiro"],
        "box_canto_90": ["box_canto", "box_em_l", "canto_90", "box_l"],
        "porta_correr_2_folhas": ["porta_correr", "porta_de_correr", "correr_2_folhas"],
        "janela_correr_2_folhas": ["janela_correr", "janela_2_folhas", "janela_duas_folhas", "janela_dupla_correr"],
        "janela_basculante": ["basculante", "janela_basculante_vidro"],
        "janela_maxim_ar": ["maxim_ar", "maximar", "janela_maxim", "janela_maxim_ar"],
        "janela_pivotante": ["janela_pivot", "janela_pivotante_vidro"],
        "guarda_corpo_linear": ["guarda_corpo", "guarda_corpo_reto", "guarda_corpo_vidro"],
        "cobertura": ["claraboia", "telhado_vidro", "cobertura_vidro", "marquise"],
        "divisoria_porta_pivotante": ["divisoria", "divisoria_porta", "divisoria_vidro"],
        "porta_correr_3_folhas": ["porta_tres_folhas", "porta_3_folhas", "porta_correr_3",
                                   "correr_3_folhas", "porta_tres_folhas_correr"],
        "box_de_giro": ["box_giro", "box_pivotante", "box_pivot", "giro"],
        "fechamento_de_sacada_6_folhas": ["sacada_6_folhas", "fechamento_sacada", "sacada_seis_folhas",
                                          "fechamento_6_folhas", "sacada"],
        "janela_quatro_folhas": ["janela_4_folhas", "janela_correr_4_folhas", "janela_4",
                                 "janela_quatro", "janela_correr_4"],
        "janela_correr_2_folhas_oriun_plus": ["janela_duas_folhas_sistema_oriun_plus",
                                               "janela_oriun_plus", "janela_oriun", "oriun_plus",
                                               "janela_duas_folhas_oriun"],
        "porta_pivotante_dupla_bandeira": ["porta_pivoltante_dupla", "pivoltante",
                                           "porta_+_bandeira_superior", "porta_bandeira_superior",
                                           "porta_bandeira", "porta_mais_bandeira_superior"],
        "box_frontal_2_folhas": ["box_de_banheiro"],
        "janela_basculante": ["janela_basculante_simples"],
        "porta_correr_3_folhas": ["porta_tres_folhas"],
        "porta_abrir": ["porta_abrir", "porta_de_abrir", "abrir", "porta_vai_vem",
                        "vai_vem", "porta_vaivem"],
        "vitrine": ["vitrine", "vitrina", "frente_de_loja", "fachada_loja"],
    }
    for canonical, alias_list in aliases_tipologia.items():
        registrar_alias(canonical, canonical, "tipologia")
        for alias in alias_list:
            registrar_alias(alias, canonical, "tipologia")

    aliases_peca = {
        "fixa": ["fixo", "fixo_1", "fixo_2", "vidro_fixo", "lateral_fixa",
                 "folha_fixa", "bandeira", "painel", "lateral"],
        "movel": ["porta", "folha_movel", "pivotante", "basculante",
                  "maxim_ar", "folha_2", "movel"],
        "correr": ["folha_de_correr", "correr", "deslizante"],
    }
    for canonical, alias_list in aliases_peca.items():
        for alias in alias_list:
            registrar_alias(alias, canonical, "classificacao_peca")

    # ═══ FERRAGENS — seed mínimo para testes (CI / fresh DB) ═════════════════
    from app.core.constitution import _get_conn
    _conn = _get_conn()
    _conn.executemany(
        "INSERT OR IGNORE INTO fabricantes (id, nome, prefixo) VALUES (?, ?, ?)",
        [
            ("HE", "HELA",       "HE"),
            ("SM", "Glasspecas", "SM"),
        ],
    )
    _conn.executemany(
        "INSERT OR IGNORE INTO ferragens"
        " (codigo, codigo_normalizado, fabricante_id, nome, tipo, material,"
        "  dimensoes_json, espessura_vidro, confianca, fonte)"
        " VALUES (?, ?, ?, ?, ?, ?, '{}', '[]', 1.0, 'seed')",
        [
            ("AL1629A", "1629", "HE", "Puxador HE 1629A",  "puxador",  "Alumínio"),
            ("SM1101",  "1101", "SM", "Dobradiça SM 1101", "dobradica","Aço Inox"),
            ("SM1201",  "1201", "SM", "Pivô SM 1201",      "pivo",     "Aço Inox"),
        ],
    )
    _conn.commit()
    _conn.close()

    log.info("Seed completo. Entries e aliases registrados.")


if __name__ == "__main__":
    seed()
