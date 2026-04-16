"""
Serviço de geração de proposta comercial em PDF.

Fluxo:
1. Pré-renderiza SVG de cada item via render_orchestrator (async)
2. Converte SVG→PNG via cairosvg para embutir no PDF
3. Monta PDF com FPDF2:
   - Cabeçalho white-label (logo + dados da empresa)
   - Dados do cliente
   - Tabela de itens com preços em BRL
   - Página de desenho técnico por item (opcional)
   - Condições de pagamento + observações
4. Retorna bytes do PDF

Dependências: fpdf2, cairosvg, Pillow (já no requirements.txt).
"""
from __future__ import annotations

import base64
import io
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional

import cairosvg
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image

from app.models.proposal import (
    ClienteInfo,
    CondicoesPagamento,
    EmpresaInfo,
    ItemProposta,
    ProposalRequest,
)
from app.models.render import PecaInput, RenderRequest
from app.services.render_orchestrator import executar

log = logging.getLogger(__name__)

# ── Sequencial de proposta (thread-safe, reinicia a cada deploy) ──────────────
_seq_lock = threading.Lock()
_seq_by_date: dict[str, int] = {}


def _gerar_numero(numero_proposta: Optional[str] = None) -> str:
    """Gera número da proposta VDX-YYYYMMDD-NNN, ou devolve o fornecido."""
    if numero_proposta:
        return numero_proposta
    date_str = datetime.now().strftime("%Y%m%d")
    with _seq_lock:
        _seq_by_date[date_str] = _seq_by_date.get(date_str, 0) + 1
        seq = _seq_by_date[date_str]
    return f"VDX-{date_str}-{seq:03d}"


