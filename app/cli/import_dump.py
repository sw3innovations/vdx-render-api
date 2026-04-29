"""CLI: importa dados do dump VDX para o constitution.db.

Uso:
    python -m app.cli.import_dump
    python -m app.cli.import_dump --dump-dir /tmp/vdx_dump_v2/extracao
"""
import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa dump VDX para constitution.db")
    parser.add_argument(
        "--dump-dir",
        default="/tmp/vdx_dump_v2/extracao",
        help="Diretório com os JSONs extraídos do dump (padrão: /tmp/vdx_dump_v2/extracao)",
    )
    args = parser.parse_args()

    dump_dir = Path(args.dump_dir)
    if not dump_dir.is_dir():
        print(f"ERRO: diretório não encontrado: {dump_dir}", file=sys.stderr)
        sys.exit(1)

    from app.core.constitution import init_db
    init_db()

    from app.services.dump_importer import importar_dump
    print(f"Importando dump de: {dump_dir}")
    stats = importar_dump(dump_dir)
    print("Concluído:")
    for k, v in stats.items():
        print(f"  {k}: {v} registros")


if __name__ == "__main__":
    main()
