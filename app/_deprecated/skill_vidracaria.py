"""
VDX Glass Skill — Base de conhecimento técnico de vidraçaria brasileira.

Fontes primárias:
- Glasspeças Catálogo Linha Santa Marina, edição 2017 (ferragens para vidro temperado)
- HELA Catálogo "Soluções em Acessórios para Vidro Temperado" — Fechaduras Hela de
  Friburgo Ferragens Ltda, Nova Friburgo/RJ (linhas Polímero e Zamac)
- AL Indústria Catálogo "Sua Obra Merece" — primeira empresa a injetar ferragens em
  polímero no mundo (fundada 2003). Linha Tradicional (AL-XXXX) e Linha CAPA (CAPA-XXXX)

Normas aplicáveis:
- NBR 7199:2016  — Vidros em edificações: requisitos e procedimentos
- NBR 14207:2009 — Divisórias e box de vidro
- NBR 14718:2019 — Guarda-corpos para edificações
- NBR 16259:2014 — Janelas e portas com vidro temperado
- NBR 16835:2025 — Ferragens para vidros temperados (nova norma ABNT)

Estrutura de cada tipologia no dict SKILL:
  - norma              : norma ABNT aplicável
  - espessura_minima_mm: espessura mínima de vidro conforme norma
  - kit_referencia     : chave do kit oficial em KITS_OFICIAIS (quando aplicável)
  - ferragens_por_peca : dict {nome_peca: [lista de ferragens]}
  - observacoes        : notas técnicas de instalação

Posicionamento:
  Todas as posições posicao_y_mm são medidas DA BASE da peça para cima.
  distancia_borda_mm = distância da borda lateral esquerda/ativa.
"""

from typing import Dict, List, Any

# ─────────────────────────────────────────────────────────────────────────────
# CATÁLOGO DE PRODUTOS
#   SM-XXXX : Linha Santa Marina (Glasspeças 2017)
#   HE-XXXX : Linha HELA Polímero/Zamac (Catálogo HELA, Nova Friburgo/RJ)
# ─────────────────────────────────────────────────────────────────────────────
# Campos:
#   nome           : denominação completa conforme catálogo
#   dimensoes_mm   : (comprimento, largura[, profundidade]) da ferragem
#   pino_mm        : diâmetro do pino de articulação
#   max_vao_mm     : (largura_max, altura_max) do vão aplicável
#   espessura_vidro_mm : espessura mínima de vidro compatível
#   material       : composição do produto
#   recorte        : dict com medidas de recorte/furo no vidro
#   formula_posicao_x: expressão para calcular posição X (basculantes)
#   obs            : observação técnica específica do produto

