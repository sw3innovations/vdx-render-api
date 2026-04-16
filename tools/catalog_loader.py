#!/usr/bin/env python3
"""
VDX Catalog Loader — Popula Constitution DB com dados dos catálogos de ferragens.

Uso:
    python -m tools.catalog_loader                    # carrega todos
    python -m tools.catalog_loader --fabricante HE    # carrega só HELA
    python -m tools.catalog_loader --dry-run          # simula sem gravar
    python -m tools.catalog_loader --stats            # mostra estatísticas
"""
import argparse
import json
import logging
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


def _load_json_file(path: Path, fabricante_id: str) -> Optional[dict]:
    """Carrega um arquivo JSON de catálogo com erro tipado e isolado.

    Retorna None se o arquivo não existe ou tem JSON corrompido — o loader
    continua com os outros fabricantes. Levanta IOError/PermissionError apenas
    para erros de sistema (disco cheio, sem permissão), que devem parar tudo.
    """
    if not path.exists():
        log.warning("[%s] Arquivo não encontrado: %s — pulando", fabricante_id, path)
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log.error(
            "[%s] JSON inválido em %s: linha %d, coluna %d: %s",
            fabricante_id, path.name, e.lineno, e.colno, e.msg,
        )
        return None
    except UnicodeDecodeError as e:
        log.error("[%s] Encoding inválido em %s: %s", fabricante_id, path.name, e)
        return None
    # IOError / PermissionError propagam intencionalmente — erro de sistema, não de dado

# Garante que o root do projeto está no sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.constitution import DB_PATH, _get_conn, migrate, normalizar_formula

# ─── Caminhos dos catálogos ───────────────────────────────────────────────────

CATALOG_DIR = ROOT / "data" / "catalogs"
HELA_JSON    = CATALOG_DIR / "catalogo_hela.json"
AL_JSON      = CATALOG_DIR / "catalogo_al_industria.json"

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _norm_tipo(tipo: str) -> str:
    """Normaliza tipo de ferragem para minúsculas sem acentos."""
    if not tipo:
        return ""
    s = unicodedata.normalize('NFD', tipo.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^a-z0-9_]', '_', s)
    return s.strip('_')


def _extrair_codigo_normalizado(codigo: str) -> str:
    """Extrai número base de 4 dígitos de qualquer formato de código.
    'HE 1101A' → '1101', '1101SG' → '1101', 'AL 1101A' → '1101'
    """
    m = re.search(r'\d{4}', str(codigo))
    return m.group(0) if m else codigo


def _j(value) -> str | None:
    """Serializa value para JSON string, ou None se vazio/None."""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


# Chaves que identificam um recorte de contexto único (vs. multi-contexto)
_SINGLE_RECORTE_KEYS = frozenset({
    "comprimento", "largura", "furo_diametro", "furo", "raio",
    "dist_borda", "altura", "profundidade",
})


def _is_multi_context_recorte(recorte_raw: dict) -> bool:
    """Detecta recorte multi-contexto: nenhuma chave dimensional no nível raiz,
    mas os valores são dicts. Ex: {"p_janela": {"furo_diametro": 25}, "p_porta": {...}}"""
    return (
        isinstance(recorte_raw, dict)
        and not any(k in _SINGLE_RECORTE_KEYS for k in recorte_raw)
        and any(isinstance(v, dict) for v in recorte_raw.values())
    )


def parse_recorte_multi_contexto(recorte_raw: dict) -> list[dict]:
    """Parseia recorte multi-contexto em lista de recortes individuais com contexto.

    'p_janela' → contexto='janela', 'p_porta' → contexto='porta'.
    Prefixo 'p_' é removido; underscores viram espaços.
    Retorna lista de dicts com chaves: contexto, comp_mm, larg_mm, furo_mm, raio_mm.
    """
    resultado = []
    for chave_ctx, dims in recorte_raw.items():
        if not isinstance(dims, dict):
            continue
        contexto = chave_ctx.removeprefix("p_").replace("_", " ")
        resultado.append({
            "contexto": contexto,
            "comp_mm":  dims.get("comprimento"),
            "larg_mm":  dims.get("largura"),
            "furo_mm":  dims.get("furo_diametro") or dims.get("furo"),
            "raio_mm":  dims.get("raio"),
        })
    return resultado


