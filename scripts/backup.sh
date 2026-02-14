#!/bin/bash
# ============================================================
# Eco Pharm Telegram Bot - Database Backup Script
# ============================================================

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/bot_db_backup_$DATE.db"

echo "💾 Database backup..."

# Create backup directory
mkdir -p $BACKUP_DIR

# Check if data directory exists
if [ ! -f "./data/bot.db" ]; then
    echo "❌ Database fayli topilmadi!"
    exit 1
fi

# Create backup
cp ./data/bot.db "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Backup yaratildi: $BACKUP_FILE"
    
    # Keep only last 7 backups
    ls -t $BACKUP_DIR/bot_db_backup_*.db 2>/dev/null | tail -n +8 | xargs -r rm
    
    echo "📁 Mavjud backuplar:"
    ls -lh $BACKUP_DIR/bot_db_backup_*.db 2>/dev/null
else
    echo "❌ Backup yaratishda xatolik!"
    exit 1
fi
