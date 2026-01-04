#!/usr/bin/env python3
"""
ربات تلگرام برای فیلتر نمادهای بورس
"""

import os
import asyncio
from datetime import datetime
from typing import List, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.error import BadRequest, TimedOut
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import jdatetime

from stock_filter import StockFilter
from find_symbol import search_symbol as find_symbol_code
from chart_generator import ChartGenerator
import io
import sys


class BourseBot:
    """کلاس ربات تلگرام برای فیلتر نمادهای بورس"""

    # States برای ConversationHandler
    WAITING_ADD_SYMBOL = 1
    WAITING_REMOVE_SYMBOL = 2
    WAITING_CUSTOM_FILTER_PARAMS = 3

    def __init__(self):
        load_dotenv()

        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN در فایل .env یافت نشد")

        # لیست کاربران مجاز
        authorized = os.getenv('AUTHORIZED_USERS', '')
        self.authorized_users = [int(uid.strip()) for uid in authorized.split(',') if uid.strip()]

        self.stock_filter = StockFilter()
        self.chart_generator = ChartGenerator()
        self.app = None

        # Scheduler برای اسکن اتوماتیک
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Tehran'))
        self.auto_scan_enabled = False

    def is_authorized(self, user_id: int) -> bool:
        """بررسی مجاز بودن کاربر"""
        if not self.authorized_users:
            return True  # اگر لیست خالی باشد، همه مجاز هستند
        return user_id in self.authorized_users

    def get_main_keyboard(self) -> InlineKeyboardMarkup:
        """ساخت کیبورد اصلی"""
        # دکمه اتوماتیک بر اساس وضعیت
        if self.auto_scan_enabled:
            auto_button = InlineKeyboardButton("⏸ توقف اتوماتیک", callback_data="stop_auto")
        else:
            auto_button = InlineKeyboardButton("▶️ شروع اتوماتیک", callback_data="start_auto")

        keyboard = [
            [
                InlineKeyboardButton("🔍 اسکن", callback_data="scan"),
                InlineKeyboardButton("📊 فیلتر", callback_data="filter"),
            ],
            [
                InlineKeyboardButton("📑 Excel", callback_data="excel"),
                InlineKeyboardButton("📋 نمادها", callback_data="symbols"),
            ],
            [
                auto_button,
            ],
            [
                InlineKeyboardButton("✏️ مدیریت نمادها", callback_data="manage_symbols"),
            ],
            [
                InlineKeyboardButton("📈 آمار", callback_data="stats"),
                InlineKeyboardButton("🔄 ریست", callback_data="reset"),
            ],
            [
                InlineKeyboardButton("❓ راهنما", callback_data="help"),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_manage_symbols_keyboard(self) -> InlineKeyboardMarkup:
        """ساخت کیبورد مدیریت نمادها"""
        keyboard = [
            [
                InlineKeyboardButton("➕ اضافه کردن", callback_data="add_symbol"),
                InlineKeyboardButton("➖ حذف", callback_data="remove_symbol"),
            ],
            [
                InlineKeyboardButton("📋 لیست نمادها", callback_data="list_symbols"),
            ],
            [
                InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main"),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_filter_menu_keyboard(self) -> InlineKeyboardMarkup:
        """ساخت کیبورد انتخاب نوع فیلتر"""
        keyboard = [
            [
                InlineKeyboardButton("📈 فیلتر تغییر قدرت پول", callback_data="filter_power_change"),
            ],
            [
                InlineKeyboardButton("💰 فیلتر ورود پول", callback_data="filter_money_flow"),
            ],
            [
                InlineKeyboardButton("📈 رشد مثبت (شیب ملایم)", callback_data="filter_positive_gentle"),
            ],
            [
                InlineKeyboardButton("🚀 رشد قوی +10% (شیب رو به بالا)", callback_data="filter_significant"),
            ],
            [
                InlineKeyboardButton("📊 همه رشدها (فیلتر ساده)", callback_data="filter_all_growth"),
            ],
            [
                InlineKeyboardButton("📉 نمودار برترین‌ها", callback_data="chart_top"),
            ],
            [
                InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main"),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        user_id = update.effective_user.id

        if not self.is_authorized(user_id):
            await update.message.reply_text(
                "❌ شما مجاز به استفاده از این ربات نیستید.\n"
                f"User ID شما: {user_id}"
            )
            return

        welcome_text = """🤖 ربات فیلتر نمادهای بورس

✅ اسکن نمادها و محاسبه قدرت خریدار
✅ فیلتر نمادهای با رشد قدرت خریدار
✅ دریافت فایل Excel با تمام داده‌ها

یک گزینه را انتخاب کنید:"""

        await update.message.reply_text(
            welcome_text,
            reply_markup=self.get_main_keyboard()
        )

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

📅 /scandate تاریخ
اسکن داده‌های تاریخی (روزهای گذشته)
مثال: /scandate 2025-12-30

📈 /stats
نمایش آمار کلی نمادها

💡 نکات:
- اولین اسکن روز مبنای مقایسه قرار میگیره
- برای نتیجه بهتر، اول صبح یه بار اسکن کن
- فایل Excel روزانه ذخیره میشه
- با /scandate می‌تونی روزهای قبل رو بررسی کنی
        """

        await update.message.reply_text(help_text)

    async def scan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /scan - اسکن نمادها"""
        if not self.is_authorized(update.effective_user.id):
            return

        # چک کردن حالت
        process_all = len(self.stock_filter.symbols) == 0
        try:
            import json
            with open('symbols.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                process_all = config.get('process_all', False) or process_all
        except:
            pass

        if process_all:
            msg = await update.message.reply_text(
                "⏳ در حال اسکن همه نمادها...\n"
                "📊 تعداد: 1369 نماد (کل بازار)\n\n"
                "⚠️ این ممکن است 1-2 دقیقه طول بکشد\n"
                "لطفا صبور باشید..."
            )
        else:
            msg = await update.message.reply_text(
                "⏳ در حال اسکن نمادها...\n"
                f"📋 تعداد نمادها: {len(self.stock_filter.symbols)}\n"
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

        # چک کردن حالت "همه نمادها"
        if len(symbols) == 0:
            # بررسی اینکه process_all فعال است یا نه
            try:
                import json
                with open('symbols.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if config.get('process_all', False):
                        result = "⚙️ حالت: پردازش همه نمادها\n\n"
                        result += "📊 تعداد: 1369 نماد (کل بازار)\n\n"
                        result += "ℹ️ در این حالت، تمام نمادهای بورس پردازش می‌شوند.\n\n"
                        result += "برای تغییر به حالت نمادهای خاص:\n"
                        result += "1. فایل symbols.json را ویرایش کنید\n"
                        result += '2. "process_all": false قرار دهید\n'
                        result += "3. لیست نمادهای دلخواه را اضافه کنید"
                        await update.message.reply_text(result)
                        return
            except:
                pass

            result = "⚠️ لیست نمادها خالی است!\n\n"
            result += "برای افزودن نماد:\n"
            result += "1. از /search برای پیدا کردن ticker استفاده کنید\n"
            result += "2. فایل symbols.json را ویرایش کنید"
            await update.message.reply_text(result)
            return

        result = f"📋 نمادهای انتخاب شده ({len(symbols)} نماد):\n\n"

        # نمایش حداکثر 50 نماد اول
        for i, symbol in enumerate(symbols[:50], 1):
            result += f"{i}. {symbol.get('name', 'نامشخص')} ({symbol.get('ticker', '')})\n"

        if len(symbols) > 50:
            result += f"\n... و {len(symbols) - 50} نماد دیگر"

        result += "\n\nℹ️ برای پردازش همه نمادها:"
        result += "\ncp symbols_all.json symbols.json"

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

    async def scandate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /scandate - اسکن برای تاریخ خاص"""
        if not self.is_authorized(update.effective_user.id):
            return

        if not context.args:
            await update.message.reply_text(
                "❌ لطفا تاریخ را وارد کنید.\n"
                "📅 فرمت: YYYY-MM-DD\n\n"
                "مثال:\n"
                "/scandate 2025-12-30\n"
                "/scandate 2025-12-25"
            )
            return

        date = context.args[0]

        # بررسی فرمت تاریخ
        import re
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
            await update.message.reply_text(
                "❌ فرمت تاریخ اشتباه است!\n"
                "📅 فرمت صحیح: YYYY-MM-DD\n\n"
                "مثال: /scandate 2025-12-30"
            )
            return

        msg = await update.message.reply_text(
            f"📅 در حال اسکن داده‌های تاریخ {date}...\n"
            "⏱ لطفا صبر کنید..."
        )

        try:
            # اجرای اسکن با تاریخ
            data = self.stock_filter.fetch_and_calculate(force_refresh=True, date=date)

            if not data:
                await msg.edit_text(
                    f"❌ خطا در دریافت داده‌های تاریخ {date}\n\n"
                    "احتمالاً:\n"
                    "• API این تاریخ را پشتیبانی نمی‌کند\n"
                    "• تاریخ تعطیل بورس بوده\n"
                    "• API Key معتبر نیست"
                )
                return

            # ذخیره در Excel
            # نام فایل با تاریخ
            original_filename = self.stock_filter.excel_manager.filename
            date_filename = original_filename.replace(
                datetime.now().strftime('%Y-%m-%d'),
                date
            )
            self.stock_filter.excel_manager.filename = date_filename
            self.stock_filter.excel_manager.save_data(data)
            self.stock_filter.excel_manager.filename = original_filename  # بازگشت به نام اصلی

            # مرتب‌سازی
            data_sorted = sorted(data, key=lambda x: x.get('قدرت_خریدار', 0), reverse=True)
            top_5 = data_sorted[:5]

            result = f"✅ اسکن تاریخ {date} انجام شد\n\n"
            result += f"📊 تعداد: {len(data)} نماد\n\n"
            result += "🔝 5 نماد برتر:\n\n"

            for i, item in enumerate(top_5, 1):
                result += f"{i}. {item['نماد']}\n"
                result += f"   💪 {item['قدرت_خریدار']}\n"
                result += f"   💰 {item['ورود_پول_خالص_میلیون']:,.0f} م\n\n"

            result += f"\n📁 فایل Excel ذخیره شد:\n{os.path.basename(date_filename)}"

            await msg.edit_text(result)

            # ارسال فایل
            if os.path.exists(date_filename):
                await update.message.reply_document(
                    document=open(date_filename, 'rb'),
                    filename=os.path.basename(date_filename),
                    caption=f"📊 گزارش {date}"
                )

        except Exception as e:
            await msg.edit_text(f"❌ خطا: {str(e)}")

    async def scanshamsi_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /scanshamsi - اسکن با تاریخ شمسی"""
        if not self.is_authorized(update.effective_user.id):
            return

        if not context.args:
            await update.message.reply_text(
                "❌ لطفا تاریخ شمسی را وارد کنید.\n"
                "📅 فرمت: YYYY/MM/DD یا YYYY-MM-DD\n\n"
                "مثال:\n"
                "/scanshamsi 1404/10/10\n"
                "/scanshamsi 1404-10-10"
            )
            return

        shamsi_date = context.args[0]

        # تبدیل / به - برای سازگاری
        shamsi_date = shamsi_date.replace('/', '-')

        # بررسی فرمت
        import re
        if not re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', shamsi_date):
            await update.message.reply_text(
                "❌ فرمت تاریخ اشتباه است!\n"
                "📅 فرمت صحیح: YYYY/MM/DD\n\n"
                "مثال: /scanshamsi 1404/10/10"
            )
            return

        try:
            # تجزیه تاریخ شمسی
            parts = shamsi_date.split('-')
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])

            # تبدیل به میلادی
            jdate = jdatetime.date(year, month, day)
            gregorian_date = jdate.togregorian()
            miladi_str = gregorian_date.strftime('%Y-%m-%d')

            msg = await update.message.reply_text(
                f"📅 تاریخ شمسی: {year}/{month}/{day}\n"
                f"📅 تاریخ میلادی: {miladi_str}\n\n"
                f"⏱ در حال اسکن..."
            )

            # اجرای اسکن
            data = self.stock_filter.fetch_and_calculate(force_refresh=True, date=miladi_str)

            if not data:
                await msg.edit_text(
                    f"❌ خطا در دریافت داده‌های {year}/{month}/{day}\n\n"
                    "احتمالاً:\n"
                    "• API این تاریخ را پشتیبانی نمی‌کند\n"
                    "• تاریخ تعطیل بورس بوده\n"
                    "• تاریخ در آینده است"
                )
                return

            # ذخیره در Excel
            original_filename = self.stock_filter.excel_manager.filename
            date_filename = original_filename.replace(
                datetime.now().strftime('%Y-%m-%d'),
                f"{year}-{month:02d}-{day:02d}_shamsi"
            )
            self.stock_filter.excel_manager.filename = date_filename
            self.stock_filter.excel_manager.save_data(data)
            self.stock_filter.excel_manager.filename = original_filename

            # مرتب‌سازی
            data_sorted = sorted(data, key=lambda x: x.get('قدرت_خریدار', 0), reverse=True)
            top_5 = data_sorted[:5]

            result = f"✅ اسکن تاریخ {year}/{month}/{day} انجام شد\n"
            result += f"📅 میلادی: {miladi_str}\n\n"
            result += f"📊 تعداد: {len(data)} نماد\n\n"
            result += "🔝 5 نماد برتر:\n\n"

            for i, item in enumerate(top_5, 1):
                result += f"{i}. {item['نماد']}\n"
                result += f"   💪 {item['قدرت_خریدار']}\n"
                result += f"   💰 {item['ورود_پول_خالص_میلیون']:,.0f} م\n\n"

            result += f"\n📁 فایل Excel ذخیره شد"

            await msg.edit_text(result)

            # ارسال فایل
            if os.path.exists(date_filename):
                await update.message.reply_document(
                    document=open(date_filename, 'rb'),
                    filename=os.path.basename(date_filename),
                    caption=f"📊 گزارش {year}/{month}/{day}"
                )

        except ValueError as e:
            await update.message.reply_text(
                f"❌ تاریخ نامعتبر: {shamsi_date}\n\n"
                "لطفا تاریخ صحیح وارد کنید.\n"
                "مثال: /scanshamsi 1404/10/10"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ خطا: {str(e)}")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /stats - نمایش آمار"""
        if not self.is_authorized(update.effective_user.id):
            return

        # چک کردن حالت همه نمادها
        process_all = len(self.stock_filter.symbols) == 0
        try:
            import json
            with open('symbols.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                process_all = config.get('process_all', False) or process_all
        except:
            pass

        stats = f"📊 آمار سیستم\n\n"

        if process_all:
            stats += f"⚙️ حالت: پردازش همه نمادها\n"
            stats += f"📋 تعداد: 1369 نماد (کل بازار)\n"
        else:
            stats += f"⚙️ حالت: نمادهای انتخاب شده\n"
            stats += f"📋 تعداد: {len(self.stock_filter.symbols)} نماد\n"

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

    async def auto_scan_job(self):
        """اسکن اتوماتیک (هر 5 دقیقه)"""
        try:
            current_time = datetime.now()
            print(f"🔄 اسکن اتوماتیک - {current_time.strftime('%H:%M:%S')}")

            # اجرای اسکن
            data = self.stock_filter.fetch_and_calculate()

            if data:
                # اولین اسکن روز رو ذخیره کن (برای baseline)
                if not self.stock_filter.initial_data:
                    time_key = current_time.strftime('%H:%M')
                    data_dict = {item['کد']: item for item in data}

                    # ذخیره در historical_records
                    self.stock_filter.historical_records[time_key] = data_dict

                    # ذخیره برای backward compatibility
                    self.stock_filter.initial_data = data_dict

                    print(f"✅ داده پایه ذخیره شد - {len(data)} نماد (زمان: {time_key})")

                # ذخیره در Excel (فایل قبلی پاک میشه)
                self.stock_filter.excel_manager.save_data(data)
                print(f"✅ Excel ذخیره شد - {len(data)} نماد")
            else:
                print("❌ خطا در اسکن اتوماتیک")

        except Exception as e:
            print(f"❌ خطا در اسکن اتوماتیک: {e}")

    def start_auto_scan(self):
        """شروع اسکن اتوماتیک"""
        if self.auto_scan_enabled:
            return "⚠️ اسکن اتوماتیک قبلاً فعال شده"

        # ساعات کاری بورس: شنبه تا چهارشنبه 9:00-12:30
        # هر 5 دقیقه
        # روزها: sat=5, sun=6, mon=0, tue=1, wed=2
        trigger = CronTrigger(
            day_of_week='sat,sun,mon,tue,wed',  # شنبه تا چهارشنبه
            hour='9-12',
            minute='*/5',
            timezone=pytz.timezone('Asia/Tehran')
        )

        self.scheduler.add_job(
            self.auto_scan_job,
            trigger,
            id='auto_scan',
            replace_existing=True
        )

        if not self.scheduler.running:
            self.scheduler.start()

        self.auto_scan_enabled = True

        # محاسبه زمان بعدی اسکن
        now = datetime.now(pytz.timezone('Asia/Tehran'))
        next_run = None

        # پیدا کردن بعدی زمان 5 دقیقه‌ای در بازه 9-12
        current_minute = now.minute
        next_minute = ((current_minute // 5) + 1) * 5

        if 9 <= now.hour < 12 or (now.hour == 12 and now.minute < 30):
            # اگر الان توی ساعات کاری هستیم
            if next_minute >= 60:
                next_run_time = now.replace(hour=now.hour + 1, minute=next_minute - 60, second=0)
            else:
                next_run_time = now.replace(minute=next_minute, second=0)

            if next_run_time.hour <= 12 and not (next_run_time.hour == 12 and next_run_time.minute > 30):
                next_run = next_run_time.strftime('%H:%M')

        msg = "✅ اسکن اتوماتیک فعال شد\n\n"
        msg += "⏰ برنامه: هر 5 دقیقه\n"
        msg += "📅 روزها: شنبه تا چهارشنبه\n"
        msg += "🕐 ساعات: 9:00 - 12:30\n"

        if next_run:
            msg += f"\n⏭ اسکن بعدی: {next_run}"
        else:
            msg += "\n💡 اسکن بعدی در ساعات کاری بورس انجام می‌شود"

        return msg

    def stop_auto_scan(self):
        """توقف اسکن اتوماتیک"""
        if not self.auto_scan_enabled:
            return "⚠️ اسکن اتوماتیک فعال نیست"

        try:
            self.scheduler.remove_job('auto_scan')
        except:
            pass

        self.auto_scan_enabled = False
        return "⏸ اسکن اتوماتیک متوقف شد"

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت کلیک روی دکمه‌های inline"""
        query = update.callback_query
        await query.answer()  # پاسخ به callback query

        if not self.is_authorized(query.from_user.id):
            await query.edit_message_text("❌ شما مجاز به استفاده از این ربات نیستید")
            return

        action = query.data

        # مسیریابی به متد مناسب
        if action == "scan":
            await self.scan_callback(query, context)
        elif action == "filter":
            await self.filter_callback(query, context)
        elif action == "excel":
            await self.excel_callback(query, context)
        elif action == "symbols":
            await self.symbols_callback(query, context)
        elif action == "stats":
            await self.stats_callback(query, context)
        elif action == "reset":
            await self.reset_callback(query, context)
        elif action == "help":
            await self.help_callback(query, context)
        elif action == "start_auto":
            # شروع اسکن اتوماتیک
            msg = self.start_auto_scan()
            await query.edit_message_text(msg, reply_markup=self.get_main_keyboard())
        elif action == "stop_auto":
            # توقف اسکن اتوماتیک
            msg = self.stop_auto_scan()
            await query.edit_message_text(msg, reply_markup=self.get_main_keyboard())
        elif action == "manage_symbols":
            # مدیریت نمادها
            await self.manage_symbols_callback(query, context)
        elif action == "add_symbol":
            # اضافه کردن نماد
            await self.add_symbol_callback(query, context)
        elif action == "remove_symbol":
            # حذف نماد
            await self.remove_symbol_callback(query, context)
        elif action.startswith("delete_"):
            # تایید حذف نماد
            ticker = action.replace("delete_", "")
            await self.confirm_remove_symbol(query, context, ticker)
        elif action == "list_symbols":
            # لیست نمادها
            await self.list_symbols_callback(query, context)
        elif action == "filter_positive_gentle":
            # فیلتر رشد مثبت با شیب ملایم
            await self.apply_filter(query, context, 'positive_gentle')
        elif action == "filter_significant":
            # فیلتر رشد قوی +10%
            await self.apply_filter(query, context, 'significant_upward')
        elif action == "filter_all_growth":
            # فیلتر ساده همه رشدها
            await self.apply_filter(query, context, 'all_growth')
        elif action == "filter_power_change":
            # فیلتر تغییر قدرت پول
            await self.power_change_filter_callback(query, context)
        elif action == "filter_money_flow":
            # فیلتر ورود پول
            await self.money_flow_filter_callback(query, context)
        elif action == "chart_top":
            # نمودار برترین نمادها
            await self.chart_top_callback(query, context)
        elif action == "back_to_main":
            # بازگشت به منوی اصلی
            await query.edit_message_text(
                "🤖 منوی اصلی\n\nیک گزینه را انتخاب کنید:",
                reply_markup=self.get_main_keyboard()
            )
        elif action == "menu":
            # بازگشت به منوی اصلی
            await query.edit_message_text(
                "🤖 منوی اصلی\n\nیک گزینه را انتخاب کنید:",
                reply_markup=self.get_main_keyboard()
            )

    def get_back_button(self) -> InlineKeyboardMarkup:
        """دکمه بازگشت به منو"""
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منو", callback_data="menu")]]
        return InlineKeyboardMarkup(keyboard)

    async def scan_callback(self, query, context):
        """اسکن نمادها از طریق callback"""
        # چک کردن حالت
        process_all = len(self.stock_filter.symbols) == 0
        try:
            import json
            with open('symbols.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                process_all = config.get('process_all', False) or process_all
        except:
            pass

        if process_all:
            await query.edit_message_text(
                "⏳ در حال اسکن همه نمادها...\n"
                "📊 1369 نماد (کل بازار)\n\n"
                "⏱ لطفا صبر کنید..."
            )
        else:
            await query.edit_message_text(
                f"⏳ در حال اسکن {len(self.stock_filter.symbols)} نماد...\n\n"
                "⏱ لطفا صبر کنید..."
            )

        try:
            # تعیین اینکه آیا اولین اسکن روز است یا نه
            is_first_scan = not self.stock_filter.initial_data

            # اجرای اسکن
            data = self.stock_filter.fetch_and_calculate()

            if not data:
                await query.edit_message_text(
                    "❌ خطا در دریافت داده‌ها",
                    reply_markup=self.get_back_button()
                )
                return

            # ذخیره داده‌های اولیه در صورت نیاز
            if is_first_scan:
                current_time = datetime.now().strftime('%H:%M')
                data_dict = {item['کد']: item for item in data}

                # ذخیره در historical_records
                self.stock_filter.historical_records[current_time] = data_dict

                # ذخیره برای backward compatibility
                self.stock_filter.initial_data = data_dict

                status = f"✅ اسکن اول روز انجام شد (زمان: {current_time})"
            else:
                status = "✅ اسکن انجام شد"

            # ذخیره در Excel
            self.stock_filter.excel_manager.save_data(data)

            # مرتب‌سازی بر اساس قدرت خریدار
            data_sorted = sorted(data, key=lambda x: x.get('قدرت_خریدار', 0), reverse=True)

            # نمایش 5 نماد برتر
            top_5 = data_sorted[:5]

            result = f"{status}\n\n"
            result += f"🕐 {datetime.now().strftime('%H:%M:%S')}\n"
            result += f"📊 تعداد: {len(data)} نماد\n\n"
            result += "🔝 5 نماد برتر:\n\n"

            for i, item in enumerate(top_5, 1):
                result += f"{i}. {item['نماد']}\n"
                result += f"   💪 {item['قدرت_خریدار']}\n"
                result += f"   💰 {item['ورود_پول_خالص_میلیون']:,.0f} م\n\n"

            await query.edit_message_text(result, reply_markup=self.get_back_button())

        except Exception as e:
            await query.edit_message_text(
                f"❌ خطا: {str(e)}",
                reply_markup=self.get_back_button()
            )

    async def filter_callback(self, query, context):
        """نمایش منوی انتخاب نوع فیلتر"""
        if not self.stock_filter.initial_data:
            await query.edit_message_text(
                "⚠️ هنوز اسکن اولیه انجام نشده\n\n"
                "ابتدا گزینه 'اسکن' را بزنید",
                reply_markup=self.get_back_button()
            )
            return

        # نمایش منوی انتخاب فیلتر
        history_count = len(self.stock_filter.history)
        text = "📊 انتخاب نوع فیلتر\n\n"

        if history_count >= 3:
            text += f"✅ داده کافی برای شیب ({history_count} snapshot)\n\n"
        else:
            text += f"⚠️ برای شیب دقیق‌تر، {3 - history_count} اسکن دیگر نیاز است\n\n"

        text += "🔹 رشد مثبت: نمادهایی با رشد >0 و روند مثبت\n"
        text += "🔹 رشد قوی: نمادهایی با رشد >10% و شیب تند به بالا\n"
        text += "🔹 همه رشدها: فیلتر ساده بدون بررسی شیب\n"

        await query.edit_message_text(text, reply_markup=self.get_filter_menu_keyboard())

    async def apply_filter(self, query, context, filter_type: str):
        """اعمال فیلتر بر اساس نوع انتخاب شده"""
        await query.edit_message_text("🔍 در حال فیلتر...")

        try:
            # دریافت داده‌های فعلی
            current_data = self.stock_filter.fetch_and_calculate()

            if not current_data:
                await query.edit_message_text(
                    "❌ خطا در دریافت داده‌ها",
                    reply_markup=self.get_back_button()
                )
                return

            # فیلتر کردن بر اساس نوع
            if filter_type == 'positive_gentle':
                filtered = self.stock_filter.filter_with_slope(current_data, 'positive_gentle')
                title = "📈 رشد مثبت (شیب ملایم)"
            elif filter_type == 'significant_upward':
                filtered = self.stock_filter.filter_with_slope(current_data, 'significant_upward')
                title = "🚀 رشد قوی +10%"
            else:  # all_growth
                filtered = self.stock_filter.filter_by_growth(current_data)
                title = "📊 همه رشدها"

            if not filtered:
                await query.edit_message_text(
                    f"📭 هیچ نمادی در فیلتر '{title}' پیدا نشد",
                    reply_markup=self.get_filter_menu_keyboard()
                )
                return

            # ذخیره در شیت جداگانه
            self.stock_filter.excel_manager.create_summary_sheet(filtered)

            result = f"{title}\n"
            result += f"🎯 {len(filtered)} نماد فیلتر شده\n"
            result += f"🕐 {datetime.now().strftime('%H:%M:%S')}\n\n"

            for i, item in enumerate(filtered[:10], 1):
                result += f"{i}. {item['نماد']}\n"
                result += f"   📈 رشد: {item['رشد_قدرت_خریدار_درصد']:.1f}%\n"
                result += f"   💰 ورود پول: {item['ورود_پول_خالص_میلیون']:,.0f} م\n"
                if 'شیب' in item and item['شیب'] != 0:
                    slope_emoji = "📈" if item['شیب'] > 0 else "📉"
                    result += f"   {slope_emoji} شیب: {item['شیب']:.4f}\n"
                result += "\n"

            if len(filtered) > 10:
                result += f"و {len(filtered) - 10} نماد دیگر..."

            await query.edit_message_text(result, reply_markup=self.get_back_button())

        except Exception as e:
            await query.edit_message_text(
                f"❌ خطا: {str(e)}",
                reply_markup=self.get_back_button()
            )

    async def chart_top_callback(self, query, context):
        """ارسال نمودار برترین نمادها"""
        history = self.stock_filter.history

        if len(history) < 2:
            await query.edit_message_text(
                "⚠️ داده کافی برای نمودار نیست\n\n"
                f"تعداد اسکن‌ها: {len(history)}\n"
                "حداقل 2 اسکن نیاز است\n\n"
                "لطفا چند بار اسکن کنید یا auto-scan را فعال کنید",
                reply_markup=self.get_filter_menu_keyboard()
            )
            return

        await query.edit_message_text("📊 در حال ساخت نمودار...")

        try:
            # ساخت نمودار برترین‌ها
            chart_bytes = self.chart_generator.generate_top_symbols_chart(history, top_n=10)

            if not chart_bytes:
                await query.edit_message_text(
                    "❌ خطا در ساخت نمودار",
                    reply_markup=self.get_filter_menu_keyboard()
                )
                return

            # حذف پیام قبلی
            await query.message.delete()

            # ارسال نمودار
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=io.BytesIO(chart_bytes),
                caption=f"📊 نمودار 10 نماد برتر\n"
                        f"🕐 {datetime.now().strftime('%H:%M:%S')}\n"
                        f"📈 بر اساس {len(history)} اسکن",
                reply_markup=self.get_filter_menu_keyboard()
            )

        except Exception as e:
            await query.edit_message_text(
                f"❌ خطا در ساخت نمودار: {str(e)}",
                reply_markup=self.get_filter_menu_keyboard()
            )

    async def power_change_filter_callback(self, query, context):
        """شروع فیلتر تغییر قدرت پول - دریافت پارامتر"""
        baseline_data = self.stock_filter.get_baseline_record()

        if not baseline_data:
            await query.edit_message_text(
                "⚠️ هنوز اسکن اولیه انجام نشده\n\n"
                "ابتدا گزینه 'اسکن' را بزنید",
                reply_markup=self.get_back_button()
            )
            return

        context.user_data['waiting_for'] = 'power_change_param'

        text = """📈 فیلتر تغییر قدرت پول

لطفا حداقل درصد تغییر قدرت را وارد کنید:

مثال:
15
(یعنی: نمادهایی که قدرت خریدارشان نسبت به صبح حداقل 15% افزایش داشته)

💡 توضیح:
• مبنای مقایسه: رکورد ساعت 9:05 صبح (یا نزدیک‌ترین رکورد موجود)
• فقط نمادهایی نشان داده می‌شوند که تغییر قدرتشان بیشتر از این مقدار باشد

برای لغو: /cancel"""

        await query.edit_message_text(text)

    async def money_flow_filter_callback(self, query, context):
        """شروع فیلتر ورود پول - دریافت پارامتر"""
        baseline_data = self.stock_filter.get_baseline_record()

        if not baseline_data:
            await query.edit_message_text(
                "⚠️ هنوز اسکن اولیه انجام نشده\n\n"
                "ابتدا گزینه 'اسکن' را بزنید",
                reply_markup=self.get_back_button()
            )
            return

        context.user_data['waiting_for'] = 'money_flow_param'

        text = """💰 فیلتر ورود پول

لطفا حداقل ورود پول را وارد کنید (میلیون تومان):

مثال:
500
(یعنی: نمادهایی که ورود پول خالصشان حداقل 500 میلیون تومان باشد)

💡 توضیح:
• مبنای مقایسه: رکورد ساعت 9:05 صبح (یا نزدیک‌ترین رکورد موجود)
• فقط نمادهایی نشان داده می‌شوند که ورود پولشان بیشتر از این مقدار باشد

برای لغو: /cancel"""

        await query.edit_message_text(text)

    async def apply_power_change_filter(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                         min_power_change: float):
        """اعمال فیلتر تغییر قدرت پول"""
        await update.message.reply_text("🔍 در حال فیلتر بر اساس تغییر قدرت پول...")

        try:
            # دریافت داده‌های فعلی
            current_data = self.stock_filter.fetch_and_calculate()

            if not current_data:
                await update.message.reply_text(
                    "❌ خطا در دریافت داده‌ها",
                    reply_markup=self.get_main_keyboard()
                )
                return

            baseline_data = self.stock_filter.get_baseline_record()

            if not baseline_data:
                await update.message.reply_text(
                    "⚠️ داده اولیه موجود نیست",
                    reply_markup=self.get_main_keyboard()
                )
                return

            # فیلتر کردن
            filtered = []
            for current in current_data:
                symbol_code = current['کد']
                initial = baseline_data.get(symbol_code)

                if initial:
                    initial_power = initial.get('قدرت_خریدار', 0)
                    current_power = current.get('قدرت_خریدار', 0)

                    # محاسبه درصد تغییر
                    if initial_power > 0:
                        power_change = ((current_power - initial_power) / initial_power) * 100
                    else:
                        power_change = 0

                    # اعمال فیلتر
                    if power_change >= min_power_change:
                        current['تغییر_قدرت_خریدار_درصد'] = power_change
                        current['قدرت_خریدار_اولیه'] = initial_power
                        filtered.append(current)

            if not filtered:
                await update.message.reply_text(
                    f"📭 هیچ نمادی با تغییر قدرت بیش از {min_power_change}% پیدا نشد",
                    reply_markup=self.get_main_keyboard()
                )
                return

            # مرتب‌سازی بر اساس تغییر قدرت
            filtered.sort(key=lambda x: x['تغییر_قدرت_خریدار_درصد'], reverse=True)

            # ذخیره در Excel
            self.stock_filter.excel_manager.create_summary_sheet(filtered)

            # نمایش نتایج
            result = f"📈 فیلتر تغییر قدرت پول\n\n"
            result += f"📊 شرط: تغییر قدرت >{min_power_change}%\n"
            result += f"🎯 {len(filtered)} نماد فیلتر شده\n"
            result += f"🕐 {datetime.now().strftime('%H:%M:%S')}\n\n"

            for i, item in enumerate(filtered[:10], 1):
                result += f"{i}. {item['نماد']}\n"
                result += f"   📈 تغییر قدرت: {item['تغییر_قدرت_خریدار_درصد']:.1f}%\n"
                result += f"   💪 قدرت صبح: {item['قدرت_خریدار_اولیه']:.2f}\n"
                result += f"   💪 قدرت الان: {item['قدرت_خریدار']:.2f}\n"
                result += f"   💰 ورود پول: {item['ورود_پول_خالص_میلیون']:,.0f} م\n\n"

            if len(filtered) > 10:
                result += f"و {len(filtered) - 10} نماد دیگر..."

            await update.message.reply_text(result, reply_markup=self.get_main_keyboard())

        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا: {str(e)}",
                reply_markup=self.get_main_keyboard()
            )

    async def apply_money_flow_filter(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                       min_money_flow: float):
        """اعمال فیلتر ورود پول"""
        await update.message.reply_text("🔍 در حال فیلتر بر اساس ورود پول...")

        try:
            # دریافت داده‌های فعلی
            current_data = self.stock_filter.fetch_and_calculate()

            if not current_data:
                await update.message.reply_text(
                    "❌ خطا در دریافت داده‌ها",
                    reply_markup=self.get_main_keyboard()
                )
                return

            baseline_data = self.stock_filter.get_baseline_record()

            if not baseline_data:
                await update.message.reply_text(
                    "⚠️ داده اولیه موجود نیست",
                    reply_markup=self.get_main_keyboard()
                )
                return

            # فیلتر کردن
            filtered = []
            for current in current_data:
                symbol_code = current['کد']
                initial = baseline_data.get(symbol_code)
                money_flow = current.get('ورود_پول_خالص_میلیون', 0)

                if initial and money_flow >= min_money_flow:
                    initial_power = initial.get('قدرت_خریدار', 0)
                    current_power = current.get('قدرت_خریدار', 0)

                    # محاسبه درصد تغییر برای نمایش
                    if initial_power > 0:
                        power_change = ((current_power - initial_power) / initial_power) * 100
                    else:
                        power_change = 0

                    current['تغییر_قدرت_خریدار_درصد'] = power_change
                    current['قدرت_خریدار_اولیه'] = initial_power
                    filtered.append(current)

            if not filtered:
                await update.message.reply_text(
                    f"📭 هیچ نمادی با ورود پول بیش از {min_money_flow:,.0f} میلیون پیدا نشد",
                    reply_markup=self.get_main_keyboard()
                )
                return

            # مرتب‌سازی بر اساس ورود پول
            filtered.sort(key=lambda x: x['ورود_پول_خالص_میلیون'], reverse=True)

            # ذخیره در Excel
            self.stock_filter.excel_manager.create_summary_sheet(filtered)

            # نمایش نتایج
            result = f"💰 فیلتر ورود پول\n\n"
            result += f"📊 شرط: ورود پول >{min_money_flow:,.0f} م\n"
            result += f"🎯 {len(filtered)} نماد فیلتر شده\n"
            result += f"🕐 {datetime.now().strftime('%H:%M:%S')}\n\n"

            for i, item in enumerate(filtered[:10], 1):
                result += f"{i}. {item['نماد']}\n"
                result += f"   💰 ورود پول: {item['ورود_پول_خالص_میلیون']:,.0f} م\n"
                result += f"   📈 تغییر قدرت: {item['تغییر_قدرت_خریدار_درصد']:.1f}%\n"
                result += f"   💪 قدرت صبح: {item['قدرت_خریدار_اولیه']:.2f}\n"
                result += f"   💪 قدرت الان: {item['قدرت_خریدار']:.2f}\n\n"

            if len(filtered) > 10:
                result += f"و {len(filtered) - 10} نماد دیگر..."

            await update.message.reply_text(result, reply_markup=self.get_main_keyboard())

        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا: {str(e)}",
                reply_markup=self.get_main_keyboard()
            )

    async def excel_callback(self, query, context):
        """ارسال فایل Excel"""
        excel_file = self.stock_filter.excel_manager.filename

        if not os.path.exists(excel_file):
            await query.edit_message_text(
                "❌ فایل Excel موجود نیست\n\n"
                "ابتدا 'اسکن' را بزنید",
                reply_markup=self.get_back_button()
            )
            return

        await query.edit_message_text("📤 در حال ارسال...")

        try:
            # ارسال فایل
            await query.message.reply_document(
                document=open(excel_file, 'rb'),
                filename=os.path.basename(excel_file),
                caption=f"📊 گزارش - {datetime.now().strftime('%Y-%m-%d')}"
            )

            await query.edit_message_text(
                "✅ فایل ارسال شد",
                reply_markup=self.get_back_button()
            )

        except Exception as e:
            await query.edit_message_text(
                f"❌ خطا: {str(e)}",
                reply_markup=self.get_back_button()
            )

    async def symbols_callback(self, query, context):
        """نمایش نمادها"""
        symbols = self.stock_filter.symbols

        # چک کردن حالت "همه نمادها"
        if len(symbols) == 0:
            try:
                import json
                with open('symbols.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if config.get('process_all', False):
                        result = "⚙️ حالت: همه نمادها\n\n"
                        result += "📊 1369 نماد (کل بازار)"
                        await query.edit_message_text(result, reply_markup=self.get_back_button())
                        return
            except:
                pass

            result = "⚠️ لیست نمادها خالی است"
            await query.edit_message_text(result, reply_markup=self.get_back_button())
            return

        result = f"📋 {len(symbols)} نماد انتخاب شده\n\n"

        # نمایش 20 نماد اول
        for i, symbol in enumerate(symbols[:20], 1):
            result += f"{i}. {symbol.get('ticker', '')}\n"

        if len(symbols) > 20:
            result += f"\n... و {len(symbols) - 20} نماد دیگر"

        await query.edit_message_text(result, reply_markup=self.get_back_button())

    async def stats_callback(self, query, context):
        """نمایش آمار"""
        # چک کردن حالت
        process_all = len(self.stock_filter.symbols) == 0
        try:
            import json
            with open('symbols.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                process_all = config.get('process_all', False) or process_all
        except:
            pass

        stats = f"📊 آمار سیستم\n\n"

        if process_all:
            stats += f"⚙️ حالت: همه نمادها\n"
            stats += f"📋 تعداد: 1369 نماد\n"
        else:
            stats += f"⚙️ حالت: انتخابی\n"
            stats += f"📋 تعداد: {len(self.stock_filter.symbols)}\n"

        stats += f"🕐 {datetime.now().strftime('%H:%M:%S')}\n"

        if self.stock_filter.initial_data:
            stats += f"✅ داده پایه: {len(self.stock_filter.initial_data)}\n"
        else:
            stats += "⚠️ داده پایه: ندارد\n"

        excel_file = self.stock_filter.excel_manager.filename
        if os.path.exists(excel_file):
            file_size = os.path.getsize(excel_file) / 1024
            stats += f"📁 Excel: {file_size:.1f} KB"
        else:
            stats += "📁 Excel: ندارد"

        await query.edit_message_text(stats, reply_markup=self.get_back_button())

    async def reset_callback(self, query, context):
        """ریست داده‌ها"""
        self.stock_filter.initial_data = {}

        await query.edit_message_text(
            "🔄 داده‌های پایه پاک شد\n\n"
            "اسکن بعدی مبنای جدید خواهد بود",
            reply_markup=self.get_back_button()
        )

    async def help_callback(self, query, context):
        """راهنما"""
        help_text = """📖 راهنمای ربات

🔍 اسکن: محاسبه قدرت خریدار
📊 فیلتر: نمادهای با رشد +10%
📑 Excel: دریافت فایل کامل
📋 نمادها: لیست نمادها
📈 آمار: وضعیت سیستم
🔄 ریست: پاک کردن داده پایه

💡 نکته: اولین اسکن روز مبنای مقایسه است"""

        await query.edit_message_text(help_text, reply_markup=self.get_back_button())

    # متدهای مدیریت نمادها
    async def manage_symbols_callback(self, query, context):
        """نمایش منوی مدیریت نمادها"""
        symbols = self.stock_filter.get_symbols()
        text = f"✏️ مدیریت نمادها\n\n"
        text += f"📊 تعداد نمادها: {len(symbols)}\n\n"
        text += "یک گزینه را انتخاب کنید:"

        await query.edit_message_text(text, reply_markup=self.get_manage_symbols_keyboard())

    async def add_symbol_callback(self, query, context):
        """شروع فرایند اضافه کردن نماد"""
        # ابتدا لیست نمادها رو بگیر
        await query.edit_message_text("🔍 در حال دریافت لیست نمادها...")

        try:
            # از همون API که برای اسکن استفاده می‌کنیم
            all_symbols = self.stock_filter.api_client.get_all_symbols()

            if not all_symbols:
                await query.edit_message_text(
                    "❌ خطا در دریافت لیست نمادها\n\nلطفا دوباره تلاش کنید",
                    reply_markup=self.get_manage_symbols_keyboard()
                )
                return

            # ذخیره در context برای استفاده بعدی
            context.user_data['all_symbols_cache'] = all_symbols
            context.user_data['waiting_for'] = 'add_symbol'

            text = f"""➕ اضافه کردن نماد جدید

✅ {len(all_symbols)} نماد آماده است

لطفا نماد (ticker) را دقیق ارسال کنید:

مثال:
وبملت
شپنا
کگل

برای لغو، /cancel را ارسال کنید."""

            await query.edit_message_text(text)

        except Exception as e:
            await query.edit_message_text(
                f"❌ خطا در دریافت لیست نمادها\n\n{str(e)}",
                reply_markup=self.get_manage_symbols_keyboard()
            )

    async def remove_symbol_callback(self, query, context):
        """نمایش لیست نمادها برای حذف"""
        symbols = self.stock_filter.get_symbols()

        if not symbols:
            await query.edit_message_text(
                "❌ هیچ نمادی برای حذف وجود ندارد",
                reply_markup=self.get_manage_symbols_keyboard()
            )
            return

        # ساخت کیبورد با دکمه‌های حذف
        keyboard = []
        for symbol in symbols:
            ticker = symbol.get('ticker', '')
            name = symbol.get('name', '')
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ {ticker} - {name[:30]}",
                    callback_data=f"delete_{ticker}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="manage_symbols")
        ])

        await query.edit_message_text(
            "➖ حذف نماد\n\nیک نماد را برای حذف انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def confirm_remove_symbol(self, query, context, ticker: str):
        """تایید و اجرای حذف نماد"""
        success = self.stock_filter.remove_symbol(ticker)

        if success:
            text = f"✅ نماد {ticker} با موفقیت حذف شد"
        else:
            text = f"❌ خطا در حذف نماد {ticker}"

        # بازگشت به منوی مدیریت نمادها
        symbols = self.stock_filter.get_symbols()
        text += f"\n\n📊 تعداد نمادها: {len(symbols)}"

        await query.edit_message_text(text, reply_markup=self.get_manage_symbols_keyboard())

    async def list_symbols_callback(self, query, context):
        """نمایش لیست کامل نمادها"""
        symbols = self.stock_filter.get_symbols()

        if not symbols:
            text = "❌ هیچ نمادی تعریف نشده است"
        else:
            text = f"📋 لیست نمادها ({len(symbols)} نماد):\n\n"
            for i, symbol in enumerate(symbols, 1):
                ticker = symbol.get('ticker', 'N/A')
                name = symbol.get('name', 'N/A')
                text += f"{i}. {ticker} - {name}\n"

        await query.edit_message_text(text, reply_markup=self.get_manage_symbols_keyboard())

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت پیام‌های متنی (برای اضافه کردن نماد)"""
        if not self.is_authorized(update.effective_user.id):
            return

        # چک کردن آیا در حال انتظار برای ورودی هستیم
        waiting_for = context.user_data.get('waiting_for')

        if waiting_for == 'add_symbol':
            text = update.message.text.strip()

            if not text:
                await update.message.reply_text("❌ نماد نمی‌تواند خالی باشد")
                return

            # چک کن اگر فرمت manual (نام | ticker) استفاده شده
            if '|' in text:
                parts = text.split('|')
                if len(parts) == 2:
                    name = parts[0].strip()
                    ticker = parts[1].strip()

                    if name and ticker:
                        success = self.stock_filter.add_symbol(name, ticker)

                        if success:
                            symbols = self.stock_filter.get_symbols()
                            await update.message.reply_text(
                                f"✅ نماد اضافه شد\n\n"
                                f"📌 نماد: {ticker}\n"
                                f"📄 نام: {name}\n\n"
                                f"📊 تعداد کل نمادها: {len(symbols)}",
                                reply_markup=self.get_main_keyboard()
                            )
                        else:
                            await update.message.reply_text(
                                f"❌ نماد {ticker} قبلا وجود دارد",
                                reply_markup=self.get_main_keyboard()
                            )

                        context.user_data.pop('waiting_for', None)
                        return

            # جستجو در cache (از BrsApi data)
            ticker_search = text.strip()  # حفظ حروف کوچک و بزرگ برای جستجو
            all_symbols = context.user_data.get('all_symbols_cache', [])

            if not all_symbols:
                await update.message.reply_text(
                    "❌ لیست نمادها موجود نیست\n\nلطفا دوباره تلاش کنید",
                    reply_markup=self.get_main_keyboard()
                )
                context.user_data.pop('waiting_for', None)
                return

            # جستجوی exact match (case-insensitive)
            found = None
            for symbol in all_symbols:
                # l18 = ticker, l30 = name
                symbol_ticker = symbol.get('l18', '').strip()
                if symbol_ticker == ticker_search:
                    found = symbol
                    break

            if found:
                # نماد پیدا شد!
                name = found.get('l30', ticker_search)
                found_ticker = found.get('l18', ticker_search)

                # اضافه کردن نماد
                success = self.stock_filter.add_symbol(name, found_ticker)

                if success:
                    symbols = self.stock_filter.get_symbols()
                    await update.message.reply_text(
                        f"✅ نماد اضافه شد\n\n"
                        f"📌 نماد: {found_ticker}\n"
                        f"📄 نام: {name}\n\n"
                        f"📊 تعداد کل نمادها: {len(symbols)}",
                        reply_markup=self.get_main_keyboard()
                    )
                else:
                    await update.message.reply_text(
                        f"❌ نماد {found_ticker} قبلا وجود دارد",
                        reply_markup=self.get_main_keyboard()
                    )
            else:
                # جستجوی نمادهای مشابه
                similar = []
                ticker_upper = ticker_search.upper()
                for symbol in all_symbols:
                    symbol_ticker = symbol.get('l18', '').strip()
                    symbol_name = symbol.get('l30', '').strip()
                    # جستجو در ticker یا name
                    if (ticker_upper in symbol_ticker.upper() or
                        ticker_upper in symbol_name.upper()):
                        similar.append(symbol)
                        if len(similar) >= 10:  # حداکثر 10 نماد مشابه
                            break

                if similar:
                    msg = f"❌ نماد '{text}' دقیق پیدا نشد\n\n"
                    msg += "📋 نمادهای مشابه:\n\n"
                    for s in similar:
                        msg += f"• {s.get('l18', 'N/A')} - {s.get('l30', 'N/A')[:35]}\n"
                    msg += "\n💡 نماد دقیق را از لیست بالا وارد کنید"
                else:
                    msg = f"❌ نماد '{text}' پیدا نشد\n\n"
                    msg += "💡 نماد دقیق را وارد کنید\n"
                    msg += "یا از فرمت manual استفاده کنید:\n"
                    msg += f"نام | {text}"

                await update.message.reply_text(
                    msg,
                    reply_markup=self.get_main_keyboard()
                )

            # پاک کردن state
            context.user_data.pop('waiting_for', None)

        elif waiting_for == 'power_change_param':
            text = update.message.text.strip()

            try:
                min_power_change = float(text)

                # Clear state
                context.user_data.pop('waiting_for', None)

                # Apply filter
                await self.apply_power_change_filter(update, context, min_power_change)

            except ValueError:
                await update.message.reply_text(
                    "❌ لطفا فقط عدد وارد کنید\n\n"
                    "مثال: 15"
                )

        elif waiting_for == 'money_flow_param':
            text = update.message.text.strip()

            try:
                min_money_flow = float(text)

                # Clear state
                context.user_data.pop('waiting_for', None)

                # Apply filter
                await self.apply_money_flow_filter(update, context, min_money_flow)

            except ValueError:
                await update.message.reply_text(
                    "❌ لطفا فقط عدد وارد کنید\n\n"
                    "مثال: 500"
                )

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لغو عملیات جاری"""
        context.user_data.pop('waiting_for', None)
        await update.message.reply_text(
            "✅ عملیات لغو شد",
            reply_markup=self.get_main_keyboard()
        )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت خطاها"""
        print(f"Error: {context.error}")

        # Skip certain errors
        if isinstance(context.error, BadRequest):
            if "Message is not modified" in str(context.error):
                # پیام تغییری نکرده، نادیده بگیر
                return
            if "Query is too old" in str(context.error):
                # کوئری خیلی قدیمیه، نادیده بگیر
                return

        # Handle other errors
        try:
            if update and update.callback_query:
                try:
                    await update.callback_query.answer("❌ خطایی رخ داد", show_alert=True)
                except:
                    pass
            elif update and update.message:
                await update.message.reply_text(
                    "❌ خطایی رخ داد. لطفا دوباره تلاش کنید."
                )
        except Exception as e:
            print(f"Error in error handler: {e}")

    async def setup_bot_commands(self):
        """ثبت کامندها در منوی تلگرام"""
        commands = [
            BotCommand("start", "شروع و نمایش منوی اصلی"),
            BotCommand("help", "راهنمای استفاده از ربات"),
            BotCommand("scan", "اسکن و فیلتر نمادها"),
            BotCommand("filter", "نمایش نمادهای فیلتر شده"),
            BotCommand("excel", "دریافت فایل اکسل"),
            BotCommand("symbols", "لیست نمادهای تحت پوشش"),
            BotCommand("search", "جستجوی نماد (مثال: /search وبملت)"),
            BotCommand("scandate", "اسکن تاریخی با تاریخ میلادی (مثال: /scandate 2024-12-20)"),
            BotCommand("scanshamsi", "اسکن تاریخی با تاریخ شمسی (مثال: /scanshamsi 1403-09-29)"),
            BotCommand("stats", "نمایش آمار"),
            BotCommand("reset", "ریست داده‌ها"),
            BotCommand("cancel", "لغو عملیات جاری"),
        ]
        await self.app.bot.set_my_commands(commands)

    def run(self):
        """راه‌اندازی ربات"""
        self.app = Application.builder().token(self.bot_token).build()

        # اضافه کردن handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("scan", self.scan))
        self.app.add_handler(CommandHandler("filter", self.filter_command))
        self.app.add_handler(CommandHandler("excel", self.excel_command))
        self.app.add_handler(CommandHandler("reset", self.reset_command))
        self.app.add_handler(CommandHandler("symbols", self.symbols_command))
        self.app.add_handler(CommandHandler("search", self.search_command))
        self.app.add_handler(CommandHandler("scandate", self.scandate_command))
        self.app.add_handler(CommandHandler("scanshamsi", self.scanshamsi_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        self.app.add_handler(CommandHandler("cancel", self.cancel_command))

        # Handler برای پیام‌های متنی (برای اضافه کردن نماد)
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))

        # Error handler
        self.app.add_error_handler(self.error_handler)

        print("🤖 ربات شروع به کار کرد...")
        print(f"📊 تعداد نمادهای تحت پوشش: {len(self.stock_filter.symbols)}")

        if self.authorized_users:
            print(f"🔐 کاربران مجاز: {self.authorized_users}")
        else:
            print("⚠️  هشدار: همه کاربران مجاز هستند!")

        # ثبت کامندها در منوی تلگرام
        asyncio.get_event_loop().run_until_complete(self.setup_bot_commands())
        print("✅ کامندها در منوی تلگرام ثبت شدند")

        # شروع خودکار اسکن اتوماتیک
        self.start_auto_scan()
        print("✅ اسکن اتوماتیک فعال شد (هر 5 دقیقه در ساعات بورس)")

        # شروع polling
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    bot = BourseBot()
    bot.run()