def inferir_tipo_recorte(
    comprimento: float | None,
    largura: float | None,
    furo_diametro: float | None,
    raio: float | None,
    nome_ferragem: str = "",
) -> str:
    """Infere tipo de recorte a partir das dimensões disponíveis.

    Regras (por ordem de prioridade):
    1. Só furo sem dimensões retangulares → 'furo_passante'
    2. Comp + larg + furo + raio → 'retangular_arredondado' (fechaduras)
    3. Comp + larg + furo (sem raio) → 'onda' (dobradiças / pivôs)
    4. Comp + larg + raio (sem furo) → 'retangular_arredondado'
    5. Comp + larg → 'retangular'
    6. Fallback por nome da ferragem → default 'furo_passante'
    """
    tem_furo = furo_diametro is not None and furo_diametro > 0
    tem_comp = comprimento is not None and comprimento > 0
    tem_larg = largura is not None and largura > 0
    tem_raio = raio is not None and raio > 0

    if tem_furo and not tem_comp and not tem_larg:
        return "furo_passante"
    if tem_comp and tem_larg and tem_furo and tem_raio:
        return "retangular_arredondado"
    if tem_comp and tem_larg and tem_furo:
        return "onda"
    if tem_comp and tem_larg and tem_raio:
        return "retangular_arredondado"
    if tem_comp and tem_larg:
        return "retangular"

    # Fallback por nome
    nome = nome_ferragem.lower()
    if any(p in nome for p in ("dobradica", "dobradiça", "pivo", "pivô")):
        return "onda"
    if any(p in nome for p in ("fechadura", "fecho", "fechamento")):
        return "retangular_arredondado"
    if any(p in nome for p in ("trinco", "trava")):
        return "retangular"
    if any(p in nome for p in ("botao", "botão", "puxador", "suporte")):
        return "furo_passante"

    return "furo_passante"


# ─── Dados Glasspeças/Santa Marina (inline) ───────────────────────────────────

