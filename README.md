# 🏢 Korxona Vazifa Boshqaruv Boti

Telegram bot orqali korxona filiallari va xodimlarini boshqarish, vazifalarni topshirish va natijalarni nazorat qilish tizimi.

## 📋 Xususiyatlar

### 👨‍💼 Admin Panel
- **Filiallar boshqaruvi**: Yaratish, tahrirlash, o'chirish
- **Statistika**: Jami xodimlar va har bir filialdagi xodimlar soni
- **Vazifa yaratish**:
  - Filiallarni tanlash (bitta yoki hammasi)
  - Smena tanlash (Kunduzgi, Kechki yoki Hammasi)
  - Vazifa turi: Bir martalik yoki Har kunlik
  - Vaqt sozlamalari: Boshlanish vaqti va Deadline
  - Natija turi: Matn yoki Rasm
- **Hisobotlar**: Deadline tugashida avtomatik hisobot

### 👷 Xodim Panel
- **Ro'yxatdan o'tish**: Ism, Familiya, Filial, Smena
- **Profil**: Ma'lumotlarni tahrirlash
- **Vazifalar**: Ko'rish va natija yuborish
- **Unique Photo Logic**: Takroriy rasmlarni aniqlash

### 🔔 Bildirishnomalar
- Vazifa yaratilganda xabarnoma
- Vazifa boshlanish vaqtida ogohlantirish
- Deadline yaqinlashganda (30 daqiqa) ogohlantirish
- Deadline tugaganda hisobot

## 🛠 Texnologiyalar

- **Python 3.11+**
- **Aiogram 3.x** - Telegram Bot API
- **aiosqlite** - Asinxron SQLite
- **APScheduler** - Vazifalar rejalashtiruvi
- **Docker** - Konteynerizatsiya

## 📁 Loyiha Strukturasi

```
telegram_bot/
├── bot.py                 # Asosiy bot fayli
├── config.py              # Konfiguratsiya
├── requirements.txt       # Python kutubxonalar
├── Dockerfile            # Docker konfiguratsiya
├── docker-compose.yml    # Docker Compose
├── .env.example          # Environment namunasi
├── .gitignore
├── README.md
├── database/
│   ├── __init__.py
│   └── db.py             # Ma'lumotlar bazasi operatsiyalari
├── handlers/
│   ├── __init__.py
│   ├── admin.py          # Admin handlerlari
│   └── employee.py       # Xodim handlerlari
├── keyboards/
│   ├── __init__.py
│   ├── admin_kb.py       # Admin klaviaturalari
│   └── employee_kb.py    # Xodim klaviaturalari
├── middlewares/
│   └── __init__.py
└── utils/
    ├── __init__.py
    ├── helpers.py        # Yordamchi funksiyalar
    └── scheduler.py      # Bildirishnomalar
```

## 🚀 O'rnatish

### 1. Loyihani yuklab olish

```bash
git clone <repository-url>
cd telegram_bot
```

### 2. Environment sozlash

```bash
cp .env.example .env
```

`.env` faylini tahrirlang:
```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
TIMEZONE=Asia/Tashkent
```

### 3. Docker orqali ishga tushirish

```bash
docker-compose up -d --build
```

### 4. Loglarni ko'rish

```bash
docker-compose logs -f
```

### 5. To'xtatish

```bash
docker-compose down
```

## 💻 Mahalliy ishga tushirish (Docker siz)

```bash
# Virtual environment yaratish
python -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate  # Windows

# Kutubxonalarni o'rnatish
pip install -r requirements.txt

# Botni ishga tushirish
python bot.py
```

## 📱 Foydalanish

### Admin buyruqlari
- `/start` - Botni boshlash
- `/admin` - Admin panelni ochish

### Xodim buyruqlari
- `/start` - Botni boshlash va ro'yxatdan o'tish

## 📊 Ma'lumotlar bazasi

SQLite ma'lumotlar bazasi quyidagi jadvallardan iborat:

- **branches** - Filiallar
- **employees** - Xodimlar
- **tasks** - Vazifalar
- **task_branches** - Vazifa-Filial bog'lanish
- **task_results** - Vazifa natijalari
- **used_photos** - Ishlatilgan rasmlar

## ⚙️ Konfiguratsiya

| O'zgaruvchi | Tavsif | Misol |
|-------------|--------|-------|
| BOT_TOKEN | Telegram bot tokeni | 123456:ABC-DEF |
| ADMIN_IDS | Admin ID'lar (vergul bilan ajratilgan) | 123456789,987654321 |
| TIMEZONE | Vaqt zonasi | Asia/Tashkent |

## 🔒 Xavfsizlik

- Admin huquqlari faqat `ADMIN_IDS` da ko'rsatilgan foydalanuvchilarga beriladi
- Rasmlarning `file_unique_id` si tekshiriladi (takroriy rasmlar qabul qilinmaydi)
- Xodimlar faqat o'zlariga tegishli vazifalarni ko'ra oladi

## 📝 Litsenziya

MIT License

## 👨‍💻 Muallif

Sizning ismingiz

---

⭐ Agar loyiha yoqgan bo'lsa, yulduzcha qo'ying!