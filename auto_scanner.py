#!/usr/bin/env python3
"""
اسکنر خودکار بورس - بدون تلگرام
هر 1 دقیقه در ساعات بورس اسکن می‌کند و در Excel ذخیره می‌کند
"""

import time
import schedule
from datetime import datetime
import pytz
from stock_filter import StockFilter


class AutoScanner:
    """اسکنر خودکار برای ذخیره داده‌های بورس در Excel"""

    def __init__(self):
        self.stock_filter = StockFilter()
        print("=" * 60)
        print("🤖 اسکنر خودکار بورس راه‌اندازی شد")
        print("=" * 60)
        print(f"📊 تعداد نمادها برای اسکن: {'همه (1369)' if not self.stock_filter.symbols else len(self.stock_filter.symbols)}")
        print(f"📋 نمادها برای Excel: {self.stock_filter.excel_manager.allowed_symbols}")
        print(f"📁 مسیر فایل Excel: {self.stock_filter.excel_manager.filename}")
        print("⏰ برنامه: هر 1 دقیقه در ساعات بورس")
        print("🕐 ساعات کاری: 9:00 - 12:30 (شنبه تا چهارشنبه)")
        print("=" * 60)

    def scan_and_save(self):
        """اجرای یک اسکن و ذخیره در Excel"""
        try:
            current_time = datetime.now()
            print(f"\n{'=' * 60}")
            print(f"🔄 شروع اسکن - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'=' * 60}")

            # اجرای اسکن با force refresh
            data = self.stock_filter.fetch_and_calculate(force_refresh=True)

            if not data:
                print("❌ خطا در دریافت داده‌ها")
                return

            # ذخیره در historical_records
            if not self.stock_filter.initial_data:
                # اولین اسکن روز
                time_key = current_time.strftime('%H:%M')
                data_dict = {item['کد']: item for item in data}
                self.stock_filter.historical_records[time_key] = data_dict
                self.stock_filter.initial_data = data_dict
                print(f"✅ داده‌های baseline ذخیره شد (زمان: {time_key})")

            # ذخیره در Excel
            self.stock_filter.excel_manager.save_data(data)

            # نمایش خلاصه
            print(f"\n📊 خلاصه اسکن:")
            print(f"  • کل نمادهای پردازش شده: {len(data)}")

            # نمادهای ذخیره شده در Excel
            saved_symbols = [item['نماد'] for item in data if item['نماد'] in self.stock_filter.excel_manager.allowed_symbols]
            if saved_symbols:
                print(f"  • نمادهای ذخیره شده در Excel: {', '.join(saved_symbols[:10])}")
                if len(saved_symbols) > 10:
                    print(f"    و {len(saved_symbols) - 10} نماد دیگر...")

            # آمار baseline
            baseline = self.stock_filter.get_baseline_record()
            if baseline:
                baseline_time = None
                for time_key, data_dict in self.stock_filter.historical_records.items():
                    if data_dict == baseline:
                        baseline_time = time_key
                        break
                if baseline_time:
                    print(f"  • زمان baseline: {baseline_time}")

            print(f"\n✅ اسکن کامل شد - {current_time.strftime('%H:%M:%S')}")
            print(f"{'=' * 60}\n")

        except Exception as e:
            print(f"❌ خطا در اسکن: {e}")
            import traceback
            traceback.print_exc()

    def is_market_open(self):
        """بررسی باز بودن بازار"""
        now = datetime.now(pytz.timezone('Asia/Tehran'))

        # روزهای کاری: شنبه تا چهارشنبه (0-4 در weekday)
        # در Python: شنبه=5, یکشنبه=6, دوشنبه=0, سه‌شنبه=1, چهارشنبه=2
        weekday = now.weekday()
        is_working_day = weekday in [5, 6, 0, 1, 2]

        # ساعات کاری: 9:00 - 12:30
        hour = now.hour
        minute = now.minute
        is_working_hours = (9 <= hour < 12) or (hour == 12 and minute <= 30)

        return is_working_day and is_working_hours

    def run_if_market_open(self):
        """اجرای اسکن فقط اگر بازار باز باشد"""
        if self.is_market_open():
            self.scan_and_save()
        else:
            now = datetime.now(pytz.timezone('Asia/Tehran'))
            print(f"⏸ بازار بسته است - {now.strftime('%Y-%m-%d %H:%M:%S')}")
            print("   (ساعات کاری: شنبه-چهارشنبه 9:00-12:30)")

    def start(self):
        """شروع اسکنر خودکار"""
        # اجرای فوری در startup
        print("\n🚀 اجرای اسکن اولیه...")
        self.run_if_market_open()

        # برنامه‌ریزی اسکن‌های بعدی
        schedule.every(1).minutes.do(self.run_if_market_open)

        print("\n✅ اسکنر خودکار فعال شد")
        print("⏰ اسکن بعدی: 1 دقیقه دیگر")
        print("\n💡 برای توقف: Ctrl+C")
        print(f"{'=' * 60}\n")

        # حلقه اصلی
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)  # چک کردن هر 30 ثانیه
        except KeyboardInterrupt:
            print("\n\n⏹ اسکنر متوقف شد")
            print("=" * 60)


def main():
    """تابع اصلی"""
    scanner = AutoScanner()
    scanner.start()


if __name__ == '__main__':
    main()
