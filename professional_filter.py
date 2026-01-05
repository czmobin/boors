#!/usr/bin/env python3
"""
سیستم فیلتر نویسی حرفه‌ای بورس ایران
مشابه سایت TSETMC و Rahavard365
"""

from pytse_client import Ticker
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import List, Dict, Callable, Optional
import os


class TechnicalIndicators:
    """محاسبه اندیکاتورهای تکنیکال"""

    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
        """
        محاسبه RSI (Relative Strength Index)

        Args:
            prices: سری قیمت‌های پایانی
            period: دوره محاسبه (پیش‌فرض 14)

        Returns:
            مقدار RSI (0-100)
        """
        if len(prices) < period + 1:
            return 50.0

        # محاسبه تغییرات
        delta = prices.diff()

        # جدا کردن سود و زیان
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # میانگین سود و زیان
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # محاسبه RS و RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else 50.0

    @staticmethod
    def calculate_mfi(ticker_obj, period: int = 14) -> float:
        """
        محاسبه MFI (Money Flow Index)

        Args:
            ticker_obj: شیء Ticker
            period: دوره محاسبه

        Returns:
            مقدار MFI (0-100)
        """
        try:
            history = ticker_obj.history
            if history is None or len(history) < period + 1:
                return 50.0

            # قیمت معمولی (Typical Price)
            tp = (history['high'] + history['low'] + history['close']) / 3

            # جریان پول خام (Raw Money Flow)
            rmf = tp * history['volume']

            # تغییرات قیمت معمولی
            tp_change = tp.diff()

            # جریان پول مثبت و منفی
            positive_flow = rmf.where(tp_change > 0, 0).rolling(window=period).sum()
            negative_flow = rmf.where(tp_change < 0, 0).rolling(window=period).sum()

            # نسبت جریان پول
            mfr = positive_flow / negative_flow

            # MFI
            mfi = 100 - (100 / (1 + mfr))

            return round(mfi.iloc[-1], 2) if not pd.isna(mfi.iloc[-1]) else 50.0

        except Exception as e:
            return 50.0


class StockData:
    """کلاس برای نگهداری و محاسبه داده‌های سهام"""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.ticker = None
        self.data = {}
        self._fetch_data()

    def _fetch_data(self):
        """دریافت تمام داده‌های مورد نیاز"""
        try:
            self.ticker = Ticker(self.symbol)

            # اطلاعات پایه
            self.data['نماد'] = self.symbol
            self.data['قیمت_پایانی'] = self.ticker.adj_close
            self.data['قیمت_آخرین'] = self.ticker.last_price
            self.data['حجم'] = self.ticker.volume
            self.data['ارزش'] = self.ticker.value
            self.data['تعداد_معاملات'] = getattr(self.ticker, 'count', 0)

            # محاسبه تغییر درصد
            if hasattr(self.ticker, 'yesterday_price') and self.ticker.yesterday_price > 0:
                self.data['تغییر_درصد'] = round(
                    ((self.data['قیمت_پایانی'] - self.ticker.yesterday_price) /
                     self.ticker.yesterday_price) * 100,
                    2
                )
            else:
                self.data['تغییر_درصد'] = 0.0

            # P/E و EPS
            self.data['pe'] = getattr(self.ticker, 'p_e_ratio', 0) or 0
            self.data['eps'] = getattr(self.ticker, 'eps', 0) or 0

            # حجم مبنا
            self.data['حجم_مبنا'] = getattr(self.ticker, 'base_volume', 0) or 0

            # نسبت حجم به حجم مبنا
            if self.data['حجم_مبنا'] > 0:
                self.data['نسبت_حجم_به_مبنا'] = round(
                    self.data['حجم'] / self.data['حجم_مبنا'],
                    2
                )
            else:
                self.data['نسبت_حجم_به_مبنا'] = 0

            # داده‌های حقیقی/حقوقی
            self._fetch_client_types()

            # محاسبه اندیکاتورها
            self._calculate_indicators()

        except Exception as e:
            print(f"❌ خطا در دریافت داده‌های {self.symbol}: {e}")

    def _fetch_client_types(self):
        """دریافت اطلاعات حقیقی/حقوقی"""
        try:
            client_types = self.ticker.client_types

            if client_types is not None and not client_types.empty:
                latest = client_types.iloc[-1]

                # حجم‌ها
                buy_I = latest.get('buy_I_Volume', 0)
                sell_I = latest.get('sell_I_Volume', 0)
                buy_N = latest.get('buy_N_Volume', 0)
                sell_N = latest.get('sell_N_Volume', 0)

                self.data['خرید_حقیقی'] = buy_I
                self.data['فروش_حقیقی'] = sell_I
                self.data['خرید_حقوقی'] = buy_N
                self.data['فروش_حقوقی'] = sell_N

                # خالص
                self.data['خالص_حقیقی'] = buy_I - sell_I
                self.data['خالص_حقوقی'] = buy_N - sell_N

                # ورود پول (میلیون تومان)
                price = self.data['قیمت_آخرین']
                self.data['ورود_پول_حقیقی'] = round(
                    (buy_I - sell_I) * price / 10_000_000,
                    2
                )
                self.data['ورود_پول_حقوقی'] = round(
                    (buy_N - sell_N) * price / 10_000_000,
                    2
                )

                # قدرت خرید (درصد)
                total_I = buy_I + sell_I
                total_N = buy_N + sell_N

                self.data['قدرت_حقیقی'] = round(
                    (buy_I / total_I * 100) if total_I > 0 else 50.0,
                    2
                )
                self.data['قدرت_حقوقی'] = round(
                    (buy_N / total_N * 100) if total_N > 0 else 50.0,
                    2
                )

            else:
                # مقادیر پیش‌فرض
                for key in ['خرید_حقیقی', 'فروش_حقیقی', 'خرید_حقوقی', 'فروش_حقوقی',
                            'خالص_حقیقی', 'خالص_حقوقی', 'ورود_پول_حقیقی',
                            'ورود_پول_حقوقی', 'قدرت_حقیقی', 'قدرت_حقوقی']:
                    self.data[key] = 0

        except Exception as e:
            print(f"⚠️  خطا در دریافت داده‌های حقیقی/حقوقی {self.symbol}: {e}")

    def _calculate_indicators(self):
        """محاسبه اندیکاتورهای تکنیکال"""
        try:
            history = self.ticker.history
            if history is not None and not history.empty:
                # RSI
                self.data['rsi'] = TechnicalIndicators.calculate_rsi(
                    history['close'],
                    period=14
                )

                # MFI
                self.data['mfi'] = TechnicalIndicators.calculate_mfi(
                    self.ticker,
                    period=14
                )
            else:
                self.data['rsi'] = 50.0
                self.data['mfi'] = 50.0

        except Exception as e:
            self.data['rsi'] = 50.0
            self.data['mfi'] = 50.0


