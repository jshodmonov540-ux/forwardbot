# Xavfsizlik va Maxfiylik Kafolatlari (Security Checklist & Threat Model)

Ushbu hujjat ForwardBot loyihasining xavfsizlik arxitekturasi va ma'lumotlar daxlsizligi standartlarini bayon qiladi.

---

### 1. Foydalanuvchi identifikatsiyasi va Sessiyalar
- [x] **Xavfsiz QR-kod orqali ulanish:** Foydalanuvchilar SMS kodlarsiz va telefon raqamlarini oshkor qilmasdan, rasmiy Telegram Desktop/Web QR-kod protokoli orqali ulanadi.
- [x] **2FA (Ikki bosqichli tekshiruv) xavfsizligi:** Kiritilgan 2FA bulutli parollari bazada saqlanmaydi va foydalanuvchi yozgan xabar chatdan darhol o'chirib tashlanadi.
- [x] **Sessiyani to'xtatish kafolati:** Foydalanuvchi Telegram ilovasi (Sozlamalar -> Qurilmalar) orqali yoki botdagi «Akkauntni uzish» tugmasi orqali sessiyani istalgan soniyada butunlay yakunlay oladi.
- [x] **Bir hisob chegarasi:** Har bir foydalanuvchi bir vaqtning o'zida faqat 1 ta hisob ulashi mumkin. Yangi hisob ulanishidan oldin eski hisobni uzish bo'yicha ogohlantirish beriladi.
- [x] **To'liq ma'lumotlarni o'chirish (`/ochirish`):** Foydalanuvchi barcha ma'lumotlarini (sessiya kalitlari, whitelist chatlar, sozlamalar) bazadan qaytarib bo'lmaydigan qilib o'chirishi mumkin.

---

### 2. Xabarlar va Ma'lumotlarni Saqlash Xavfsizligi
- [x] **XABARLAR MATNI VA MEDIALAR HECH QACHON SAQLANMAYDI:**
  Bazada xabarlar matnini yoki fayllarini saqlaydigan birorta maydon yo'q. Xabar kelishi bilan kanalga yo'naltiriladi va xotiradan tozalanadi.
- [x] **Whitelist (Oq ro'yxat) qat'iy filtri:**
  Faqat foydalanuvchi o'zi ruxsat bergan chatlardan kelgan xabarlargina forward qilinadi. Boshqa barcha shaxsiy yozishmalar to'liq e'tiborsiz qoldiriladi.

---

### 3. Loglash va Sanitizatsiya (Sensitive Data Filter)
- [x] `SensitiveDataFilter` maxsus logging filtri orqali quyidagi ma'lumotlar avtomatik niqoblanadi (masking):
  - Karta raqamlari (Uzcard, Humo, Visa, Mastercard) -> `[CARD_MASKED]`
  - O'zbekiston va xalqaro telefon raqamlari -> `[PHONE_MASKED]`
  - Telegram bot tokenlari -> `[BOT_TOKEN_MASKED]`

---

### 4. Xakerlik (Hack) Hujumlari Xatar Baholash (Threat Model)
- **Xabarlar sizib chiqishi xavfi:** 0% (xabarlar bazada saqlanmagani sababli xakerlar ularni qo'lga kirita olmaydi).
- **Sessiya kalitlari xavfi:** Agar ma'lumotlar bazasi qo'lga kiritilsa, buzg'unchi StringSession orqali ulanishga urinishi mumkin. Bunga qarshi:
  - Baza tashqi internetdan to'liq yopiq.
  - Zaxira nusxalar AES-256 shifrlangan.
  - Foydalanuvchi o'z Telegram Qurilmalar bo'limidan sessiyani bir zumda to'xtata oladi.
