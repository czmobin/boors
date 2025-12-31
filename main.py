#!/usr/bin/env python3
"""
برنامه اصلی فیلتر نمادهای بورس
اجرای دوره‌ای هر 5 دقیقه
"""

import schedule
import time
import argparse
from stock_filter import StockFilter
from config import UPDATE_INTERVAL_MINUTES


def main():
    """تابع اصلی برنامه"""

    parser = argparse.ArgumentParser(description='فیلتر نمادهای بورس ایران')
    parser.add_argument(
        '--once',
        action='store_true',
        help='اجرای یک بار بدون حلقه تکرار'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=UPDATE_INTERVAL_MINUTES,
        help=f'فاصله زمانی به دقیقه (پیش‌فرض: {UPDATE_INTERVAL_MINUTES})'
    )
    parser.add_argument(
        '--symbols',
        type=str,
        default='symbols.json',
        help='آدرس فایل نمادها (پیش‌فرض: symbols.json)'
    )

    args = parser.parse_args()

    # ایجاد نمونه فیلتر
    stock_filter = StockFilter(symbols_file=args.symbols)

    if args.once:
        # اجرای یک بار
        print("اجرای یک بار...")
        stock_filter.run_once(save_as_initial=True)
    else:
        # اجرای دوره‌ای
        print(f"شروع برنامه فیلتر نمادهای بورس")
        print(f"فاصله زمانی: هر {args.interval} دقیقه")
        print(f"فایل نمادها: {args.symbols}")
        print("برای توقف برنامه Ctrl+C را فشار دهید\n")

        # اجرای اولیه و ذخیره به عنوان داده پایه
        print("اجرای اولیه و ثبت داده‌های پایه...")
        stock_filter.run_once(save_as_initial=True)

        # برنامه‌ریزی اجرای دوره‌ای
        schedule.every(args.interval).minutes.do(
            lambda: stock_filter.run_once(save_as_initial=False)
        )

        # حلقه اصلی
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)  # چک کردن هر 30 ثانیه
        except KeyboardInterrupt:
            print("\n\nبرنامه متوقف شد.")


if __name__ == '__main__':
    main()
