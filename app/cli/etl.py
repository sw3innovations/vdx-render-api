"""CLI: ETL canônico — popula schema 3NF a partir das tabelas staging.

Uso:
    python -m app.cli.etl run
    python -m app.cli.etl reset
    python -m app.cli.etl audit
"""
import argparse
import sys
from pathlib import Path


def cmd_run() -> None:
    from app.core.constitution import init_db
    init_db()

    from app.etl.loaders.load_canonical import CanonicalLoader
    print("Executando ETL canônico…")
    with CanonicalLoader() as loader:
        stats = loader.run()

    print("Concluído:")
    print(f"  materiais:       {stats.materiais}")
    print(f"  acabamentos:     {stats.acabamentos}")
    print(f"  variaveis:       {stats.variaveis}")
    print(f"  tipologias:      {stats.tipologias}")
    print(f"  modelos:         {stats.modelos}")
    print(f"  pecas_geometria: {stats.pecas_geometria}")
    print(f"  ferragens:       {stats.ferragens}")
    if stats.erros:
        print(f"\nAvisos ({len(stats.erros)}):")
        for e in stats.erros[:20]:
            print(f"  - {e}")
        if len(stats.erros) > 20:
            print(f"  … e mais {len(stats.erros) - 20} avisos")


def cmd_reset() -> None:
    from app.core.constitution import init_db
    init_db()

    from app.etl.loaders.load_canonical import CanonicalLoader
    print("Resetando tabelas canônicas…")
    with CanonicalLoader() as loader:
        loader.reset()
    print("Concluído.")


def cmd_audit() -> None:
    from app.core.constitution import _get_conn
    conn = _get_conn()
    rows = conn.execute(
        "SELECT estagio, tabela_destino, registros_aceitos, registros_rejeitados, timestamp "
        "FROM etl_auditoria ORDER BY timestamp DESC LIMIT 50"
    ).fetchall()
    conn.close()
    if not rows:
        print("Nenhum registro de auditoria encontrado.")
        return
    print(f"{'Estágio':<20} {'Tabela':<35} {'Aceitos':>8} {'Rejeit.':>8}  Timestamp")
    print("-" * 90)
    for estagio, tabela, aceitos, rejeitados, ts in rows:
        print(f"{estagio:<20} {tabela:<35} {aceitos:>8} {rejeitados:>8}  {ts}")


def _generate_quality_report(output_path: str) -> None:
    from app.core.constitution import _get_conn
    conn = _get_conn()
    lines = ["# ETL Quality Report\n"]

    tables = [
        ("materiais_canonicos",      "Materiais"),
        ("acabamentos_canonicos",    "Acabamentos"),
        ("variaveis_canonicas",      "Variáveis"),
        ("tipologias_canonicas",     "Tipologias"),
        ("modelos_canonicos",        "Modelos"),
        ("pecas_geometria_canonicas","Peças Geometria"),
        ("ferragens_canonicas",      "Ferragens"),
        ("etl_auditoria",            "Auditoria ETL"),
    ]

    lines.append("## Contagens por tabela\n")
    lines.append("| Tabela | Registros |")
    lines.append("|--------|-----------|")
    for table, label in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            count = "ERRO"
        lines.append(f"| {label} | {count} |")

    lines.append("\n## Modelos com nome inferido\n")
    row = conn.execute("SELECT COUNT(*) FROM modelos_canonicos WHERE nome_inferido=1").fetchone()
    infer = row[0] if row else 0
    total = conn.execute("SELECT COUNT(*) FROM modelos_canonicos").fetchone()[0]
    lines.append(f"- Total modelos: **{total}**")
    lines.append(f"- Nome inferido: **{infer}** ({100*infer//max(total,1)}%)")

    lines.append("\n## Ferragens por tipo\n")
    rows = conn.execute(
        "SELECT tipo, COUNT(*) as n FROM ferragens_canonicas GROUP BY tipo ORDER BY n DESC LIMIT 10"
    ).fetchall()
    for tipo, n in rows:
        lines.append(f"- {tipo or '(sem tipo)'}: {n}")

    lines.append("\n## Últimas entradas de auditoria\n")
    audit_rows = conn.execute(
        "SELECT estagio, tabela_destino, registros_aceitos, registros_rejeitados "
        "FROM etl_auditoria ORDER BY id DESC LIMIT 10"
    ).fetchall()
    lines.append("| Estágio | Tabela | Aceitos | Rejeitados |")
    lines.append("|---------|--------|---------|------------|")
    for estagio, tabela, aceitos, rej in audit_rows:
        lines.append(f"| {estagio} | {tabela} | {aceitos} | {rej} |")

    conn.close()
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Relatório gerado: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ETL canônico VDX")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("run",   help="Popula tabelas canônicas a partir do staging")
    sub.add_parser("reset", help="Trunca todas as tabelas canônicas")
    sub.add_parser("audit", help="Exibe log de auditoria ETL")
    report_p = sub.add_parser("report", help="Gera relatório de qualidade")
    report_p.add_argument("--output", default="/tmp/etl_quality_report.md")

    args = parser.parse_args()

    if args.cmd == "run":
        cmd_run()
    elif args.cmd == "reset":
        cmd_reset()
    elif args.cmd == "audit":
        cmd_audit()
    elif args.cmd == "report":
        _generate_quality_report(args.output)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
