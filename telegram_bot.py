#!/usr/bin/env python3
"""
ربات تلگرام برای فیلتر نمادهای بورس
"""

import os
import asyncio
from datetime import datetime
from typing import List, Dict
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from dotenv import load_dotenv

from stock_filter import StockFilter
from find_symbol import search_symbol as find_symbol_code
import io
import sys


class BourseBot:
    """کلاس ربات تلگرام برای فیلتر نمادهای بورس"""

    def __init__(self):
        load_dotenv()

        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN در فایل .env یافت نشد")

        # لیست کاربران مجاز
        authorized = os.getenv('AUTHORIZED_USERS', '')
        self.authorized_users = [int(uid.strip()) for uid in authorized.split(',') if uid.strip()]

        self.stock_filter = StockFilter()
        self.app = None

    def is_authorized(self, user_id: int) -> bool:
        """بررسی مجاز بودن کاربر"""
        if not self.authorized_users:
            return True  # اگر لیست خالی باشد، همه مجاز هستند
        return user_id in self.authorized_users

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        user_id = update.effective_user.id

        if not self.is_authorized(user_id):
            await update.message.reply_text(
                "❌ شما مجاز به استفاده از این ربات نیستید.\n"
                f"User ID شما: {user_id}"
            )
            return

        welcome_text = """
🤖 سلام! من ربات فیلتر نمادهای بورس هستم.

با من می‌تونی:
✅ نمادهای بورس رو اسکن کنی
✅ قدرت خریدار و ورود پول رو ببینی
✅ نمادهای با رشد قدرت خریدار رو فیلتر کنی
✅ فایل Excel نتایج رو دریافت کنی

📋 دستورات موجود:
/scan - اسکن همه نمادها
/filter - نمایش نمادهای فیلتر شده
/excel - دریافت فایل Excel
/reset - ریست داده‌های روز
/symbols - لیست نمادهای تحت پوشش
/search <نام> - جستجوی نماد
/stats - آمار کلی
/help - راهنمای کامل

برای شروع /scan رو بزن!
        """

        await update.message.reply_text(welcome_text)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /help"""
        if not self.is_authorized(update.effective_user.id):
            return

        help_text = """
📖 راهنمای کامل ربات

🔍 /scan
اسکن کامل همه نمادها و محاسبه قدرت خریدار
اگر اولین بار روزه، به عنوان داده پایه ذخیره میشه

📊 /filter
نمایش نمادهایی که قدرت خریدارشون نسبت به ابتدای روز رشد کرده
حداقل رشد: 10%

📑 /excel
دریافت فایل Excel امروز با تمام داده‌ها
شامل شیت فیلتر شده

🔄 /reset
پاک کردن داده‌های پایه روز
برای شروع دوباره از ابتدای روز

📋 /symbols
نمایش لیست نمادهای تحت پوشش

🔎 /search نماد
جستجوی نماد و پیدا کردن insCode
مثال: /search غدیر

📈 /stats
نمایش آمار کلی نمادها

