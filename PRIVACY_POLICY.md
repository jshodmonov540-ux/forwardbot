# Maxfiylik Siyosati (Privacy Policy)

**Oxirgi yangilanish sanasi:** 2026-yil noyabr  
**Loyiha:** Telegram ForwardBot (Userbot & Bot Forwarder xizmati)

Ushbu Maxfiylik Siyosati loyiha foydalanuvchilarining shaxsiy daxlsizligi, ularning ma'lumotlarini to'plash, qayta ishlash, saqlash hamda yuzaga kelishi mumkin bo'lgan kiberxavfsizlik xatarlari (xakerlik hujumlari) oqibatlari haqida to'liq va ochiq ma'lumot beradi.

---

## 1. Qanday ma'lumotlar to'planadi va saqlanadi?

Loyiha minimalizm va **Privacy First (Xavfsizlik birinchi o'rinda)** tamoyiliga tayanadi. Bazada faqat tizim ishlashi uchun o'ta zarur bo'lgan quyidagi texnik ma'lumotlargina saqlanadi:

1. **Foydalanuvchi profili:**
   - Telegram foydalanuvchi identifikatori (`user_id`).
   - Telegram ismi (`full_name`) va username (`@username`).
2. **Sessiya ma'lumoti:**
   - Shifrlangan Telethon sessiya kaliti (`StringSession`). Bu kalit foydalanuvchi har safar botga kirganda qaytadan QR-kod skanerlamasdan, xabarlarni uzluksiz forward qilish imkonini beradi.
3. **Sozlamalar va Manzillar:**
   - Ruxsat berilgan chatlar (Whitelist) ro'yxati — faqat siz ruxsat bergan botlar yoki chatlarning identifikatorlari.
   - Maqsad kanal yoki guruh identifikatori (`destination_chat_id`).

---

## 2. Qanday ma'lumotlar QAT'IYAN SAQLANMAYDI?

* ❌ **Xabarlar tarixi va mazmuni:** Foydalanuvchining shaxsiy yozishmalari, xabarlari matni, rasmlari, videolari, audiolari va fayllari ma'lumotlar bazasida **UMUMAN SAQLANMAYDI**. Xabar kelishi bilan kanalingizga forward qilinadi va operativ xotiradan (RAM) darhol yo'q qilinadi.
* ❌ **Ruxsat berilmagan chatlar:** Siz tasdiqlamagan shaxsiy suhbatlar, kontaktlar, guruhlar va kanallardagi yozishmalarga bot va userbot aslo kirmaydi, o'qimaydi va logga yozmaydi.
* ❌ **Moliyaviy ma'lumotlar:** Bank kartalari PIN-kodlari, SMS tasdiqlash kodlari, CVV kodlari va parollar saqlanmaydi va loglarda avtomatik ravishda `[CARD_MASKED]` va `[PHONE_MASKED]` filtrlari orqali yashiriladi.
* ❌ **2FA Bulutli parollar:** Ikki bosqichli tekshiruv paroli kiritilganda, u xotirada saqlanmaydi va foydalanuvchi yozgan xabar chatdan darhol o'chirib tashlanadi.

---

## 3. Ma'lumotlardan qanday maqsadlarda foydalaniladi?

To'plangan texnik ma'lumotlar faqat quyidagi maqsadlarda ishlatiladi:
1. Siz ruxsat bergan chatlardan keluvchi bildirishnomalarni belgilangan kanalingizga avtomatik forward qilish.
2. Xizmat faoliyati va uzilishlarsiz ishlashini ta'minlash.
3. Sizning buyrug'ingiz bilan hisobni to'xtatish yoki tozalash.

Ma'lumotlar hech qachon uchinchi shaxslarga berilmaydi, sotilmaydi yoki reklama maqsadlarida tahlil qilinmaydi.

---

## 4. Kiberxavfsizlik va Xakerlik (Hack) holatida nima bo'ladi?

Har qanday internet tizimida xakerlik yoki serverga noqonuniy kirish xavfi nazariy jihatdan mavjud. Agar server kiberhujumga uchrasa, foydalanuvchilar qanday zarar ko'rishi mumkin va bunga qarshi qanday choralar ko'rilgan?

### A) Yozishmalar va maxfiy ma'lumotlar sizib chiqadimi?
* **Yo'q!** Xaker server bazasini to'liq qo'lga kiritgan taqdirda ham, u yerdan **hech qanday xabarlar matni, media fayllar yoki yozishmalar tarixini topa olmaydi**, chunki ular bazada mavjud emas.

### B) Sessiya kalitlari (`session_string`) xavfi:
* **Potensial xatar:** Agar buzg'unchi ma'lumotlar bazasini qo'lga kiritsa, u yerdagi `session_string` orqali ulangan Telegram hisobiga klient sifatida ulanishga urinishi mumkin.
* **Ko'rilgan himoya choralari:**
  1. Ma'lumotlar bazasi tashqi internetdan to'liq yopiq (tashqi IP orqali to'g'ridan-to'g'ri ulanib bo'lmaydi).
  2. Barcha zaxira nusxalari (backup) kuchli AES-256 shifrlash algoritmi bilan himoyalangan.
  3. Konteyner imtiyozsiz (non-root) foydalanuvchi orqali ishlaydi.

### C) Foydalanuvchi o'zini qanday himoyalashi mumkin?
Foydalanuvchi o'z Telegram hisobi ustidan 100% nazoratga ega:
1. **Sessiyani darhol bekor qilish:** Telegram ilovangizda: **Sozlamalar** ➡️ **Qurilmalar (Devices)** bo'limiga kirsangiz, ushbu bot ulangan sessiya ko'rinib turadi. Istalgan shubhali holatda "Sessiyani yakunlash" (Terminate Session) tugmasini bossangiz, botning hisobingizga kirish huquqi shu soniyaning o'zidayoq butunlay bekor bo'ladi.
2. **2FA paroli:** Telegram akkauntingizda har doim Ikki bosqichli tekshiruv (Cloud Password) yoqilgan bo'lishini tavsiya etamiz.
3. **To'liq tozalash (`/ochirish`):** Bot ichida `/ochirish` buyrug'ini yuborsangiz, sizga tegishli barcha sessiyalar, kalitlar va sozlamalar bazadan to'liq va qaytarib bo'lmas darajada yo'q qilinadi.

---

## 5. Foydalanuvchi huquqlari

Har bir foydalanuvchi:
- O'z hisobini istalgan paytda uzish (`/sozlamalar` ➡️ «Akkauntni uzish»);
- Ruxsat berilgan chatlarni o'chirish yoki qo'shish (`/manbalar`);
- O'ziga tegishli barcha ma'lumotlarni bazadan to'liq o'chirish (`/ochirish`) huquqiga ega.

---

Ushbu shartlar xizmatdan foydalanuvchi har bir shaxsning shaxsiy daxlsizligi va erkinligini himoya qilish uchun qat'iy kafolatlanadi.