CATALOGO_PRODUTOS: Dict[str, Any] = {

    # ─── DOBRADIÇAS PIVOTANTES (Linha Santa Marina) ───────────────────────────
    "SM-1101":    {"nome": "Dobradiça Superior Pivotante 1101",
                   "dimensoes_mm": (130, 50), "pino_mm": 8,
                   "max_vao_mm": (1000, 2200), "material": "Latão/Zamac",
                   "recorte": {"furo_mm": 25, "dist_borda_mm": 107, "dist_base_mm": 25}},

    "SM-1101PGA": {"nome": "Dobradiça Superior Reforçada 4F Alumínio 1101PGA",
                   "dimensoes_mm": (135, 90), "pino_mm": 8,
                   "max_vao_mm": (1400, 3000), "material": "Alumínio",
                   "recorte": {"furo_mm": 20, "dist_borda_mm": 115, "dist_base_mm": 30}},

    "SM-1101R":   {"nome": "Dobradiça Superior Reforçada 3F 1101R",
                   "dimensoes_mm": (200, 60), "pino_mm": 8,
                   "max_vao_mm": (1200, 2800), "material": "Aço/Zamac",
                   "obs": "Porta >1200mm: deslocar dobradiça"},

    "SM-1103":    {"nome": "Dobradiça Inferior Pivotante 1103",
                   "dimensoes_mm": (150, 55), "pino_mm": 8,
                   "max_vao_mm": (1000, 2200), "material": "Latão/Zamac",
                   "recorte": {"furo_mm": 25, "dist_borda_mm": 125, "dist_base_mm": 25}},

    "SM-1103PGA": {"nome": "Dobradiça Inferior Reforçada 4F Alumínio 1103PGA",
                   "dimensoes_mm": (145, 90),
                   "max_vao_mm": (1400, 3000), "material": "Alumínio"},

    "SM-1103RM":  {"nome": "Dobradiça Inferior Reforçada 3F 1103RM",
                   "dimensoes_mm": (200, 60),
                   "max_vao_mm": (1200, 2800)},

    # ─── BOX ──────────────────────────────────────────────────────────────────
    "SM-1114":    {"nome": "Dobradiça Automática Box 1114",
                   "dimensoes_mm": (115, 100, 50), "pino_mm": 8,
                   "max_vao_mm": (600, 1900), "espessura_vidro_mm": 8,
                   "material": "Latão/Zamac",
                   "recorte": {"furos_mm": 20, "espacamento_mm": 50,
                               "dist_topo_mm": 25, "dist_borda_mm": 25, "total_mm": 300}},

    "SM-1114BG":  {"nome": "Dobradiça Automática Box 1114BG",
                   "dimensoes_mm": (80, 85, 50),
                   "max_vao_mm": (600, 1900), "espessura_vidro_mm": 8,
                   "material": "Zamac"},

    "SM-1115":    {"nome": "Dobradiça sem Caimento Box 1115",
                   "dimensoes_mm": (100, 115, 50),
                   "max_vao_mm": (600, 1900), "espessura_vidro_mm": 8},

    "SM-1118":    {"nome": "Dobradiça de Batente V/A 1118",
                   "dimensoes_mm": (95, 50, 50),
                   "max_vao_mm": (800, 2100), "material": "Latão/Zamac",
                   "recorte": {"furo_mm": 18, "dist_borda_mm": 25, "espacamento_mm": 50}},

    "SM-1118D":   {"nome": "Dobradiça de Batente V/V 1118D",
                   "dimensoes_mm": (95, 50, 50),
                   "max_vao_mm": (800, 2100), "material": "Latão/Zamac"},

    "SM-1119G":   {"nome": "Dobradiça de Batente V/V com Mola 1119G",
                   "dimensoes_mm": (80, 50),
                   "max_vao_mm": (650, 1900), "material": "Zamac"},

    "SM-1120G":   {"nome": "Dobradiça Batente V/A c/ Mola Cavalete Central 1120G",
                   "dimensoes_mm": (84, 80, 50),
                   "max_vao_mm": (650, 1900), "material": "Zamac"},

    "SM-1121G":   {"nome": "Dobradiça Batente V/A c/ Mola Cavalete Deslocado 1121G",
                   "dimensoes_mm": (84, 80, 50),
                   "max_vao_mm": (650, 1900), "material": "Zamac"},

    # ─── JANELA BASCULANTE ────────────────────────────────────────────────────
    "SM-1123":    {"nome": "Dobradiça Vidro Basculante 1123",
                   "dimensoes_mm": (60, 50), "pino_mm": 8,
                   "max_vao_mm": (800, 700), "material": "Latão/Zamac",
                   "formula_posicao_x": "(48000/A)+B"},

    "SM-1123A":   {"nome": "Dobradiça Basculante com Trinco 1123A",
                   "dimensoes_mm": (60, 50),
                   "max_vao_mm": (800, 700)},

    "SM-1230":    {"nome": "Dobradiça para Basculante 1230",
                   "max_vao_mm": (800, 700)},

    "SM-1231":    {"nome": "Dobradiça para Basculante Grande 1231",
                   "max_vao_mm": (1000, 800)},

    "SM-1007":    {"nome": "Dobradiça c/ Freio Basculante/Pivotante V/A 1007",
                   "dimensoes_mm": (65, 100), "furo_mm": 38,
                   "max_vao_mm": (1000, 800)},

    "SM-1007A":   {"nome": "Dobradiça c/ Freio Basculante/Pivotante V/A 1007A",
                   "dimensoes_mm": (65, 65), "furo_mm": 38,
                   "max_vao_mm": (800, 700)},

    "SM-1008":    {"nome": "Dobradiça c/ Freio Basculante/Pivotante V/V 1008",
                   "dimensoes_mm": (100, 120),
                   "max_vao_mm": (1000, 800)},

    "SM-1008A":   {"nome": "Dobradiça c/ Freio Basculante/Pivotante V/V 1008A",
                   "dimensoes_mm": (65, 120),
                   "max_vao_mm": (800, 700)},

    # ─── ROLDANAS / CARRINHOS ─────────────────────────────────────────────────
    "SM-1125":    {"nome": "Roldana Simples Box/Correr 1125", "furo_mm": 15,
                   "max_vao_mm": (800, 2100),
                   "recorte": {"furo_mm": 15, "dist_borda_mm": 50, "dist_base_mm": 20}},

    "SM-1125D":   {"nome": "Roldana Dupla Janela Correr 1125D",
                   "max_vao_mm": (1300, 2100)},

    "SM-1126":    {"nome": "Carrinho Porta Correr Rolamento 1126",
                   "dimensoes_mm": (60, 85), "max_vao_mm": (600, 1800), "espessura_vidro_mm": 8,
                   "recorte": {"furo_mm": 20, "dist_borda_mm": 25, "espacamento_mm": 50}},

    "SM-1126D":   {"nome": "Carrinho Duplo Porta Correr 1126D",
                   "dimensoes_mm": (100, 85), "max_vao_mm": (700, 2100)},

    "SM-1126DCR": {"nome": "Carrinho Duplo Côncavo Reforçado 1126DCR",
                   "max_vao_mm": (900, 2700), "material": "Aço Carbono"},

    # ─── TRINCOS E FECHADURAS ─────────────────────────────────────────────────
    "SM-1335G":   {"nome": "Trinco sem Miolo 1335G",
                   "recorte_borda_mm": 15},

    "SM-1335":    {"nome": "Trinco sem Miolo 1335",
                   "recorte_borda_mm": 15},

    "SM-1520G":   {"nome": "Fechadura Central 1520G"},

    "SM-1520MAG": {"nome": "Fechadura Central 1520 (com chave)"},

    "SM-1531G":   {"nome": "Contra Fechadura 1531G"},

    "SM-1504AG":  {"nome": "Puxador Botão 1504AG"},

    "SM-1523G":   {"nome": "Trinco Basculante 1523G"},

    # ─── PIVÔS ────────────────────────────────────────────────────────────────
    "SM-1201SG":  {"nome": "Bucha/Pivot Superior 1201SG", "furo_mm": 8},

    "SM-1013SG":  {"nome": "Pivot Inferior 1013SG (para 1103 Sul)", "furo_mm": 6},

    "SM-1013G":   {"nome": "Pivot Inferior 1013G (para 1103, 1103PGA, 1100I, 1103RM, 112F)",
                   "furo_mm": 6},

    "SM-1014G":   {"nome": "Pivot para Dobradiças Inferiores 1014G "
                            "(1103S, 1108, 1109, 1112, 1113)"},

    # ─── CAPUCHINHOS / BATENTES ───────────────────────────────────────────────
    "SM-1038G":   {"nome": "Capuchinho p/ Trinco furo 10mm 1038G",
                   "dimensoes_mm": (22, 18, 15)},

    "SM-1038BG":  {"nome": "Capuchinho p/ Trinco 1335 Trilho Exposto 1038BG",
                   "dimensoes_mm": (50, 22, 15)},

    "SM-1302":    {"nome": "Suporte de Canto 1302"},

    "SM-1629BG":  {"nome": "Bate Fecha V/A 1629BG"},

    "SM-1629A":   {"nome": "Bate Fecha 1629A"},

    "SM-1629JG":  {"nome": "Bate Fecha Janela Correr 1629JG"},

    # ─── SUPORTES SANFONADA ───────────────────────────────────────────────────
    "SM-1124":    {"nome": "Suporte Superior c/ Rodízio Porta Sanfonada 1124",
                   "max_vao_mm": (400, 2100)},

    "SM-1127":    {"nome": "Suporte Central Porta Sanfonada Rodízio Duplo 1127",
                   "max_vao_mm": (700, 2000)},

    "SM-1127A":   {"nome": "Suporte Central Inferior c/ Pino Sanfonada 1127A"},

    # ─── HELA — Linha Polímero e Zamac (Fechaduras Hela de Friburgo Ferragens) ──
    # Fonte: Catálogo "Soluções em Acessórios para Vidro Temperado" (Nova Friburgo/RJ)

    # Dobradiças pivotantes HELA
    "HE-1101A":  {"nome": "Dobradiça Superior Pivotante s/ Pino Inox 1101A",
                  "material": "Polímero/Zamac",
                  "obs": "Equivalente HELA da SM-1101. Encaixe superior sem pino solto."},

    "HE-1103A":  {"nome": "Dobradiça Inferior Pivotante s/ Pino Inox 1103A",
                  "material": "Polímero/Zamac",
                  "obs": "Equivalente HELA da SM-1103. Encaixe inferior sem pino solto."},

    "HE-1201A":  {"nome": "Bucha/Pivot Superior 1201A",
                  "material": "Polímero",
                  "obs": "Pivot superior polímero — equivalente ao SM-1201SG."},

    "HE-1201F":  {"nome": "Bucha/Pivot Superior 1201F",
                  "material": "Polímero reforçado",
                  "obs": "Versão reforçada do pivot superior 1201A."},

    "HE-1013F":  {"nome": "Pivot Inferior 1013F",
                  "material": "Polímero/metal",
                  "obs": "Pivot inferior HELA — equivalente ao SM-1013G."},

    "HE-1504A":  {"nome": "Puxador Botão 1504A",
                  "material": "Polímero",
                  "obs": "Equivalente HELA do SM-1504AG."},

    # Dobradiça automática box HELA
    "HE-1114":   {"nome": "Dobradiça Automática Box 1114",
                  "max_vao_mm": (600, 1900), "espessura_vidro_mm": 8,
                  "material": "Polímero/Zamac",
                  "obs": "Equivalente HELA da SM-1114. Fechamento automático por gravidade."},

    # Trincos e fechaduras HELA
    "HE-1335":   {"nome": "Trinco sem Miolo 1335",
                  "recorte_borda_mm": 15,
                  "material": "Polímero/Zamac",
                  "obs": "Equivalente HELA da SM-1335G."},

    "HE-1520":   {"nome": "Fechadura Porta de Bater 1520",
                  "material": "Polímero/Zamac",
                  "obs": "Equivalente HELA da SM-1520G. Linha polímero."},

    "HE-1520WC": {"nome": "Fechadura Porta de Bater WC 1520WC",
                  "material": "Polímero/Zamac",
                  "obs": "Versão banheiro (WC) da HE-1520, trava interna."},

    "HE-1531":   {"nome": "Contra Fechadura 1531",
                  "material": "Polímero/Zamac",
                  "obs": "Equivalente HELA da SM-1531G."},

    "HE-1523":   {"nome": "Trinco Central Basculante 1523",
                  "recorte_borda_mm": 15,
                  "material": "Polímero/Zamac",
                  "obs": "Equivalente HELA da SM-1523G."},

    "HE-3530":   {"nome": "Fechadura Porta Correr V/V 3530",
                  "material": "Polímero/Zamac",
                  "obs": "Fechadura embutida para portas de correr vidro/vidro."},

    "HE-3532":   {"nome": "Fechadura Janela de Correr 3532",
                  "material": "Polímero/Zamac",
                  "obs": "Fechadura embutida para janelas de correr."},

    # Puxadores HELA
    "HE-1629A":  {"nome": "Bate Fecha / Puxador 1629A",
                  "material": "Polímero",
                  "obs": "Equivalente HELA do SM-1629BG. Serve como bate-fecha em box de abrir."},

    "HE-1629JA": {"nome": "Bate Fecha Janela Correr 1629JA",
                  "material": "Polímero",
                  "obs": "Equivalente HELA do SM-1629JG para janelas de correr."},

    # Suportes HELA
    "HE-1302":   {"nome": "Suporte de Canto 1302",
                  "material": "Polímero/Zamac",
                  "obs": "Equivalente HELA do SM-1302. Une folhas em 90°."},

    "HE-1329":   {"nome": "Suporte de Centro 1329",
                  "material": "Polímero/Zamac",
                  "obs": "Suporte central para painéis intermediários."},

    "HE-1130":   {"nome": "Suporte Basculante/Pivotante 1130",
                  "material": "Polímero/Zamac",
                  "obs": "Suporte lateral para janelas basculantes e pivotantes HELA."},

    "HE-1231":   {"nome": "Suporte c/ Ponto de Giro 1231",
                  "material": "Polímero/Zamac",
                  "obs": "Suporte com eixo de giro para basculantes de vão maior."},

    "HE-1230":   {"nome": "Dobradiça Basculante 1230",
                  "material": "Polímero/Zamac",
                  "obs": "Equivalente HELA da SM-1230. Kit basculante pequeno V/A."},

    # Haste maxim-ar HELA
    "HE-1587":   {"nome": "Haste Maxim-ar 1587",
                  "material": "Metal",
                  "obs": "Haste articulada para controle de abertura maxim-ar."},

    "HE-1132":   {"nome": "Dobradiça Maxim-ar V/V 1132",
                  "material": "Polímero/Zamac",
                  "obs": "Dobradiça para sistemas maxim-ar vidro/vidro. Kit 16 HELA."},

    # Capuchinhos / batentes HELA
    "HE-1038":   {"nome": "Capuchinho p/ Trinco 1038",
                  "dimensoes_mm": (22, 18, 15),
                  "material": "Polímero/Zamac",
                  "obs": "Equivalente HELA do SM-1038G."},

    "HE-1801":   {"nome": "Suporte Regulável Basculante 1801",
                  "material": "Metal",
                  "obs": "Suporte regulável para basculante pequeno — Kit 06 HELA."},

    "HE-1003":   {"nome": "Espaçador/Batente Basculante 1003",
                  "material": "Polímero",
                  "obs": "Batente inferior para kit basculante pequeno V/A."},

    # ─── AL INDÚSTRIA — Linha Tradicional (AL) e Linha CAPA ──────────────────────
    # Fonte: Catálogo AL Indústria "Sua Obra Merece" (fabricante brasileiro de
    # ferragens em polímero para vidro temperado; fundada 2003, 15.000 m²)
    # Linha Tradicional (AL-XXXX): NAT/BCO/PTO/BZE/1002
    # Linha CAPA (CAPA-XXXX): CRO/NAT/BCO/PTO/BZE/1002 — acabamento premium

    # ── Botões de correção ────────────────────────────────────────────────────
    "AL-1001":   {"nome": "Botão de Correção com Calota para Vidro 1001",
                  "dimensoes_mm": (18, 11, 7), "recorte": {"furo_mm": 12},
                  "material": "Polímero"},

    "AL-1002":   {"nome": "Botão de Correção Simples (Parafuso) 1002",
                  "dimensoes_mm": (22, 8), "recorte": {"furo_mm": 12},
                  "material": "Polímero"},

    "AL-1002A":  {"nome": "Botão de Correção (Lâmina) 1002A",
                  "dimensoes_mm": (23, 16, 12), "material": "Polímero"},

    "AL-1002B":  {"nome": "Botão de Correção (Lâmina com Calota) 1002B",
                  "dimensoes_mm": (18, 18, 10), "material": "Polímero"},

    # ── Argolas e correntes (basculantes) ────────────────────────────────────
    "AL-1003A":  {"nome": "Argolas para Corrente 1003A",
                  "dimensoes_mm": (27,), "material": "Polímero/Metal"},

    "AL-1003F":  {"nome": "Corrente para Trinco Basculante (por metro) 1003F",
                  "dimensoes_mm": (1000,), "material": "Metal",
                  "obs": "Vendida por metro. Usada nos kits basculante 05, 06, 07."},

    "AL-1005":   {"nome": "Calota para Corrente 1005",
                  "dimensoes_mm": (19, 11), "material": "Polímero"},

    "AL-1005A":  {"nome": "Calota para Nylon com Regulagem 1005A",
                  "material": "Polímero",
                  "obs": "Versão com regulagem para sistemas de cordão nylon (Kit 05)."},

    # ── Pivôs / pinos inferiores ─────────────────────────────────────────────
    "AL-1013":   {"nome": "Pivô para Dobradiça Inferior com Regulagem 1013",
                  "dimensoes_mm": (60, 31, 16), "material": "Polímero/Metal",
                  "obs": "Pivô ajustável para dobradiça inferior. Encaixa no piso."},

    "AL-1013A":  {"nome": "Pivô para Dobradiça com Pino Fixo 1013A",
                  "dimensoes_mm": (62, 25, 9), "material": "Polímero/Metal"},

    "AL-1013F":  {"nome": "Pino para Dobradiça Inferior AL-1103A 1013F",
                  "dimensoes_mm": (67, 22), "material": "Polímero/Metal",
                  "obs": "Pino de fixação inferior específico para dobradiça AL-1103A. "
                         "Usado nos kits 01, 06, 07, 08."},

    "AL-1201A":  {"nome": "Bucha/Pivot Superior 1201A",
                  "material": "Polímero",
                  "obs": "Pivot/bucha superior para dobradiças pivotantes AL. "
                         "Instalada no perfil superior. Usada em todos os kits pivotantes."},

    # ── Capuchinhos ──────────────────────────────────────────────────────────
    "AL-1038":   {"nome": "Capuchinho para Trinco com Furo de 10mm 1038",
                  "dimensoes_mm": (23, 19, 10, 13), "material": "Polímero",
                  "obs": "Recebe o trinco AL-1335 em perfil com furo ø10mm."},

    "AL-1038A":  {"nome": "Capuchinho para Trinco (Capelinha) 1038A",
                  "dimensoes_mm": (25, 25, 20), "material": "Polímero"},

    "AL-1038C":  {"nome": "Capuchinho para Trinco (Ferradura) 1038C",
                  "dimensoes_mm": (49, 21), "material": "Polímero",
                  "obs": "Capuchinho em forma de ferradura. Usado nos kits 03 e 04 (janela correr)."},

    # ── Dobradiças superiores pivotantes ─────────────────────────────────────
    "AL-1101":   {"nome": "Dobradiça Superior com Pino de Inox 1101",
                  "dimensoes_mm": (129, 51), "pino_mm": 7,
                  "max_vao_mm": (1000, 2200),
                  "material": "Polímero",
                  "recorte": {"furo_mm": 25, "dist_borda_mm": 110, "dist_topo_mm": 5},
                  "obs": "Versão com pino de inox incluso. Máx 1000×2200mm ou 900×2600mm. "
                         "CAPA: 133×60mm. Furo ø25mm a 110mm da borda."},

    "AL-1101A":  {"nome": "Dobradiça Superior sem Pino de Inox 1101A",
                  "dimensoes_mm": (129, 51), "pino_mm": 7,
                  "max_vao_mm": (1000, 2200),
                  "material": "Polímero",
                  "recorte": {"furo_mm": 25, "dist_borda_mm": 110, "dist_topo_mm": 5},
                  "obs": "Sem pino de inox — requer AL-1013F separado. "
                         "Máx 1000×2200mm ou 900×2600mm. CAPA: 133×60mm."},

    # ── Dobradiças inferiores pivotantes ─────────────────────────────────────
    "AL-1103":   {"nome": "Dobradiça Inferior para Mola 1103",
                  "dimensoes_mm": (147, 55),
                  "max_vao_mm": (1000, 2200),
                  "material": "Polímero",
                  "recorte": {"furo_mm": 25, "dist_borda_mm": 125, "dist_base_mm": 2},
                  "obs": "Versão com mola integrada. Máx 1000×2200mm ou 900×2600mm. "
                         "CAPA: 150×59mm. Furo ø25mm a 125mm da borda."},

    "AL-1103A":  {"nome": "Dobradiça Inferior com Regulagem para Pivô Invertido 1103A",
                  "dimensoes_mm": (147, 55),
                  "max_vao_mm": (1000, 2200),
                  "material": "Polímero",
                  "recorte": {"furo_mm": 25, "dist_borda_mm": 125, "dist_base_mm": 2},
                  "obs": "Com regulagem para pivô invertido (ex: porta com piso elevado). "
                         "Máx 1000×2200mm ou 900×2600mm."},

    # ── Dobradiças automáticas box ────────────────────────────────────────────
    "AL-1114":   {"nome": "Dobradiça Automática para Box 1114",
                  "dimensoes_mm": (98, 48),
                  "max_vao_mm": (600, 1900),
                  "material": "Polímero",
                  "recorte": {"furo_mm": 20, "espacamento_mm": 50, "dist_topo_mm": 27},
                  "obs": "Linha Tradicional apenas (sem versão CAPA). "
                         "Fechamento automático por gravidade. Máx 600×1900mm. 2 peças por folha."},

    "AL-1115":   {"nome": "Dobradiça sem Caimento para Box 1115",
                  "dimensoes_mm": (98, 48),
                  "max_vao_mm": (600, 1900),
                  "material": "Polímero",
                  "recorte": {"furo_mm": 20, "espacamento_mm": 50, "dist_topo_mm": 27},
                  "obs": "Linha Tradicional apenas. Sem caimento (sem fechamento automático). "
                         "Máx 600×1900mm. 2 peças por folha."},

    # ── Dobradiça lateral horizontal (Linha CAPA exclusiva) ──────────────────
    "CAPA-1116": {"nome": "Dobradiça Lateral Horizontal Simples 1116 (CAPA)",
                  "dimensoes_mm": (108, 58),
                  "max_vao_mm": (1000, 2200),
                  "material": "Polímero",
                  "recorte": {"furo_mm": 20, "dist_a_mm": 30, "dist_b_mm": 50},
                  "obs": "Disponível apenas na Linha CAPA. Para portas com abertura lateral. "
                         "Máx 1000×2200mm ou 900×2600mm."},

    # ── Dobradiça basculante ─────────────────────────────────────────────────
    "AL-1123":   {"nome": "Dobradiça para Vidro Basculante com Pino de Inox 1123",
                  "dimensoes_mm": (54, 58, 7),
                  "max_vao_mm": (800, 700),
                  "material": "Polímero",
                  "recorte": {"furo_mm": 30},
                  "obs": "Para janela basculante vidro/alvenaria. Máx 800×700mm. 2 peças. "
                         "CAPA: 55×60×7mm. Furo ø30mm."},

    # ── Suporte basculante/pivotante ─────────────────────────────────────────
    "AL-1130":   {"nome": "Suporte para Basculante e Pivotante com Pino de Inox 1130",
                  "dimensoes_mm": (48, 97),
                  "max_vao_mm": (1000, 800),
                  "material": "Polímero",
                  "recorte": {"furo_mm": 25, "dist_topo_mm": 7},
                  "obs": "Suporte lateral com pino de inox. Máx 1000×800mm. 2 peças. "
                         "CAPA: 55×105mm. Usado nos kits 05, 06, 07."},

    "AL-1230":   {"nome": "Dobradiça/Suporte Basculante 1230",
                  "material": "Polímero",
                  "obs": "Suporte de eixo para janelas basculantes pequenas. Kit 02 e 06 AL."},

    "AL-1231":   {"nome": "Suporte c/ Ponto de Giro (Basculante Grande) 1231",
                  "material": "Polímero",
                  "obs": "Versão maior do AL-1230. Kit 07 AL (Basculante Grande)."},

    "AL-1801":   {"nome": "Suporte Regulável Basculante 1801",
                  "material": "Polímero/Metal",
                  "obs": "Suporte/pivot superior para kits basculante 05, 06, 07. "
                         "Instalado no perfil superior da janela."},

    "AL-1065":   {"nome": "Calota/Acabamento Basculante Grande 1065",
                  "material": "Polímero",
                  "obs": "Peça de acabamento do kit 07 (Basculante Grande)."},

    # ── Roldanas ─────────────────────────────────────────────────────────────
    "AL-1029A":  {"nome": "Roldana para Janela/Porta Correr 1029A",
                  "material": "Polímero/Nylon",
                  "obs": "Roldana de correr padrão AL. Usada nos kits 03 e 04."},

    "AL-1125CR": {"nome": "Roldana Excêntrica (NYL) com Rolamento 1125CR",
                  "dimensoes_mm": (30,), "recorte": {"furo_mm": 16},
                  "material": "Nylon",
                  "obs": "Roldana excêntrica com rolamento. Melhor desempenho em trilhos."},

    "AL-1125SR": {"nome": "Roldana Excêntrica sem Rolamento 1125SR",
                  "dimensoes_mm": (30,), "recorte": {"furo_mm": 16},
                  "material": "Nylon",
                  "obs": "Roldana excêntrica sem rolamento. Versão econômica."},

    # ── Trincos e fechaduras ─────────────────────────────────────────────────
    "AL-1335":   {"nome": "Trinco sem Miolo 1335",
                  "recorte_borda_mm": 15,
                  "material": "Polímero",
                  "obs": "Trinco padrão AL para portas e janelas pivotantes. "
                         "Capuchinho AL-1038 ou AL-1038C para receber o trinco."},

    "AL-1523":   {"nome": "Trinco Basculante 1523",
                  "recorte_borda_mm": 15,
                  "material": "Polímero",
                  "obs": "Trinco central para janelas basculantes. Kits 05, 06, 07."},

    "AL-1520":   {"nome": "Fechadura Central 1520",
                  "material": "Polímero",
                  "obs": "Fechadura central para portas pivotantes. Kit 01 e 08 AL. "
                         "Linha CAPA: versão com acabamento CAPA-1520."},

    "AL-1531":   {"nome": "Contra Fechadura 1531",
                  "material": "Polímero",
                  "obs": "Contra fechadura para porta dupla pivotante. Kit 08 AL."},

    # ── Fechaduras Blindex (porta/janela correr) ──────────────────────────────
    "AL-3530":   {"nome": "Fechadura para Porta V/A Blindex 3530",
                  "material": "Polímero",
                  "obs": "Fechadura embutida para porta de correr vidro/alvenaria. "
                         "Kit 10 AL. Acompanha AL-3206."},

    "AL-3532":   {"nome": "Fechadura para Janela de Correr V/V ou V/A 3532",
                  "material": "Polímero",
                  "obs": "Fechadura embutida para janela de correr. Kits 11 e 12 AL. "
                         "V/V: acompanha AL-3536. V/A: acompanha AL-3206."},

    "AL-3534":   {"nome": "Fechadura para Porta V/V Blindex 3534",
                  "material": "Polímero",
                  "obs": "Fechadura embutida para porta de correr vidro/vidro. "
                         "Kit 09 AL. Acompanha AL-3538."},

    "AL-3536":   {"nome": "Escudo/Trava Janela V/V 3536",
                  "material": "Polímero",
                  "obs": "Escudo complementar ao AL-3532 para janela V/V. Kit 11."},

    "AL-3538":   {"nome": "Escudo/Trava Porta V/V 3538",
                  "material": "Polímero",
                  "obs": "Escudo complementar ao AL-3534 para porta V/V. Kit 09."},

    "AL-3206":   {"nome": "Capuchinho/Escudo para Fechadura Blindex V/A 3206",
                  "material": "Polímero",
                  "obs": "Peça de recepção fixada na alvenaria para fechaduras V/A. "
                         "Kits 10 e 12 AL."},

    # ── Puxadores AL ─────────────────────────────────────────────────────────
    "AL-PUX-ARCO-190": {"nome": "Puxador Arco Polímero 190mm (P ARCO)",
                        "dimensoes_mm": (190,), "material": "Polímero",
                        "obs": "Linha P ARCO — puxador arco polímero para box e portas. "
                               "Disponível em diversas cores. Fixação por furo passante."},

    "AL-PUX-CONCHA-01": {"nome": "Puxador Concha Embutido",
                         "material": "Alumínio/Polímero",
                         "obs": "Puxador concha embutido para portas e janelas de correr. "
                                "Recorte retangular na borda do vidro."},

    "AL-PAL-PTO":    {"nome": "Puxador Alumínio/Inox PAL-PTO (Entre 300, 250×25mm)",
                      "dimensoes_mm": (300, 250, 25), "material": "Alumínio/Inox"},
    "AL-PAL-800-400": {"nome": "Puxador Alumínio/Inox PAL-800 (Entre 400, 300×25mm)",
                       "dimensoes_mm": (400, 300, 25), "material": "Alumínio/Inox"},
    "AL-PAL-800-600": {"nome": "Puxador Alumínio/Inox PAL-800 (Entre 600, 500×25mm)",
                       "dimensoes_mm": (600, 500, 25), "material": "Alumínio/Inox"},
    "AL-PAL-BR-1000": {"nome": "Puxador Alumínio/Inox PAL-BR+ (Entre 1000, 630×38mm)",
                       "dimensoes_mm": (1000, 630, 38), "material": "Alumínio/Inox"},
}


