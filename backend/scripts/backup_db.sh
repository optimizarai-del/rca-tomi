#!/usr/bin/env bash
# Backup automático de la DB de RCA.
#
# Soporta:
#   - SQLite local (modo dev/staging) → copia + .dump
#   - Postgres (Supabase/Railway/RDS) → pg_dump custom format (compatible con pg_restore)
#
# Uso:
#   BACKUP_DIR=/var/backups/rca RETENTION_DAYS=30 ./scripts/backup_db.sh
#
# Vars:
#   DATABASE_URL    obligatorio (típicamente desde .env)
#   BACKUP_DIR      destino (default: ./backups)
#   RETENTION_DAYS  días a conservar (default: 30)
#
# Recomendado: correr con cron diario (ej. 3am UTC).
# Ejemplo crontab: 0 3 * * * cd /app/backend && ./scripts/backup_db.sh >> /var/log/rca-backup.log 2>&1

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)

if [ -z "${DATABASE_URL:-}" ]; then
    if [ -f .env ]; then
        # shellcheck disable=SC1091
        set -a; . .env; set +a
    fi
fi

if [ -z "${DATABASE_URL:-}" ]; then
    echo "[backup] ERROR: DATABASE_URL no está seteada"
    exit 1
fi

mkdir -p "$BACKUP_DIR"

case "$DATABASE_URL" in
    sqlite*)
        # Path al archivo: sqlite:///./fielddata.db → ./fielddata.db
        DB_FILE="${DATABASE_URL#sqlite:///}"
        if [ ! -f "$DB_FILE" ]; then
            echo "[backup] ERROR: archivo SQLite no existe: $DB_FILE"
            exit 1
        fi
        OUT="$BACKUP_DIR/rca_${TIMESTAMP}.sqlite.gz"
        echo "[backup] SQLite → $OUT"
        TMP="$BACKUP_DIR/.tmp_${TIMESTAMP}.db"
        if command -v sqlite3 >/dev/null 2>&1; then
            # .backup hace una copia consistente incluso si la DB está en uso
            sqlite3 "$DB_FILE" ".backup '$TMP'"
        else
            # Fallback: copia simple del archivo (la DB no debería estar siendo escrita en este momento)
            echo "[backup] sqlite3 no disponible — usando copia directa del archivo"
            cp "$DB_FILE" "$TMP"
        fi
        gzip -c "$TMP" > "$OUT"
        rm "$TMP"
        ;;

    postgresql*|postgres*)
        OUT="$BACKUP_DIR/rca_${TIMESTAMP}.dump"
        echo "[backup] Postgres → $OUT"
        pg_dump --format=custom --compress=9 --no-owner --no-privileges \
            --dbname="$DATABASE_URL" --file="$OUT"
        ;;

    *)
        echo "[backup] ERROR: tipo de DB no soportado: $DATABASE_URL"
        exit 1
        ;;
esac

SIZE=$(du -h "$OUT" | cut -f1)
echo "[backup] OK $OUT ($SIZE)"

# Retención: borrar más viejos
echo "[backup] Limpiando backups con más de $RETENTION_DAYS días..."
find "$BACKUP_DIR" -type f \( -name 'rca_*.sqlite.gz' -o -name 'rca_*.dump' \) \
    -mtime "+$RETENTION_DAYS" -delete -print

echo "[backup] done"
