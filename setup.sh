#!/bin/bash

# ============================================================
# Eco Pharm Bot - Complete Setup Script
# PostgreSQL Migration & Bot Deployment
# ============================================================

set -e  # Exit on error

echo "============================================================"
echo "🚀 Eco Pharm Bot - PostgreSQL Setup"
echo "============================================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from example...${NC}"
    cp .env.example .env
    echo -e "${RED}❌ Please edit .env file and add your BOT_TOKEN and ADMIN_IDS${NC}"
    echo -e "${YELLOW}Then run this script again.${NC}"
    exit 1
fi

# Check if BOT_TOKEN is set
source .env
if [ -z "$BOT_TOKEN" ] || [ "$BOT_TOKEN" = "your_bot_token_here" ]; then
    echo -e "${RED}❌ BOT_TOKEN not configured in .env file${NC}"
    echo -e "${YELLOW}Please edit .env and add your bot token${NC}"
    exit 1
fi

echo ""
echo "1️⃣ Checking system dependencies..."
echo "------------------------------------------------------------"

# Python venv va pip o'rnatish (docker o'rnatilganini taxmin qilamiz)
if command -v apt-get &> /dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y python3-pip python3-venv
fi

# Docker mavjudligini tekshirish
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker o'rnatilmagan! Iltimos, avval Docker o'rnating.${NC}"
    echo "  curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# docker-compose yoki docker compose mavjudligini tekshirish
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo -e "${YELLOW}⚠️  docker-compose topilmadi, o'rnatilmoqda...${NC}"
    sudo apt-get install -y docker-compose-plugin 2>/dev/null || pip3 install docker-compose
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
fi

echo -e "${GREEN}✅ Docker: $(docker --version)${NC}"
echo -e "${GREEN}✅ Compose: $COMPOSE_CMD${NC}"

# Docker ishlayotganligini tekshirish
sudo systemctl enable docker 2>/dev/null || true
sudo systemctl start docker 2>/dev/null || true

echo -e "${GREEN}✅ System dependencies OK${NC}"

echo ""
echo "2️⃣ Creating Python virtual environment..."
echo "------------------------------------------------------------"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠️  Virtual environment already exists${NC}"
fi

echo ""
echo "3️⃣ Activating virtual environment and installing packages..."
echo "------------------------------------------------------------"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✅ Python packages installed${NC}"

echo ""
echo "4️⃣ Starting PostgreSQL with Docker..."
echo "------------------------------------------------------------"
$COMPOSE_CMD down 2>/dev/null || true
$COMPOSE_CMD up -d postgres

echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Check if PostgreSQL is ready
for i in {1..30}; do
    if $COMPOSE_CMD exec -T postgres pg_isready -U eco_pharm -d eco_pharm_bot &> /dev/null; then
        echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ PostgreSQL failed to start${NC}"
        exit 1
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

echo ""
echo "5️⃣ Migrating data from SQLite to PostgreSQL..."
echo "------------------------------------------------------------"

# SQLite faylini qidirish (bir nechta joydan)
SQLITE_FILE=""
for path in "server_data/data/bot.db" "data/bot.db" "/app/data/bot.db" "bot.db"; do
    if [ -f "$path" ]; then
        SQLITE_FILE="$path"
        echo -e "${GREEN}✅ SQLite database topildi: $path${NC}"
        break
    fi
done

if [ -n "$SQLITE_FILE" ]; then
    # Migration scriptga to'g'ri path berish
    SQLITE_PATH="$SQLITE_FILE" python3 migrate_sqlite_to_postgres.py
    echo -e "${GREEN}✅ Data migration completed${NC}"
else
    echo -e "${YELLOW}⚠️  SQLite database topilmadi!${NC}"
    echo -e "${YELLOW}   Qidirilgan joylar: server_data/data/bot.db, data/bot.db, /app/data/bot.db, bot.db${NC}"
    echo ""
    echo -e "${YELLOW}   Agar eski serverdagi ma'lumotlarni ko'chirmoqchi bo'lsangiz:${NC}"
    echo -e "${YELLOW}   1. Eski serverdan bot.db faylini ko'chiring:${NC}"
    echo -e "${YELLOW}      scp eski_server:/path/to/data/bot.db ./server_data/data/bot.db${NC}"
    echo -e "${YELLOW}   2. Migration scriptni qayta ishga tushiring:${NC}"
    echo -e "${YELLOW}      source venv/bin/activate && python3 migrate_sqlite_to_postgres.py${NC}"
    echo ""
    echo -e "${YELLOW}   Hozircha bo'sh database yaratilmoqda...${NC}"
    python3 -c "import asyncio; from database.db_postgres import init_db; asyncio.run(init_db())"
    echo -e "${GREEN}✅ Empty database created${NC}"
fi

echo ""
echo "6️⃣ Creating systemd service..."
echo "------------------------------------------------------------"
SERVICE_FILE="/etc/systemd/system/eco-pharm-bot.service"
CURRENT_DIR=$(pwd)
USER_NAME=$(whoami)

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Eco Pharm Telegram Bot
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/venv/bin:/usr/bin"
ExecStart=$CURRENT_DIR/venv/bin/python3 $CURRENT_DIR/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable eco-pharm-bot.service
echo -e "${GREEN}✅ Systemd service created${NC}"

echo ""
echo "============================================================"
echo "✅ Setup completed successfully!"
echo "============================================================"
echo ""
echo "📋 Available commands:"
echo "  • Start bot:    sudo systemctl start eco-pharm-bot"
echo "  • Stop bot:     sudo systemctl stop eco-pharm-bot"
echo "  • Bot status:   sudo systemctl status eco-pharm-bot"
echo "  • View logs:    sudo journalctl -u eco-pharm-bot -f"
echo ""
echo "  • PostgreSQL:   $COMPOSE_CMD logs -f postgres"
echo "  • DB shell:     $COMPOSE_CMD exec postgres psql -U eco_pharm -d eco_pharm_bot"
echo ""
echo "🎯 Starting bot now..."
sudo systemctl start eco-pharm-bot
sleep 2
sudo systemctl status eco-pharm-bot --no-pager
echo ""
echo "✅ Bot is running! Check logs with: sudo journalctl -u eco-pharm-bot -f"
echo "============================================================"
