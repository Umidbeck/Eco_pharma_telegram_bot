# Eco Pharm Telegram Bot - PostgreSQL Migration Guide

## 🚀 Bitta buyruq bilan ishga tushirish

```bash
chmod +x setup.sh
./setup.sh
```

Bu script avtomatik:
- ✅ Barcha kerakli paketlarni o'rnatadi
- ✅ PostgreSQL ni Docker'da ishga tushiradi (port 5433)
- ✅ SQLite dan PostgreSQL ga ma'lumotlarni ko'chiradi
- ✅ Systemd service yaratadi
- ✅ Botni ishga tushiradi

## 📋 Qo'lda o'rnatish (agar setup.sh ishlamasa)

### 1. PostgreSQL ni Docker bilan ishga tushirish

```bash
docker-compose up -d postgres
```

PostgreSQL:
- **Port:** 5433 (standart 5432 emas!)
- **Database:** eco_pharm_bot
- **User:** eco_pharm
- **Password:** eco_pharm_2024

### 2. Python paketlarini o'rnatish

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. .env faylini yaratish

```bash
cp .env.example .env
nano .env
```

Kerakli qiymatlarni kiriting:
- `BOT_TOKEN` - Telegram BotFather dan token
- `ADMIN_IDS` - Admin Telegram ID'lar
- `DATABASE_TYPE=postgresql`

### 4. Ma'lumotlarni ko'chirish (migration)

```bash
python3 migrate_sqlite_to_postgres.py
```

### 5. Botni ishga tushirish

```bash
python3 main.py
```

## 🔧 Kerakli buyruqlar

### PostgreSQL boshqarish

```bash
# PostgreSQL ishga tushirish
docker-compose up -d postgres

# PostgreSQL to'xtatish
docker-compose down

# PostgreSQL loglarini ko'rish
docker-compose logs -f postgres

# PostgreSQL shell
docker-compose exec postgres psql -U eco_pharm -d eco_pharm_bot

# Database backup
docker-compose exec postgres pg_dump -U eco_pharm eco_pharm_bot > backup.sql

# Database restore
docker-compose exec -T postgres psql -U eco_pharm eco_pharm_bot < backup.sql
```

### Bot boshqarish (systemd service)

```bash
# Botni ishga tushirish
sudo systemctl start eco-pharm-bot

# Botni to'xtatish
sudo systemctl stop eco-pharm-bot

# Bot statusini ko'rish
sudo systemctl status eco-pharm-bot

# Botni qayta ishga tushirish
sudo systemctl restart eco-pharm-bot

# Loglarni ko'rish (real-time)
sudo journalctl -u eco-pharm-bot -f

# Oxirgi 100 ta log
sudo journalctl -u eco-pharm-bot -n 100
```

### Ma'lumotlar bazasi bilan ishlash

```bash
# SQL query bajarish
docker-compose exec postgres psql -U eco_pharm -d eco_pharm_bot -c "SELECT COUNT(*) FROM employees;"

# Barcha jadvallarni ko'rish
docker-compose exec postgres psql -U eco_pharm -d eco_pharm_bot -c "\dt"

# Jadvaldagi ma'lumotlarni ko'rish
docker-compose exec postgres psql -U eco_pharm -d eco_pharm_bot -c "SELECT * FROM branches;"
```

## 🔍 Troubleshooting

### PostgreSQL ulanmayapti

```bash
# PostgreSQL status
docker-compose ps

# PostgreSQL loglarni tekshirish
docker-compose logs postgres

# PostgreSQL restart
docker-compose restart postgres
```

### Port 5433 band

Agar 5433 port band bo'lsa, `docker-compose.yml` da portni o'zgartiring:

```yaml
ports:
  - "5434:5432"  # 5434 ga o'zgartiring
```

Va `.env` faylida:

```env
POSTGRES_PORT=5434
```

### Ma'lumotlar ko'chirilmadi

```bash
# SQLite faylni tekshirish
ls -lh server_data/data/bot.db

# Migration qayta bajarish
python3 migrate_sqlite_to_postgres.py
```

### Bot ishga tushmayapti

```bash
# Loglarni tekshirish
sudo journalctl -u eco-pharm-bot -f

# Qo'lda ishga tushirib ko'rish
source venv/bin/activate
python3 main.py
```

## 📊 Monitoring

### PostgreSQL performance

```bash
# Active connections
docker-compose exec postgres psql -U eco_pharm -d eco_pharm_bot -c "SELECT count(*) FROM pg_stat_activity;"

# Database size
docker-compose exec postgres psql -U eco_pharm -d eco_pharm_bot -c "SELECT pg_size_pretty(pg_database_size('eco_pharm_bot'));"

# Table sizes
docker-compose exec postgres psql -U eco_pharm -d eco_pharm_bot -c "SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

## 🔐 Security

### PostgreSQL parolni o'zgartirish

1. `docker-compose.yml` da `POSTGRES_PASSWORD` ni o'zgartiring
2. `.env` da `POSTGRES_PASSWORD` ni o'zgartiring
3. PostgreSQL ni qayta ishga tushiring:

```bash
docker-compose down
docker volume rm telegram_bot_eco_pharm_postgres_data
docker-compose up -d postgres
```

## 📁 Fayl tuzilmasi

```
telegram_bot_eco_pharm/
├── bot.py                          # Bot entry point
├── main.py                         # Main server entry point
├── config.py                       # Configuration (PostgreSQL support)
├── requirements.txt                # Python dependencies (updated)
├── docker-compose.yml              # PostgreSQL container
├── setup.sh                        # One-command setup script
├── migrate_sqlite_to_postgres.py   # Migration script
├── .env                            # Environment variables
├── .env.example                    # Environment template
├── database/
│   ├── __init__.py                 # Auto-select DB type
│   ├── db.py                       # SQLite (legacy)
│   └── db_postgres.py              # PostgreSQL (new)
├── server_data/
│   └── data/
│       └── bot.db                  # Old SQLite database
└── logs/
    └── bot.log                     # Bot logs
```

## ✅ Migration Checklist

- [ ] SQLite fayli `server_data/data/bot.db` da bor
- [ ] `.env` fayli yaratilgan va to'ldirilgan
- [ ] PostgreSQL Docker'da ishga tushgan
- [ ] Migration script muvaffaqiyatli bajarildi
- [ ] Bot ishga tushdi va xabar yubordi
- [ ] Adminlarga xabar keldi
- [ ] Eski ma'lumotlar PostgreSQL da ko'rinadi

## 🎯 Production Deployment

### Auto-start on boot

```bash
sudo systemctl enable eco-pharm-bot
sudo systemctl enable docker
```

### Backup automation

`/etc/cron.daily/eco-pharm-backup`:

```bash
#!/bin/bash
docker-compose -f /path/to/telegram_bot_eco_pharm/docker-compose.yml exec -T postgres \
  pg_dump -U eco_pharm eco_pharm_bot | gzip > \
  /backups/eco_pharm_$(date +%Y%m%d).sql.gz

# Keep only last 30 days
find /backups/ -name "eco_pharm_*.sql.gz" -mtime +30 -delete
```

## 📞 Support

Agar muammo bo'lsa:
1. Loglarni tekshiring: `sudo journalctl -u eco-pharm-bot -f`
2. PostgreSQL loglarni ko'ring: `docker-compose logs postgres`
3. Database ulanishini tekshiring: `docker-compose exec postgres pg_isready`

---

**PostgreSQL Port:** 5433 (standart 5432 emas!)
**Auto-start:** Setup script systemd service yaratadi
