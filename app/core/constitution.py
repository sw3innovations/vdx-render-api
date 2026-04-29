"""
Constitution DB — base de conhecimento viva do plugin VDX.
SQLite local com WAL mode. Migra pra PostgreSQL quando escalar.
"""
import sqlite3
import json
import logging
import re
import unicodedata
from urllib.parse import unquote as _url_unquote
from pathlib import Path
from typing import Optional, List

log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "constitution.db"

# ─── Contrato de fórmulas ─────────────────────────────────────────────────────
# Variáveis de fórmula são SEMPRE minúsculas neste sistema.
# Este dict é a fonte da verdade — loader e engine usam este mesmo mapeamento.
FORMULA_VARS_CANONICAS: dict[str, str] = {
    "VANO_H":      "vano_h",
    "VANO_L":      "vano_l",
    "COMPRIMENTO": "comprimento",
    "ESPESSURA":   "espessura",
    "LARGURA":     "largura",
    "ALTURA":      "altura",
    "A":           "a",
    "B":           "b",
    "X":           "x",
    "Y":           "y",
}


def normalizar_formula(formula: str) -> str:
    """Normaliza variáveis de fórmula para minúsculas.

    Ordenadas por comprimento (maior primeiro) para evitar substituição parcial:
    'ALTURA' deve ser substituído antes de 'A', caso contrário 'ALTURA' → 'alTURA'.
    Esta função é idempotente: aplicar N vezes dá o mesmo resultado.
    """
    resultado = formula
    for var_upper in sorted(FORMULA_VARS_CANONICAS, key=len, reverse=True):
        resultado = resultado.replace(var_upper, FORMULA_VARS_CANONICAS[var_upper])
    return resultado


