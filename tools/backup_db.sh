#!/usr/bin/env bash
# Backup diário da Constitution DB usando VACUUM INTO (consistente, sem bloquear WAL).
# Uso: ./tools/backup_db.sh [--dry-run]
# Cron sugerido: 0 3 * * * $HOME/vdx-render-api/tools/backup_db.sh >> $HOME/logs/vdx-backup.log 2>&1

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB_PATH="${DB_PATH:-$REPO_ROOT/data/constitution.db}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/vdx}"
KEEP_DAYS="${KEEP_DAYS:-7}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/constitution_${TIMESTAMP}.db"

# ── Dry run ───────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--dry-run" ]]; then
    echo "[DRY RUN] DB: $DB_PATH"
    echo "[DRY RUN] Destino: $BACKUP_FILE"
    echo "[DRY RUN] Retenção: $KEEP_DAYS dias"
    exit 0
fi

# ── Validação ──────────────────────────────────────────────────────────────────
if [[ ! -f "$DB_PATH" ]]; then
    echo "[ERROR] DB não encontrada: $DB_PATH" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"

# ── Backup com VACUUM INTO (snapshot atômico e consistente) ───────────────────
sqlite3 "$DB_PATH" "VACUUM INTO '$BACKUP_FILE';"

SIZE="$(du -h "$BACKUP_FILE" | cut -f1)"
echo "[OK] Backup: $BACKUP_FILE ($SIZE)"

# ── Limpeza de backups antigos ────────────────────────────────────────────────
DELETED=$(find "$BACKUP_DIR" -name "constitution_*.db" -mtime +"$KEEP_DAYS" -print -delete | wc -l | tr -d ' ')
if [[ "$DELETED" -gt 0 ]]; then
    echo "[OK] Removidos $DELETED backup(s) com mais de $KEEP_DAYS dias"
fi
