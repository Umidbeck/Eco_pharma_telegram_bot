#!/bin/bash
# ============================================================
# Eco Pharm Telegram Bot - Deploy Script
# Linux Server uchun
# ============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo "============================================================"
echo "     Eco Pharm Telegram Bot - Deploy Script"
echo "============================================================"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker topilmadi! Iltimos, Docker o'rnating."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    log_error "Docker Compose topilmadi! Iltimos, Docker Compose o'rnating."
    exit 1
fi

# Check .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        log_warning ".env fayli topilmadi. .env.example dan nusxa olinmoqda..."
        cp .env.example .env
        log_warning "Iltimos, .env faylini tahrirlang va kerakli qiymatlarni kiriting!"
        echo ""
        echo "   nano .env"
        echo ""
        exit 1
    else
        log_error ".env fayli topilmadi!"
        exit 1
    fi
fi

# Create data directories
log_info "Data papkalarini yaratish..."
mkdir -p data logs
chmod 777 data logs

# Stop existing container
log_info "Mavjud konteynerlarni to'xtatish..."
docker-compose down 2>/dev/null || docker compose down 2>/dev/null || true

# Build image
log_info "Docker image qurish..."
docker-compose build --no-cache 2>/dev/null || docker compose build --no-cache

# Start container
log_info "Konteynerlarni ishga tushirish..."
docker-compose up -d 2>/dev/null || docker compose up -d

# Wait for startup
log_info "Bot ishga tushishini kutish..."
sleep 5

# Check status
if docker ps | grep -q "eco_pharm_telegram_bot"; then
    log_success "Bot muvaffaqiyatli ishga tushdi!"
    echo ""
    echo "Foydali buyruqlar:"
    echo "  • Loglarni ko'rish:    docker logs -f eco_pharm_telegram_bot"
    echo "  • Statusni tekshirish: docker ps"
    echo "  • To'xtatish:          docker-compose down"
    echo "  • Qayta ishga tushirish: docker-compose restart"
else
    log_error "Bot ishga tushmadi! Loglarni tekshiring:"
    docker logs eco_pharm_telegram_bot 2>/dev/null || true
    exit 1
fi