GLASSPECAS_DATA = {
    "fabricante": {
        "id": "SM",
        "nome": "Glasspeças / Santa Marina",
        "prefixo": "SM",
    },
    "produtos": [
        {"codigo": "1201SG", "nome": "Pivô Superior",             "tipo": "pivo",      "material": "Zamac"},
        {"codigo": "1101SG", "nome": "Dobradiça Superior 1101",   "tipo": "dobradica", "material": "Zamac"},
        {"codigo": "1103SG", "nome": "Dobradiça Inferior 1103",   "tipo": "dobradica", "material": "Zamac"},
        {"codigo": "1013SG", "nome": "Pivô Inferior",             "tipo": "pivo",      "material": "Zamac"},
        {"codigo": "1520G",  "nome": "Fechadura Central 1520",    "tipo": "fechadura", "material": "Zamac"},
        {"codigo": "1504AG", "nome": "Contra Fechadura 1504A",    "tipo": "contra_fechadura", "material": "Zamac"},
        {"codigo": "1510G",  "nome": "Bico-Papagaio 1510",        "tipo": "bico_papagaio",    "material": "Zamac"},
    ],
    "kits": [
        {
            "numero": "01",
            "nome": "Porta Simples Pivotante",
            "componentes": [
                {"codigo": "1201SG", "nome": "Pivô Superior",        "quantidade": 1},
                {"codigo": "1101SG", "nome": "Dobradiça Superior",   "quantidade": 1},
                {"codigo": "1103SG", "nome": "Dobradiça Inferior",   "quantidade": 1},
                {"codigo": "1013SG", "nome": "Pivô Inferior",        "quantidade": 1},
                {"codigo": "1520G",  "nome": "Fechadura",            "quantidade": 1},
                {"codigo": "1504AG", "nome": "Contra Fechadura",     "quantidade": 1},
            ],
            "max_vao": {"opcao1": "1000x2200mm", "opcao2": "900x2600mm"},
        },
    ],
    "recortes": [
        {"ferragens_compativeis": ["1101SG"], "tipo": "onda",        "comprimento_mm": 110, "largura_mm": 25, "furo_diametro_mm": 25},
        {"ferragens_compativeis": ["1103SG"], "tipo": "onda",        "comprimento_mm": 125, "largura_mm": 25, "furo_diametro_mm": 25},
        {"ferragens_compativeis": ["1520G"],  "tipo": "retangular",  "comprimento_mm": 73,  "largura_mm": 45, "raio_mm": 8},
        {"ferragens_compativeis": ["1510G"],  "tipo": "retangular",  "comprimento_mm": 120, "largura_mm": 45, "raio_mm": 5},
    ],
    "folgas_nbr": [
        {"tipo": "movel_fixo",      "valor_mm": 3, "fonte": "Glasspeças catálogo p.94"},
        {"tipo": "movel_movel",     "valor_mm": 4, "fonte": "Glasspeças catálogo p.94"},
        {"tipo": "movel_piso",      "valor_mm": 8, "fonte": "Glasspeças catálogo p.94"},
        {"tipo": "fixo_fixo",       "valor_mm": 1, "fonte": "Glasspeças catálogo p.94"},
        {"tipo": "movel_alvenaria", "valor_mm": 5, "fonte": "Glasspeças catálogo p.94"},
    ],
    "formulas": [
        {
            "nome": "basculante_posicao_x",
            "formula": "(48000 / largura + altura) / 2",
            "variaveis": {"largura": "largura da janela em mm", "altura": "altura da janela em mm"},
            "notas": "Fórmula Glasspeças para posição X do trinco basculante V/A",
        }
    ],
    "equivalencias": [
        {"codigo_normalizado": "1101", "codigo_fabricante": "1101SG"},
        {"codigo_normalizado": "1103", "codigo_fabricante": "1103SG"},
        {"codigo_normalizado": "1201", "codigo_fabricante": "1201SG"},
        {"codigo_normalizado": "1013", "codigo_fabricante": "1013SG"},
        {"codigo_normalizado": "1520", "codigo_fabricante": "1520G"},
        {"codigo_normalizado": "1504", "codigo_fabricante": "1504AG"},
    ],
}

# Equivalências entre fabricantes (mesma peça, códigos diferentes)
EQUIVALENCIAS_CROSS = [
    {"codigo_normalizado": "1101", "HE": "HE 1101A", "AL": "1101A",  "SM": "1101SG"},
    {"codigo_normalizado": "1103", "HE": "HE 1103A", "AL": "1103A",  "SM": "1103SG"},
    {"codigo_normalizado": "1201", "HE": "HE 1201A", "AL": "1201A",  "SM": "1201SG"},
    {"codigo_normalizado": "1013", "HE": "HE 1013F", "AL": "1013F",  "SM": "1013SG"},
    {"codigo_normalizado": "1520", "HE": "HE 1520",  "AL": "1520",   "SM": "1520G"},
    {"codigo_normalizado": "1504", "HE": "HE 1504A", "AL": "1504A",  "SM": "1504AG"},
]


# ─── Loader por fabricante ────────────────────────────────────────────────────

