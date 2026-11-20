#!/bin/bash
# ==============================================================================
# ForwardBot Shifrlangan Ma'lumotlar Bazasi Zaxira Nusxasi (Encrypted Backup)
# ==============================================================================

set -e

BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
PLAIN_BACKUP="${BACKUP_DIR}/dump_${TIMESTAMP}.sql"
ENCRYPTED_BACKUP="${PLAIN_BACKUP}.enc"

# Shifrlash kaliti (Muhit o'zgaruvchisidan olinadi)
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-SuperSecretBackupKey2026}"

mkdir -p "$BACKUP_DIR"

echo "[INFO] PostgreSQL bazasidan zaxira olinmoqda..."
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h "${DB_HOST:-db}" -U "${POSTGRES_USER:-botuser}" -d "${POSTGRES_DB:-forwardbot}" > "$PLAIN_BACKUP"

echo "[INFO] Zaxira OpenSSL AES-256-CBC orqali shifrlanmoqda..."
openssl enc -aes-256-cbc -salt -pbkdf2 -in "$PLAIN_BACKUP" -out "$ENCRYPTED_BACKUP" -k "$ENCRYPTION_KEY"

# Asl ochiq matnli faylni yo'q qilish
rm -f "$PLAIN_BACKUP"

echo "[SUCCESS] Shifrlangan zaxira yaratildi: $ENCRYPTED_BACKUP"

# 14 kundan eski zaxiralarni tozalash
find "$BACKUP_DIR" -type f -name "*.enc" -mtime +14 -exec rm -f {} \;
