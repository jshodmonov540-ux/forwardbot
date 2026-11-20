# ForwardBot — Telegram Xabar va Tranzaksiyalarni Yo'naltiruvchi Tizim (Hybrid Forwarder)

Telegram botlari, kanallari va foydalanuvchilaridan keluvchi xabarlar va tranzaksiyalarni real vaqtda avtomatik kuzatuvchi, xabar egasining nomi bilan manzil kanaliga/guruhiga forward qiluvchi gibrid tizim.

---

## 🏗 Arxitektura (Gibrid Tizim)

Telegram Bot API platformasida botlar boshqa botlarning xabarlarini to'g'ridan-to'g'ri o'qiy olmaydi (Bot-to-Bot messaging bloklangan). Ushbu cheklovni yengib o'tish uchun loyiha **ikki qatlamli gibrid arxitektura**da qurilgan:

1. **Telethon MTProto Userbot (Mijoz qatlami):**
   - Foydalanuvchi hech qanday kod yoki API ID kiritmasdan, to'g'ridan-to'g'ri Telegram bot orqali **bir martalik QR-kod**ni skanerlab hisobini ulaydi.
   - Userbot barcha ruxsat etilgan botlar (`habarchi`, to'lov botlari va boshqalar) hamda kanallardan xabarlarni to'liq ushlaydi.
   - 2FA (Cloud Password) to'liq qo'llab-quvvatlanadi.

2. **Aiogram 3 Bot (Boshqaruv va Yetkazib berish qatlami):**
   - Foydalanuvchi interfeysi (Bosh menyu, Holat paneli, Manbalar ro'yxati, Maxfiylik).
   - Manzil kanallariga admin huquqi bilan xabarlarni muallif nomi bilan chiroyli formatda yetkazib berish.

---

## 🛡 Xavfsizlik va Maxfiylik Kafolatlari

- 🔒 **Xabarlar matni bazada saqlanmaydi:** Xabarlar faqat xotirada o'qilib, manzilga yuboriladi va o'sha zahoti xotiradan o'chiriladi.
- 🛡 **Whitelist (Oq ro'yxat) filtri:** Faqat foydalanuvchi tasdiqlagan manbalardan xabarlar qabul qilinadi.
- 🔑 **2FA Parollar xavfsizligi:** Parol kiritilishi bilanoq chatdan o'chiriladi va bazada saqlanmaydi.
- ⚡️ **Sessiyani darhol bekor qilish:** Foydalanuvchi istalgan paytda Telegram ilovasidan (*Settings ➡️ Devices ➡️ Terminate*) yoki botdan bitta tugma bilan sessiyani uzishi mumkin.
- 🧹 **To'liq tozalash (`/ochirish`):** Barcha shaxsiy sozlamalar va sessiya kaliti bazadan qaytarib bo'lmas darajada o'chiriladi.

---

## 🛠 Texnologiyalar Steki

- **Til:** Python 3.11 / 3.12+
- **Telegram Bot:** Aiogram 3.14+
- **Telegram MTProto:** Telethon 1.36+
- **QR-kod generatsiyasi:** qrcode, Pillow
- **Ma'lumotlar Bazasi:** PostgreSQL / SQLite (SQLAlchemy 2.0 Async + Alembic)
- **Konfiguratsiya:** Pydantic v2 Settings

---

## 🎮 Mavjud Buyruqlar

| Buyruq | Vazifasi |
|---|---|
| `/start` | Botni ishga tushirish va Maxfiylik shartlari |
| `/ulash` | Akkauntni QR-kod orqali ulash |
| `/holat` | Tizim holati (Userbot holati, Manbalar, Maqsad kanal) |
| `/manbalar` | Ruxsat etilgan manbalar (Whitelist) ro'yxati, yangi manba qo'shish, nomlash yoki o'chirish |
| `/maqsad` | Tranzaksiyalarni qayerga yuborishni tanlash (Kanal, Guruh yoki Shaxsiy chat) |
| `/pauza` | Yo'naltirishni vaqtincha to'xtatish |
| `/davom` | Yo'naltirishni qayta yoqish |
| `/maxfiylik` | Maxfiylik va kiberxavfsizlik siyosatini o'qish |
| `/ochirish` | Barcha ma'lumotlarni bazadan to'liq o'chirish |
| `/yordam` | Qo'llanma va buyruqlar tavsifi |

---

## 🚀 Ishga Tushirish

### 1. Bog'liqliklarni o'rnatish:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Sozlamalar:
`.env.example` faylidan `.env` nusxasini oling va to'ldiring:
```env
BOT_TOKEN=your_telegram_bot_token
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
DATABASE_URL=sqlite+aiosqlite:///./test.db
```

### 3. Botni ishga tushirish:
```bash
python main.py
```

---

## ☁️ Railway yoki VPS Hostingga joylash

1. **Railway:**
   - GitHub omboringizni Railway'ga ulang.
   - Variables bo'limiga `.env`dagi kalitlarni kiriting.
   - Start Command: `python main.py`
   - Baza sifatida Railway PostgreSQL plaginini ulab, `DATABASE_URL`ga uning manzilini ko'rsatishingiz mumkin.

2. **Docker / VPS:**
   ```bash
   docker compose up -d --build
   ```
