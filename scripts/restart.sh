#!/bin/bash
# ============================================================
# Eco Pharm Telegram Bot - Restart Script
# ============================================================

echo "🔄 Botni qayta ishga tushirish..."

docker-compose restart 2>/dev/null || docker compose restart 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Bot qayta ishga tushdi!"
    sleep 3
    docker ps --filter "name=eco_pharm_telegram_bot" --format "table {{.Names}}\t{{.Status}}"
else
    echo "⚠️ Xatolik yuz berdi"
fi