# ─────────────────────────────────────────────────────────────────────────────
# KITS OFICIAIS — composição conforme catálogo Santa Marina (Glasspeças 2017)
# ─────────────────────────────────────────────────────────────────────────────
# Campos:
#   descricao   : nome do kit conforme catálogo
#   max_vao_mm  : (largura_max, altura_max) do vão aplicável ao kit
#   obs         : nota técnica do kit
#   componentes : lista de {"codigo": str, "qtd": int}

KITS_OFICIAIS: Dict[str, Any] = {

    "kit_01_porta_simples_pivotante": {
        "descricao": "Kit 1 — Porta Simples Pivotante",
        "max_vao_mm": (1000, 2200),
        "componentes": [
            {"codigo": "SM-1201SG", "qtd": 1},
            {"codigo": "SM-1101",   "qtd": 1},
            {"codigo": "SM-1103",   "qtd": 1},
            {"codigo": "SM-1013SG", "qtd": 1},
            {"codigo": "SM-1520G",  "qtd": 1},
            {"codigo": "SM-1504AG", "qtd": 1},
        ]
    },

    "kit_02_janela_pivotante": {
        "descricao": "Kit 2 — Janela Pivotante",
        "max_vao_mm": (800, 700),
        "componentes": [
            {"codigo": "SM-1201SG", "qtd": 2},
            {"codigo": "SM-1230",   "qtd": 2},
            {"codigo": "SM-1335G",  "qtd": 1},
            {"codigo": "SM-1038G",  "qtd": 1},
        ]
    },

    "kit_03_janela_correr_4_folhas": {
        "descricao": "Kit 3 — Janela de Correr 4 Folhas",
        "componentes": [
            {"codigo": "SM-1038BG", "qtd": 2},
            {"codigo": "SM-1335G",  "qtd": 2},
            {"codigo": "SM-1629JG", "qtd": 2},
        ]
    },

    "kit_04_janela_correr_2_folhas": {
        "descricao": "Kit 4 — Janela de Correr 2 Folhas",
        "componentes": [
            {"codigo": "SM-1038BG", "qtd": 1},
            {"codigo": "SM-1335G",  "qtd": 1},
            {"codigo": "SM-1629JG", "qtd": 1},
        ]
    },

    "kit_05_box_abrir_va": {
        "descricao": "Kit 5 — Box de Abrir V/A",
        "max_vao_mm": (600, 1900),
        "componentes": [
            {"codigo": "SM-1114",   "qtd": 2},
            {"codigo": "SM-1629BG", "qtd": 1},
        ]
    },

    "kit_06_basculante_va_pequeno": {
        "descricao": "Kit 6 — Basculante V/A Pequeno",
        "max_vao_mm": (800, 700),
        "componentes": [
            {"codigo": "SM-1201SG", "qtd": 2},
            {"codigo": "SM-1230",   "qtd": 2},
            {"codigo": "SM-1523G",  "qtd": 1},
        ]
    },

    "kit_07_basculante_va_grande": {
        "descricao": "Kit 7 — Basculante V/A Grande",
        "max_vao_mm": (1000, 800),
        "componentes": [
            {"codigo": "SM-1201SG", "qtd": 2},
            {"codigo": "SM-1231",   "qtd": 2},
            {"codigo": "SM-1523G",  "qtd": 1},
        ]
    },

    "kit_08_porta_dupla_pivotante": {
        "descricao": "Kit 8 — Porta Dupla Pivotante",
        "max_vao_mm": (1000, 2200),
        "obs": "Dimensões por folha",
        "componentes": [
            {"codigo": "SM-1201SG", "qtd": 2},
            {"codigo": "SM-1101",   "qtd": 2},
            {"codigo": "SM-1103",   "qtd": 2},
            {"codigo": "SM-1013SG", "qtd": 2},
            {"codigo": "SM-1520G",  "qtd": 1},
            {"codigo": "SM-1531G",  "qtd": 1},
            {"codigo": "SM-1335G",  "qtd": 1},
            {"codigo": "SM-1038G",  "qtd": 1},
        ]
    },

    "kit_15_porta_pivotante_forcada": {
        "descricao": "Kit 15 — Porta Pivotante (Reforçada)",
        "componentes": [
            {"codigo": "SM-1101PGA", "qtd": 1},
            {"codigo": "SM-1103PGA", "qtd": 1},
        ]
    },

    "kit_16_porta_pivotante_com_chave": {
        "descricao": "Kit 16 — Porta Pivotante com Chave",
        "componentes": [
            {"codigo": "SM-1201SG",  "qtd": 1},
            {"codigo": "SM-1101",    "qtd": 1},
            {"codigo": "SM-1013SG",  "qtd": 1},
            {"codigo": "SM-1520MAG", "qtd": 1},
        ]
    },

    # ─── KITS OFICIAIS HELA — Polímero (Fechaduras Hela de Friburgo Ferragens) ───
    # Fonte: Catálogo HELA "Soluções em Acessórios para Vidro Temperado"

    "hela_kit_01_porta_simples_pivotante": {
        "descricao": "HELA Kit 01 — Porta Simples Pivotante (Polímero)",
        "max_vao_mm": (1000, 2200),
        "obs": "Equivalente HELA do Kit 1 Santa Marina. Linha Polímero.",
        "componentes": [
            {"codigo": "HE-1201A", "qtd": 1},
            {"codigo": "HE-1101A", "qtd": 1},
            {"codigo": "HE-1504A", "qtd": 1},
            {"codigo": "HE-1103A", "qtd": 1},
            {"codigo": "HE-1520",  "qtd": 1},
            {"codigo": "HE-1013F", "qtd": 1},
        ]
    },

    "hela_kit_02_janela_pivotante_va": {
        "descricao": "HELA Kit 02 — Janela Pivotante V/A (Polímero)",
        "max_vao_mm": (800, 700),
        "obs": "Equivalente HELA do Kit 2 Santa Marina. Linha Polímero.",
        "componentes": [
            {"codigo": "HE-1201F", "qtd": 2},
            {"codigo": "HE-1230",  "qtd": 2},
            {"codigo": "HE-1335",  "qtd": 1},
            {"codigo": "HE-1038",  "qtd": 1},
        ]
    },

    "hela_kit_05_box_abrir_automatico": {
        "descricao": "HELA Kit 05 — Box de Abrir Automático (Polímero)",
        "max_vao_mm": (600, 1900),
        "obs": "Equivalente HELA do Kit 5 Santa Marina. Fechamento automático por gravidade.",
        "componentes": [
            {"codigo": "HE-1114",  "qtd": 2},
            {"codigo": "HE-1629A", "qtd": 1},
        ]
    },

    "hela_kit_06_basculante_pequeno_va": {
        "descricao": "HELA Kit 06 — Basculante Pequeno V/A (Polímero)",
        "max_vao_mm": (800, 700),
        "obs": "Equivalente HELA do Kit 6 Santa Marina. Suporte regulável 1801.",
        "componentes": [
            {"codigo": "HE-1801",  "qtd": 1},
            {"codigo": "HE-1523",  "qtd": 1},
            {"codigo": "HE-1201F", "qtd": 2},
            {"codigo": "HE-1230",  "qtd": 2},
            {"codigo": "HE-1003",  "qtd": 1},
        ]
    },

    "hela_kit_08_porta_dupla_pivotante": {
        "descricao": "HELA Kit 08 — Porta Dupla Pivotante (Polímero)",
        "max_vao_mm": (1000, 2200),
        "obs": "Equivalente HELA do Kit 8 Santa Marina. Dimensões por folha.",
        "componentes": [
            {"codigo": "HE-1201A", "qtd": 2},
            {"codigo": "HE-1101A", "qtd": 2},
            {"codigo": "HE-1520",  "qtd": 1},
            {"codigo": "HE-1531",  "qtd": 1},
            {"codigo": "HE-1103A", "qtd": 2},
            {"codigo": "HE-1335",  "qtd": 1},
            {"codigo": "HE-1013F", "qtd": 2},
            {"codigo": "HE-1038",  "qtd": 1},
        ]
    },

    "hela_kit_16_maxim_ar_va": {
        "descricao": "HELA Kit 16 — Maxim-ar V/A (Polímero)",
        "obs": "Kit haste para controle de abertura maxim-ar vidro/alvenaria.",
        "componentes": [
            {"codigo": "HE-1587", "qtd": 1},
            {"codigo": "HE-1132", "qtd": 2},
        ]
    },

    # ─── KITS OFICIAIS AL INDÚSTRIA ───────────────────────────────────────────
    # Fonte: Catálogo AL Indústria "Sua Obra Merece" (p.12–15)
    # Cada kit disponível em Linha Tradicional (AL) e Linha CAPA.

    "al_kit_01_porta_simples_pivotante": {
        "descricao": "AL Kit 01 — Porta Simples Pivotante",
        "max_vao_mm": (1000, 2200),
        "obs": "Diagrama: 1201A topo → 1101A + 1504(puxador arco) → 1520(fechadura) → 1103A → 1013F base.",
        "componentes": [
            {"codigo": "AL-1201A",  "qtd": 1},
            {"codigo": "AL-1101A",  "qtd": 1},
            {"codigo": "AL-PUX-ARCO-190", "qtd": 1},
            {"codigo": "AL-1520",   "qtd": 1},
            {"codigo": "AL-1103A",  "qtd": 1},
            {"codigo": "AL-1013F",  "qtd": 1},
        ]
    },

    "al_kit_02_pivotante_janela": {
        "descricao": "AL Kit 02 — Pivotante (Janela)",
        "max_vao_mm": (800, 700),
        "obs": "Diagrama: 1201A topo + 1230×2 laterais + 1335 trinco + 1038 capuchinho + 1201A base.",
        "componentes": [
            {"codigo": "AL-1201A", "qtd": 2},
            {"codigo": "AL-1230",  "qtd": 2},
            {"codigo": "AL-1335",  "qtd": 1},
            {"codigo": "AL-1038",  "qtd": 1},
        ]
    },

    "al_kit_03_janela_correr_4_folhas": {
        "descricao": "AL Kit 03 — Janela de Correr 4 Folhas",
        "obs": "Diagrama: 1029A×2 (roldanas), 1335×2 trincos, 1038C×2 capuchinhos (ferradura).",
        "componentes": [
            {"codigo": "AL-1029A",  "qtd": 2},
            {"codigo": "AL-1335",   "qtd": 2},
            {"codigo": "AL-1038C",  "qtd": 2},
        ]
    },

    "al_kit_04_janela_correr_2_folhas": {
        "descricao": "AL Kit 04 — Janela de Correr 2 Folhas",
        "obs": "Diagrama: 1029A (roldana), 1335 trinco, 1038C capuchinho ferradura.",
        "componentes": [
            {"codigo": "AL-1029A",  "qtd": 1},
            {"codigo": "AL-1335",   "qtd": 1},
            {"codigo": "AL-1038C",  "qtd": 1},
        ]
    },

    "al_kit_05_basculante_cordao_nylon": {
        "descricao": "AL Kit 05 — Basculante Cordão Nylon",
        "obs": "Diagrama: 1801 topo, 1523 trinco, 1003A argola, 1130×2 suportes, 1003F corrente, 1005A calota nylon.",
        "componentes": [
            {"codigo": "AL-1801",   "qtd": 1},
            {"codigo": "AL-1523",   "qtd": 1},
            {"codigo": "AL-1003A",  "qtd": 1},
            {"codigo": "AL-1130",   "qtd": 2},
            {"codigo": "AL-1003F",  "qtd": 1},
            {"codigo": "AL-1005A",  "qtd": 1},
        ]
    },

    "al_kit_06_basculante_corrente": {
        "descricao": "AL Kit 06 — Basculante Corrente",
        "obs": "Diagrama: 1801 topo, 1523 trinco, 1003A argola, 1130×2 suportes, 1003F corrente, 1003A, 1005 calota.",
        "componentes": [
            {"codigo": "AL-1801",   "qtd": 1},
            {"codigo": "AL-1523",   "qtd": 1},
            {"codigo": "AL-1003A",  "qtd": 2},
            {"codigo": "AL-1130",   "qtd": 2},
            {"codigo": "AL-1003F",  "qtd": 1},
            {"codigo": "AL-1005",   "qtd": 1},
        ]
    },

    "al_kit_07_basculante_grande": {
        "descricao": "AL Kit 07 — Basculante Grande",
        "obs": "Diagrama: 1801 topo, 1523 trinco, 1003A, 1231×2 suportes grandes, 1003F corrente, 1003A, 1065.",
        "componentes": [
            {"codigo": "AL-1801",   "qtd": 1},
            {"codigo": "AL-1523",   "qtd": 1},
            {"codigo": "AL-1003A",  "qtd": 2},
            {"codigo": "AL-1231",   "qtd": 2},
            {"codigo": "AL-1003F",  "qtd": 1},
            {"codigo": "AL-1065",   "qtd": 1},
        ]
    },

    "al_kit_08_porta_dupla_pivotante": {
        "descricao": "AL Kit 08 — Porta Dupla Pivotante",
        "max_vao_mm": (1000, 2200),
        "obs": "Diagrama: 1201A×2 topo, 1101A×2, 1520 fechadura, 1531 contra-fech., "
               "1103A×2, 1335 trinco, 1038 capuchinho, 1013F×2 base.",
        "componentes": [
            {"codigo": "AL-1201A",  "qtd": 2},
            {"codigo": "AL-1101A",  "qtd": 2},
            {"codigo": "AL-1520",   "qtd": 1},
            {"codigo": "AL-1531",   "qtd": 1},
            {"codigo": "AL-1103A",  "qtd": 2},
            {"codigo": "AL-1335",   "qtd": 1},
            {"codigo": "AL-1038",   "qtd": 1},
            {"codigo": "AL-1013F",  "qtd": 2},
        ]
    },

    "al_kit_09_fechadura_porta_vv_blindex": {
        "descricao": "AL Kit 09 — Fechadura para Porta V/V Blindex",
        "obs": "Diagrama: 3538 + 3534. Para porta de correr vidro/vidro.",
        "componentes": [
            {"codigo": "AL-3538", "qtd": 1},
            {"codigo": "AL-3534", "qtd": 1},
        ]
    },

    "al_kit_10_fechadura_porta_va_blindex": {
        "descricao": "AL Kit 10 — Fechadura para Porta V/A Blindex",
        "obs": "Diagrama: 3530 + 3206. Para porta de correr vidro/alvenaria.",
        "componentes": [
            {"codigo": "AL-3530", "qtd": 1},
            {"codigo": "AL-3206", "qtd": 1},
        ]
    },

    "al_kit_11_fechadura_janela_vv_blindex": {
        "descricao": "AL Kit 11 — Fechadura para Janela V/V Blindex",
        "obs": "Diagrama: 3532 + 3536. Para janela de correr vidro/vidro.",
        "componentes": [
            {"codigo": "AL-3532", "qtd": 1},
            {"codigo": "AL-3536", "qtd": 1},
        ]
    },

    "al_kit_12_fechadura_janela_va_blindex": {
        "descricao": "AL Kit 12 — Fechadura para Janela V/A Blindex",
        "obs": "Diagrama: 3532 + 3206. Para janela de correr vidro/alvenaria.",
        "componentes": [
            {"codigo": "AL-3532", "qtd": 1},
            {"codigo": "AL-3206", "qtd": 1},
        ]
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# FOLGAS NBR — Folgas padrão conforme NBR 7199 / NBR 14698
# Fonte: Glasspeças catálogo 2017 p.94
# ─────────────────────────────────────────────────────────────────────────────
FOLGAS_NBR: Dict[str, Any] = {
    "entre_movel_e_fixo_mm":      3,
    "entre_moveis_mm":            4,
    "entre_movel_e_piso_mm":      8,
    "entre_fixos_mm":             1,
    "entre_movel_e_alvenaria_mm": 5,
    "fonte": "NBR 7199 / NBR 14698 (Glasspeças catálogo 2017 p.94)",
}


# ─────────────────────────────────────────────────────────────────────────────
# POSICIONAMENTO REFERÊNCIA DE MERCADO (Santa Marina / Glasspeças 2017)
# ─────────────────────────────────────────────────────────────────────────────
# Todas as posições posicao_y_mm são medidas DA BASE da peça para cima.
# distancia_borda_mm = distância da borda lateral esquerda/ativa.
#
# SM-1101  (dobradiça sup. pivotante, 130×50mm): 200mm da borda superior
# SM-1103  (dobradiça inf. pivotante, 150×55mm): 200mm da borda inferior
# SM-1114  (dobradiça automática box, 115×100×50mm): 150mm base / altura-150mm topo
# SM-1230  (dobradiça basculante): 50mm do topo
# SM-1125  (roldana simples, furo 15mm): 20mm da base
# SM-1520G (fechadura central): 900mm da base, 20mm da borda
# SM-1335G (trinco sem miolo): 1050mm da base, 15mm da borda
# SM-1523G (trinco basculante): 50mm da base, 15mm da borda
# SM-1201SG (bucha/pivot superior): encaixe no perfil superior (sem furo no vidro)

SKILL: Dict[str, Any] = {

    # ═══════════════════════════════════════════════════════
    # BOX DE BANHEIRO
    # ═══════════════════════════════════════════════════════

    "box_frontal_2_folhas": {
        "norma": "NBR 14207:2009",
        "espessura_minima_mm": 8,
        "kit_referencia": "kit_05_box_abrir_va",
        "ferragens_por_peca": {
            "folha fixa": [
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Automática Box 1114",
                    "codigo": "SM-1114",
                    "posicao_y_mm_formula": "altura_mm - 150",
                    "distancia_borda_mm": 25,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Automática Box 1114",
                    "codigo": "SM-1114",
                    "posicao_y_mm_formula": "150",
                    "distancia_borda_mm": 25,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
            ],
            "folha movel": [
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Automática Box 1114",
                    "codigo": "SM-1114",
                    "posicao_y_mm_formula": "altura_mm - 150",
                    "distancia_borda_mm": 25,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Automática Box 1114",
                    "codigo": "SM-1114",
                    "posicao_y_mm_formula": "150",
                    "distancia_borda_mm": 25,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "puxador",
                    "nome": "Puxador Arco Polímero 190mm",
                    "codigo": "AL-PUX-ARCO-190",
                    "posicao_y_mm_formula": "altura_mm * 0.55",
                    "distancia_borda_mm": 35,
                    "tipo_visual": "circulo",
                    "quantidade": 1
                },
                {
                    "tipo": "bate_fecha",
                    "nome": "Bate Fecha V/A 1629BG",
                    "codigo": "SM-1629BG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "Dobradiça 1114: 115×100×50mm. Máx 600×1900mm. Vidro 8mm obrigatório. "
            "Recorte: 4 furos ø20mm, espaçamento 50mm, dist. topo 25mm, dist. borda 25mm. "
            "Dobradiças garantem fechamento automático por gravidade. "
            "Puxador e bate-fecha SM-1629BG somente na folha móvel. "
            "Distância borda-furo: mínimo 3× a espessura do vidro."
        )
    },

    "box_canto_90": {
        "norma": "NBR 14207:2009",
        "espessura_minima_mm": 8,
        "ferragens_por_peca": {
            "folha frontal": [
                {
                    "tipo": "puxador",
                    "nome": "Puxador Arco Polímero 190mm",
                    "codigo": "AL-PUX-ARCO-190",
                    "posicao_y_mm_formula": "altura_mm * 0.55",
                    "distancia_borda_mm": 35,
                    "tipo_visual": "circulo",
                    "quantidade": 1
                },
                {
                    "tipo": "bate_fecha",
                    "nome": "Bate Fecha V/A 1629BG",
                    "codigo": "SM-1629BG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
            ],
            "folha lateral": [
                {
                    "tipo": "suporte_canto",
                    "nome": "Suporte de Canto 1302",
                    "codigo": "SM-1302",
                    "posicao_y_mm_formula": "altura_mm - 200",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "suporte_canto",
                    "nome": "Suporte de Canto 1302",
                    "codigo": "SM-1302",
                    "posicao_y_mm_formula": "200",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "Suporte SM-1302 une as duas folhas em ângulo de 90°. "
            "Kit canto completo inclui SM-1629BG (bate-fecha) e SM-1302 (suporte de canto). "
            "Vidro mínimo 8mm conforme NBR 14207."
        )
    },

    # ═══════════════════════════════════════════════════════
    # PORTAS PIVOTANTES
    # ═══════════════════════════════════════════════════════

    "porta_pivotante_simples": {
        "norma": "NBR 7199:2016",
        "espessura_minima_mm": 10,
        "kit_referencia": "kit_01_porta_simples_pivotante",
        "ferragens_por_peca": {
            "porta": [
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Superior Pivotante 1101",
                    "codigo": "SM-1101",
                    "posicao_y_mm_formula": "altura_mm - 200",
                    "distancia_borda_mm": 10,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Inferior Pivotante 1103",
                    "codigo": "SM-1103",
                    "posicao_y_mm_formula": "200",
                    "distancia_borda_mm": 10,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "puxador",
                    "nome": "Puxador Botão 1504AG",
                    "codigo": "SM-1504AG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "circulo",
                    "quantidade": 1
                },
                {
                    "tipo": "fechadura",
                    "nome": "Fechadura Central 1520G",
                    "codigo": "SM-1520G",
                    "posicao_y_mm_formula": "900",
                    "distancia_borda_mm": 20,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "SM-1101 (130×50mm) + SM-1103 (150×55mm) formam o eixo pivotante. "
            "Máx vão: 1000×2200mm. Pino ø8mm. "
            "Recorte sup.: furo ø25mm a 107mm da borda, 25mm da base. "
            "Recorte inf.: furo ø25mm a 125mm da borda, 25mm da base. "
            "Pivot inferior SM-1013SG (furo ø6mm) encaixado no piso. "
            "Fechadura SM-1520G: 900mm da base, 20mm da borda."
        )
    },

    "porta_pivotante_simples_reforcada": {
        "norma": "NBR 7199:2016",
        "espessura_minima_mm": 10,
        "kit_referencia": "kit_15_porta_pivotante_forcada",
        "ferragens_por_peca": {
            "porta": [
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Superior Reforçada 4F Alumínio 1101PGA",
                    "codigo": "SM-1101PGA",
                    "posicao_y_mm_formula": "altura_mm - 200",
                    "distancia_borda_mm": 15,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Inferior Reforçada 4F Alumínio 1103PGA",
                    "codigo": "SM-1103PGA",
                    "posicao_y_mm_formula": "200",
                    "distancia_borda_mm": 15,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "puxador",
                    "nome": "Puxador Botão 1504AG",
                    "codigo": "SM-1504AG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "circulo",
                    "quantidade": 1
                },
                {
                    "tipo": "fechadura",
                    "nome": "Fechadura Central 1520G",
                    "codigo": "SM-1520G",
                    "posicao_y_mm_formula": "900",
                    "distancia_borda_mm": 20,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "Para vãos >1200mm de largura ou >2200mm de altura. "
            "SM-1101PGA (135×90mm, 4 furos, alumínio): recorte furo ø20mm, "
            "115mm da borda, 30mm da base. "
            "SM-1103PGA (145×90mm, 4 furos, alumínio): máx 1400×3000mm. "
            "Kit 15 Santa Marina."
        )
    },

    "porta_pivotante_dupla_bandeira": {
        "norma": "NBR 7199:2016",
        "espessura_minima_mm": 10,
        "kit_referencia": "kit_08_porta_dupla_pivotante",
        "ferragens_por_peca": {
            "bandeira": [],
            "porta 1": [
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Superior Pivotante 1101",
                    "codigo": "SM-1101",
                    "posicao_y_mm_formula": "altura_mm - 200",
                    "distancia_borda_mm": 10,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Inferior Pivotante 1103",
                    "codigo": "SM-1103",
                    "posicao_y_mm_formula": "200",
                    "distancia_borda_mm": 10,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "puxador",
                    "nome": "Puxador Botão 1504AG",
                    "codigo": "SM-1504AG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "circulo",
                    "quantidade": 1
                },
                {
                    "tipo": "fechadura",
                    "nome": "Fechadura Central 1520G",
                    "codigo": "SM-1520G",
                    "posicao_y_mm_formula": "900",
                    "distancia_borda_mm": 20,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
            ],
            "porta 2": [
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Superior Pivotante 1101",
                    "codigo": "SM-1101",
                    "posicao_y_mm_formula": "altura_mm - 200",
                    "distancia_borda_mm": 10,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Inferior Pivotante 1103",
                    "codigo": "SM-1103",
                    "posicao_y_mm_formula": "200",
                    "distancia_borda_mm": 10,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "puxador",
                    "nome": "Puxador Botão 1504AG",
                    "codigo": "SM-1504AG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "circulo",
                    "quantidade": 1
                },
                {
                    "tipo": "bate_fecha",
                    "nome": "Contra Fechadura 1531G",
                    "codigo": "SM-1531G",
                    "posicao_y_mm_formula": "900",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
                {
                    "tipo": "trinco",
                    "nome": "Trinco sem Miolo 1335G",
                    "codigo": "SM-1335G",
                    "posicao_y_mm_formula": "1050",
                    "distancia_borda_mm": 15,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "Kit 8 Santa Marina — Porta Dupla Pivotante. Dimensões por folha: máx 1000×2200mm. "
            "Bandeira é vidro fixo — sem ferragens ativas, apenas suporte. "
            "SM-1531G (contra fechadura) e SM-1335G (trinco, recorte borda 15mm) na porta 2. "
            "SM-1038G (capuchinho ø10mm) para receber o trinco 1335G."
        )
    },

    # ═══════════════════════════════════════════════════════
    # PORTAS DE CORRER
    # ═══════════════════════════════════════════════════════

    "porta_correr_2_folhas": {
        "norma": "NBR 7199:2016",
        "espessura_minima_mm": 8,
        "ferragens_por_peca": {
            "folha 1": [
                {
                    "tipo": "roldana",
                    "nome": "Carrinho Porta Correr Rolamento 1126",
                    "codigo": "SM-1126",
                    "posicao_y_mm_formula": "altura_mm - 30",
                    "distancia_borda_mm": 25,
                    "tipo_visual": "retangulo",
                    "quantidade": 2
                },
                {
                    "tipo": "puxador",
                    "nome": "Puxador Concha Embutido",
                    "codigo": "AL-PUX-CONCHA-01",
                    "posicao_y_mm_formula": "altura_mm * 0.55",
                    "distancia_borda_mm": 30,
                    "tipo_visual": "circulo",
                    "quantidade": 1
                },
                {
                    "tipo": "bate_fecha",
                    "nome": "Bate Fecha V/A 1629BG",
                    "codigo": "SM-1629BG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
            ],
            "folha 2": [
                {
                    "tipo": "roldana",
                    "nome": "Carrinho Porta Correr Rolamento 1126",
                    "codigo": "SM-1126",
                    "posicao_y_mm_formula": "altura_mm - 30",
                    "distancia_borda_mm": 25,
                    "tipo_visual": "retangulo",
                    "quantidade": 2
                },
                {
                    "tipo": "puxador",
                    "nome": "Puxador Concha Embutido",
                    "codigo": "AL-PUX-CONCHA-01",
                    "posicao_y_mm_formula": "altura_mm * 0.55",
                    "distancia_borda_mm": 30,
                    "tipo_visual": "circulo",
                    "quantidade": 1
                },
                {
                    "tipo": "fechadura",
                    "nome": "Trinco sem Miolo 1335G",
                    "codigo": "SM-1335G",
                    "posicao_y_mm_formula": "1050",
                    "distancia_borda_mm": 15,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "SM-1126 (carrinho 60×85mm, rolamento): recorte furo ø20mm, "
            "dist. borda 25mm, espaçamento 50mm. Máx por folha: 600×1800mm. Vidro 8mm. "
            "SM-1126D (duplo, 100×85mm) para folhas até 700×2100mm. "
            "Folha 1: bate-fecha SM-1629BG; Folha 2: trinco SM-1335G (recorte borda 15mm)."
        )
    },

    # ═══════════════════════════════════════════════════════
    # JANELAS
    # ═══════════════════════════════════════════════════════

    "janela_pivotante": {
        "norma": "NBR 7199:2016",
        "espessura_minima_mm": 8,
        "kit_referencia": "kit_02_janela_pivotante",
        "ferragens_por_peca": {
            "folha": [
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Superior Pivotante 1101",
                    "codigo": "SM-1101",
                    "posicao_y_mm_formula": "altura_mm - 150",
                    "distancia_borda_mm": 10,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Inferior Pivotante 1103",
                    "codigo": "SM-1103",
                    "posicao_y_mm_formula": "150",
                    "distancia_borda_mm": 10,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "trinco",
                    "nome": "Trinco sem Miolo 1335G",
                    "codigo": "SM-1335G",
                    "posicao_y_mm_formula": "altura_mm * 0.85",
                    "distancia_borda_mm": 15,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "Kit 2 Santa Marina — Janela Pivotante. Máx 800×700mm (por folha). "
            "SM-1201SG (bucha/pivot superior, furo ø8mm) × 2 no perfil superior. "
            "SM-1230 (dobradiça basculante) × 2. SM-1335G (trinco, recorte borda 15mm). "
            "SM-1038G (capuchinho ø10mm, 22×18×15mm) para receber o trinco. "
            "Trinco posicionado no lado oposto às dobradiças."
        )
    },

    "janela_correr_2_folhas": {
        "norma": "NBR 7199:2016",
        "espessura_minima_mm": 6,
        "kit_referencia": "kit_04_janela_correr_2_folhas",
        "ferragens_por_peca": {
            "folha 1": [
                {
                    "tipo": "roldana",
                    "nome": "Roldana Simples Box/Correr 1125",
                    "codigo": "SM-1125",
                    "posicao_y_mm_formula": "20",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "retangulo",
                    "quantidade": 2
                },
                {
                    "tipo": "bate_fecha",
                    "nome": "Bate Fecha Janela Correr 1629JG",
                    "codigo": "SM-1629JG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
            ],
            "folha 2": [
                {
                    "tipo": "roldana",
                    "nome": "Roldana Simples Box/Correr 1125",
                    "codigo": "SM-1125",
                    "posicao_y_mm_formula": "20",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "retangulo",
                    "quantidade": 2
                },
                {
                    "tipo": "trinco",
                    "nome": "Trinco sem Miolo 1335G",
                    "codigo": "SM-1335G",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 15,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
                {
                    "tipo": "capuchinho",
                    "nome": "Capuchinho p/ Trinco 1335 Trilho Exposto 1038BG",
                    "codigo": "SM-1038BG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "Kit 4 Santa Marina — Janela Correr 2 Folhas. "
            "SM-1125 (roldana simples, furo ø15mm): recorte furo ø15mm, "
            "dist. borda 50mm, dist. base 20mm. Máx 800×2100mm por folha. "
            "SM-1038BG (capuchinho 50×22×15mm) para trilho exposto. "
            "SM-1629JG (bate-fecha janela correr) na folha 1."
        )
    },

    "janela_correr_4_folhas": {
        "norma": "NBR 7199:2016",
        "espessura_minima_mm": 6,
        "kit_referencia": "kit_03_janela_correr_4_folhas",
        "ferragens_por_peca": {
            "folha 1": [
                {
                    "tipo": "roldana",
                    "nome": "Roldana Simples Box/Correr 1125",
                    "codigo": "SM-1125",
                    "posicao_y_mm_formula": "20",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "retangulo",
                    "quantidade": 2
                },
                {
                    "tipo": "bate_fecha",
                    "nome": "Bate Fecha Janela Correr 1629JG",
                    "codigo": "SM-1629JG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
            ],
            "folha 2": [
                {
                    "tipo": "roldana",
                    "nome": "Roldana Simples Box/Correr 1125",
                    "codigo": "SM-1125",
                    "posicao_y_mm_formula": "20",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "retangulo",
                    "quantidade": 2
                },
                {
                    "tipo": "trinco",
                    "nome": "Trinco sem Miolo 1335G",
                    "codigo": "SM-1335G",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 15,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
                {
                    "tipo": "capuchinho",
                    "nome": "Capuchinho p/ Trinco 1335 Trilho Exposto 1038BG",
                    "codigo": "SM-1038BG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
            ],
            "folha 3": [
                {
                    "tipo": "roldana",
                    "nome": "Roldana Simples Box/Correr 1125",
                    "codigo": "SM-1125",
                    "posicao_y_mm_formula": "20",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "retangulo",
                    "quantidade": 2
                },
                {
                    "tipo": "bate_fecha",
                    "nome": "Bate Fecha Janela Correr 1629JG",
                    "codigo": "SM-1629JG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
            ],
            "folha 4": [
                {
                    "tipo": "roldana",
                    "nome": "Roldana Simples Box/Correr 1125",
                    "codigo": "SM-1125",
                    "posicao_y_mm_formula": "20",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "retangulo",
                    "quantidade": 2
                },
                {
                    "tipo": "trinco",
                    "nome": "Trinco sem Miolo 1335G",
                    "codigo": "SM-1335G",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 15,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
                {
                    "tipo": "capuchinho",
                    "nome": "Capuchinho p/ Trinco 1335 Trilho Exposto 1038BG",
                    "codigo": "SM-1038BG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "Kit 3 Santa Marina — Janela Correr 4 Folhas. "
            "SM-1038BG × 2 (capuchinho trilho exposto, 50×22×15mm). "
            "SM-1335G × 2 (trinco sem miolo, recorte borda 15mm). "
            "SM-1629JG × 2 (bate-fecha janela correr). "
            "Roldanas SM-1125 (furo ø15mm): dist. borda 50mm, dist. base 20mm."
        )
    },

    "janela_basculante": {
        "norma": "NBR 7199:2016",
        "espessura_minima_mm": 6,
        "kit_referencia": "kit_06_basculante_va_pequeno",
        "ferragens_por_peca": {
            "folha": [
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça para Basculante 1230",
                    "codigo": "SM-1230",
                    "posicao_y_mm_formula": "altura_mm - 50",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "retangulo",
                    "quantidade": 2
                },
                {
                    "tipo": "trinco",
                    "nome": "Trinco Basculante 1523G",
                    "codigo": "SM-1523G",
                    "posicao_y_mm_formula": "50",
                    "distancia_borda_mm": 15,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "Kit 6 Santa Marina — Basculante V/A Pequeno. Máx 800×700mm. "
            "SM-1230 (dobradiça basculante): 2 unidades no topo, posição 50mm da borda superior. "
            "SM-1523G (trinco basculante): na base, 50mm da borda inferior, recorte 15mm. "
            "SM-1201SG (bucha/pivot superior, furo ø8mm) × 2 no perfil superior. "
            "Para vãos maiores (≤1000×800mm), usar SM-1231 (dobradiça grande) — Kit 7."
        )
    },

    "janela_basculante_grande": {
        "norma": "NBR 7199:2016",
        "espessura_minima_mm": 6,
        "kit_referencia": "kit_07_basculante_va_grande",
        "ferragens_por_peca": {
            "folha": [
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça para Basculante Grande 1231",
                    "codigo": "SM-1231",
                    "posicao_y_mm_formula": "altura_mm - 50",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "retangulo",
                    "quantidade": 2
                },
                {
                    "tipo": "trinco",
                    "nome": "Trinco Basculante 1523G",
                    "codigo": "SM-1523G",
                    "posicao_y_mm_formula": "50",
                    "distancia_borda_mm": 15,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "Kit 7 Santa Marina — Basculante V/A Grande. Máx 1000×800mm. "
            "SM-1231 (dobradiça basculante grande): 2 unidades no topo. "
            "SM-1523G (trinco basculante): base, 15mm da borda. "
            "SM-1201SG × 2 no perfil superior."
        )
    },

    "janela_basculante_vv": {
        "norma": "NBR 7199:2016",
        "espessura_minima_mm": 6,
        "ferragens_por_peca": {
            "folha": [
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Vidro Basculante 1123",
                    "codigo": "SM-1123",
                    "posicao_y_mm_formula": "altura_mm - 50",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "retangulo",
                    "quantidade": 2
                },
                {
                    "tipo": "trinco",
                    "nome": "Trinco Basculante 1523G",
                    "codigo": "SM-1523G",
                    "posicao_y_mm_formula": "50",
                    "distancia_borda_mm": 15,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "Basculante Vidro/Vidro — dobradiça SM-1123 (60×50mm, pino ø8mm, Latão/Zamac). "
            "Máx 800×700mm. "
            "Fórmula ponto de giro X: X = (48000 / largura_mm) + distancia_base_mm. "
            "SM-1123A (com trinco integrado) como alternativa à SM-1123 + SM-1523G. "
            "SM-1123 no topo da folha (50mm da borda superior). "
            "SM-1523G trinco: posicao_y=50mm, distancia_borda=15mm."
        )
    },

    "janela_maxim_ar": {
        "norma": "NBR 7199:2016",
        "espessura_minima_mm": 6,
        "ferragens_por_peca": {
            "folha": [
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Basculante com Trinco 1123A",
                    "codigo": "SM-1123A",
                    "posicao_y_mm_formula": "altura_mm - 50",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "retangulo",
                    "quantidade": 2
                },
                {
                    "tipo": "trinco",
                    "nome": "Trinco sem Miolo 1335G",
                    "codigo": "SM-1335G",
                    "posicao_y_mm_formula": "50",
                    "distancia_borda_mm": 15,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "SM-1123A (dobradiça basculante com trinco integrado, 60×50mm): "
            "alternativa compacta para maxim-ar. Máx 800×700mm. "
            "Abertura máxima controlada por limitador de corrente ou freio."
        )
    },

    # ═══════════════════════════════════════════════════════
    # PORTA SANFONADA
    # ═══════════════════════════════════════════════════════

    "porta_sanfonada_3_folhas": {
        "norma": "NBR 7199:2016",
        "espessura_minima_mm": 6,
        "ferragens_por_peca": {
            "folha 1 (fixa)": [
                {
                    "tipo": "suporte_sanfonada",
                    "nome": "Suporte Superior c/ Rodízio Porta Sanfonada 1124",
                    "codigo": "SM-1124",
                    "posicao_y_mm_formula": "altura_mm - 20",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
            ],
            "folha 2 (central)": [
                {
                    "tipo": "suporte_sanfonada",
                    "nome": "Suporte Central Porta Sanfonada Rodízio Duplo 1127",
                    "codigo": "SM-1127",
                    "posicao_y_mm_formula": "altura_mm - 20",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "suporte_sanfonada",
                    "nome": "Suporte Central Inferior c/ Pino Sanfonada 1127A",
                    "codigo": "SM-1127A",
                    "posicao_y_mm_formula": "20",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
            ],
            "folha 3 (movel)": [
                {
                    "tipo": "suporte_sanfonada",
                    "nome": "Suporte Superior c/ Rodízio Porta Sanfonada 1124",
                    "codigo": "SM-1124",
                    "posicao_y_mm_formula": "altura_mm - 20",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "puxador",
                    "nome": "Puxador Botão 1504AG",
                    "codigo": "SM-1504AG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 35,
                    "tipo_visual": "circulo",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "SM-1124 (suporte superior c/ rodízio): máx 400×2100mm por folha. "
            "SM-1127 (suporte central rodízio duplo): máx 700×2000mm. "
            "SM-1127A (suporte inferior c/ pino): fixação no piso. "
            "Folha central usa SM-1127 (topo) + SM-1127A (base). "
            "Folhas externas usam SM-1124. Folha móvel recebe puxador."
        )
    },

    # ═══════════════════════════════════════════════════════
    # GUARDA-CORPO
    # ═══════════════════════════════════════════════════════

    "guarda_corpo_linear": {
        "norma": "NBR 14718:2019",
        "espessura_minima_mm": 10,
        "ferragens_por_peca": {
            "painel": [
                {
                    "tipo": "perfil",
                    "nome": "Perfil U Inox (base)",
                    "codigo": "PERFIL-U-INOX",
                    "posicao_y_mm_formula": "20",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
                {
                    "tipo": "perfil",
                    "nome": "Corrimão Inox (topo)",
                    "codigo": "CORRIMAO-INOX",
                    "posicao_y_mm_formula": "altura_mm - 20",
                    "distancia_borda_mm": 0,
                    "tipo_visual": "linha_h",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "Altura mínima: 1100mm (NBR 14718:2019). "
            "Vidro laminado obrigatório (NBR 16259:2014). "
            "Perfil U na base ou fixação por bóton. "
            "Espessura mínima 10mm; para alturas >1,5m recomenda-se 12mm laminado."
        )
    },

    # ═══════════════════════════════════════════════════════
    # DIVISÓRIAS
    # ═══════════════════════════════════════════════════════

    "divisoria_porta_pivotante": {
        "norma": "NBR 7199:2016",
        "espessura_minima_mm": 10,
        "kit_referencia": "kit_01_porta_simples_pivotante",
        "ferragens_por_peca": {
            "fixo": [],
            "porta": [
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Superior Pivotante 1101",
                    "codigo": "SM-1101",
                    "posicao_y_mm_formula": "altura_mm - 200",
                    "distancia_borda_mm": 10,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "dobradica",
                    "nome": "Dobradiça Inferior Pivotante 1103",
                    "codigo": "SM-1103",
                    "posicao_y_mm_formula": "200",
                    "distancia_borda_mm": 10,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
                {
                    "tipo": "puxador",
                    "nome": "Puxador Botão 1504AG",
                    "codigo": "SM-1504AG",
                    "posicao_y_mm_formula": "altura_mm * 0.50",
                    "distancia_borda_mm": 50,
                    "tipo_visual": "circulo",
                    "quantidade": 1
                },
                {
                    "tipo": "fechadura",
                    "nome": "Fechadura Central 1520G",
                    "codigo": "SM-1520G",
                    "posicao_y_mm_formula": "900",
                    "distancia_borda_mm": 20,
                    "tipo_visual": "retangulo",
                    "quantidade": 1
                },
            ]
        },
        "observacoes": (
            "Painéis fixos sem ferragens ativas. "
            "Porta com kit completo pivotante SM-1101 + SM-1103. "
            "SM-1101 (130×50mm, máx 1000×2200mm). SM-1103 (150×55mm). "
            "Fechadura SM-1520G: 900mm da base, 20mm da borda."
        )
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ─────────────────────────────────────────────────────────────────────────────

def get_ferragens_para_peca(
    tipologia_chave: str,
    peca_nome: str,
    largura_mm: float,
    altura_mm: float
) -> List[Dict]:
    """
    Retorna lista de ferragens com posições calculadas para uma peça específica.
    Usa a skill como fonte primária — 100% determinista, sem IA.

    Args:
        tipologia_chave: chave da tipologia no dict SKILL
        peca_nome      : nome da peça (ex: "porta", "folha movel", "folha 1")
        largura_mm     : largura da peça em mm
        altura_mm      : altura da peça em mm

    Returns:
        Lista de dicts com ferragens posicionadas. Lista vazia se não encontrado.
    """
    tipologia = SKILL.get(tipologia_chave)
    if not tipologia:
        return []

    ferragens_config = tipologia.get("ferragens_por_peca", {})

    # Buscar peça por match parcial (case insensitive, sem acentos)
    import unicodedata as _ud

    def _norm(s: str) -> str:
        n = _ud.normalize('NFD', s.lower())
        return ''.join(c for c in n if _ud.category(c) != 'Mn')

    # Aliases: nomes curtos que o backend envia → lista de fragmentos a procurar na chave da skill
    # Ordem importa: a primeira correspondência encontrada vence.
    _PECA_ALIASES: dict[str, list[str]] = {
        # folha ativa / móvel / porta de correr
        "movel":    ["movel", "folha 2", "folha 1"],
        "porta":    ["movel", "folha 2"],
        "ativa":    ["movel", "folha 2"],
        # folha fixo / parede
        "fixo":     ["fixa", "folha 1"],
        "parede":   ["fixa", "folha 1"],
        # lateral (box canto, guarda-corpo)
        "lateral":  ["lateral"],
        # bandeira / travessa
        "bandeira": ["bandeira"],
        "travessa": ["travessa"],
        "superior": ["superior", "folha 1"],
        "inferior": ["inferior", "folha 2"],
        # folha numerada explícita
        "folha 1":  ["folha 1"],
        "folha 2":  ["folha 2"],
        "folha 3":  ["folha 3"],
        "folha 4":  ["folha 4"],
        "f1":       ["folha 1"],
        "f2":       ["folha 2"],
        "f3":       ["folha 3"],
        "f4":       ["folha 4"],
    }

    peca_key = None
    peca_nome_norm = _norm(peca_nome)

    # 1ª tentativa: match substring direto (cobre maioria dos casos)
    for key in ferragens_config:
        key_norm = _norm(key)
        if key_norm in peca_nome_norm or peca_nome_norm in key_norm:
            peca_key = key
            break

    # 2ª tentativa: via aliases → fragmentos mapeados como substring da chave da skill
    if not peca_key:
        for alias_input, alias_targets in _PECA_ALIASES.items():
            if alias_input in peca_nome_norm:
                for target in alias_targets:
                    for key in ferragens_config:
                        if target in _norm(key):
                            peca_key = key
                            break
                    if peca_key:
                        break
            if peca_key:
                break

    if not peca_key:
        return []

    ferragens = []
    for f in ferragens_config[peca_key]:
        try:
            posicao_y = eval(
                f["posicao_y_mm_formula"],
                {"altura_mm": altura_mm, "largura_mm": largura_mm}
            )
        except Exception:
            posicao_y = altura_mm * 0.5

        ferragens.append({
            "tipo": f["tipo"],
            "nome": f["nome"],
            "codigo": f.get("codigo", ""),
            "posicao_y_mm": round(posicao_y, 1),
            "distancia_borda_mm": f["distancia_borda_mm"],
            "tipo_visual": f["tipo_visual"],
            "quantidade": f.get("quantidade", 1),
            "inferida_por_ia": False,
        })

    return ferragens


def normalizar_para_skill(tipologia_nome: str) -> str:
    """
    Normaliza o nome da tipologia para a chave da skill.
    Retorna a chave correspondente ou string vazia se não encontrar.

    Args:
        tipologia_nome: nome livre da tipologia (ex: "porta pivotante", "basculante vv")

    Returns:
        Chave exata do dict SKILL, ou "" se não mapeada.
    """
    import unicodedata
    nome = unicodedata.normalize('NFD', tipologia_nome.lower())
    nome = ''.join(c for c in nome if unicodedata.category(c) != 'Mn')
    nome = nome.replace(' ', '_').replace('-', '_')

    mapeamentos = {
        "box_frontal_2_folhas": [
            "box_frontal_2", "box_2_folhas", "box_de_banheiro", "box_abrir",
        ],
        "box_canto_90": [
            "box_canto", "box_em_l", "canto_90",
        ],
        "porta_pivotante_simples": [
            "porta_pivotante", "pivotante_simples",
        ],
        "porta_pivotante_simples_reforcada": [
            "pivotante_reforcada", "porta_gigante", "porta_pesada",
            "pivotante_4f", "pivotante_pga",
        ],
        "porta_pivotante_dupla_bandeira": [
            "pivotante_dupla", "dupla_bandeira", "porta_dupla",
        ],
        "porta_correr_2_folhas": [
            "porta_correr", "correr_2_folhas", "porta_de_correr",
        ],
        "porta_sanfonada_3_folhas": [
            "sanfonada", "porta_sanfonada", "porta_acordeao",
        ],
        "janela_pivotante": [
            "janela_pivotante", "janela_pivot",
        ],
        "janela_correr_2_folhas": [
            "janela_correr_2", "janela_2_folhas", "janela_duas_folhas",
        ],
        "janela_correr_4_folhas": [
            "janela_correr_4", "janela_4_folhas", "janela_quatro_folhas",
        ],
        "janela_basculante_vv": [
            "basculante_vv", "basculante_vidro_vidro",
        ],
        "janela_basculante_grande": [
            "basculante_grande", "janela_basculante_grande",
        ],
        "janela_basculante": [
            "basculante", "janela_basculante", "basculante_va",
            "basculante_vidro_alvenaria",
        ],
        "janela_maxim_ar": [
            "maxim_ar", "maximar", "janela_maxim",
        ],
        "guarda_corpo_linear": [
            "guarda_corpo", "guarda_corpo_linear",
        ],
        "divisoria_porta_pivotante": [
            "divisoria", "divisoria_porta",
        ],
    }

    for chave, aliases in mapeamentos.items():
        if chave in nome:
            return chave
        for alias in aliases:
            if alias in nome:
                return chave

    return ""
