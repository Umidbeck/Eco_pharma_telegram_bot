# 🚀 Eco Pharm Bot - PostgreSQL - Bitta Buyruq!

## ⚡ Tezkor Ishga Tushirish

```bash
./setup.sh
```

**HAMMASI SHU! 🎉**

Setup script avtomatik:
- ✅ System paketlarni o'rnatadi (Docker, Python)
- ✅ Python virtual environment yaratadi
- ✅ Python paketlarni o'rnatadi
- ✅ PostgreSQL ni Docker'da ishga tushiradi (port 5433)
- ✅ SQLite dan barcha ma'lumotlarni PostgreSQL ga ko'chiradi
- ✅ Systemd service yaratadi (auto-start)
- ✅ Botni ishga tushiradi

---

## 📋 Keyin nima qilish kerak?

### Bot boshqarish

```bash
# Bot statusini ko'rish
sudo systemctl status eco-pharm-bot

# Loglarni ko'rish
sudo journalctl -u eco-pharm-bot -f

# Botni to'xtatish
sudo systemctl stop eco-pharm-bot

# Botni qayta ishga tushirish
sudo systemctl restart eco-pharm-bot
```

### PostgreSQL boshqarish

```bash
# PostgreSQL statusini ko'rish
docker-compose ps

# PostgreSQL loglarni ko'rish
docker-compose logs -f postgres

# PostgreSQL to'xtatish
docker-compose down

# PostgreSQL qayta ishga tushirish
docker-compose restart postgres
```

### Database backup

```bash
# Backup yaratish
docker-compose exec postgres pg_dump -U eco_pharm eco_pharm_bot > backup_$(date +%Y%m%d).sql

# Backup restore qilish
docker-compose exec -T postgres psql -U eco_pharm eco_pharm_bot < backup_20260214.sql
```

---

## 🔧 Agar setup.sh ishlamasa

### 1-qadam: PostgreSQL ishga tushirish

```bash
docker-compose up -d postgres
```

### 2-qadam: Python paketlarni o'rnatish

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3-qadam: Ma'lumotlarni ko'chirish

```bash
python3 migrate_sqlite_to_postgres.py
```

### 4-qadam: Botni ishga tushirish

```bash
python3 main.py
```

---

## ✅ Tekshirish

### Bot ishlayaptimi?

```bash
sudo systemctl status eco-pharm-bot
```

Ko'rsatilishi kerak:
- `Active: active (running)`
- `Main PID: xxxxx`

### PostgreSQL ishlayaptimi?

```bash
docker-compose ps
```

Ko'rsatilishi kerak:
- `eco_pharm_postgres    Up`

### Ma'lumotlar ko'chirilganmi?

```bash
docker-compose exec postgres psql -U eco_pharm -d eco_pharm_bot -c "SELECT COUNT(*) FROM employees;"
```

Xodimlar soni ko'rsatilishi kerak.

---

## 🎯 Port: 5433

**Diqqat!** PostgreSQL port **5433** da ishlaydi (standart 5432 emas).

Bu qilindi, chunki serverizdagi eski PostgreSQL 5432 da ishlayapti.

Agar port o'zgartirish kerak bo'lsa:
1. `docker-compose.yml` da port o'zgartiring
2. `.env` da `POSTGRES_PORT` ni o'zgartiring
3. `docker-compose restart postgres`

---

## 📞 Yordam kerakmi?

### Loglarni ko'ring:

```bash
# Bot loglari
sudo journalctl -u eco-pharm-bot -f

# PostgreSQL loglari
docker-compose logs -f postgres
```

### Database tekshiring:

```bash
# PostgreSQL shell
docker-compose exec postgres psql -U eco_pharm -d eco_pharm_bot

# Jadvallarni ko'rish
\dt

# Xodimlarni ko'rish
SELECT * FROM employees LIMIT 5;

# Chiqish
\q
```

---

## 🎉 Tayyor!

Bot endi PostgreSQL bilan ishlayapti va serverda avtomatik ishga tushadi!

Agar xatolik bo'lsa, `README_POSTGRES.md` faylini o'qing.