def _fmt_brl(valor: Optional[float]) -> str:
    """Formata valor monetário em R$ brasileiro (1.250,00)."""
    if valor is None:
        return "-"
    s = f"{valor:,.2f}"          # "1,250.00"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _hex_rgb(hex_color: str) -> tuple[int, int, int]:
    """Converte '#1a5276' → (26, 82, 118)."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (26, 82, 118)  # fallback azul VDX
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return (26, 82, 118)


def _lighter(rgb: tuple[int, int, int], factor: float = 0.85) -> tuple[int, int, int]:
    """Clareia uma cor RGB misturando com branco."""
    r, g, b = rgb
    return (
        min(255, int(r + (255 - r) * factor)),
        min(255, int(g + (255 - g) * factor)),
        min(255, int(b + (255 - b) * factor)),
    )


# ── Render helper ─────────────────────────────────────────────────────────────

async def _render_item(item: ItemProposta) -> Optional[str]:
    """Renderiza um item e retorna o SVG. Retorna None em caso de falha (graceful)."""
    try:
        req = RenderRequest(
            tipologia_nome=item.tipologia,
            pecas=[PecaInput(
                nome=item.descricao,
                largura_mm=item.largura,
                altura_mm=item.altura,
            )],
            espessura_vidro_mm=float(item.espessura or 8),
        )
        result = await executar(req)
        return result.svg if result.svg else None
    except Exception as e:
        log.warning("Falha ao renderizar item '%s': %s", item.tipologia, e)
        return None


def _svg_para_png_bytes(svg: str, largura_px: int = 960) -> Optional[bytes]:
    """Converte SVG → PNG bytes para embutir no PDF."""
    try:
        return cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=largura_px)
    except Exception as e:
        log.warning("Falha ao converter SVG→PNG: %s", e)
        return None


# ── PDF Builder ───────────────────────────────────────────────────────────────

class _ProposalPDF(FPDF):
    """FPDF2 com cabeçalho e rodapé automáticos."""

    def __init__(self, empresa: EmpresaInfo):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.empresa = empresa
        self.cor = _hex_rgb(empresa.cor_primaria)
        self.cor_light = _lighter(self.cor)
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(left=15, top=15, right=15)

    def footer(self) -> None:  # type: ignore[override]
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, f"Pagina {self.page_no()}  |  {self.empresa.nome}", align="C")
        self.set_text_color(0, 0, 0)


# ── Sections ──────────────────────────────────────────────────────────────────

def _section_header(pdf: _ProposalPDF, empresa: EmpresaInfo) -> None:
    """Barra colorida com nome e contatos da empresa."""
    r, g, b = pdf.cor
    pdf.set_fill_color(r, g, b)
    pdf.rect(x=15, y=15, w=180, h=36, style="F")

    # Logo (se fornecido em base64)
    logo_w = 0
    if empresa.logo_base64:
        try:
            logo_bytes = base64.b64decode(empresa.logo_base64)
            img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
            # Redimensionar para caber em 30×30mm
            fundo = Image.new("RGBA", img.size, (255, 255, 255, 0))
            fundo.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
            out = io.BytesIO()
            fundo.convert("RGB").save(out, format="PNG")
            out.seek(0)
            pdf.image(out, x=18, y=18, h=30)
            logo_w = 35
        except Exception as e:
            log.debug("Logo ignorado: %s", e)

    # Nome da empresa
    pdf.set_xy(15 + logo_w + 3, 20)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(180 - logo_w - 3, 8, empresa.nome, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Contatos
    pdf.set_x(15 + logo_w + 3)
    pdf.set_font("Helvetica", "", 8)
    contatos = []
    if empresa.telefone:
        contatos.append(empresa.telefone)
    if empresa.email:
        contatos.append(empresa.email)
    if empresa.cnpj:
        contatos.append(f"CNPJ: {empresa.cnpj}")
    if empresa.endereco:
        contatos.append(empresa.endereco)
    if contatos:
        pdf.multi_cell(180 - logo_w - 3, 5, "  |  ".join(contatos))

    pdf.set_text_color(0, 0, 0)
    pdf.set_y(55)


def _section_proposta_info(pdf: _ProposalPDF, numero: str, validade_dias: int) -> None:
    """Linha com número da proposta, data e validade."""
    hoje = datetime.now()
    validade = hoje + timedelta(days=validade_dias)
    r, g, b = pdf.cor

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(r, g, b)
    pdf.cell(90, 7, f"PROPOSTA  {numero}")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(90, 7, f"Emissão: {hoje.strftime('%d/%m/%Y')}     Válida até: {validade.strftime('%d/%m/%Y')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)

    # Linha divisória
    pdf.set_draw_color(r, g, b)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y() + 1, 195, pdf.get_y() + 1)
    pdf.ln(5)


def _section_cliente(pdf: _ProposalPDF, cliente: ClienteInfo) -> None:
    """Box com dados do cliente."""
    r, g, b = pdf.cor
    lr, lg, lb = pdf.cor_light

    y0 = pdf.get_y()
    pdf.set_fill_color(lr, lg, lb)
    pdf.rect(x=15, y=y0, w=180, h=5, style="F")

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(r, g, b)
    pdf.cell(180, 5, "  CLIENTE", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_fill_color(248, 248, 248)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)

    linhas = [cliente.nome]
    if cliente.telefone:
        linhas.append(cliente.telefone)
    if cliente.email:
        linhas.append(cliente.email)
    if cliente.endereco:
        linhas.append(cliente.endereco)
    if cliente.cpf_cnpj:
        linhas.append(f"CPF/CNPJ: {cliente.cpf_cnpj}")

    h_box = len(linhas) * 5 + 4
    pdf.rect(x=15, y=pdf.get_y(), w=180, h=h_box, style="F")
    for linha in linhas:
        pdf.cell(180, 5, f"  {linha}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    pdf.set_text_color(0, 0, 0)


def _section_tabela(pdf: _ProposalPDF, itens: list[ItemProposta]) -> None:
    """Tabela de itens do orçamento com cores alternadas."""
    r, g, b = pdf.cor
    lr, lg, lb = pdf.cor_light

    # Larguras das colunas (total = 180mm)
    W_DESC  = 70
    W_DIM   = 28
    W_QTD   = 12
    W_UNIT  = 35
    W_TOT   = 35
    H_ROW   = 7

    # Cabeçalho da tabela
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_draw_color(r, g, b)

    pdf.cell(W_DESC, H_ROW, "  Descrição",         border=0, fill=True)
    pdf.cell(W_DIM,  H_ROW, "Dimensões",            border=0, fill=True, align="C")
    pdf.cell(W_QTD,  H_ROW, "Qtd",                  border=0, fill=True, align="C")
    pdf.cell(W_UNIT, H_ROW, "Unitário",              border=0, fill=True, align="R")
    pdf.cell(W_TOT,  H_ROW, "Total  ",              border=0, fill=True, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 8)
    pdf.set_draw_color(210, 210, 210)

    for i, item in enumerate(itens):
        # Zebra
        if i % 2 == 0:
            pdf.set_fill_color(255, 255, 255)
        else:
            pdf.set_fill_color(245, 245, 245)

        pdf.set_text_color(40, 40, 40)

        dim = f"{int(item.largura)}×{int(item.altura)}mm"
        unit_str = _fmt_brl(item.valor_unitario)
        tot_str  = _fmt_brl(item.valor_total)

        # Linha de texto — multi_cell para descrição longa
        y_before = pdf.get_y()
        x_before = pdf.get_x()

        # Descrição (pode ser longa)
        pdf.cell(W_DESC, H_ROW, f"  {item.descricao[:38]}", border="B", fill=True)
        pdf.cell(W_DIM,  H_ROW, dim,      border="B", fill=True, align="C")
        pdf.cell(W_QTD,  H_ROW, str(item.quantidade), border="B", fill=True, align="C")
        pdf.cell(W_UNIT, H_ROW, unit_str, border="B", fill=True, align="R")
        pdf.cell(W_TOT,  H_ROW, f"{tot_str}  ", border="B", fill=True, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Observações do item (linha extra se houver)
        if item.observacoes:
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(W_DESC + W_DIM + W_QTD + W_UNIT + W_TOT, 5,
                     f"    > {item.observacoes[:80]}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(40, 40, 40)

    # Borda inferior da tabela
    pdf.set_draw_color(r, g, b)
    pdf.set_line_width(0.4)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(2)


def _section_totais(pdf: _ProposalPDF, itens: list[ItemProposta],
                    condicoes: Optional[CondicoesPagamento]) -> None:
    """Bloco de totais e condições de pagamento."""
    r, g, b = pdf.cor

    subtotal = sum(i.valor_total or 0 for i in itens)
    desconto = 0.0
    total = subtotal

    if condicoes and condicoes.desconto_percentual:
        desconto = subtotal * condicoes.desconto_percentual / 100
        total = subtotal - desconto

    # Alinhado à direita
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)

    if subtotal > 0:
        if desconto > 0:
            pdf.cell(140, 6, "Subtotal", align="R")
            pdf.cell(40, 6, _fmt_brl(subtotal), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(180, 0, 0)
            pdf.cell(140, 6, f"Desconto ({condicoes.desconto_percentual:.0f}%)", align="R")
            pdf.cell(40, 6, f"- {_fmt_brl(desconto)}", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_draw_color(r, g, b)
            pdf.line(120, pdf.get_y(), 195, pdf.get_y())

        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(r, g, b)
        pdf.cell(140, 8, "TOTAL", align="R")
        pdf.cell(40, 8, _fmt_brl(total), align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

    # Condições de pagamento
    if condicoes:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(180, 5, f"Forma de pagamento: {condicoes.forma}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if condicoes.parcelas and condicoes.parcelas > 1 and total > 0:
            parc = total / condicoes.parcelas
            pdf.cell(180, 5, f"Parcelas: {condicoes.parcelas}× de {_fmt_brl(parc)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if condicoes.observacoes:
            pdf.cell(180, 5, f"Obs.: {condicoes.observacoes}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)


def _section_validade_rodape(pdf: _ProposalPDF, validade_dias: int,
                              observacoes: Optional[str]) -> None:
    """Nota de validade e observações gerais."""
    r, g, b = pdf.cor
    validade = (datetime.now() + timedelta(days=validade_dias)).strftime("%d/%m/%Y")

    pdf.ln(5)
    pdf.set_draw_color(r, g, b)
    pdf.set_line_width(0.3)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(180, 5, f"Esta proposta é válida até {validade} ({validade_dias} dias).", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if observacoes:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(180, 5, "Observações:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 8)
        pdf.multi_cell(180, 5, observacoes)

    pdf.set_text_color(0, 0, 0)


def _page_desenho(pdf: _ProposalPDF, item: ItemProposta,
                  svg: Optional[str], incluir_ferragens: bool,
                  ferragens: list[dict]) -> None:
    """Página de desenho técnico de um item."""
    pdf.add_page()
    r, g, b = pdf.cor
    lr, lg, lb = pdf.cor_light

    # Título do item
    pdf.set_fill_color(lr, lg, lb)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(r, g, b)
    pdf.cell(180, 9, f"  {item.descricao}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    info_partes = [
        f"{int(item.largura)} × {int(item.altura)} mm",
        f"Vidro {item.espessura or 8}mm",
    ]
    if item.cor_vidro and item.cor_vidro != "incolor":
        info_partes.append(item.cor_vidro.capitalize())
    if item.fabricante:
        info_partes.append(f"Ferragens: {item.fabricante}")
    pdf.cell(180, 5, "    " + "  |  ".join(info_partes), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # Desenho técnico
    if svg:
        png_bytes = _svg_para_png_bytes(svg, largura_px=960)
        if png_bytes:
            # Redimensionar para caber no A4 com margem
            try:
                img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
                fundo = Image.new("RGBA", img.size, (255, 255, 255, 255))
                fundo.paste(img, mask=img.split()[3])
                out = io.BytesIO()
                fundo.convert("RGB").save(out, format="PNG")
                out.seek(0)

                # Manter proporção, max 170mm de largura
                img_w_mm = 170
                ratio = img.height / img.width if img.width else 1
                img_h_mm = img_w_mm * ratio
                if img_h_mm > 160:  # limitar altura
                    img_h_mm = 160
                    img_w_mm = img_h_mm / ratio

                x_centered = 15 + (180 - img_w_mm) / 2
                pdf.image(out, x=x_centered, w=img_w_mm)
                pdf.ln(4)
            except Exception as e:
                log.debug("Falha ao inserir imagem no PDF: %s", e)
    else:
        # Placeholder cinza
        pdf.set_fill_color(240, 240, 240)
        pdf.set_draw_color(200, 200, 200)
        pdf.rect(x=15, y=pdf.get_y(), w=180, h=60, style="FD")
        pdf.set_xy(15, pdf.get_y() + 25)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(180, 5, "Desenho técnico não disponível para esta tipologia", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(40)

    # Lista de ferragens
    if incluir_ferragens and ferragens:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(r, g, b)
        pdf.cell(180, 6, "Ferragens:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(50, 50, 50)

        vistos: set[str] = set()
        for f in ferragens:
            nome = f.get("nome", "")
            codigo = f.get("codigo", "")
            chave_f = f"{nome}|{codigo}"
            if chave_f in vistos:
                continue
            vistos.add(chave_f)
            label = f"  - {nome}"
            if codigo:
                label += f" ({codigo})"
            pdf.cell(180, 5, label, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_text_color(0, 0, 0)


# ── Public API ────────────────────────────────────────────────────────────────

async def gerar_proposta(request: ProposalRequest) -> bytes:
    """Gera PDF da proposta comercial e retorna bytes.

    1. Pré-renderiza SVG de cada item (async, graceful degradation)
    2. Monta PDF com FPDF2 (sync)
    """
    # ── 1. Pré-renderizar itens ───────────────────────────────────────────────
    svgs: dict[int, Optional[str]] = {}
    ferragens_por_item: dict[int, list[dict]] = {}

    if request.incluir_desenho:
        from app.models.render import PecaInput, RenderRequest as RReq
        for idx, item in enumerate(request.itens):
            svg = await _render_item(item)
            svgs[idx] = svg

            # Também buscar ferragens para listar
            if svg and request.incluir_ferragens:
                try:
                    req = RReq(
                        tipologia_nome=item.tipologia,
                        pecas=[PecaInput(
                            nome=item.descricao,
                            largura_mm=item.largura,
                            altura_mm=item.altura,
                        )],
                        espessura_vidro_mm=float(item.espessura or 8),
                    )
                    result = await executar(req)
                    ferr_list = []
                    for peca in result.pecas:
                        for f in peca.ferragens:
                            ferr_list.append({
                                "nome": f.nome,
                                "codigo": f.codigo or "",
                                "tipo": f.tipo,
                            })
                    ferragens_por_item[idx] = ferr_list
                except Exception as e:
                    log.debug("Falha ao coletar ferragens para item %d: %s", idx, e)
                    ferragens_por_item[idx] = []

    # ── 2. Montar PDF ─────────────────────────────────────────────────────────
    numero = _gerar_numero(request.numero_proposta)
    empresa = request.empresa

    pdf = _ProposalPDF(empresa)
    pdf.add_page()

    _section_header(pdf, empresa)
    _section_proposta_info(pdf, numero, request.validade_dias)
    _section_cliente(pdf, request.cliente)
    pdf.ln(3)
    _section_tabela(pdf, request.itens)
    _section_totais(pdf, request.itens, request.condicoes)
    _section_validade_rodape(pdf, request.validade_dias, request.observacoes_gerais)

    # Páginas de desenho técnico
    if request.incluir_desenho:
        for idx, item in enumerate(request.itens):
            _page_desenho(
                pdf, item,
                svg=svgs.get(idx),
                incluir_ferragens=request.incluir_ferragens,
                ferragens=ferragens_por_item.get(idx, []),
            )

    return bytes(pdf.output())
