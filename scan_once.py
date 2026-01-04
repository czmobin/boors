#!/usr/bin/env python3
"""
اسکن یکبار - برای تست و اجرای دستی
"""

from datetime import datetime
from stock_filter import StockFilter


def main():
    """اجرای یک اسکن ساده"""
    print("=" * 60)
    print("🔍 اسکن یکباره بورس")
    print("=" * 60)

    stock_filter = StockFilter()

    print(f"\n📊 تعداد نمادها برای اسکن: {'همه (1369)' if not stock_filter.symbols else len(stock_filter.symbols)}")
    print(f"📋 نمادها برای Excel: {stock_filter.excel_manager.allowed_symbols}")
    print(f"📁 مسیر فایل Excel: {stock_filter.excel_manager.filename}")

    print("\n🔄 در حال اسکن...")
    start_time = datetime.now()

    # اجرای اسکن
    data = stock_filter.fetch_and_calculate(force_refresh=True)

    if not data:
        print("❌ خطا در دریافت داده‌ها")
        return

    # ذخیره baseline
    if not stock_filter.initial_data:
        time_key = start_time.strftime('%H:%M')
        data_dict = {item['کد']: item for item in data}
        stock_filter.historical_records[time_key] = data_dict
        stock_filter.initial_data = data_dict
        print(f"✅ داده‌های baseline ذخیره شد (زمان: {time_key})")

    # ذخیره در Excel
    stock_filter.excel_manager.save_data(data)

    # نمایش نتایج
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n{'=' * 60}")
    print(f"✅ اسکن با موفقیت انجام شد")
    print(f"{'=' * 60}")
    print(f"⏱ زمان اجرا: {duration:.2f} ثانیه")
    print(f"📊 تعداد نمادهای پردازش شده: {len(data)}")

    # نمادهای ذخیره شده در Excel
    saved_symbols = [item['نماد'] for item in data if item['نماد'] in stock_filter.excel_manager.allowed_symbols]
    if saved_symbols:
        print(f"💾 نمادهای ذخیره شده در Excel ({len(saved_symbols)}):")
        for symbol in saved_symbols:
            symbol_data = next((item for item in data if item['نماد'] == symbol), None)
            if symbol_data:
                print(f"  • {symbol}: قدرت={symbol_data.get('قدرت_خریدار', 0):.2f}, "
                      f"ورود پول={symbol_data.get('ورود_پول_خالص_میلیون', 0):,.0f}م")

    print(f"\n📁 فایل Excel: {stock_filter.excel_manager.filename}")
    print(f"{'=' * 60}\n")


if __name__ == '__main__':
    main()
