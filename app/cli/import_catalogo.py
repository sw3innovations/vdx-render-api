"""CLI: importa catálogos PDF de puxadores para o constitution.db.

Uso:
    python -m app.cli.import_catalogo
    python -m app.cli.import_catalogo --catalog-dir ~/Downloads
    python -m app.cli.import_catalogo --arquivo ~/Downloads/extraido_al_vision.json
"""
import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa catálogos PDF de puxadores para constitution.db")
    parser.add_argument(
        "--catalog-dir",
        default=str(Path.home() / "Downloads"),
        help="Diretório com JSONs extraídos dos catálogos (padrão: ~/Downloads)",
    )
    parser.add_argument(
        "--arquivo",
        help="Importar um único arquivo JSON de catálogo",
    )
    args = parser.parse_args()

    from app.core.constitution import init_db
    init_db()

    if args.arquivo:
        fpath = Path(args.arquivo)
        if not fpath.exists():
            print(f"ERRO: arquivo não encontrado: {fpath}", file=sys.stderr)
            sys.exit(1)
        from app.services.catalogo_importer import importar_catalogo_arquivo
        stats = importar_catalogo_arquivo(fpath)
        print(f"Importado: {stats}")
    else:
        catalog_dir = Path(args.catalog_dir)
        if not catalog_dir.is_dir():
            print(f"ERRO: diretório não encontrado: {catalog_dir}", file=sys.stderr)
            sys.exit(1)
        from app.services.catalogo_importer import importar_catalogos
        print(f"Importando catálogos de: {catalog_dir}")
        stats = importar_catalogos(catalog_dir)
        print(f"Concluído: {stats['total_produtos']} produtos de {len(stats['arquivos'])} arquivo(s)")
        for a in stats["arquivos"]:
            print(f"  {a['arquivo']}: {a['produtos']} produtos")


if __name__ == "__main__":
    main()