💡 نکات:
- اولین اسکن روز مبنای مقایسه قرار میگیره
- برای نتیجه بهتر، اول صبح یه بار اسکن کن
- فایل Excel روزانه ذخیره میشه
        """

        await update.message.reply_text(help_text)

    async def scan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /scan - اسکن نمادها"""
        if not self.is_authorized(update.effective_user.id):
            return

        msg = await update.message.reply_text(
            "⏳ در حال اسکن نمادها...\n"
            f"تعداد نمادها: {len(self.stock_filter.symbols)}\n"
            "لطفا صبر کنید..."
        )

        try:
            # تعیین اینکه آیا اولین اسکن روز است یا نه
            is_first_scan = not self.stock_filter.initial_data

            # اجرای اسکن
            data = self.stock_filter.fetch_and_calculate()

            if not data:
                await msg.edit_text("❌ خطا در دریافت داده‌ها. لطفا دوباره تلاش کنید.")
                return

            # ذخیره داده‌های اولیه در صورت نیاز
            if is_first_scan:
                self.stock_filter.initial_data = {item['کد']: item for item in data}
                status = "✅ اسکن اول روز انجام شد و به عنوان مبنا ذخیره شد"
            else:
                status = "✅ اسکن انجام شد"

            # ذخیره در Excel
            self.stock_filter.excel_manager.save_data(data)

            # مرتب‌سازی بر اساس قدرت خریدار
            data_sorted = sorted(data, key=lambda x: x.get('قدرت_خریدار', 0), reverse=True)

            # نمایش 10 نماد برتر
            top_10 = data_sorted[:10]

            result = f"{status}\n\n"
            result += f"🕐 زمان: {datetime.now().strftime('%H:%M:%S')}\n"
            result += f"📊 تعداد نمادهای اسکن شده: {len(data)}\n\n"
            result += "🔝 10 نماد برتر بر اساس قدرت خریدار:\n\n"

            for i, item in enumerate(top_10, 1):
                result += f"{i}. {item['نماد']}\n"
                result += f"   💪 قدرت خریدار: {item['قدرت_خریدار']}\n"
                result += f"   💰 ورود پول: {item['ورود_پول_خالص_میلیون']:,.0f} م\n\n"

            result += "\nبرای دیدن نمادهای فیلتر شده: /filter"

            await msg.edit_text(result)

        except Exception as e:
            await msg.edit_text(f"❌ خطا در اسکن: {str(e)}")

    async def filter_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /filter - نمایش نمادهای فیلتر شده"""
        if not self.is_authorized(update.effective_user.id):
            return

        if not self.stock_filter.initial_data:
            await update.message.reply_text(
                "⚠️ هنوز اسکن اولیه انجام نشده.\n"
                "ابتدا دستور /scan را اجرا کنید."
            )
            return

        msg = await update.message.reply_text("🔍 در حال فیلتر کردن نمادها...")

        try:
            # دریافت داده‌های فعلی
            current_data = self.stock_filter.fetch_and_calculate()

            if not current_data:
                await msg.edit_text("❌ خطا در دریافت داده‌ها")
                return

            # فیلتر کردن
            filtered = self.stock_filter.filter_by_growth(current_data)

            if not filtered:
                await msg.edit_text(
                    "📭 هیچ نمادی با رشد بیش از 10% پیدا نشد.\n\n"
                    "💡 این می‌تونه به این دلایل باشه:\n"
                    "- هنوز تغییر قابل توجهی نداشتیم\n"
                    "- بازار نزولی هست\n"
                    "- باید بیشتر صبر کنیم"
                )
                return

            # ذخیره در شیت جداگانه
            self.stock_filter.excel_manager.create_summary_sheet(filtered)

            result = f"🎯 نمادهای فیلتر شده ({len(filtered)} نماد)\n"
            result += f"🕐 زمان: {datetime.now().strftime('%H:%M:%S')}\n\n"

            for i, item in enumerate(filtered[:20], 1):  # نمایش 20 نماد اول
                result += f"{i}. {item['نماد']}\n"
                result += f"   📈 رشد: {item['رشد_قدرت_خریدار_درصد']:.1f}%\n"
                result += f"   💪 قدرت اولیه: {item['قدرت_خریدار_اولیه']:.2f}\n"
                result += f"   💪 قدرت فعلی: {item['قدرت_خریدار']:.2f}\n"
                result += f"   💰 ورود پول: {item['ورود_پول_خالص_میلیون']:,.0f} م\n\n"

            if len(filtered) > 20:
                result += f"\n... و {len(filtered) - 20} نماد دیگر\n"

            result += "\nبرای دریافت فایل Excel: /excel"

            await msg.edit_text(result)

        except Exception as e:
            await msg.edit_text(f"❌ خطا: {str(e)}")

    async def excel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /excel - ارسال فایل Excel"""
        if not self.is_authorized(update.effective_user.id):
            return

        excel_file = self.stock_filter.excel_manager.filename

        if not os.path.exists(excel_file):
            await update.message.reply_text(
                "❌ فایل Excel موجود نیست.\n"
                "ابتدا /scan را اجرا کنید."
            )
            return

        msg = await update.message.reply_text("📤 در حال ارسال فایل...")

        try:
            # ارسال فایل
            await update.message.reply_document(
                document=open(excel_file, 'rb'),
                filename=os.path.basename(excel_file),
                caption=f"📊 گزارش بورس - {datetime.now().strftime('%Y-%m-%d')}"
            )

            await msg.delete()

        except Exception as e:
            await msg.edit_text(f"❌ خطا در ارسال فایل: {str(e)}")

    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /reset - ریست داده‌های روز"""
        if not self.is_authorized(update.effective_user.id):
            return

        self.stock_filter.initial_data = {}

        await update.message.reply_text(
            "🔄 داده‌های پایه روز پاک شد.\n\n"
            "اسکن بعدی به عنوان مبنای جدید ذخیره خواهد شد.\n"
            "برای شروع: /scan"
        )

    async def symbols_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /symbols - نمایش لیست نمادها"""
        if not self.is_authorized(update.effective_user.id):
            return

        symbols = self.stock_filter.symbols

        result = f"📋 نمادهای تحت پوشش ({len(symbols)} نماد):\n\n"

        for i, symbol in enumerate(symbols, 1):
            result += f"{i}. {symbol.get('name', 'نامشخص')} ({symbol.get('ticker', '')})\n"

        await update.message.reply_text(result)

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /search - جستجوی نماد"""
        if not self.is_authorized(update.effective_user.id):
            return

        if not context.args:
            await update.message.reply_text(
                "❌ لطفا نام نماد را وارد کنید.\n"
                "مثال: /search غدیر"
            )
            return

        search_term = ' '.join(context.args)
        msg = await update.message.reply_text(f"🔍 در حال جستجو برای: {search_term}")

        try:
            # گرفتن خروجی find_symbol
            import requests
            search_url = f"https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/{search_term}"
            headers = {
                'accept': 'application/json, text/plain, */*',
                'user-agent': 'Mozilla/5.0'
            }

            response = requests.get(search_url, headers=headers, timeout=15)
            data = response.json()

            if 'instrumentSearch' in data and data['instrumentSearch']:
                results = data['instrumentSearch'][:5]  # 5 نتیجه اول

                result_text = f"🔎 نتایج جستجو برای '{search_term}':\n\n"

                for i, item in enumerate(results, 1):
                    result_text += f"{i}. {item.get('lVal18', 'N/A')}\n"
                    result_text += f"   📌 نام: {item.get('lVal30', 'N/A')}\n"
                    result_text += f"   🔢 کد: {item.get('insCode', 'N/A')}\n\n"

                await msg.edit_text(result_text)
            else:
                await msg.edit_text(f"❌ نمادی با نام '{search_term}' پیدا نشد")

        except Exception as e:
            await msg.edit_text(f"❌ خطا در جستجو: {str(e)}")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /stats - نمایش آمار"""
        if not self.is_authorized(update.effective_user.id):
            return

        stats = f"📊 آمار سیستم\n\n"
        stats += f"📋 تعداد نمادها: {len(self.stock_filter.symbols)}\n"
        stats += f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d')}\n"
        stats += f"🕐 ساعت: {datetime.now().strftime('%H:%M:%S')}\n"

        if self.stock_filter.initial_data:
            stats += f"✅ داده پایه: موجود ({len(self.stock_filter.initial_data)} نماد)\n"
        else:
            stats += "⚠️ داده پایه: موجود نیست\n"

        excel_file = self.stock_filter.excel_manager.filename
        if os.path.exists(excel_file):
            file_size = os.path.getsize(excel_file) / 1024  # KB
            stats += f"📁 فایل Excel: {file_size:.1f} KB\n"
        else:
            stats += "📁 فایل Excel: موجود نیست\n"

        await update.message.reply_text(stats)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت خطاها"""
        print(f"Error: {context.error}")

        if update and update.message:
            await update.message.reply_text(
                "❌ خطایی رخ داد. لطفا دوباره تلاش کنید."
            )

    def run(self):
        """راه‌اندازی ربات"""
        self.app = Application.builder().token(self.bot_token).build()

        # اضافه کردن handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("scan", self.scan))
        self.app.add_handler(CommandHandler("filter", self.filter_command))
        self.app.add_handler(CommandHandler("excel", self.excel_command))
        self.app.add_handler(CommandHandler("reset", self.reset_command))
        self.app.add_handler(CommandHandler("symbols", self.symbols_command))
        self.app.add_handler(CommandHandler("search", self.search_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))

        # Error handler
        self.app.add_error_handler(self.error_handler)

        print("🤖 ربات شروع به کار کرد...")
        print(f"📊 تعداد نمادهای تحت پوشش: {len(self.stock_filter.symbols)}")

        if self.authorized_users:
            print(f"🔐 کاربران مجاز: {self.authorized_users}")
        else:
            print("⚠️  هشدار: همه کاربران مجاز هستند!")

        # شروع polling
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    bot = BourseBot()
    bot.run()
