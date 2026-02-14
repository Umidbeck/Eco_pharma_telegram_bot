#!/bin/bash
# ============================================================
# Eco Pharm Telegram Bot - View Logs Script
# ============================================================

echo "📋 Bot loglarini ko'rsatish..."
echo "To'xtatish uchun Ctrl+C bosing"
echo "============================================================"
echo ""

docker logs -f eco_pharm_telegram_bot --tail 100
