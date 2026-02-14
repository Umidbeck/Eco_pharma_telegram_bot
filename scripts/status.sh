#!/bin/bash
# ============================================================
# Eco Pharm Telegram Bot - Status Script
# ============================================================

echo "============================================================"
echo "     Eco Pharm Telegram Bot - Status"
echo "============================================================"
echo ""

# Check if container exists
if docker ps -a | grep -q "eco_pharm_telegram_bot"; then
    echo "📊 Container holati:"
    docker ps -a --filter "name=eco_pharm_telegram_bot" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    
    # Check if running
    if docker ps | grep -q "eco_pharm_telegram_bot"; then
        echo "✅ Bot ishlayapti!"
        echo ""
        echo "📈 Resurs ishlatish:"
        docker stats eco_pharm_telegram_bot --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
        echo ""
        echo "📋 Oxirgi loglar:"
        docker logs eco_pharm_telegram_bot --tail 10
    else
        echo "❌ Bot to'xtagan!"
        echo ""
        echo "📋 Xatolik loglari:"
        docker logs eco_pharm_telegram_bot --tail 20
    fi
else
    echo "❌ Container topilmadi!"
    echo "   Bot o'rnatilmagan yoki o'chirilgan."
fi