class CatalogLoader:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.conn: sqlite3.Connection | None = None
        self.contadores: dict = {
            "fabricantes": 0,
            "ferragens":   0,
            "kits":        0,
            "kit_componentes": 0,
            "recortes":    0,
            "equivalencias": 0,
            "formulas":    0,
            "folgas_nbr":  0,
        }

    def __enter__(self):
        if not self.dry_run:
            self.conn = _get_conn()
        return self

    def __exit__(self, *_):
        if self.conn:
            self.conn.commit()
            self.conn.close()

    def _exec(self, sql: str, params: tuple = ()):
        self.contadores  # acessa só pra não otimizar
        if self.dry_run:
            return None
        cur = self.conn.execute(sql, params)
        return cur

    def _upsert_fabricante(self, fab_id: str, nome: str, prefixo: str, metadata: dict = None):
        self._exec("""
            INSERT INTO fabricantes (id, nome, prefixo, metadata)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                nome=excluded.nome, prefixo=excluded.prefixo, metadata=excluded.metadata
        """, (fab_id, nome, prefixo, _j(metadata)))
        self.contadores["fabricantes"] += 1

    def _upsert_ferragem(self, codigo: str, fab_id: str, nome: str, tipo: str = None,
                          material: str = None, dimensoes: dict = None,
                          espessura_vidro=None, cores: dict = None,
                          pagina: int = None, fonte: str = None) -> int | None:
        norm = _extrair_codigo_normalizado(codigo)
        esp_json = _j(espessura_vidro) if isinstance(espessura_vidro, list) else (
            _j([espessura_vidro]) if espessura_vidro else None
        )
        if self.dry_run:
            self.contadores["ferragens"] += 1
            return None
        cur = self.conn.execute("""
            INSERT INTO ferragens
                (codigo, codigo_normalizado, fabricante_id, nome, tipo, material,
                 dimensoes_json, espessura_vidro, cores_json, pagina_catalogo, fonte)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(codigo, fabricante_id) DO UPDATE SET
                nome=excluded.nome, tipo=excluded.tipo, material=excluded.material,
                dimensoes_json=excluded.dimensoes_json, espessura_vidro=excluded.espessura_vidro,
                cores_json=excluded.cores_json, pagina_catalogo=excluded.pagina_catalogo,
                fonte=excluded.fonte
        """, (codigo, norm, fab_id, nome, _norm_tipo(tipo or ""), material,
              _j(dimensoes), esp_json, _j(cores), pagina, fonte))
        self.contadores["ferragens"] += 1
        return cur.lastrowid

    def _upsert_kit(self, numero: str, fab_id: str, nome: str, linha: str = None,
                     max_vao: dict = None, acabamentos=None, pagina: int = None) -> int | None:
        if self.dry_run:
            self.contadores["kits"] += 1
            return None
        cur = self.conn.execute("""
            INSERT INTO kits (numero, fabricante_id, nome, linha, max_vao_json, acabamentos_json, pagina_catalogo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(numero, fabricante_id) DO UPDATE SET
                nome=excluded.nome, linha=excluded.linha, max_vao_json=excluded.max_vao_json,
                acabamentos_json=excluded.acabamentos_json, pagina_catalogo=excluded.pagina_catalogo
        """, (numero, fab_id, nome, linha, _j(max_vao), _j(acabamentos), pagina))
        self.contadores["kits"] += 1
        return cur.lastrowid

    def _get_kit_id(self, numero: str, fab_id: str) -> int | None:
        if self.dry_run or not self.conn:
            return None
        row = self.conn.execute(
            "SELECT id FROM kits WHERE numero=? AND fabricante_id=?", (numero, fab_id)
        ).fetchone()
        return row["id"] if row else None

    def _insert_kit_componente(self, kit_id: int, ferragem_codigo: str, quantidade: int = 1,
                                posicao: str = None, nome: str = None):
        if self.dry_run:
            self.contadores["kit_componentes"] += 1
            return
        self.conn.execute("""
            INSERT INTO kit_componentes (kit_id, ferragem_codigo, quantidade, posicao, nome)
            VALUES (?, ?, ?, ?, ?)
        """, (kit_id, ferragem_codigo, quantidade, posicao, nome))
        self.contadores["kit_componentes"] += 1

    def _insert_recorte(self, ferragem_codigo: str, fab_id: str, tipo: str = None,
                         comp_mm: float = None, larg_mm: float = None,
                         furo_mm: float = None, raio_mm: float = None,
                         notas: str = None, pagina: int = None,
                         contexto: str = None, nome_ferragem: str = ""):
        # Inferir tipo quando não fornecido — nunca inserir NULL no campo tipo
        if tipo is None:
            tipo = inferir_tipo_recorte(comp_mm, larg_mm, furo_mm, raio_mm, nome_ferragem)
        if self.dry_run:
            self.contadores["recortes"] += 1
            return
        self.conn.execute("""
            INSERT INTO recortes
                (ferragem_codigo, fabricante_id, tipo, comprimento_mm, largura_mm,
                 furo_diametro_mm, raio_mm, notas, pagina_catalogo, contexto_aplicacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ferragem_codigo, fab_id, tipo, comp_mm, larg_mm, furo_mm, raio_mm,
              notas, pagina, contexto))
        self.contadores["recortes"] += 1

    def _upsert_equivalencia(self, codigo_norm: str, fab_id: str, codigo_fab: str):
        if self.dry_run:
            self.contadores["equivalencias"] += 1
            return
        self.conn.execute("""
            INSERT INTO equivalencias (codigo_normalizado, fabricante_id, codigo_fabricante)
            VALUES (?, ?, ?)
            ON CONFLICT(fabricante_id, codigo_fabricante) DO UPDATE SET
                codigo_normalizado=excluded.codigo_normalizado
        """, (codigo_norm, fab_id, codigo_fab))
        self.contadores["equivalencias"] += 1

    def _upsert_formula(self, nome: str, formula: str, variaveis: dict = None,
                         ferragens: list = None, notas: str = None, fab_id: str = None):
        # Normalizar variáveis para minúsculas — contrato VDX obrigatório
        formula = normalizar_formula(formula)
        if self.dry_run:
            self.contadores["formulas"] += 1
            return
        row = self.conn.execute("SELECT id FROM formulas WHERE nome=?", (nome,)).fetchone()
        if row:
            self.conn.execute("""
                UPDATE formulas SET formula=?, variaveis_json=?, ferragens_aplicaveis=?,
                    notas=?, fabricante_id=? WHERE nome=?
            """, (formula, _j(variaveis), _j(ferragens), notas, fab_id, nome))
        else:
            self.conn.execute("""
                INSERT INTO formulas (nome, formula, variaveis_json, ferragens_aplicaveis, notas, fabricante_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nome, formula, _j(variaveis), _j(ferragens), notas, fab_id))
        self.contadores["formulas"] += 1

    def _upsert_folga(self, tipo: str, valor_mm: float, fonte: str = None):
        if self.dry_run:
            self.contadores["folgas_nbr"] += 1
            return
        self.conn.execute("""
            INSERT INTO folgas_nbr (tipo, valor_mm, fonte)
            VALUES (?, ?, ?)
            ON CONFLICT(tipo) DO UPDATE SET valor_mm=excluded.valor_mm, fonte=excluded.fonte
        """, (tipo, valor_mm, fonte))
        self.contadores["folgas_nbr"] += 1

    # ── Loaders por fabricante ────────────────────────────────────────────────

    def carregar_hela(self):
        data = _load_json_file(HELA_JSON, "HE")
        if data is None:
            print("[HE] AVISO: catálogo HELA não carregado (arquivo ausente ou JSON inválido)")
            return
        fab = data["fabricante"]
        fab_id = fab.get("prefixo", "HE")

        self._upsert_fabricante(fab_id, fab["nome"], fab.get("prefixo", "HE"))
        print(f"[HE] Fabricante: {fab['nome']} ({fab_id})")

        # Produtos
        produtos = data.get("produtos", [])
        print(f"[HE] Carregando {len(produtos)} ferragens...")
        for p in produtos:
            self._upsert_ferragem(
                codigo=p["codigo"], fab_id=fab_id, nome=p["nome"],
                tipo=p.get("tipo"), material=p.get("material"),
                dimensoes=p.get("dimensoes_mm"),
                espessura_vidro=p.get("espessura_vidro_mm"),
                pagina=p.get("pagina_catalogo"),
                fonte=f"catalogo_hela.json p.{p.get('pagina_catalogo', '?')}",
            )
            # Equivalência
            norm = _extrair_codigo_normalizado(p["codigo"])
            if norm:
                self._upsert_equivalencia(norm, fab_id, p["codigo"])

        # Kits
        kits = data.get("kits", [])
        print(f"[HE] Carregando {len(kits)} kits...")
        for k in kits:
            num = str(k["numero"])
            self._upsert_kit(
                numero=num, fab_id=fab_id, nome=k["nome"],
                linha=k.get("linha"),
                acabamentos=k.get("acabamentos"),
                pagina=k.get("pagina_catalogo"),
            )
            kit_id = self._get_kit_id(num, fab_id)
            if kit_id:
                # Limpar componentes antigos antes de re-inserir (idempotência)
                if not self.dry_run:
                    self.conn.execute("DELETE FROM kit_componentes WHERE kit_id=?", (kit_id,))
                for comp in k.get("componentes", []):
                    self._insert_kit_componente(
                        kit_id=kit_id,
                        ferragem_codigo=comp["codigo"],
                        quantidade=comp.get("quantidade", 1),
                        nome=comp.get("nome"),
                    )

        # Recortes
        recortes = data.get("recortes", [])
        print(f"[HE] Carregando {len(recortes)} recortes...")
        # Limpar recortes do fabricante antes de re-inserir
        if not self.dry_run:
            self.conn.execute("DELETE FROM recortes WHERE fabricante_id=?", (fab_id,))
        for r in recortes:
            dim = r.get("dimensoes_mm", {})
            for codigo_ferr in r.get("ferragens_compativeis", []):
                self._insert_recorte(
                    ferragem_codigo=codigo_ferr, fab_id=fab_id,
                    tipo=r.get("tipo_recorte"),
                    comp_mm=dim.get("comprimento") if isinstance(dim, dict) else None,
                    larg_mm=dim.get("largura") if isinstance(dim, dict) else None,
                    furo_mm=dim.get("furo_diametro") if isinstance(dim, dict) else None,
                    raio_mm=dim.get("raio") if isinstance(dim, dict) else None,
                    nome_ferragem=r.get("nome", codigo_ferr),
                    pagina=r.get("pagina_catalogo"),
                )

        print(f"[HE] ✓ HELA carregada")

    def carregar_al(self):
        data = _load_json_file(AL_JSON, "AL")
        if data is None:
            print("[AL] AVISO: catálogo AL Indústria não carregado (arquivo ausente ou JSON inválido)")
            return
        fab = data["fabricante"]
        fab_id = fab.get("prefixo", "AL")

        self._upsert_fabricante(fab_id, fab["nome"], fab.get("prefixo", "AL"))
        print(f"[AL] Fabricante: {fab['nome']} ({fab_id})")

        # Produtos (recortes inline)
        produtos = data.get("produtos", [])
        print(f"[AL] Carregando {len(produtos)} ferragens...")
        recortes_inline = 0
        if not self.dry_run:
            self.conn.execute("DELETE FROM recortes WHERE fabricante_id=?", (fab_id,))
        for p in produtos:
            cores = {}
            if p.get("cores_capa"):
                cores["capa"] = p["cores_capa"]
            if p.get("cores_tradicional"):
                cores["tradicional"] = p["cores_tradicional"]
            self._upsert_ferragem(
                codigo=p["codigo"], fab_id=fab_id, nome=p["nome"],
                tipo=p.get("tipo"), material=p.get("material"),
                dimensoes=p.get("dimensoes_mm"),
                espessura_vidro=p.get("espessura_vidro_mm"),
                cores=cores or None,
                pagina=p.get("pagina_catalogo"),
                fonte=f"catalogo_al_industria.json p.{p.get('pagina_catalogo', '?')}",
            )
            # Equivalência
            norm = _extrair_codigo_normalizado(p["codigo"])
            if norm:
                self._upsert_equivalencia(norm, fab_id, p["codigo"])

            # Recortes INLINE no campo recorte_mm
            recorte_raw = p.get("recorte_mm")
            if recorte_raw:
                if isinstance(recorte_raw, dict) and _is_multi_context_recorte(recorte_raw):
                    # Recorte varia por aplicação: inserir um registro por contexto
                    for ctx in parse_recorte_multi_contexto(recorte_raw):
                        self._insert_recorte(
                            ferragem_codigo=p["codigo"], fab_id=fab_id,
                            comp_mm=ctx["comp_mm"], larg_mm=ctx["larg_mm"],
                            furo_mm=ctx["furo_mm"], raio_mm=ctx["raio_mm"],
                            contexto=ctx["contexto"],
                            nome_ferragem=p.get("nome", ""),
                            pagina=p.get("pagina_catalogo"),
                        )
                        recortes_inline += 1
                elif isinstance(recorte_raw, dict):
                    self._insert_recorte(
                        ferragem_codigo=p["codigo"], fab_id=fab_id,
                        comp_mm=recorte_raw.get("comprimento"),
                        larg_mm=recorte_raw.get("largura"),
                        furo_mm=recorte_raw.get("furo_diametro") or recorte_raw.get("furo"),
                        raio_mm=recorte_raw.get("raio"),
                        nome_ferragem=p.get("nome", ""),
                        pagina=p.get("pagina_catalogo"),
                    )
                    recortes_inline += 1
                elif isinstance(recorte_raw, str) and recorte_raw.strip():
                    # String crua não estruturada — não deve ocorrer com catálogos bem formados
                    self._insert_recorte(
                        ferragem_codigo=p["codigo"], fab_id=fab_id,
                        notas=recorte_raw, nome_ferragem=p.get("nome", ""),
                        pagina=p.get("pagina_catalogo"),
                    )
                    recortes_inline += 1

        print(f"[AL] Extraindo {recortes_inline} recortes inline...")

        # Kits
        kits = data.get("kits", [])
        print(f"[AL] Carregando {len(kits)} kits...")
        for k in kits:
            num = str(k["numero"])
            self._upsert_kit(numero=num, fab_id=fab_id, nome=k["nome"])
            kit_id = self._get_kit_id(num, fab_id)
            if kit_id:
                if not self.dry_run:
                    self.conn.execute("DELETE FROM kit_componentes WHERE kit_id=?", (kit_id,))
                for comp in k.get("componentes", []):
                    self._insert_kit_componente(
                        kit_id=kit_id,
                        ferragem_codigo=comp["codigo"],
                        posicao=comp.get("posicao"),
                        nome=comp.get("nome"),
                    )

        # Fórmulas (se existir no catálogo AL)
        for f in data.get("formulas", []):
            self._upsert_formula(
                nome=f.get("nome", "formula_al"),
                formula=f.get("formula", ""),
                fab_id=fab_id,
            )

        print(f"[AL] ✓ AL Indústria carregada")

    def carregar_glasspecas(self):
        data = GLASSPECAS_DATA
        fab = data["fabricante"]
        fab_id = fab["id"]

        self._upsert_fabricante(fab_id, fab["nome"], fab["prefixo"])
        print(f"[SM] Fabricante: {fab['nome']} ({fab_id})")

        # Produtos
        produtos = data["produtos"]
        print(f"[SM] Carregando {len(produtos)} ferragens...")
        for p in produtos:
            self._upsert_ferragem(
                codigo=p["codigo"], fab_id=fab_id, nome=p["nome"],
                tipo=p.get("tipo"), material=p.get("material"),
                fonte="Glasspeças catálogo Santa Marina",
            )
            norm = _extrair_codigo_normalizado(p["codigo"])
            if norm:
                self._upsert_equivalencia(norm, fab_id, p["codigo"])

        # Kits
        kits = data["kits"]
        print(f"[SM] Carregando {len(kits)} kits...")
        for k in kits:
            num = str(k["numero"])
            self._upsert_kit(
                numero=num, fab_id=fab_id, nome=k["nome"],
                max_vao=k.get("max_vao"),
            )
            kit_id = self._get_kit_id(num, fab_id)
            if kit_id:
                if not self.dry_run:
                    self.conn.execute("DELETE FROM kit_componentes WHERE kit_id=?", (kit_id,))
                for comp in k.get("componentes", []):
                    self._insert_kit_componente(
                        kit_id=kit_id,
                        ferragem_codigo=comp["codigo"],
                        quantidade=comp.get("quantidade", 1),
                        nome=comp.get("nome"),
                    )

        # Recortes
        print(f"[SM] Carregando {len(data['recortes'])} recortes...")
        if not self.dry_run:
            self.conn.execute("DELETE FROM recortes WHERE fabricante_id=?", (fab_id,))
        for r in data["recortes"]:
            for codigo_ferr in r.get("ferragens_compativeis", []):
                self._insert_recorte(
                    ferragem_codigo=codigo_ferr, fab_id=fab_id,
                    tipo=r.get("tipo"),
                    comp_mm=r.get("comprimento_mm"),
                    larg_mm=r.get("largura_mm"),
                    furo_mm=r.get("furo_diametro_mm"),
                    raio_mm=r.get("raio_mm"),
                )

        # Folgas NBR
        for folga in data["folgas_nbr"]:
            self._upsert_folga(folga["tipo"], folga["valor_mm"], folga["fonte"])
        print(f"[SM] Folgas NBR: {len(data['folgas_nbr'])} registros")

        # Fórmulas
        for f in data["formulas"]:
            self._upsert_formula(
                nome=f["nome"], formula=f["formula"],
                variaveis=f.get("variaveis"), notas=f.get("notas"), fab_id=fab_id,
            )
        print(f"[SM] ✓ Glasspeças carregada")

    def carregar_equivalencias_cross(self):
        """Carrega as equivalências cruzadas entre todos os fabricantes."""
        print("[CROSS] Carregando equivalências entre fabricantes...")
        for eq in EQUIVALENCIAS_CROSS:
            norm = eq["codigo_normalizado"]
            for fab_id, codigo in eq.items():
                if fab_id == "codigo_normalizado":
                    continue
                self._upsert_equivalencia(norm, fab_id, codigo)
        print(f"[CROSS] ✓ {len(EQUIVALENCIAS_CROSS) * 3} equivalências registradas")

    def mostrar_stats(self):
        from app.core.constitution import get_stats
        stats = get_stats()
        print("\n── Estatísticas da Constitution DB ──────────────────────────")
        for tabela, count in stats.items():
            print(f"  {tabela:<30} {count:>6} registros")
        print("─────────────────────────────────────────────────────────────\n")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="VDX Catalog Loader — Popula Constitution DB com catálogos de ferragens"
    )
    parser.add_argument("--fabricante", choices=["HE", "AL", "SM"],
                        help="Carrega apenas um fabricante específico")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simula sem gravar no banco")
    parser.add_argument("--stats", action="store_true",
                        help="Mostra estatísticas do banco ao final")
    args = parser.parse_args()

    if args.dry_run:
        print("🔍 Modo DRY-RUN — nenhuma alteração será gravada\n")

    # Garante que as tabelas existem
    if not args.dry_run:
        migrate()

    with CatalogLoader(dry_run=args.dry_run) as loader:
        if args.fabricante == "HE":
            loader.carregar_hela()
        elif args.fabricante == "AL":
            loader.carregar_al()
        elif args.fabricante == "SM":
            loader.carregar_glasspecas()
        else:
            loader.carregar_hela()
            loader.carregar_al()
            loader.carregar_glasspecas()
            loader.carregar_equivalencias_cross()

        c = loader.contadores
        print(
            f"\n✓ Constitution populada: "
            f"{c['ferragens']} ferragens, "
            f"{c['kits']} kits, "
            f"{c['recortes']} recortes, "
            f"{c['equivalencias']} equivalências"
        )

    if args.stats or not args.dry_run:
        loader.mostrar_stats()


if __name__ == "__main__":
    main()
