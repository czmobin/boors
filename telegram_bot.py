#!/usr/bin/env python3
"""
ربات تلگرام برای فیلتر نمادهای بورس
"""

import os
import asyncio
from datetime import datetime
from typing import List, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

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
                InlineKeyboardButton("📈 آمار", callback_data="stats"),
                InlineKeyboardButton("🔄 ریست", callback_data="reset"),
            ],
            [
                InlineKeyboardButton("❓ راهنما", callback_data="help"),
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
            print(f"🔄 اسکن اتوماتیک - {datetime.now().strftime('%H:%M:%S')}")

            # اجرای اسکن
            data = self.stock_filter.fetch_and_calculate()

            if data:
                # اولین اسکن روز رو ذخیره کن
                if not self.stock_filter.initial_data:
                    self.stock_filter.initial_data = {item['کد']: item for item in data}
                    print(f"✅ داده پایه ذخیره شد - {len(data)} نماد")

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
        trigger = CronTrigger(
            day_of_week='sat-wed',  # شنبه تا چهارشنبه
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
        return "✅ اسکن اتوماتیک فعال شد\n\n⏰ هر 5 دقیقه (ساعات بورس: 9:00-12:30)"

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
                self.stock_filter.initial_data = {item['کد']: item for item in data}
                status = "✅ اسکن اول روز انجام شد"
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
        """فیلتر نمادها از طریق callback"""
        if not self.stock_filter.initial_data:
            await query.edit_message_text(
                "⚠️ هنوز اسکن اولیه انجام نشده\n\n"
                "ابتدا گزینه 'اسکن' را بزنید",
                reply_markup=self.get_back_button()
            )
            return

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

            # فیلتر کردن
            filtered = self.stock_filter.filter_by_growth(current_data)

            if not filtered:
                await query.edit_message_text(
                    "📭 هیچ نمادی با رشد +10% پیدا نشد",
                    reply_markup=self.get_back_button()
                )
                return

            # ذخیره در شیت جداگانه
            self.stock_filter.excel_manager.create_summary_sheet(filtered)

            result = f"🎯 {len(filtered)} نماد فیلتر شده\n"
            result += f"🕐 {datetime.now().strftime('%H:%M:%S')}\n\n"

            for i, item in enumerate(filtered[:10], 1):
                result += f"{i}. {item['نماد']}\n"
                result += f"   📈 {item['رشد_قدرت_خریدار_درصد']:.1f}%\n"
                result += f"   💰 {item['ورود_پول_خالص_میلیون']:,.0f} م\n\n"

            if len(filtered) > 10:
                result += f"و {len(filtered) - 10} نماد دیگر..."

            await query.edit_message_text(result, reply_markup=self.get_back_button())

        except Exception as e:
            await query.edit_message_text(
                f"❌ خطا: {str(e)}",
                reply_markup=self.get_back_button()
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

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت خطاها"""
        print(f"Error: {context.error}")

        if update and update.callback_query:
            await update.callback_query.edit_message_text(
                "❌ خطایی رخ داد",
                reply_markup=self.get_back_button()
            )
        elif update and update.message:
            await update.message.reply_text(
                "❌ خطایی رخ داد. لطفا دوباره تلاش کنید."
            )

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
