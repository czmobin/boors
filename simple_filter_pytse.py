#!/usr/bin/env python3
"""
فیلتر ساده بورس بدون نیاز به سرور
استفاده از کتابخانه pytse-client
"""

from pytse_client import Ticker, download_client_types_records
import pandas as pd
from datetime import datetime
import json


class SimpleBourseFilter:
    """فیلتر ساده بورس بدون سرور"""

    def __init__(self, symbols_file='symbols.json'):
        """بارگذاری نمادهای مورد نظر"""
        self.symbols = self._load_symbols(symbols_file)
        print(f"✅ {len(self.symbols)} نماد بارگذاری شد")

    def _load_symbols(self, symbols_file):
        """خواندن نمادها از فایل JSON"""
        try:
            with open(symbols_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [s['ticker'] for s in data.get('symbols', [])]
        except Exception as e:
            print(f"❌ خطا در خواندن فایل نمادها: {e}")
            return []

    def get_symbol_info(self, symbol):
        """دریافت اطلاعات یک نماد"""
        try:
            ticker = Ticker(symbol)

            # دریافت آخرین قیمت و حجم
            last_price = ticker.last_price
            closing_price = ticker.adj_close
            volume = ticker.volume

            # دریافت اطلاعات حقیقی/حقوقی
            client_types = ticker.client_types

            if client_types is not None and not client_types.empty:
                # آخرین رکورد (امروز)
                latest = client_types.iloc[-1]

                # محاسبه ورود پول حقیقی
                buy_I_Volume = latest.get('buy_I_Volume', 0)  # حجم خرید حقیقی
                sell_I_Volume = latest.get('sell_I_Volume', 0)  # حجم فروش حقیقی

                # ورود خالص پول حقیقی
                net_real_volume = buy_I_Volume - sell_I_Volume
                net_real_value = net_real_volume * last_price / 10_000_000  # به میلیون تومان

                # محاسبه قدرت خرید (درصد حقیقی)
                total_volume = buy_I_Volume + sell_I_Volume
                if total_volume > 0:
                    real_power_percent = (buy_I_Volume / total_volume) * 100
                else:
                    real_power_percent = 50.0

                return {
                    'نماد': symbol,
                    'قیمت': last_price,
                    'حجم': volume,
                    'ورود_پول_حقیقی_میلیون': round(net_real_value, 2),
                    'قدرت_خرید_حقیقی_درصد': round(real_power_percent, 2),
                    'حجم_خرید_حقیقی': buy_I_Volume,
                    'حجم_فروش_حقیقی': sell_I_Volume
                }
            else:
                return {
                    'نماد': symbol,
                    'قیمت': last_price,
                    'حجم': volume,
                    'ورود_پول_حقیقی_میلیون': 0,
                    'قدرت_خرید_حقیقی_درصد': 0,
                    'حجم_خرید_حقیقی': 0,
                    'حجم_فروش_حقیقی': 0
                }

        except Exception as e:
            print(f"❌ خطا در دریافت اطلاعات {symbol}: {e}")
            return None

    def filter_money_flow(self, min_money_flow=50):
        """
        فیلتر ورود پول
        نمادهایی که ورود پول حقیقی بالاتر از آستانه داشته‌اند

        Args:
            min_money_flow: حداقل ورود پول به میلیون تومان
        """
        print(f"\n🔍 در حال اعمال فیلتر ورود پول (حداقل {min_money_flow} میلیون تومان)...")

        results = []
        for i, symbol in enumerate(self.symbols, 1):
            print(f"[{i}/{len(self.symbols)}] در حال بررسی {symbol}...")
            info = self.get_symbol_info(symbol)

            if info and info['ورود_پول_حقیقی_میلیون'] >= min_money_flow:
                results.append(info)

        # مرتب‌سازی بر اساس ورود پول (نزولی)
        results.sort(key=lambda x: x['ورود_پول_حقیقی_میلیون'], reverse=True)

        return results

    def filter_buying_power(self, min_power_percent=55):
        """
        فیلتر قدرت خرید
        نمادهایی که قدرت خرید حقیقی بالاتر از آستانه دارند

        Args:
            min_power_percent: حداقل درصد قدرت خرید حقیقی
        """
        print(f"\n🔍 در حال اعمال فیلتر قدرت خرید (حداقل {min_power_percent}%)...")

        results = []
        for i, symbol in enumerate(self.symbols, 1):
            print(f"[{i}/{len(self.symbols)}] در حال بررسی {symbol}...")
            info = self.get_symbol_info(symbol)

            if info and info['قدرت_خرید_حقیقی_درصد'] >= min_power_percent:
                results.append(info)

        # مرتب‌سازی بر اساس قدرت خرید (نزولی)
        results.sort(key=lambda x: x['قدرت_خرید_حقیقی_درصد'], reverse=True)

        return results

    def print_results(self, results, filter_name="فیلتر"):
        """چاپ نتایج فیلتر"""
        print(f"\n{'='*80}")
        print(f"📊 نتایج {filter_name}")
        print(f"{'='*80}")

        if not results:
            print("❌ نمادی یافت نشد!")
            return

        print(f"✅ تعداد نمادهای یافت شده: {len(results)}\n")

        for i, item in enumerate(results, 1):
            print(f"{i}. {item['نماد']:10s} | "
                  f"قیمت: {item['قیمت']:>10,.0f} | "
                  f"ورود پول: {item['ورود_پول_حقیقی_میلیون']:>10,.2f} م.تومان | "
                  f"قدرت خرید: {item['قدرت_خرید_حقیقی_درصد']:>6.2f}%")


def main():
    """تابع اصلی"""
    print("="*80)
    print("🚀 فیلتر ساده بورس ایران - بدون نیاز به سرور")
    print("="*80)

    # ایجاد شیء فیلتر
    filter_tool = SimpleBourseFilter()

    if not filter_tool.symbols:
        print("❌ هیچ نمادی یافت نشد. لطفا فایل symbols.json را بررسی کنید.")
        return

    # منوی انتخاب
    print("\n📋 انتخاب فیلتر:")
    print("1. فیلتر ورود پول (حقیقی)")
    print("2. فیلتر قدرت خرید (حقیقی)")
    print("3. اطلاعات تمام نمادها")

    choice = input("\nانتخاب شما (1-3): ").strip()

    if choice == "1":
        min_flow = input("حداقل ورود پول (میلیون تومان) [پیش‌فرض: 50]: ").strip()
        min_flow = float(min_flow) if min_flow else 50.0

        results = filter_tool.filter_money_flow(min_money_flow=min_flow)
        filter_tool.print_results(results, "فیلتر ورود پول")

    elif choice == "2":
        min_power = input("حداقل قدرت خرید (درصد) [پیش‌فرض: 55]: ").strip()
        min_power = float(min_power) if min_power else 55.0

        results = filter_tool.filter_buying_power(min_power_percent=min_power)
        filter_tool.print_results(results, "فیلتر قدرت خرید")

    elif choice == "3":
        print("\n🔍 در حال دریافت اطلاعات تمام نمادها...")
        results = []
        for i, symbol in enumerate(filter_tool.symbols, 1):
            print(f"[{i}/{len(filter_tool.symbols)}] {symbol}...")
            info = filter_tool.get_symbol_info(symbol)
            if info:
                results.append(info)

        filter_tool.print_results(results, "اطلاعات تمام نمادها")
    else:
        print("❌ انتخاب نامعتبر!")

    print("\n✅ اتمام عملیات")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  عملیات توسط کاربر لغو شد")
    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")
