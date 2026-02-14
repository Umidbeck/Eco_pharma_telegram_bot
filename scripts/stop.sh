#!/bin/bash
# ============================================================
# Eco Pharm Telegram Bot - Stop Script
# ============================================================

echo "🛑 Botni to'xtatish..."

docker-compose down 2>/dev/null || docker compose down 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Bot to'xtatildi!"
else
    echo "⚠️ Xatolik yuz berdi"
fi
