# شروع سریع - ربات تلگرام

این راهنما به شما کمک می‌کند ظرف 5 دقیقه ربات تلگرام خود را راه‌اندازی کنید.

## مرحله 1: ساخت ربات (2 دقیقه)

1. در تلگرام به [@BotFather](https://t.me/BotFather) بروید
2. دستور `/newbot` را بزنید
3. نام ربات: `Bourse Filter Bot`
4. username ربات: `your_username_bot` (باید به bot ختم شود)
5. توکن را کپی کنید (مثال: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

## مرحله 2: پیدا کردن Chat ID (1 دقیقه)

1. به [@userinfobot](https://t.me/userinfobot) بروید
2. Chat ID خود را یادداشت کنید (مثال: `123456789`)

## مرحله 3: نصب و تنظیم (2 دقیقه)

```bash
# نصب کتابخانه‌ها
pip install -r requirements.txt

# کپی فایل محیطی
cp .env.example .env

# ویرایش فایل .env (با nano، vim، یا ویرایشگر دلخواه)
nano .env
```

محتوای `.env`:
```env
TELEGRAM_BOT_TOKEN=توکن_ربات_از_BotFather
AUTHORIZED_USERS=Chat_ID_شما
```

**مثال:**
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
AUTHORIZED_USERS=123456789
```

ذخیره و خروج (در nano: Ctrl+O, Enter, Ctrl+X)

## مرحله 4: اجرا (10 ثانیه)

```bash
python telegram_bot.py
```

باید ببینید:
```
🤖 ربات شروع به کار کرد...
📊 تعداد نمادهای تحت پوشش: 1
🔐 کاربران مجاز: [123456789]
```

## مرحله 5: تست (1 دقیقه)

در تلگرام به ربات خود بروید و بزنید:

```
/start
```

باید پیام خوش‌آمدگویی دریافت کنید.

سپس:
```
/scan
```

ربات شروع به اسکن نمادها می‌کند!

## دستورات کاربردی

```
/scan     - اسکن نمادها
/filter   - نمایش نمادهای فیلتر شده
/excel    - دریافت فایل Excel
/search غدیر  - جستجوی نماد
/help     - راهنمای کامل
```

## افزودن نمادهای بیشتر

1. جستجوی نماد:
```
/search نام_نماد
```

2. کپی کردن `insCode` از نتیجه

3. ویرایش `symbols.json`:
```json
{
  "symbols": [
    {
      "name": "نام کامل",
      "insCode": "کد_از_جستجو",
      "ticker": "نماد_کوتاه"
    }
  ]
}
```

4. ریستارت ربات (Ctrl+C و دوباره `python telegram_bot.py`)

## اجرای دائمی (بونوس)

برای اجرای ربات در background:

### روش ساده - Screen

```bash
screen -S bourse
python telegram_bot.py

# برای خروج: Ctrl+A سپس D
# برای برگشت: screen -r bourse
```

### روش پیشرفته - systemd

فایل `/etc/systemd/system/bourse-bot.service`:

```ini
[Unit]
Description=Bourse Telegram Bot
After=network.target

[Service]
Type=simple
User=USERNAME
WorkingDirectory=/path/to/boors
ExecStart=/usr/bin/python3 /path/to/boors/telegram_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

سپس:
```bash
sudo systemctl enable bourse-bot
sudo systemctl start bourse-bot
sudo systemctl status bourse-bot
```

## کامل شد! 🎉

ربات شما آماده است. حالا می‌توانید:
- هر موقع که خواستید `/scan` بزنید
- نمادهای فیلتر شده را با `/filter` ببینید
- فایل Excel را با `/excel` دریافت کنید

برای راهنمای کامل: [TELEGRAM_BOT_GUIDE.md](TELEGRAM_BOT_GUIDE.md)