def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Cria tabelas e aplica migrações. Não popula dados — chame seed() separadamente.

    Idempotente — seguro de chamar múltiplas vezes.
    """
    conn = _get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS constitution_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nicho TEXT NOT NULL DEFAULT 'vidros',
        tipo TEXT NOT NULL,
        chave TEXT NOT NULL,
        dados TEXT NOT NULL,
        origem TEXT NOT NULL DEFAULT 'seed',
        confianca REAL NOT NULL DEFAULT 1.0,
        validado_por TEXT,
        versao TEXT NOT NULL DEFAULT '2026.03.20',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(nicho, tipo, chave)
    );

    CREATE TABLE IF NOT EXISTS constitution_aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nicho TEXT NOT NULL DEFAULT 'vidros',
        alias TEXT NOT NULL,
        canonical TEXT NOT NULL,
        tipo TEXT NOT NULL,
        origem TEXT NOT NULL DEFAULT 'seed',
        confianca REAL NOT NULL DEFAULT 1.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(nicho, alias, tipo)
    );

    CREATE INDEX IF NOT EXISTS idx_entries_chave ON constitution_entries(nicho, tipo, chave);
    CREATE INDEX IF NOT EXISTS idx_aliases_alias ON constitution_aliases(nicho, alias, tipo);

    CREATE TABLE IF NOT EXISTS constitution_validations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nicho TEXT NOT NULL DEFAULT 'vidros',
        entry_chave TEXT NOT NULL,
        tipo_validacao TEXT NOT NULL,
        resultado TEXT NOT NULL,
        correcoes TEXT,
        validado_por TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()
    migrate()


# ─── Migrações versionadas ────────────────────────────────────────────────────

def _m001_fabricantes_ferragens_kits(conn) -> None:
    """Sprint 1 — tabelas de catálogo: fabricantes, ferragens, kits e componentes."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS fabricantes (
        id TEXT PRIMARY KEY,
        nome TEXT NOT NULL,
        prefixo TEXT NOT NULL,
        metadata TEXT
    );
    CREATE TABLE IF NOT EXISTS ferragens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL,
        codigo_normalizado TEXT NOT NULL,
        fabricante_id TEXT NOT NULL REFERENCES fabricantes(id),
        nome TEXT NOT NULL,
        tipo TEXT,
        material TEXT,
        dimensoes_json TEXT,
        espessura_vidro TEXT,
        cores_json TEXT,
        pagina_catalogo INTEGER,
        confianca REAL DEFAULT 0.9,
        fonte TEXT,
        UNIQUE(codigo, fabricante_id)
    );
    CREATE TABLE IF NOT EXISTS kits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT NOT NULL,
        fabricante_id TEXT NOT NULL REFERENCES fabricantes(id),
        nome TEXT NOT NULL,
        linha TEXT,
        max_vao_json TEXT,
        acabamentos_json TEXT,
        pagina_catalogo INTEGER,
        UNIQUE(numero, fabricante_id)
    );
    CREATE TABLE IF NOT EXISTS kit_componentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kit_id INTEGER NOT NULL REFERENCES kits(id),
        ferragem_codigo TEXT NOT NULL,
        quantidade INTEGER DEFAULT 1,
        posicao TEXT,
        nome TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_ferragens_codigo ON ferragens(codigo);
    CREATE INDEX IF NOT EXISTS idx_ferragens_normalizado ON ferragens(codigo_normalizado);
    CREATE INDEX IF NOT EXISTS idx_ferragens_fabricante ON ferragens(fabricante_id);
    CREATE INDEX IF NOT EXISTS idx_ferragens_tipo ON ferragens(tipo);
    CREATE INDEX IF NOT EXISTS idx_kits_numero ON kits(numero);
    """)


def _m002_recortes_equivalencias(conn) -> None:
    """Sprint 2 — recortes por ferragem e equivalências entre fabricantes."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS recortes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ferragem_codigo TEXT NOT NULL,
        fabricante_id TEXT NOT NULL REFERENCES fabricantes(id),
        tipo TEXT,
        comprimento_mm REAL,
        largura_mm REAL,
        furo_diametro_mm REAL,
        raio_mm REAL,
        notas TEXT,
        pagina_catalogo INTEGER
    );
    CREATE TABLE IF NOT EXISTS equivalencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_normalizado TEXT NOT NULL,
        fabricante_id TEXT NOT NULL REFERENCES fabricantes(id),
        codigo_fabricante TEXT NOT NULL,
        UNIQUE(fabricante_id, codigo_fabricante)
    );
    CREATE INDEX IF NOT EXISTS idx_equivalencias_normalizado ON equivalencias(codigo_normalizado);
    CREATE INDEX IF NOT EXISTS idx_recortes_ferragem ON recortes(ferragem_codigo);
    """)


def _m003_formulas_folgas(conn) -> None:
    """Sprint 3 — fórmulas de posicionamento e folgas NBR."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS formulas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        formula TEXT NOT NULL,
        variaveis_json TEXT,
        ferragens_aplicaveis TEXT,
        notas TEXT,
        fabricante_id TEXT REFERENCES fabricantes(id)
    );
    CREATE TABLE IF NOT EXISTS folgas_nbr (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL UNIQUE,
        valor_mm REAL NOT NULL,
        fonte TEXT
    );
    """)


def _m004_add_contexto_aplicacao(conn) -> None:
    """Sprint 4 — adiciona coluna contexto_aplicacao à tabela recortes."""
    try:
        conn.execute("ALTER TABLE recortes ADD COLUMN contexto_aplicacao TEXT DEFAULT NULL")
    except Exception:
        pass  # SQLite não suporta ADD COLUMN IF NOT EXISTS; coluna já existe


def _m005_normalize_formula_vars(conn) -> None:
    """Sprint 4 — normaliza variáveis de fórmula para minúsculas (contrato VDX)."""
    conn.execute("""
        UPDATE formulas SET formula =
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                formula,
                'VANO_H',      'vano_h'),
                'VANO_L',      'vano_l'),
                'COMPRIMENTO', 'comprimento'),
                'ESPESSURA',   'espessura'),
                'LARGURA',     'largura'),
                'ALTURA',      'altura'),
                'VANO_H',      'vano_h'),
                'VANO_L',      'vano_l')
        WHERE formula LIKE '%LARGURA%' OR formula LIKE '%ALTURA%'
           OR formula LIKE '%COMPRIMENTO%' OR formula LIKE '%ESPESSURA%'
           OR formula LIKE '%VANO_L%' OR formula LIKE '%VANO_H%'
    """)


def _m006_cleanup_artefatos(conn) -> None:
    """Sprint 4 — remove tipologias fora do domínio de vidraçaria."""
    _ARTEFATOS = ('escada_rolante', 'tipologia_inexistente_xyz')
    conn.execute(
        "DELETE FROM constitution_entries WHERE chave IN ({})".format(
            ','.join('?' * len(_ARTEFATOS))
        ),
        _ARTEFATOS,
    )


def _m007_dump_tabelas(conn) -> None:
    """Sprint 9 — tabelas dump_* para dados importados do sistema legado VDX."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS dump_tipologias (
            nu_tip       INTEGER PRIMARY KEY,
            ds_tmd       TEXT NOT NULL,
            id_ativo     TEXT,
            sacada       TEXT,
            importado_em TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS dump_modelos (
            nu_mod       INTEGER PRIMARY KEY,
            ds_mod       TEXT NOT NULL,
            nu_tip       INTEGER,
            div_largura  INTEGER,
            div_altura   INTEGER,
            importado_em TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_dump_modelos_tip ON dump_modelos(nu_tip);

        CREATE TABLE IF NOT EXISTS dump_geometria_pecas (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            nu_dmd       INTEGER,
            nu_mod       INTEGER NOT NULL,
            nu_peca      INTEGER NOT NULL,
            eixo_x_alt   REAL,
            eixo_x_lar   REAL,
            eixo_y_alt   REAL,
            eixo_y_lar   REAL,
            ds_formula_alt TEXT,
            ds_formula_lar TEXT,
            ds_tipo      TEXT,
            ds_peca      TEXT,
            ds_descricao TEXT,
            importado_em TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(nu_mod, nu_peca)
        );
        CREATE INDEX IF NOT EXISTS idx_dump_geo_mod  ON dump_geometria_pecas(nu_mod);
        CREATE INDEX IF NOT EXISTS idx_dump_geo_tipo ON dump_geometria_pecas(ds_tipo);

        CREATE TABLE IF NOT EXISTS dump_variaveis_altura (
            nu_mda        INTEGER PRIMARY KEY,
            nu_mod        INTEGER NOT NULL,
            ds_altura     TEXT,
            var_altura    INTEGER,
            altura_padrao REAL,
            importado_em  TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_dump_var_alt_mod ON dump_variaveis_altura(nu_mod);
        CREATE INDEX IF NOT EXISTS idx_dump_var_alt_ds  ON dump_variaveis_altura(ds_altura);

        CREATE TABLE IF NOT EXISTS dump_variaveis_largura (
            nu_mdl        INTEGER PRIMARY KEY,
            nu_mod        INTEGER NOT NULL,
            ds_largura    TEXT,
            var_largura   INTEGER,
            largura_padrao REAL,
            importado_em  TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_dump_var_larg_mod ON dump_variaveis_largura(nu_mod);

        CREATE TABLE IF NOT EXISTS dump_formulas_marcacao (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            nu_mod       INTEGER,
            ds_formula   TEXT,
            importado_em TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS dump_categorias_ferragens (
            nu_cat       INTEGER PRIMARY KEY,
            ds_cat       TEXT NOT NULL,
            id_ativo     TEXT,
            importado_em TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS dump_ferragens_individuais (
            nu_fer       INTEGER PRIMARY KEY,
            ds_fer       TEXT,
            nu_cat       INTEGER,
            importado_em TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS dump_projetos_anonimizados (
            nu_prj_hash  TEXT PRIMARY KEY,
            nu_mod       INTEGER,
            largura_mm   REAL,
            altura_mm    REAL,
            importado_em TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)


def _m008_catalogo_tabelas(conn) -> None:
    """Sprint 9 — tabelas catalogo_* para produtos de catálogos PDF de puxadores."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS catalogo_fabricantes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo       TEXT NOT NULL UNIQUE,
            nome         TEXT,
            importado_em TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS catalogo_puxadores (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            fabricante_id        TEXT NOT NULL,
            codigo               TEXT,
            codigo_normalizado   TEXT,
            nome                 TEXT,
            tipo_visual          TEXT,
            comp_mm              REAL,
            diametro_mm          REAL,
            largura_mm           REAL,
            altura_mm            REAL,
            profundidade_mm      REAL,
            distancia_furos_mm   REAL,
            material             TEXT,
            acabamento           TEXT,
            observacoes          TEXT,
            pagina_origem        INTEGER,
            importado_em         TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_cat_pux_fab      ON catalogo_puxadores(fabricante_id);
        CREATE INDEX IF NOT EXISTS idx_cat_pux_codigo   ON catalogo_puxadores(codigo_normalizado);
        CREATE INDEX IF NOT EXISTS idx_cat_pux_tipo     ON catalogo_puxadores(tipo_visual);
        CREATE INDEX IF NOT EXISTS idx_cat_pux_material ON catalogo_puxadores(material);

        CREATE TABLE IF NOT EXISTS catalogo_puxador_equivalencias (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            puxador_a_id INTEGER NOT NULL,
            puxador_b_id INTEGER NOT NULL,
            tipo_equiv   TEXT,
            importado_em TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(puxador_a_id, puxador_b_id)
        );
    """)


def _m009_canonical_schema(conn) -> None:
    """Sprint 10 — schema canônico 3NF unificando Render + Dump VDX + Catálogo PDF."""
    conn.executescript("""
        -- ── lookup: materiais ────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS materiais_canonicos (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo            TEXT NOT NULL UNIQUE,
            nome_apresentacao TEXT NOT NULL,
            densidade_kg_m3   REAL,
            observacoes       TEXT,
            created_at        TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS materiais_aliases (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id  INTEGER NOT NULL REFERENCES materiais_canonicos(id),
            alias        TEXT NOT NULL,
            fonte        TEXT NOT NULL,
            UNIQUE(alias, fonte)
        );
        CREATE INDEX IF NOT EXISTS idx_mat_aliases_alias ON materiais_aliases(alias);

        -- ── lookup: acabamentos ───────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS acabamentos_canonicos (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo            TEXT NOT NULL UNIQUE,
            nome_apresentacao TEXT NOT NULL,
            created_at        TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS acabamentos_aliases (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            acabamento_id  INTEGER NOT NULL REFERENCES acabamentos_canonicos(id),
            alias          TEXT NOT NULL,
            fonte          TEXT NOT NULL,
            UNIQUE(alias, fonte)
        );
        CREATE INDEX IF NOT EXISTS idx_acab_aliases_alias ON acabamentos_aliases(alias);

        -- ── lookup: variaveis ─────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS variaveis_canonicas (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo            TEXT NOT NULL UNIQUE,
            nome_apresentacao TEXT NOT NULL,
            eixo              TEXT NOT NULL CHECK(eixo IN ('altura','largura','neutro')),
            unidade           TEXT NOT NULL DEFAULT 'mm',
            descricao         TEXT,
            created_at        TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS variaveis_aliases (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            variavel_id INTEGER NOT NULL REFERENCES variaveis_canonicas(id),
            alias       TEXT NOT NULL,
            fonte       TEXT NOT NULL,
            UNIQUE(alias, fonte)
        );
        CREATE INDEX IF NOT EXISTS idx_var_aliases_alias ON variaveis_aliases(alias);

        -- ── tipologias canônicas ──────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS tipologias_canonicas (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo            TEXT NOT NULL UNIQUE,
            nome_apresentacao TEXT NOT NULL,
            categoria         TEXT,
            schema_render     TEXT,
            nu_tip_dump       INTEGER,
            fonte_origem      TEXT,
            created_at        TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_tip_can_nu_tip ON tipologias_canonicas(nu_tip_dump);

        -- ── modelos canônicos ─────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS modelos_canonicos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            tipologia_id  INTEGER NOT NULL REFERENCES tipologias_canonicas(id),
            nu_mod_dump   INTEGER UNIQUE,
            nome          TEXT,
            nome_inferido INTEGER NOT NULL DEFAULT 0,
            largura_div   INTEGER,
            altura_div    INTEGER,
            fonte_origem  TEXT,
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_mod_can_tipologia ON modelos_canonicos(tipologia_id);

        -- ── ferragens canônicas ───────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS ferragens_canonicas (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_normalizado  TEXT NOT NULL,
            tipo                TEXT,
            subtipo             TEXT,
            nome_apresentacao   TEXT NOT NULL,
            material_id         INTEGER REFERENCES materiais_canonicos(id),
            acabamento_id       INTEGER REFERENCES acabamentos_canonicos(id),
            fabricante_codigo   TEXT,
            comprimento_mm      REAL,
            diametro_mm         REAL,
            largura_mm          REAL,
            altura_mm           REAL,
            profundidade_mm     REAL,
            distancia_furos_mm  REAL,
            fontes_json         TEXT,
            observacoes         TEXT,
            created_at          TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(codigo_normalizado, fabricante_codigo)
        );
        CREATE INDEX IF NOT EXISTS idx_ferr_can_codigo  ON ferragens_canonicas(codigo_normalizado);
        CREATE INDEX IF NOT EXISTS idx_ferr_can_fab     ON ferragens_canonicas(fabricante_codigo);
        CREATE INDEX IF NOT EXISTS idx_ferr_can_tipo    ON ferragens_canonicas(tipo);
        CREATE TABLE IF NOT EXISTS ferragens_aliases (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ferragem_id  INTEGER NOT NULL REFERENCES ferragens_canonicas(id),
            codigo_alias TEXT NOT NULL,
            fabricante   TEXT,
            fonte        TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ferr_aliases_codigo ON ferragens_aliases(codigo_alias);

        -- ── peças geometria canônicas ─────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS pecas_geometria_canonicas (
            id                       INTEGER PRIMARY KEY AUTOINCREMENT,
            modelo_id                INTEGER NOT NULL REFERENCES modelos_canonicos(id),
            nu_peca                  INTEGER NOT NULL,
            ds_peca                  TEXT,
            tipo_peca                TEXT,
            eixo_x_alt               REAL,
            eixo_y_alt               REAL,
            eixo_x_larg              REAL,
            eixo_y_larg              REAL,
            formula_alt_original     TEXT,
            formula_alt_normalizada  TEXT,
            formula_larg_original    TEXT,
            formula_larg_normalizada TEXT,
            fonte_origem             TEXT,
            created_at               TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_pec_geo_can_modelo ON pecas_geometria_canonicas(modelo_id);

        -- ── auditoria ETL ─────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS etl_auditoria (
            id                       INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp                TEXT NOT NULL DEFAULT (datetime('now')),
            estagio                  TEXT NOT NULL,
            transformer              TEXT,
            tabela_destino           TEXT,
            registros_processados    INTEGER DEFAULT 0,
            registros_aceitos        INTEGER DEFAULT 0,
            registros_rejeitados     INTEGER DEFAULT 0,
            motivos_rejeicao_json    TEXT,
            observacoes              TEXT
        );
    """)


# Registro central — adicionar novas migrações AQUI (nunca alterar as anteriores)
_MIGRATIONS = [
    (1, "create_fabricantes_ferragens_kits",  _m001_fabricantes_ferragens_kits),
    (2, "create_recortes_equivalencias",      _m002_recortes_equivalencias),
    (3, "create_formulas_folgas",             _m003_formulas_folgas),
    (4, "add_contexto_aplicacao",             _m004_add_contexto_aplicacao),
    (5, "normalize_formula_vars",             _m005_normalize_formula_vars),
    (6, "cleanup_artefatos_teste",            _m006_cleanup_artefatos),
    (7, "dump_tabelas",                       _m007_dump_tabelas),
    (8, "catalogo_tabelas",                   _m008_catalogo_tabelas),
    (9, "canonical_schema",                   _m009_canonical_schema),
]


def migrate() -> None:
    """Executa migrações pendentes. Cada migration roda exatamente uma vez.

    A tabela schema_migrations controla quais versões já foram aplicadas.
    Adicionar novas migrações em _MIGRATIONS — nunca alterar as existentes.
    """
    conn = _get_conn()

    # Tabela de controle (auto-bootstrap — ela própria não precisa de migration)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    INTEGER PRIMARY KEY,
            name       TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

    applied = {
        row[0]
        for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    }

    for version, name, fn in _MIGRATIONS:
        if version in applied:
            continue
        log.info("Applying migration %d (%s)...", version, name)
        fn(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
            (version, name),
        )
        conn.commit()
        log.info("Migration %d (%s) applied.", version, name)

    conn.close()


# ─── CRUD original (tipologias) ───────────────────────────────────────────────

def buscar(chave: str, tipo: str = "tipologia", nicho: str = "vidros") -> Optional[dict]:
    chave = _url_unquote(chave)  # normalize URL-encoded keys
    conn = _get_conn()
    row = conn.execute(
        "SELECT dados, confianca, origem FROM constitution_entries WHERE nicho=? AND tipo=? AND chave=?",
        (nicho, tipo, chave)
    ).fetchone()
    conn.close()
    if row:
        return {
            "dados": json.loads(row["dados"]),
            "confianca": row["confianca"],
            "origem": row["origem"]
        }
    return None


def registrar(chave: str, dados: dict, tipo: str = "tipologia",
              nicho: str = "vidros", origem: str = "claude_inferido",
              confianca: float = 0.7, validado_por: str = None) -> None:
    chave = _url_unquote(chave)  # normalize URL-encoded keys before any DB write
    conn = _get_conn()
    conn.execute("""
        INSERT INTO constitution_entries (nicho, tipo, chave, dados, origem, confianca, validado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(nicho, tipo, chave) DO UPDATE SET
            dados=excluded.dados, origem=excluded.origem,
            confianca=excluded.confianca, validado_por=excluded.validado_por,
            updated_at=CURRENT_TIMESTAMP
    """, (nicho, tipo, chave, json.dumps(dados, ensure_ascii=False),
          origem, confianca, validado_por))
    conn.commit()
    conn.close()


def normalizar(nome: str, tipo: str = "tipologia", nicho: str = "vidros") -> str:
    """Resolve alias → canonical. Se não encontrar, retorna nome normalizado."""
    nome_norm = unicodedata.normalize('NFD', nome.lower().strip())
    nome_norm = ''.join(c for c in nome_norm if unicodedata.category(c) != 'Mn')
    nome_norm = nome_norm.replace(' ', '_').replace('-', '_')

    conn = _get_conn()
    row = conn.execute(
        "SELECT canonical FROM constitution_aliases WHERE nicho=? AND tipo=? AND alias=?",
        (nicho, tipo, nome_norm)
    ).fetchone()
    conn.close()
    if row:
        return row["canonical"]
    return nome_norm


def registrar_alias(alias: str, canonical: str, tipo: str = "tipologia",
                    nicho: str = "vidros", origem: str = "seed") -> None:
    alias_norm = unicodedata.normalize('NFD', alias.lower().strip())
    alias_norm = ''.join(c for c in alias_norm if unicodedata.category(c) != 'Mn')
    alias_norm = alias_norm.replace(' ', '_').replace('-', '_')

    conn = _get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO constitution_aliases (nicho, alias, canonical, tipo, origem)
        VALUES (?, ?, ?, ?, ?)
    """, (nicho, alias_norm, canonical, tipo, origem))
    conn.commit()
    conn.close()


def marcar_validada(chave: str, tipo: str = "tipologia",
                    nicho: str = "vidros", confianca: float = 0.95) -> None:
    """Marca entry como validada, atualiza confiança."""
    conn = _get_conn()
    conn.execute(
        "UPDATE constitution_entries SET confianca=?, updated_at=CURRENT_TIMESTAMP "
        "WHERE nicho=? AND tipo=? AND chave=?",
        (confianca, nicho, tipo, chave))
    conn.commit()
    conn.close()


def registrar_validacao(chave: str, tipo_validacao: str, resultado: str,
                         correcoes: str = None,
                         validado_por: str = "claude_validator",
                         nicho: str = "vidros") -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT INTO constitution_validations "
        "(nicho, entry_chave, tipo_validacao, resultado, correcoes, validado_por) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (nicho, chave, tipo_validacao, resultado, correcoes, validado_por))
    conn.commit()
    conn.close()


def foi_validada(chave: str, tipo: str = "tipologia", nicho: str = "vidros") -> bool:
    """Retorna True se a entry já tem confiança >= 0.95 (validada ou seed)."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT confianca FROM constitution_entries WHERE nicho=? AND tipo=? AND chave=?",
        (nicho, tipo, chave)).fetchone()
    conn.close()
    return bool(row and row["confianca"] >= 0.95)


def limpar_previews() -> None:
    """Remove todos os previews cacheados para forçar regeneração."""
    conn = _get_conn()
    conn.execute("DELETE FROM constitution_entries WHERE tipo='preview'")
    conn.commit()
    conn.close()


def listar_entries(tipo: str = None, nicho: str = "vidros") -> list:
    conn = _get_conn()
    if tipo:
        rows = conn.execute(
            "SELECT chave, confianca, origem FROM constitution_entries WHERE nicho=? AND tipo=?",
            (nicho, tipo)).fetchall()
    else:
        rows = conn.execute(
            "SELECT tipo, chave, confianca, origem FROM constitution_entries WHERE nicho=?",
            (nicho,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── API de consulta ao catálogo de ferragens ─────────────────────────────────

def _extrair_codigo_normalizado(codigo: str) -> str:
    """Extrai número base de 4 dígitos de qualquer formato de código."""
    m = re.search(r'\d{4}', codigo)
    return m.group(0) if m else codigo


def buscar_kit(numero: str, fabricante_id: str = None) -> List[dict]:
    """Busca kit por número. Se fabricante_id=None, retorna todos os fabricantes."""
    conn = _get_conn()
    if fabricante_id:
        rows = conn.execute(
            "SELECT k.*, f.nome as fabricante_nome FROM kits k "
            "JOIN fabricantes f ON f.id = k.fabricante_id "
            "WHERE k.numero=? AND k.fabricante_id=?",
            (numero, fabricante_id)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT k.*, f.nome as fabricante_nome FROM kits k "
            "JOIN fabricantes f ON f.id = k.fabricante_id "
            "WHERE k.numero=?",
            (numero,)
        ).fetchall()

    resultado = []
    for row in rows:
        kit = dict(row)
        # Carregar componentes
        comps = conn.execute(
            "SELECT * FROM kit_componentes WHERE kit_id=?", (kit["id"],)
        ).fetchall()
        kit["componentes"] = [dict(c) for c in comps]
        if kit.get("max_vao_json"):
            kit["max_vao"] = json.loads(kit["max_vao_json"])
        if kit.get("acabamentos_json"):
            kit["acabamentos"] = json.loads(kit["acabamentos_json"])
        resultado.append(kit)

    conn.close()
    return resultado


def buscar_ferragem(codigo: str) -> Optional[dict]:
    """Busca ferragem por código (aceita qualquer formato: 'HE 1101A', '1101', '1101A')."""
    conn = _get_conn()
    # Busca exata primeiro
    row = conn.execute(
        "SELECT f.*, fab.nome as fabricante_nome FROM ferragens f "
        "JOIN fabricantes fab ON fab.id = f.fabricante_id "
        "WHERE f.codigo=?", (codigo,)
    ).fetchone()

    if not row:
        # Busca por código normalizado
        norm = _extrair_codigo_normalizado(codigo)
        row = conn.execute(
            "SELECT f.*, fab.nome as fabricante_nome FROM ferragens f "
            "JOIN fabricantes fab ON fab.id = f.fabricante_id "
            "WHERE f.codigo_normalizado=? LIMIT 1", (norm,)
        ).fetchone()

    conn.close()
    if row:
        resultado = dict(row)
        if resultado.get("dimensoes_json"):
            resultado["dimensoes"] = json.loads(resultado["dimensoes_json"])
        if resultado.get("cores_json"):
            resultado["cores"] = json.loads(resultado["cores_json"])
        if resultado.get("espessura_vidro"):
            resultado["espessura_vidro_mm"] = json.loads(resultado["espessura_vidro"])
        return resultado
    return None


def buscar_equivalentes(codigo: str) -> List[dict]:
    """Dado um código de qualquer fabricante, retorna equivalentes dos outros."""
    norm = _extrair_codigo_normalizado(codigo)
    conn = _get_conn()
    rows = conn.execute(
        "SELECT e.*, f.nome as fabricante_nome FROM equivalencias e "
        "JOIN fabricantes f ON f.id = e.fabricante_id "
        "WHERE e.codigo_normalizado=?", (norm,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_recortes(codigo_ferragem: str) -> List[dict]:
    """Retorna recortes necessários para uma ferragem."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT r.*, f.nome as fabricante_nome FROM recortes r "
        "JOIN fabricantes f ON f.id = r.fabricante_id "
        "WHERE r.ferragem_codigo=?", (codigo_ferragem,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def listar_kits(fabricante_id: str = None) -> List[dict]:
    """Lista todos os kits, opcionalmente filtrando por fabricante."""
    conn = _get_conn()
    if fabricante_id:
        rows = conn.execute(
            "SELECT k.*, f.nome as fabricante_nome FROM kits k "
            "JOIN fabricantes f ON f.id = k.fabricante_id "
            "WHERE k.fabricante_id=? ORDER BY k.numero",
            (fabricante_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT k.*, f.nome as fabricante_nome FROM kits k "
            "JOIN fabricantes f ON f.id = k.fabricante_id "
            "ORDER BY k.fabricante_id, k.numero"
        ).fetchall()
    conn.close()
    resultado = []
    for row in rows:
        kit = dict(row)
        if kit.get("max_vao_json"):
            kit["max_vao"] = json.loads(kit["max_vao_json"])
        if kit.get("acabamentos_json"):
            kit["acabamentos"] = json.loads(kit["acabamentos_json"])
        resultado.append(kit)
    return resultado


def buscar_folga_nbr(tipo: str) -> Optional[float]:
    """Retorna folga NBR em mm pelo tipo. Ex: 'movel_fixo' → 3.0. Retorna None se não encontrado."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT valor_mm FROM folgas_nbr WHERE tipo = ?", (tipo,)
    ).fetchone()
    conn.close()
    return row["valor_mm"] if row else None


def todas_folgas_nbr() -> dict:
    """Retorna todas as folgas NBR como dict {tipo: valor_mm}."""
    conn = _get_conn()
    rows = conn.execute("SELECT tipo, valor_mm FROM folgas_nbr").fetchall()
    conn.close()
    return {r["tipo"]: r["valor_mm"] for r in rows}


def get_stats() -> dict:
    """Retorna contagem de registros por tabela."""
    conn = _get_conn()
    stats = {}
    # tabela vem de lista literal interna — sem risco de SQL injection
    _TABELAS_VALIDAS = frozenset([
        "fabricantes", "ferragens", "kits", "kit_componentes",
        "recortes", "equivalencias", "formulas", "folgas_nbr",
        "constitution_entries", "constitution_aliases",
    ])
    for tabela in _TABELAS_VALIDAS:
        try:
            row = conn.execute(f"SELECT COUNT(*) as n FROM {tabela}").fetchone()
            stats[tabela] = row["n"]
        except Exception as e:
            log.warning(f"get_stats: falha ao contar '{tabela}': {e}")
            stats[tabela] = 0
    conn.close()
    return stats
