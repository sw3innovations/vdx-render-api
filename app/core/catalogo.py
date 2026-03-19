import unicodedata
import re


def normalizar_nome(nome: str) -> str:
    """Lowercase, remove acentos, colapsa espaços."""
    nfkd = unicodedata.normalize("NFKD", nome.lower())
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento).strip()


CATALOGO_LAYOUTS: dict[str, str] = {
    # BOX
    "box frontal 2 folhas": "paralelas",
    "box frontal 3 folhas": "paralelas",
    "box frontal 4 folhas": "paralelas",
    "box canto 90": "canto_l",
    "box canto 2 folhas": "canto_l",
    "box canto 3 folhas": "canto_l",
    "box abrir automatico": "paralelas",
    "box abrir": "paralelas",
    # PORTAS
    "porta pivotante simples": "paralelas",
    "porta pivotante dupla bandeira": "bandeira_topo",
    "porta pivotante dupla com bandeira": "bandeira_topo",
    "porta pivotante dupla sem bandeira": "paralelas",
    "porta pivotante dupla": "bandeira_topo",
    "porta correr 2 folhas": "paralelas",
    "porta correr 4 folhas": "paralelas",
    "porta correr fixo": "fixo_movel_fixo",
    "porta correr vidragem aluminio": "fixo_movel_fixo",
    "porta sanfonada 3 folhas": "paralelas",
    "porta sanfonada 4 folhas": "paralelas",
    "porta sanfonada": "paralelas",
    # JANELAS
    "janela pivotante": "paralelas",
    "janela correr 2 folhas": "paralelas",
    "janela correr 4 folhas": "paralelas",
    "janela correr 6 folhas": "paralelas",
    "janela basculante": "basculante",
    "janela maxim ar": "basculante",
    "janela guilhotina": "basculante",
    "janela fixa": "paralelas",
    "janela veneziana": "basculante",
    # GUARDA-CORPO
    "guarda corpo linear perfil u": "paineis_lineares",
    "guarda corpo linear boton": "paineis_lineares",
    "guarda corpo linear": "paineis_lineares",
    "guarda corpo canto": "canto_l",
    "guarda corpo escada": "paineis_lineares",
    "guarda corpo u": "paineis_lineares",
    # SACADA / FECHAMENTO
    "cortina vidro": "paineis_lineares",
    "fechamento sacada": "paineis_lineares",
    "envidracamento varanda": "paineis_lineares",
    "fechamento versatik": "paralelas",
    "sacada retratil": "paineis_lineares",
    # COBERTURAS
    "cobertura plana": "cobertura",
    "cobertura inclinada": "cobertura",
    "claraboia": "cobertura",
    "telhado vidro": "cobertura",
    # DIVISÓRIAS
    "divisoria interna": "paralelas",
    "divisoria porta pivotante": "fixo_movel_fixo",
    "divisoria correr": "fixo_movel_fixo",
    "fechamento closet": "fixo_movel_fixo",
    # OUTROS
    "vitrine frontal": "paralelas",
    "fachada fixa": "paineis_lineares",
    "espelho": "paralelas",
    "tampo mesa": "paralelas",
    "muro vidro": "paineis_lineares",
    "portao vidro": "paralelas",
    "kit pia": "canto_l",
    "painel decorativo": "paralelas",
}

FERRAGEM_DEFAULTS: dict[str, dict] = {
    "bate_fecha":  {"posicao_y_mm_pct": 0.90, "distancia_borda_mm": 0,  "tipo_visual": "linha_h"},
    "puxador":     {"posicao_y_mm_pct": 0.50, "distancia_borda_mm": 50, "tipo_visual": "circulo"},
    "dobradica":   {"posicao_y_mm_pct": 0.15, "distancia_borda_mm": 10, "tipo_visual": "retangulo"},
    "trinco":      {"posicao_y_mm_pct": 0.85, "distancia_borda_mm": 0,  "tipo_visual": "linha_h"},
    "fechadura":   {"posicao_y_mm_pct": 0.45, "distancia_borda_mm": 20, "tipo_visual": "retangulo"},
    "amortecedor": {"posicao_y_mm_pct": 0.10, "distancia_borda_mm": 15, "tipo_visual": "retangulo"},
    "perfil":      {"posicao_y_mm_pct": 0.50, "distancia_borda_mm": 0,  "tipo_visual": "linha_h"},
}


FERRAGENS_POR_TIPOLOGIA: dict[str, list[dict]] = {
    # PORTAS
    "pivotante": [
        {"tipo": "puxador",   "nome": "Puxador Barra Inox"},
        {"tipo": "dobradica", "nome": "Dobradiça 180°"},
        {"tipo": "fechadura", "nome": "Fechadura Central"},
    ],
    "porta correr": [
        {"tipo": "puxador",    "nome": "Puxador Concha"},
        {"tipo": "bate_fecha", "nome": "Bate Fecha Mini"},
    ],
    "sanfonada": [
        {"tipo": "dobradica", "nome": "Dobradiça Sanfonada"},
        {"tipo": "puxador",   "nome": "Puxador Concha"},
    ],
    # BOX
    "box": [
        {"tipo": "puxador",    "nome": "Puxador Arco Polímero"},
        {"tipo": "bate_fecha", "nome": "Bate Fecha V/V"},
        {"tipo": "dobradica",  "nome": "Dobradiça Automática Box"},
    ],
    # JANELAS
    "janela": [
        {"tipo": "bate_fecha", "nome": "Bate Fecha Mini V/A"},
        {"tipo": "trinco",     "nome": "Trinco s/ Miolo"},
    ],
    "basculante": [
        {"tipo": "trinco", "nome": "Trinco Basculante"},
    ],
    # GUARDA-CORPO
    "guarda corpo": [
        {"tipo": "perfil", "nome": "Perfil U Inox"},
    ],
    # DIVISÓRIA
    "divisoria": [
        {"tipo": "dobradica", "nome": "Dobradiça 180°"},
        {"tipo": "fechadura", "nome": "Fechadura Central"},
    ],
}


def inferir_ferragens_por_tipologia(tipologia_nome: str) -> list[dict]:
    """Retorna ferragens padrão baseado no nome da tipologia."""
    nome = normalizar_nome(tipologia_nome)
    for chave, ferragens in FERRAGENS_POR_TIPOLOGIA.items():
        if chave in nome:
            return ferragens
    return []


def resolver_layout_por_nome(tipologia_nome: str) -> str | None:
    """Busca o layout no catálogo pelo nome normalizado. Retorna None se não encontrar."""
    chave = normalizar_nome(tipologia_nome)
    # match exato
    if chave in CATALOGO_LAYOUTS:
        return CATALOGO_LAYOUTS[chave]
    # match parcial — pega a chave mais longa que seja substring do nome
    candidatos = [(k, v) for k, v in CATALOGO_LAYOUTS.items() if k in chave or chave in k]
    if candidatos:
        return max(candidatos, key=lambda x: len(x[0]))[1]
    return None


def aplicar_defaults_ferragem(tipo: str, altura_mm: float) -> dict:
    """Retorna posicao_y_mm e distancia_borda_mm a partir dos defaults do tipo."""
    defaults = FERRAGEM_DEFAULTS.get(tipo, FERRAGEM_DEFAULTS["puxador"])
    return {
        "posicao_y_mm": round(altura_mm * defaults["posicao_y_mm_pct"], 1),
        "distancia_borda_mm": defaults["distancia_borda_mm"],
        "tipo_visual": defaults["tipo_visual"],
    }