class FilterEngine:
    """موتور فیلتر نویسی حرفه‌ای"""

    def __init__(self, symbols_file: str = 'symbols.json'):
        self.symbols = self._load_symbols(symbols_file)
        self.stocks_data: List[StockData] = []
        self.predefined_filters = self._create_predefined_filters()

    def _load_symbols(self, symbols_file: str) -> List[str]:
        """بارگذاری نمادها"""
        try:
            with open(symbols_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [s['ticker'] for s in data.get('symbols', [])]
        except Exception as e:
            print(f"❌ خطا در خواندن فایل نمادها: {e}")
            return []

    def scan_all(self):
        """اسکن تمام نمادها"""
        print(f"\n🔍 در حال اسکن {len(self.symbols)} نماد...")

        self.stocks_data = []
        for i, symbol in enumerate(self.symbols, 1):
            print(f"[{i}/{len(self.symbols)}] {symbol}...")
            stock = StockData(symbol)
            if stock.data:
                self.stocks_data.append(stock)

        print(f"✅ اسکن {len(self.stocks_data)} نماد کامل شد")

    def _create_predefined_filters(self) -> Dict[str, Dict]:
        """ایجاد فیلترهای از پیش تعریف شده"""
        return {
            '1': {
                'name': 'ورود پول حقیقی بالا',
                'description': 'نمادهایی با ورود پول حقیقی بالاتر از 50 میلیون تومان',
                'condition': lambda data: data['ورود_پول_حقیقی'] >= 50
            },
            '2': {
                'name': 'قدرت خرید حقیقی',
                'description': 'نمادهایی با قدرت خرید حقیقی بالاتر از 60%',
                'condition': lambda data: data['قدرت_حقیقی'] >= 60
            },
            '3': {
                'name': 'RSI اشباع فروش',
                'description': 'نمادهایی با RSI کمتر از 30 (اشباع فروش)',
                'condition': lambda data: data['rsi'] < 30
            },
            '4': {
                'name': 'RSI اشباع خرید',
                'description': 'نمادهایی با RSI بالاتر از 70 (اشباع خرید)',
                'condition': lambda data: data['rsi'] > 70
            },
            '5': {
                'name': 'P/E کمتر از 10',
                'description': 'نمادهایی با نسبت P/E کمتر از 10 (ارزان)',
                'condition': lambda data: 0 < data['pe'] < 10
            },
            '6': {
                'name': 'حجم بالای مبنا',
                'description': 'نمادهایی با حجم بیش از 2 برابر حجم مبنا',
                'condition': lambda data: data['نسبت_حجم_به_مبنا'] > 2
            },
            '7': {
                'name': 'رشد قیمت بالا',
                'description': 'نمادهایی با رشد قیمت بیش از 3%',
                'condition': lambda data: data['تغییر_درصد'] > 3
            },
            '8': {
                'name': 'خروج حقوقی',
                'description': 'نمادهایی که حقوقی‌ها در حال فروش هستند',
                'condition': lambda data: data['ورود_پول_حقوقی'] < -20
            },
            '9': {
                'name': 'ورود پول هوشمند',
                'description': 'ورود حقیقی + خروج حقوقی (پول هوشمند)',
                'condition': lambda data: (data['ورود_پول_حقیقی'] > 30 and
                                          data['ورود_پول_حقوقی'] < 0)
            },
            '10': {
                'name': 'MFI میانه',
                'description': 'نمادهایی با MFI بین 40 تا 60',
                'condition': lambda data: 40 <= data['mfi'] <= 60
            },
            '11': {
                'name': 'حجم مشکوک',
                'description': 'حجم بیش از 5 برابر مبنا + تغییر قیمت کم',
                'condition': lambda data: (data['نسبت_حجم_به_مبنا'] > 5 and
                                          abs(data['تغییر_درصد']) < 1)
            },
            '12': {
                'name': 'سهام ارزان با رشد',
                'description': 'P/E < 8 + رشد قیمت > 2%',
                'condition': lambda data: (0 < data['pe'] < 8 and
                                          data['تغییر_درصد'] > 2)
            }
        }

    def apply_predefined_filter(self, filter_id: str) -> List[Dict]:
        """اعمال فیلتر از پیش تعریف شده"""
        if filter_id not in self.predefined_filters:
            print(f"❌ فیلتر {filter_id} یافت نشد")
            return []

        filter_info = self.predefined_filters[filter_id]
        condition = filter_info['condition']

        results = []
        for stock in self.stocks_data:
            try:
                if condition(stock.data):
                    results.append(stock.data)
            except Exception as e:
                continue

        return results

    def apply_custom_filter(self, condition_func: Callable) -> List[Dict]:
        """
        اعمال فیلتر سفارشی

        Args:
            condition_func: تابع شرط (lambda یا تابع عادی)

        مثال:
            lambda data: data['pe'] < 10 and data['ورود_پول_حقیقی'] > 100
        """
        results = []
        for stock in self.stocks_data:
            try:
                if condition_func(stock.data):
                    results.append(stock.data)
            except Exception as e:
                continue

        return results

    def print_filter_menu(self):
        """نمایش منوی فیلترها"""
        print("\n" + "="*80)
        print("📋 فیلترهای از پیش تعریف شده:")
        print("="*80)

        for filter_id, filter_info in self.predefined_filters.items():
            print(f"{filter_id:>2}. {filter_info['name']:<30} - {filter_info['description']}")

    def print_results(self, results: List[Dict], filter_name: str = "فیلتر"):
        """نمایش نتایج"""
        print(f"\n{'='*100}")
        print(f"📊 نتایج {filter_name}")
        print(f"{'='*100}")

        if not results:
            print("❌ نمادی یافت نشد!")
            return

        print(f"✅ تعداد نمادهای یافت شده: {len(results)}\n")

        # نمایش جدول
        print(f"{'ردیف':<5} {'نماد':<10} {'قیمت':<12} {'تغییر%':<10} "
              f"{'RSI':<8} {'P/E':<8} {'ورود پول':<15} {'قدرت حقیقی':<12}")
        print("-" * 100)

        for i, item in enumerate(results, 1):
            print(f"{i:<5} {item['نماد']:<10} "
                  f"{item['قیمت_پایانی']:>10,.0f}  "
                  f"{item['تغییر_درصد']:>8.2f}%  "
                  f"{item['rsi']:>6.2f}  "
                  f"{item['pe']:>6.2f}  "
                  f"{item['ورود_پول_حقیقی']:>12,.2f}  "
                  f"{item['قدرت_حقیقی']:>10.2f}%")

    def save_filter(self, name: str, condition_code: str, description: str = ""):
        """ذخیره فیلتر سفارشی"""
        filters_file = 'my_filters.json'

        # بارگذاری فیلترهای موجود
        if os.path.exists(filters_file):
            with open(filters_file, 'r', encoding='utf-8') as f:
                filters = json.load(f)
        else:
            filters = {}

        # اضافه کردن فیلتر جدید
        filters[name] = {
            'condition': condition_code,
            'description': description,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # ذخیره
        with open(filters_file, 'w', encoding='utf-8') as f:
            json.dump(filters, f, ensure_ascii=False, indent=2)

        print(f"✅ فیلتر '{name}' ذخیره شد")

    def load_saved_filters(self) -> Dict:
        """بارگذاری فیلترهای ذخیره شده"""
        filters_file = 'my_filters.json'

        if not os.path.exists(filters_file):
            return {}

        with open(filters_file, 'r', encoding='utf-8') as f:
            return json.load(f)


def main():
    """تابع اصلی"""
    print("="*100)
    print("🚀 سیستم فیلتر نویسی حرفه‌ای بورس ایران")
    print("مشابه TSETMC و Rahavard365 - بدون نیاز به سرور")
    print("="*100)

    # ایجاد موتور فیلتر
    engine = FilterEngine()

    if not engine.symbols:
        print("❌ هیچ نمادی یافت نشد")
        return

    # اسکن اولیه
    engine.scan_all()

    # حلقه اصلی
    while True:
        print("\n" + "="*100)
        print("📋 منوی اصلی:")
        print("="*100)
        print("1. نمایش فیلترهای آماده")
        print("2. اجرای فیلتر از پیش تعریف شده")
        print("3. اجرای فیلتر سفارشی")
        print("4. ذخیره فیلتر سفارشی")
        print("5. مشاهده فیلترهای ذخیره شده")
        print("6. اسکن مجدد")
        print("0. خروج")

        choice = input("\n➤ انتخاب شما: ").strip()

        if choice == "1":
            engine.print_filter_menu()

        elif choice == "2":
            engine.print_filter_menu()
            filter_id = input("\n➤ شماره فیلتر: ").strip()

            if filter_id in engine.predefined_filters:
                filter_info = engine.predefined_filters[filter_id]
                print(f"\n🔍 در حال اعمال فیلتر '{filter_info['name']}'...")

                results = engine.apply_predefined_filter(filter_id)
                engine.print_results(results, filter_info['name'])
            else:
                print("❌ فیلتر یافت نشد!")

        elif choice == "3":
            print("\n💡 مثال‌های فیلتر سفارشی:")
            print("1. lambda d: d['pe'] < 10 and d['rsi'] < 40")
            print("2. lambda d: d['ورود_پول_حقیقی'] > 100 and d['تغییر_درصد'] > 2")
            print("3. lambda d: d['قدرت_حقیقی'] > 65 and d['حجم'] > 1000000")

            condition_str = input("\n➤ شرط فیلتر (lambda): ").strip()

            if not condition_str:
                print("❌ شرط خالی است!")
                continue

            try:
                # ایجاد تابع lambda از رشته
                condition_func = eval(condition_str)

                print("\n🔍 در حال اعمال فیلتر سفارشی...")
                results = engine.apply_custom_filter(condition_func)
                engine.print_results(results, "فیلتر سفارشی")

                # پیشنهاد ذخیره
                save = input("\n💾 ذخیره این فیلتر؟ (y/n): ").strip().lower()
                if save == 'y':
                    name = input("نام فیلتر: ").strip()
                    desc = input("توضیحات (اختیاری): ").strip()
                    engine.save_filter(name, condition_str, desc)

            except Exception as e:
                print(f"❌ خطا در اجرای فیلتر: {e}")

        elif choice == "4":
            print("\n💡 ذخیره فیلتر سفارشی")
            name = input("نام فیلتر: ").strip()
            condition = input("شرط فیلتر (lambda): ").strip()
            desc = input("توضیحات: ").strip()

            engine.save_filter(name, condition, desc)

        elif choice == "5":
            saved = engine.load_saved_filters()

            if not saved:
                print("\n❌ هیچ فیلتر ذخیره شده‌ای وجود ندارد")
            else:
                print("\n📂 فیلترهای ذخیره شده:")
                print("="*80)
                for name, info in saved.items():
                    print(f"\n📌 {name}")
                    print(f"   توضیحات: {info.get('description', 'ندارد')}")
                    print(f"   شرط: {info['condition']}")
                    print(f"   تاریخ: {info['created_at']}")

        elif choice == "6":
            print("\n🔄 در حال اسکن مجدد...")
            engine.scan_all()

        elif choice == "0":
            print("\n👋 خداحافظ!")
            break

        else:
            print("❌ انتخاب نامعتبر!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  عملیات توسط کاربر لغو شد")
    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")
